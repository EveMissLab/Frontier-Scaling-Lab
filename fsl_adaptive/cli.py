"""Frontier Scaling Lab v0.2 command line interface.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import date

from .engine import forecast, posterior
from .registry import (
    DataError, add_evidence, as_date, connect, insert_feedback,
    insert_forecast, snapshot,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "data" / "adaptive_scenarios.json"
DEFAULT_DB = ROOT / "data" / "fsl_adaptive.sqlite"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(value, output):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     indent=2, allow_nan=False) + "\n"
    if output:
        p = Path(output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(raw, encoding="utf-8")
    else:
        sys.stdout.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Adaptive AI scaling scenarios with immutable evidence and prequential updates")
    sub = parser.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init", help="initialize SQLite registry")
    init.add_argument("--db", default=str(DEFAULT_DB))
    ingest = sub.add_parser("ingest", help="append dated fact/correction/retraction")
    ingest.add_argument("--db", default=str(DEFAULT_DB))
    ingest.add_argument("--event", required=True, help="UTF-8 JSON evidence event")
    snap = sub.add_parser("snapshot", help="inspect known evidence as of a UTC calendar date")
    snap.add_argument("--db", default=str(DEFAULT_DB))
    snap.add_argument("--as-of", required=True)
    snap.add_argument("--output")
    fc = sub.add_parser("forecast", help="issue a conditional parameter multiplier envelope")
    fc.add_argument("--db", default=str(DEFAULT_DB))
    fc.add_argument("--config", default=str(DEFAULT_CONFIG))
    fc.add_argument("--as-of", default="2026-11-06", help="evidence cutoff YYYY-MM-DD")
    fc.add_argument("--year", type=float, required=True)
    fc.add_argument("--target", default="synthetic-reference")
    fc.add_argument("--target-class", choices=("synthetic", "observational"), default="synthetic")
    fc.add_argument("--include-planned", action="store_true")
    fc.add_argument("--persist", action="store_true")
    fc.add_argument("--output")
    learn = sub.add_parser("feedback", help="ingest actual later public parameter-multiplier outcome")
    learn.add_argument("--db", default=str(DEFAULT_DB))
    learn.add_argument("--event", required=True)
    state = sub.add_parser("weights", help="inspect prior or evidence-updated hypothesis weights")
    state.add_argument("--db", default=str(DEFAULT_DB))
    state.add_argument("--config", default=str(DEFAULT_CONFIG))
    state.add_argument("--as-of", required=True)

    args = parser.parse_args(argv)
    try:
        with connect(args.db) as db:
            if args.cmd == "init":
                emit({"database": str(args.db), "schema_version": "fsl-adaptive/0.2",
                      "state": "initialized"}, None)
            elif args.cmd == "ingest":
                event = read_json(args.event)
                emit({"appended_event_id": add_evidence(db, event)}, None)
            elif args.cmd == "snapshot":
                facts, proven = snapshot(db, as_date(args.as_of))
                emit({"as_of": args.as_of, "provenance": proven,
                      "facts": [
                          {"entity_id": entity, "field": field, **record}
                          for (entity, field), record in sorted(facts.items())
                      ]}, args.output)
            elif args.cmd == "forecast":
                result = forecast(
                    db, read_json(args.config), as_of=args.as_of,
                    target_year=args.year, target_key=args.target,
                    target_class=args.target_class, allow_planned=args.include_planned)
                if args.persist:
                    result["forecast_id"] = insert_forecast(db, result)
                emit(result, args.output)
            elif args.cmd == "feedback":
                emit({"appended_feedback_id": insert_feedback(db, read_json(args.event))}, None)
            elif args.cmd == "weights":
                config = read_json(args.config)
                result = posterior(db, as_date(args.as_of), config["calibration_group"],
                                   [case["id"] for case in config["hypotheses"]])
                emit(result, None)
    except (DataError, KeyError, ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"input error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
