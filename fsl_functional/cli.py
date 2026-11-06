"""Record and audit durable functional mission outcomes via SQLite.

No background agent is launched by this CLI. Actual days/weeks/months of
work must be performed and externally evidenced by a separate running system.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .store import MissionError, add_event, add_run, add_spec, connect
from .audit import evaluate


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _out(value, output):
    data=json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                    allow_nan=False)+"\n"
    if output:
        target=Path(output)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(data,encoding="utf-8")
    else:
        print(data,end="")


def main(argv=None):
    p=argparse.ArgumentParser(
        description="FSL v0.6: mission continuity, dynamic adaptation and finished works")
    p.add_argument("--db",default="data/fsl_adaptive.sqlite")
    actions=p.add_subparsers(dest="command",required=True)
    actions.add_parser("init")
    spec=actions.add_parser("spec")
    spec.add_argument("--file",required=True)
    run=actions.add_parser("run")
    run.add_argument("--file",required=True)
    event=actions.add_parser("event")
    event.add_argument("--file",required=True)
    batch=actions.add_parser("ingest-example")
    batch.add_argument("--file",required=True,
                       help="synthetic fixture containing spec, run, events")
    audit=actions.add_parser("audit")
    audit.add_argument("--run-id",required=True)
    audit.add_argument("--as-of",default=None)
    audit.add_argument("--output")
    args=p.parse_args(argv)
    try:
        with connect(args.db) as db:
            if args.command=="init":
                value={"schema":"fsl/functional/v0.6","database":args.db,
                       "certification":"not_supported_by_event_log_alone"}
            elif args.command=="spec":
                value={"spec_id":add_spec(db,_load(args.file))}
            elif args.command=="run":
                value={"run_id":add_run(db,_load(args.file))}
            elif args.command=="event":
                value={"event_id":add_event(db,_load(args.file))}
            elif args.command=="ingest-example":
                package=_load(args.file)
                if package["spec"].get("evidence_class")!="synthetic":
                    raise MissionError("ingest-example only accepts synthetic test material")
                spec_id=add_spec(db,package["spec"])
                run_id=add_run(db,package["run"])
                for item in package["events"]:
                    add_event(db,item)
                value={"spec_id":spec_id,"run_id":run_id,
                       "events_logged":len(package["events"]),
                       "claim":"synthetic_only_not_empirical"}
            elif args.command=="audit":
                cutoff=args.as_of or datetime.now(timezone.utc).isoformat()
                value=evaluate(db,args.run_id,as_of=cutoff)
            else:
                raise MissionError("unsupported command")
        _out(value,getattr(args,"output",None))
    except (MissionError,ValueError,KeyError,TypeError,OSError,
            json.JSONDecodeError) as exc:
        p.exit(2,f"functional mission error: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
