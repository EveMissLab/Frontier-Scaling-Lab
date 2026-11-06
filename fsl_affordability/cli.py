"""Cost and usage analysis, separate from AI functional capability certification.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .ledger import CostError, analyze, connect, save


def main(argv=None):
    p=argparse.ArgumentParser(
        description="FSL v0.8.1: subscription/API/cost-access experiment ledgers")
    sub=p.add_subparsers(dest="command",required=True)
    for verb in ("analyze","save"):
        q=sub.add_parser(verb)
        q.add_argument("--file",required=True,help="UTF-8 JSON cost/usage record")
        q.add_argument("--output")
        if verb=="save":q.add_argument("--db",default="data/affordability.sqlite")
    args=p.parse_args(argv)
    try:
        data=json.loads(Path(args.file).read_text(encoding="utf-8"))
        if args.command=="save":
            if (data.get("access",{}).get("evidence_class")=="observational" and
                datetime.fromisoformat(data["access"]["ends_at"].replace("Z","+00:00"))
                > datetime.now(timezone.utc)):
                raise CostError("real run cannot claim a future end time")
            with connect(args.db) as db:
                result=save(db,data)
        else:
            result=analyze(data)
        raw=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
        if args.output:
            dst=Path(args.output)
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_text(raw,encoding="utf-8")
        else:print(raw,end="")
    except (ValueError,TypeError,KeyError,OSError) as exc:
        p.exit(2,f"cost-input error: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
