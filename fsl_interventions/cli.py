"""Experimental G2 intervention intake. This is an auditor, not an AI policy.

External evaluators must retain hidden oracle labels and high-entropy nonces
until the Agent has made a decision and the outcome is independently reviewed.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .ledger import (
    InterventionError, add_protocol, bind_choice,
    connect, evaluate, oracle_commitment, preregister, reveal,
)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(value, path=None):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,
                   indent=2,allow_nan=False)+"\n"
    if path:
        target=Path(path)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(raw,encoding="utf-8")
    else:
        print(raw,end="")


def main(argv=None):
    parser=argparse.ArgumentParser(
        description="FSL v0.8: blind G2 adaptation intervention evidence")
    parser.add_argument("--db",default="data/fsl_observatory.sqlite")
    actions=parser.add_subparsers(dest="command",required=True)
    actions.add_parser("init")
    for command in ("protocol","preregister","bind","reveal"):
        p=actions.add_parser(command)
        p.add_argument("--file",required=True)
    au=actions.add_parser("audit")
    au.add_argument("--protocol-id",required=True)
    au.add_argument("--as-of")
    au.add_argument("--output")
    demo=actions.add_parser("synthetic-demo")
    demo.add_argument("--file",required=True)
    demo.add_argument("--as-of",default="2026-01-17T00:00:00Z")
    demo.add_argument("--output")
    args=parser.parse_args(argv)
    try:
        with connect(args.db) as db:
            if args.command=="init":
                result={"database":args.db,"schema":"fsl/g2/v0.8",
                        "state":"initialized_not_an_agent"}
            elif args.command=="protocol":
                result={"protocol_id":add_protocol(db,load(args.file))}
            elif args.command=="preregister":
                result={"preregistered_case_id":preregister(db,load(args.file))}
            elif args.command=="bind":
                result=bind_choice(db,load(args.file))
            elif args.command=="reveal":
                result=reveal(db,load(args.file))
            elif args.command=="audit":
                cutoff=args.as_of or datetime.now(timezone.utc).isoformat()
                result=evaluate(db,args.protocol_id,cutoff)
            elif args.command=="synthetic-demo":
                fixture=load(args.file)
                if fixture.get("mode")!="synthetic" or (
                    fixture.get("spec",{}).get("evidence_class")!="synthetic"):
                    raise InterventionError("demo accepts clearly synthetic fixtures only")
                from fsl_functional.store import add_spec, add_run, add_event
                add_spec(db,fixture["spec"])
                add_run(db,fixture["run"])
                add_protocol(db,fixture["protocol"])
                # A fabricated fixture may carry expected answers openly;
                # this must NEVER be done in observational Agent trials.
                # Production preregister accepts only sealed hashes.
                for case in fixture["preregistered_cases"]:
                    claim=fixture["synthetic_oracles"][case["case_id"]]
                    prepared=dict(case,sealed_oracle_sha256=oracle_commitment(
                        case["case_id"],claim["expected_action"],
                        claim["expected_goal_sha256"],claim["oracle_nonce"]))
                    preregister(db,prepared)
                for event in fixture["mission_events"]:
                    add_event(db,event)
                for item in fixture["bindings"]:
                    bind_choice(db,item)
                for item in fixture["reveals"]:
                    reveal(db,item)
                result=evaluate(db,fixture["protocol"]["protocol_id"],args.as_of)
                result["demo_label"]="SYNTHETIC_ONLY_NOT_REAL_LONG_TERM_AI"
                if result["evidence_class"]!="synthetic" or result["G2_externally_verified"]:
                    raise InterventionError("invalid synthetic guard state")
            else:
                raise InterventionError("unsupported command")
        emit(result,getattr(args,"output",None))
    except (InterventionError,ValueError,KeyError,TypeError,OSError) as exc:
        parser.exit(2,f"intervention error: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
