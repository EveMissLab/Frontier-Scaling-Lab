"""Arena history via official HF Parquet index and bounded local DuckDB projection.

This path avoids /filter and /search HTTP 500s on a large indexed split. It
downloads only the chosen subset/split Parquet files, then selects aggregate
leaderboard rows for exactly one model and category. No individual votes.

Optional dependency: duckdb (installed in data-acquisition workflow only).
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request

from fsl_sources.adapters import (
    ARENA_DATASET, HF_DATASETS, USER_AGENT,
    json_api_get, parse_arena_page
)
from fsl_sources.catalog import CatalogError, connect, save_snapshot
from .arena_history import filter_url

INDEX_URL = HF_DATASETS + "/parquet?dataset=" + urllib.parse.quote(ARENA_DATASET)
ALLOWED_CONFIGS = {
    "text", "text_style_control", "vision", "vision_style_control",
    "search", "search_style_control", "document", "document_style_control",
    "webdev", "agent", "agent_bash_recovery_steps", "agent_bash_reliability",
    "agent_praise_complaint", "agent_steerability",
    "agent_task_outcome_explicit", "agent_tool_hallucination",
}
MAX_FILE_BYTES = 100 * 1024 * 1024


def choose_parquet(index, *, config, split="full", max_files=3,
                   max_total_bytes=MAX_FILE_BYTES):
    if config not in ALLOWED_CONFIGS or split not in ("full", "latest"):
        raise CatalogError("unknown Arena subset/split")
    if not isinstance(index, dict) or not isinstance(index.get("parquet_files"), list):
        raise CatalogError("bad official /parquet index")
    if index.get("partial") is True:
        raise CatalogError("official Parquet index is partial, cannot claim complete history")
    matches = []
    for row in index["parquet_files"]:
        if not isinstance(row, dict):
            continue
        if row.get("config") != config or row.get("split") != split:
            continue
        url = row.get("url")
        p = urllib.parse.urlsplit(url or "")
        if (p.scheme != "https" or p.hostname != "huggingface.co" or
            "/datasets/lmarena-ai/leaderboard-dataset/" not in p.path):
            raise CatalogError("untrusted parquet file URL")
        size = row.get("size")
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise CatalogError("parquet file missing valid size")
        matches.append({"url": url, "bytes": size, "filename": row.get("filename")})
    if not matches:
        raise CatalogError("no Parquet files for requested Arena subset/split")
    if len(matches) > max_files:
        raise CatalogError("subset has too many parquet files for approved cap")
    total = sum(x["bytes"] for x in matches)
    if total > max_total_bytes:
        raise CatalogError(f"subset needs {total} bytes, exceeds approved budget")
    return matches


def _download(url, dest, declared_size):
    """Bounded HF-hosted download with SHA256; no arbitrary input URL."""
    p = urllib.parse.urlsplit(url)
    if (p.scheme != "https" or p.hostname != "huggingface.co" or
        "/datasets/lmarena-ai/leaderboard-dataset/" not in p.path):
        raise CatalogError("unapproved source URL")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    sha = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            with open(dest, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_BYTES or total > max(declared_size * 2, declared_size + 1048576):
                        raise CatalogError("download exceeds announced/absolute byte cap")
                    sha.update(chunk)
                    output.write(chunk)
    except (OSError, TimeoutError) as exc:
        raise CatalogError(f"Parquet download error: {type(exc).__name__}: {exc}") from exc
    return {"sha256": sha.hexdigest(), "downloaded_bytes": total}


def _query_parquet(files, *, config, model, category, max_rows):
    try:
        import duckdb
    except ImportError as exc:
        raise CatalogError("duckdb is required only for Parquet history ingestion") from exc
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or not 1 <= max_rows <= 500:
        raise CatalogError("max_rows must be 1..500")
    # All file paths are created inside TemporaryDirectory; DuckDB receives
    # query values as bound parameters, not SQL string interpolation.
    paths = [str(file) for file in files]
    con = duckdb.connect(database=":memory:")
    try:
        con.execute("SET threads=2")
        if config.startswith("agent"):
            cols = ("score, score_ci_lower, score_ci_upper, "
                    "observation_count")
        else:
            cols = "rating, rating_lower, rating_upper, vote_count"
        query = f"""
            SELECT model_name, category, leaderboard_publish_date, {cols}
            FROM read_parquet(?)
            WHERE model_name = ? AND category = ?
            ORDER BY leaderboard_publish_date DESC
            LIMIT ?
        """
        cur = con.execute(query, [paths, model, category, max_rows+1])
        names = [x[0] for x in cur.description]
        records = [dict(zip(names, row)) for row in cur.fetchall()]
    finally:
        con.close()
    return records[:max_rows], len(records)>max_rows


def parquet_history(db, *, config, model, category="overall", retrieved_on=None,
                    max_rows=300, fetch_index=json_api_get,
                    download=_download, query=_query_parquet):
    # Validate model/category identifiers safely before any network operation.
    filter_url(config=config, model=model, category=category)
    if config not in ALLOWED_CONFIGS:
        raise CatalogError("Arena config is not allowlisted")
    if retrieved_on is None:
        retrieved_on = date.today().isoformat()
    index = fetch_index(INDEX_URL)
    matched = choose_parquet(index, config=config, split="full")
    with tempfile.TemporaryDirectory(prefix="fsl-arena-") as td:
        paths = []
        provenance = []
        for idx, ref in enumerate(matched):
            local = Path(td) / f"part-{idx}.parquet"
            receipt = download(ref["url"], local, ref["bytes"])
            paths.append(local)
            provenance.append({"source_url":ref["url"],"size_claimed":ref["bytes"],
                               **receipt})
        records, truncated = query(paths, config=config, model=model,
                                   category=category, max_rows=max_rows)
    if not records:
        raise CatalogError("requested exact Arena model has no published history")
    items = []
    by_date = {}
    for row in records:
        day_raw = row.get("leaderboard_publish_date")
        day = str(day_raw)[:10] if day_raw is not None else None
        if not day or len(day) != 10:
            raise CatalogError("invalid historical publication date")
        if day in by_date:
            previous = by_date[day]
            if previous != row:
                raise CatalogError("conflicting same-day leaderboard rows require manual audit")
            continue
        by_date[day] = row
        row = dict(row, leaderboard_publish_date=day)
        items.append({"row_idx":len(items), "row":row})
    payload = {"rows":items,"parquet_sha256":provenance,
               "index_sha256":hashlib.sha256(json.dumps(index,sort_keys=True,
                                      ensure_ascii=False).encode("utf-8")).hexdigest()}
    prepared = parse_arena_page(payload, config=config, split="full",
                                offset=0, retrieved_on=retrieved_on)
    prepared["resource_id"] = (
        ARENA_DATASET + ":" + config + ":parquet:full:" + model + ":" + category)
    prepared["url"] = "https://huggingface.co/datasets/" + ARENA_DATASET
    prepared["note"] += ("; source Parquet SHA256 in payload hash; "
                         "only selected published aggregate rows, not raw battles")
    stored = save_snapshot(db, **prepared)
    return {
        "schema":"fsl/arena-parquet/0.4","status":"historical_retrospective",
        "config":config,"model":model,"category":category,
        "retrieved_on":retrieved_on,"rows_stored":len(items),
        "max_rows":max_rows,"truncated_by_cap":truncated,
        "parquet_files":[{"url":x["source_url"],"sha256":x["sha256"],
                           "downloaded_bytes":x["downloaded_bytes"]} for x in provenance],
        "snapshot":stored,
        "warning":"Historical rows downloaded today cannot serve as an earlier known-at-time forecast.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description="Read-only selected Arena Parquet history")
    p.add_argument("--db",default="reports/arena_parquet.sqlite")
    p.add_argument("--config",default="text_style_control")
    p.add_argument("--model",required=True)
    p.add_argument("--category",default="overall")
    p.add_argument("--max-rows",type=int,default=300)
    p.add_argument("--report")
    args=p.parse_args(argv)
    try:
        with connect(args.db) as db:
            result=parquet_history(db,config=args.config,model=args.model,
                                   category=args.category,
                                   retrieved_on=date.today().isoformat(),
                                   max_rows=args.max_rows)
        raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
        if args.report:
            Path(args.report).parent.mkdir(parents=True,exist_ok=True)
            Path(args.report).write_text(raw,encoding="utf-8")
        else:
            print(raw)
    except (CatalogError,OSError,ValueError,KeyError) as exc:
        p.exit(2,f"parquet import failed: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
