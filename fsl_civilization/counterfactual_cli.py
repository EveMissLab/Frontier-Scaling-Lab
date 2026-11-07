"""GICCF counterfactual/definition-evolution read-only CLI.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .counterfactual import CounterfactualError, audit, load_protocol


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate counterfactual human capability studies without inventing years."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("protocol", help="validate versioned counterfactual protocol")
    report = sub.add_parser("audit", help="audit a versioned assessment file")
    report.add_argument("--file", required=True)
    report.add_argument("--as-of", help="ISO 8601 UTC cutoff; date-only selects end-of-day UTC")
    report.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "protocol":
            data = load_protocol()
            result = {
                "protocol_version": data["version"],
                "framework_version": data["framework_anchor"]["version"],
                "no_ai_scenario_types": data["scenario_kinds"],
                "automatic_year_prediction": False,
                "certified_counterfactual_result": False
            }
        else:
            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            result = audit(payload, as_of=args.as_of)
        rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if args.command == "audit" and args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(status=2, message=f"Counterfactual validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
