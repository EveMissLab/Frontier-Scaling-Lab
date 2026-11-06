from __future__ import annotations
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from .replay import validate_cases,replay_case,replay_all,ReplayError

def main(argv=None):
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="action",required=True)
    for mode in ("validate","case","all"):
        q=sub.add_parser(mode)
        q.add_argument("--output")
        if mode!="validate":
            q.add_argument("--as-of",required=True)
            q.add_argument("--mode",default="retrospective",choices=("retrospective","strict_known_at_time"))
        if mode=="case":q.add_argument("--case-id",required=True)
    a=p.parse_args(argv)
    try:
        d=json.loads(Path("data/agi_asi_public_interviews_seed_2026-11-07.json").read_text("utf-8"))
        m=json.loads(Path("data/official_ai_history_2024_2026_v0.9.json").read_text("utf-8"))
        c=json.loads(Path("data/longitudinal_narrative_cases_v0.11.json").read_text("utf-8"))
        r=(validate_cases(c,discourse=d,market=m) if a.action=="validate" else
           replay_case(d,m,c,case_id=a.case_id,as_of=a.as_of,mode=a.mode) if a.action=="case" else
           replay_all(d,m,c,as_of=a.as_of,mode=a.mode))
        now=datetime.now(timezone.utc)
        r["report_generated_at_utc"]=now.isoformat()
        r["report_generated_at_Asia_Taipei"]=now.astimezone(ZoneInfo("Asia/Taipei")).isoformat()
        raw=json.dumps(r,ensure_ascii=False,indent=2)+"\n"
        if a.output:
            path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw,"utf-8")
        else:print(raw,end="")
    except (ReplayError,ValueError,KeyError,OSError,TypeError) as e:
        p.exit(2,"narrative replay error: "+str(e)+"\n")
    return 0
if __name__=="__main__":raise SystemExit(main())
