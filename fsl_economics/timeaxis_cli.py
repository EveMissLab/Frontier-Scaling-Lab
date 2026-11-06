"""Explicit cutoff and reproducible capture time for FSL temporal studies.

Always require the as-of cutoff. Every report has actual UTC and Taipei
generation times. Historical publisher dates retain day precision.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .timeaxis import TemporalError, audit_asof, validate_mission_clock
from .temporal_panel import compare_time_anchored


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="FSL v0.8.3: no-lookahead source vintage and exact UTC mission clocks"
    )
    actions = parser.add_subparsers(dest="command", required=True)
    source = actions.add_parser("audit-sources")
    source.add_argument("--catalog", required=True)
    source.add_argument("--as-of", required=True,
                        help="study-day cutoff YYYY-MM-DD, never inferred")
    source.add_argument("--mode", choices=("strict_known_at_time",
                       "retrospective_reconstruction"),
                        default="strict_known_at_time")
    source.add_argument("--output")
    mission = actions.add_parser("audit-mission")
    mission.add_argument("--file", required=True)
    mission.add_argument("--output")
    panel = actions.add_parser("audit-panel")
    panel.add_argument("--file", required=True)
    panel.add_argument("--output")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        if args.command == "audit-sources":
            result = audit_asof(
                _read(args.catalog), as_of=args.as_of, mode=args.mode)
        elif args.command == "audit-panel":
            result = compare_time_anchored(_read(args.file), checked_at=now.isoformat())
        else:
            result = validate_mission_clock(
                _read(args.file), checked_at=now.isoformat())
        result["report_generated_at_utc"] = now.isoformat(timespec="seconds")
        result["report_generated_at_Asia_Taipei"] = now.astimezone(
            ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
        result["report_clock_source"] = "runtime_utc_clock_not_trusted_timestamp_service"
        output = json.dumps(
            result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        ) + "\n"
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (TemporalError, KeyError, ValueError, TypeError, OSError) as exc:
        parser.exit(2, "temporal study error: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
