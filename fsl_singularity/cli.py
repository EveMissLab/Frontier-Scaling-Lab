"""Read-only audit of the SAS-01/EWDT-19 source definition interface.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .protocol import SingularityStudyError, audit, load_protocol


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Systemic singularity evidence protocol, never an AGI/ASI or singularity certification"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("definition", help="verify SAS-01 and EWDT-19 source priority")
    check = sub.add_parser("audit", help="replay synthetic or sourced assertion events")
    check.add_argument("--file", required=True)
    check.add_argument("--as-of", help="ISO-8601 offset-aware cutoff, or UTC calendar date")
    check.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "definition":
            p = load_protocol()
            result = {
                "canonical_source": p["definition_priority"][0]["document_id"],
                "secondary_interface": p["definition_priority"][1]["document_id"],
                "gates": [g["id"] for g in p["boundary_gates"]],
                "state_dimensions": [x["id"] for x in p["system_state_dimensions"]],
                "vector_domains": [x["code"] for x in p["system_vector"]],
                "certified": False
            }
        else:
            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            result = audit(payload, as_of=args.as_of)
        result_text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.command == "audit" and args.output:
            dest = Path(args.output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(result_text, encoding="utf-8")
        else:
            print(result_text, end="")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"singularity evidence error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
