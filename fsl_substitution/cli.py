"""ASSO catalog and historical replay CLI. Apache-2.0."""
import argparse
import json
from pathlib import Path
from .audit import ASSOError, audit, load_catalog, load_json


def main(argv=None):
    p = argparse.ArgumentParser(description="FSL AI substitution spectrum observatory; not certification")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    a = sub.add_parser("audit")
    a.add_argument("--file", required=True)
    a.add_argument("--as-of", required=True)
    a.add_argument("--mode", default="strict_known_at_time",
                   choices=["strict_known_at_time", "retrospective_reconstruction"])
    a.add_argument("--output")
    args = p.parse_args(argv)
    try:
        if args.command == "catalog":
            result = load_catalog()
        else:
            result = audit(load_json(args.file), as_of=args.as_of, mode=args.mode)
        output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.command == "audit" and args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (ASSOError, ValueError, OSError, TypeError, KeyError) as exc:
        p.exit(2, f"ASSO validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
