"""Frontier cost/geopolitics research reader; never outputs a country winner.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .registry import load_data, validate, replay


def main(argv=None):
    parser = argparse.ArgumentParser(description="FSL v0.19 comparative AI strategy source audit")
    cmds = parser.add_subparsers(dest="command", required=True)
    cmds.add_parser("validate")
    r = cmds.add_parser("replay")
    r.add_argument("--as-of", required=True)
    r.add_argument("--mode", choices=["strict_known_at_time", "retrospective_reconstruction"],
                   default="strict_known_at_time")
    r.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        geo, cost = load_data()
        if args.command == "validate":
            result = {k:v for k,v in validate(geo, cost).items() if k != "source_index"}
            result.update({"national_frontier_cost_roi_certified":False,
                           "geopolitical_winner_certified":False})
        else:
            result = replay(geo, cost, as_of=args.as_of, mode=args.mode)
        rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.command == "replay" and args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"FSL v0.19 source validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
