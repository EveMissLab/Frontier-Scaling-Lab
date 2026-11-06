"""CLI for preregistered controlled task comparisons, separate from Arena.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from datetime import date

from .controlled import (
    TrialError,compare,connect,insert_protocol,insert_trial,vector
)


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description="Controlled task vectors; no global IQ scalar")
    p.add_argument("--db",default="data/fsl_adaptive.sqlite")
    cmd=p.add_subparsers(dest="command",required=True)
    protocol=cmd.add_parser("protocol")
    protocol.add_argument("--json",required=True)
    trial=cmd.add_parser("trial")
    trial.add_argument("--json",required=True)
    pair=cmd.add_parser("compare")
    pair.add_argument("--baseline",required=True)
    pair.add_argument("--target",required=True)
    pair.add_argument("--as-of",default=date.today().isoformat())
    vec=cmd.add_parser("vector")
    vec.add_argument("--pairs-json",required=True)
    vec.add_argument("--as-of",default=date.today().isoformat())
    args=p.parse_args(argv)
    try:
        with connect(args.db) as db:
            if args.command=="protocol":
                result={"registered_protocol_id":insert_protocol(db,_read(args.json))}
            elif args.command=="trial":
                result={"registered_trial_id":insert_trial(db,_read(args.json))}
            elif args.command=="compare":
                result=compare(db,baseline_id=args.baseline,
                               target_id=args.target,as_of=args.as_of)
            else:
                data=_read(args.pairs_json)
                result=vector(db,comparisons=data["comparisons"],as_of=args.as_of)
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True,
                         allow_nan=False))
    except (TrialError,ValueError,TypeError,KeyError,OSError) as exc:
        p.exit(2,f"controlled-evaluation error: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
