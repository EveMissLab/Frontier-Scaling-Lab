"""Bounded, filtered Arena history importer using HF Dataset Viewer /filter.

No raw battles, prompts, ratings by individual users, or personal data.
A history retrieved today is a retrospective study source, not proof that
this repository possessed those data at earlier forecast dates.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

from fsl_sources.adapters import ARENA_DATASET, HF_DATASETS, json_api_get, parse_arena_page
from fsl_sources.catalog import CatalogError, connect, save_snapshot


def filter_url(*, config, model, category="overall", offset=0, length=100):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", config):
        raise CatalogError("invalid Arena configuration identifier")
    if not isinstance(model, str) or not 1 <= len(model) <= 120:
        raise CatalogError("model_name must be 1..120 characters")
    if any(ord(c) < 32 for c in model):
        raise CatalogError("model_name contains control character")
    if not isinstance(category, str) or not re.fullmatch(r"[A-Za-z0-9_ /.-]{1,80}", category):
        raise CatalogError("invalid Arena category")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise CatalogError("offset must be a nonnegative integer")
    if isinstance(length, bool) or not isinstance(length, int) or not 1 <= length <= 100:
        raise CatalogError("length must be 1..100")
    # SQL single-quoted string literal escaping, not executable SQL.
    safe_model = model.replace("'", "''")
    safe_cat = category.replace("'", "''")
    where = f'"model_name"=\'{safe_model}\' AND "category"=\'{safe_cat}\''
    return HF_DATASETS + "/filter?" + urlencode({
        "dataset": ARENA_DATASET, "config": config, "split": "full",
        "where": where, "orderby": '"leaderboard_publish_date" DESC',
        "offset": offset, "length": length,
    })


def import_history(db, *, config, model, category="overall", retrieved_on=None,
                   page_size=100, max_pages=3, fetch=json_api_get):
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 10:
        raise CatalogError("max_pages must be 1..10")
    if retrieved_on is None:
        retrieved_on = date.today().isoformat()
    results, total_rows, truncated = [], None, False
    for page in range(max_pages):
        offset = page * page_size
        url = filter_url(config=config, model=model, category=category,
                         offset=offset, length=page_size)
        data = fetch(url)
        if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
            raise CatalogError("Arena /filter response missing rows")
        if data.get("partial") is True:
            raise CatalogError("Arena /filter index is partial: do not treat as exhaustive history")
        if total_rows is None:
            n = data.get("num_rows_total")
            total_rows = n if isinstance(n, int) and n >= 0 else None
        for item in data["rows"]:
            row = item.get("row") if isinstance(item, dict) else None
            if not isinstance(row, dict):
                raise CatalogError("malformed Arena history row")
            if row.get("model_name") != model or row.get("category") != category:
                raise CatalogError("filtered API returned a mismatched model or category")
        prepared = parse_arena_page(
            data, config=config, split="full", offset=offset,
            retrieved_on=retrieved_on)
        prepared["resource_id"] = (
            ARENA_DATASET + ":" + config + ":full:filter:" +
            model + ":" + category + ":" + str(offset))
        prepared["url"] = url
        prepared["note"] += "; targeted /filter query; no raw user ballots"
        stored = save_snapshot(db, **prepared)
        results.append({"offset": offset, "returned_rows": len(data["rows"]), **stored})
        if len(data["rows"]) < page_size:
            break
    else:
        truncated = total_rows is None or max_pages * page_size < total_rows
    return {
        "schema": "fsl/arena-history/0.4",
        "model_name": model, "config": config, "category": category,
        "retrieved_on": retrieved_on, "pages": results,
        "rows_seen": sum(x["returned_rows"] for x in results),
        "provider_reported_matching_rows": total_rows,
        "truncated_by_page_cap": truncated,
        "historical_status": "retrospective_only",
        "warning": "Older published rows fetched now are NOT admissible as earlier known-at-time evidence.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Targeted official Arena full-history importer")
    p.add_argument("--db", default="data/fsl_adaptive.sqlite")
    p.add_argument("--config", default="text_style_control")
    p.add_argument("--model", required=True, help="exact Arena model_name")
    p.add_argument("--category", default="overall")
    p.add_argument("--max-pages", type=int, default=3)
    p.add_argument("--retrieved-on", default=date.today().isoformat())
    p.add_argument("--report")
    args = p.parse_args(argv)
    if args.retrieved_on != date.today().isoformat():
        p.error("live fetching cannot be backdated; use the real UTC retrieval date")
    try:
        with connect(args.db) as db:
            result = import_history(db, config=args.config, model=args.model,
                                    category=args.category,
                                    retrieved_on=args.retrieved_on,
                                    max_pages=args.max_pages)
        output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.report:
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report).write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (CatalogError, OSError, ValueError, KeyError) as exc:
        p.exit(2, f"import failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
