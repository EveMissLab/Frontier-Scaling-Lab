"""FSL task-purchasing-power and historical counterfactual CLI.

The comparison engine never certifies the truth of externally attributed
trials; sources require independent replay/adjudication.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from hashlib import sha256

from .comparison import EconomicsError, compare_cohorts
from .historical import historical_scenarios


DDL = """
CREATE TABLE IF NOT EXISTS research_economic_runs(
 study_id TEXT PRIMARY KEY,
 kind TEXT NOT NULL,
 created_at TEXT NOT NULL,
 evidence_class TEXT NOT NULL,
 input_sha256 TEXT NOT NULL,
 result_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS no_economic_update BEFORE UPDATE ON research_economic_runs
 BEGIN SELECT RAISE(ABORT,'append-only economic run'); END;
CREATE TRIGGER IF NOT EXISTS no_economic_delete BEFORE DELETE ON research_economic_runs
 BEGIN SELECT RAISE(ABORT,'append-only economic run'); END;
"""

def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main(argv=None):
    p=argparse.ArgumentParser(description="Cross-model cost per reported finished task; history-aware")
    sub=p.add_subparsers(dest="action",required=True)
    for kind in ("compare","history"):
        q=sub.add_parser(kind)
        q.add_argument("--input",required=True)
        q.add_argument("--output")
        q.add_argument("--save-db",help="Optional append-only local SQLite database")
        q.add_argument("--study-id",help="Required if --save-db is given")
    args=p.parse_args(argv)
    try:
        data=_read(args.input)
        result=compare_cohorts(data) if args.action=="compare" else historical_scenarios(data)
        serialized=json.dumps(result,ensure_ascii=False,indent=2,
                              sort_keys=True,allow_nan=False)+"\n"
        if args.save_db:
            if not args.study_id:
                raise EconomicsError("--study-id is required for immutable saved studies")
            path=Path(args.save_db)
            if str(path)!=":memory:":
                path.parent.mkdir(parents=True,exist_ok=True)
            with sqlite3.connect(str(path)) as db:
                db.executescript(DDL)
                db.execute("""INSERT INTO research_economic_runs
                  (study_id,kind,created_at,evidence_class,input_sha256,result_json)
                  VALUES(?,?,?,?,?,?)""",
                  (args.study_id,args.action,
                   datetime.now(timezone.utc).isoformat(),
                   data.get("evidence_class","historical_scenario"),
                   sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,
                       allow_nan=False).encode("utf-8")).hexdigest(),serialized))
                db.commit()
        if args.output:
            output=Path(args.output)
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(serialized,encoding="utf-8")
        else:
            print(serialized,end="")
    except (EconomicsError,ValueError,TypeError,KeyError,OSError,
            sqlite3.DatabaseError) as exc:
        p.exit(2,f"economic comparison error: {exc}\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
