"""CLI for read-only GICCF catalog and trial assertions. Apache-2.0."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from .registry import (GICCFError, audit_observations, catalog_sha256,
                       load_catalog, validate_catalog)


def main(argv=None):
    parser = argparse.ArgumentParser(description="FSL GICCF capability research (not a certified leaderboard)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="validate 224 capability definitions and summarize catalog")
    check = sub.add_parser("audit", help="validate input observations and show sparse as-of evidence")
    check.add_argument("--file", required=True, help="UTF-8 JSON trial file")
    check.add_argument("--as-of", help="ISO UTC cutoff e.g. 2026-11-07 or 2026-11-07T12:00:00Z")
    check.add_argument("--output", help="optional output JSON path")
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog()
        if args.command == "catalog":
            meta = validate_catalog(catalog)
            result = {k: v for k, v in meta.items()
                      if k not in {"indicator_ids", "domain_ids", "dimensions", "negative_controls"}}
            result["catalog_sha256"] = catalog_sha256()
        else:
            raw = json.loads(Path(args.file).read_text(encoding="utf-8"))
            result = audit_observations(raw, catalog=catalog, as_of=args.as_of)
        output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.command == "audit" and args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(status=2, message=f"GICCF validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
