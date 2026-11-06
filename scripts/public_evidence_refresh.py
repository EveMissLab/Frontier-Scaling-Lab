"""Bounded official-source refresh; no scraping of user reviews.

Fetch Hugging Face model metadata, Arena CC-BY-4.0 leaderboard slices,
and an HF benchmark sample. Archive only normalized numeric snapshots,
source attribution, license labels and source response SHA-256 in SQLite.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from fsl_sources.adapters import (
    arena_rows_request, hf_model_request, hf_benchmark_request,
    json_api_get, parse_arena_page, parse_hf_model, parse_hf_benchmark,
)
from fsl_sources.catalog import connect, save_snapshot


def refresh(db, retrieval_date, fetch=json_api_get):
    manifest = {
        "schema": "fsl/public-refresh/0.3",
        "retrieved_on": retrieval_date,
        "sources": [],
        "limitations": [
            "This is a small sampled retrieval, not a complete census.",
            "A provider's reported score does not prove the base model's independent quality.",
            "Weights, preference ratings and benchmark scores cannot be merged into one scalar.",
            "No user messages, personal data, individual preferences or raw model weights are downloaded.",
            "No hidden model parameters or cognitive multipliers are inferred here.",
        ],
    }
    jobs = [
        ("hf_model", "Qwen/Qwen3-0.6B", hf_model_request("Qwen/Qwen3-0.6B")),
        ("arena_text", "lmarena-ai/leaderboard-dataset:text:latest",
         arena_rows_request("text", "latest", offset=0, limit=100)),
        ("arena_agent", "lmarena-ai/leaderboard-dataset:agent:latest",
         arena_rows_request("agent", "latest", offset=0, limit=100)),
        ("hf_benchmark", "SWE-bench/SWE-bench_Verified",
         hf_benchmark_request("SWE-bench/SWE-bench_Verified")),
    ]
    for kind, ident, url in jobs:
        report = {"source": kind, "resource": ident, "api_endpoint": url}
        try:
            payload = fetch(url)
            if kind == "hf_model":
                prepared = parse_hf_model(
                    payload, model_id=ident, retrieved_on=retrieval_date)
            elif kind.startswith("arena_"):
                config = "text" if kind == "arena_text" else "agent"
                prepared = parse_arena_page(
                    payload, config=config, split="latest", offset=0,
                    retrieved_on=retrieval_date)
            else:
                if not isinstance(payload, list):
                    raise ValueError("unexpected HF benchmark response shape")
                # Intentionally bounded sample. Never silently claim a full leaderboard.
                report["full_response_rows"] = len(payload)
                payload = payload[:100]
                prepared = parse_hf_benchmark(
                    payload, dataset_id=ident, retrieved_on=retrieval_date)
            result = save_snapshot(db, **prepared)
            report.update({"state": "stored", **result})
        except Exception as exc:
            # Errors are explicitly reported, not silently turned into fake
            # 0-scores, zero model parameter counts, or empty datasets.
            report.update({"state": "failed", "error_type": type(exc).__name__,
                           "error": str(exc)[:240]})
        manifest["sources"].append(report)
    manifest["stored"] = sum(x["state"] == "stored" for x in manifest["sources"])
    manifest["failed"] = sum(x["state"] == "failed" for x in manifest["sources"])
    manifest["status"] = "failed" if manifest["stored"] == 0 else (
        "partial" if manifest["failed"] else "completed")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only public evidence sampling")
    parser.add_argument("--db", default="data/fsl_adaptive.sqlite")
    parser.add_argument("--report", default="reports/public_evidence_manifest.json")
    args = parser.parse_args(argv)
    with connect(args.db) as db:
        report = refresh(db, date.today().isoformat())
    destination = Path(args.report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({"manifest": str(destination), "status": report["status"],
                      "stored": report["stored"], "failed": report["failed"]},
                     sort_keys=True))
    return 1 if report["stored"] == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
