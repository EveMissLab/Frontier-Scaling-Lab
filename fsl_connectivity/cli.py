"""Command-line reader for FSL-NET v0.16. No network collection or service mutation.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .audit import NetworkStudyError, audit, load_catalog


def main(argv=None):
    parser = argparse.ArgumentParser(description="FSL connectivity research; no scores or autonomous network testing")
    p = parser.add_subparsers(dest="command", required=True)
    p.add_parser("catalog", help="show 14 research axes and 70 unmeasured indicators")
    check = p.add_parser("audit", help="validate a source-dated observation/fixture file")
    check.add_argument("--file", required=True)
    check.add_argument("--as-of", help="timezone-aware ISO 8601 cutoff or UTC calendar date")
    check.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            data, ids = load_catalog()
            res = {"catalog":data["catalog_id"],"version":data["version"],
                   "axes":len(data["research_axes"]),"indicator_count":len(ids),
                   "observational_results_certified":False}
        else:
            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            res = audit(payload, cutoff=args.as_of)
        encoded = json.dumps(res, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        if args.command == "audit" and args.output:
            dst = Path(args.output)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        return 0
    except (NetworkStudyError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"FSL-NET validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
