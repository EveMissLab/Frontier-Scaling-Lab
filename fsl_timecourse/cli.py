"""CLI for methodology-guarded longitudinal public evidence analysis.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from fsl_sources.catalog import CatalogError, connect
from .analysis import ARENA_METHOD_BREAKS, analyze_series, study_readiness


def main(argv=None):
    p = argparse.ArgumentParser(description="Frontier Scaling Lab: v0.4 public evidence timecourse")
    p.add_argument("--db", default="data/fsl_adaptive.sqlite")
    cmd = p.add_subparsers(dest="command", required=True)

    ready = cmd.add_parser("readiness", help="audit evidence without pretending capability identifiability")
    ready.add_argument("--as-of", default=date.today().isoformat())
    ready.add_argument("--output")

    series = cmd.add_parser("series", help="one exact model/metric/methodology timecourse")
    series.add_argument("--model-id", required=True)
    series.add_argument("--measure", required=True)
    series.add_argument("--category", required=True)
    series.add_argument("--methodology", required=True)
    series.add_argument("--channel", required=True,
                        choices=("metadata","preference","benchmark","community"))
    series.add_argument("--as-of", default=date.today().isoformat())
    series.add_argument("--mode", choices=("strict_asof","retrospective"),
                        default="strict_asof")
    series.add_argument("--min-samples", type=int, default=100)
    series.add_argument("--output")
    cmd.add_parser("method-breaks", help="list conservative official Arena measurement breaks")

    args = p.parse_args(argv)
    try:
        if args.command == "method-breaks":
            result = {"source": "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset",
                      "events": [
                          {"date": day, "type": event}
                          for day, event in ARENA_METHOD_BREAKS
                      ],
                      "note": "Different methodology eras are not directly treated as cognitive changes."}
            output = None
        else:
            with connect(args.db) as db:
                if args.command == "readiness":
                    result = study_readiness(db, as_of=args.as_of)
                else:
                    result = analyze_series(
                        db, model_id=args.model_id, measure=args.measure,
                        category=args.category, methodology=args.methodology,
                        channel=args.channel, as_of=args.as_of, mode=args.mode,
                        min_samples=args.min_samples)
            output = args.output
        raw = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False,
                         allow_nan=False) + "\n"
        if output:
            dest = Path(output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(raw, encoding="utf-8")
        else:
            sys.stdout.write(raw)
    except (CatalogError, ValueError, KeyError, OSError, TypeError) as exc:
        p.exit(2, f"timecourse error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
