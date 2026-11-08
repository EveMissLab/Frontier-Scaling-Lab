"""FSL v0.18: legal case snapshots; no enforcement certification.
SPDX-License-Identifier: Apache-2.0
"""
import argparse
import json
from pathlib import Path
from .registry import load_data, validate, replay, LegalStudyError


def main(argv=None):
    parser = argparse.ArgumentParser(description="FSL data-center legal feasibility research")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("validate")
    p = subs.add_parser("replay")
    p.add_argument("--as-of", required=True)
    p.add_argument("--mode", choices=["strict_known_at_time", "retrospective_reconstruction"],
                   default="strict_known_at_time")
    p.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        snapshot = load_data()
        if args.command == "validate":
            result = {k:v for k,v in validate(snapshot).items() if k != "source_index"}
            result.update({"verified_legal_enforceability":False, "computed_MW_impact":None})
        else:
            result = replay(snapshot, as_of=args.as_of, mode=args.mode)
        output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.command == "replay" and args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"legal study source validation error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
