"""Documented AI release/rollback divergence CLI (v0.12). Original summaries only."""
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .divergence import validate,replay,DivergenceError

DEFAULT="data/ai_documented_divergences_2019_2026_v0.12.json"
COLUMNS=["case_id","company_or_speaker","baseline_day","scope_relation",
         "as_of","mode","time_bounded_classification",
         "provider_documented_state_transition",
         "provider_reported_unexpected_effect",
         "independent_review_done","causality_established",
         "strategic_reversal_established","first_FSL_capture_day"]

def main(argv=None):
    p=argparse.ArgumentParser(description="FSL v0.12: historical state changes are not private beliefs")
    p.add_argument("--file",default=DEFAULT)
    sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("validate")
    q.add_argument("--output")
    for cmd in ("replay","csv"):
        q=sub.add_parser(cmd)
        q.add_argument("--as-of",required=True)
        q.add_argument("--mode",choices=("retrospective","strict_known_at_time"),
                       default="retrospective")
        q.add_argument("--output",required=True)
    a=p.parse_args(argv)
    try:
        data=json.loads(Path(a.file).read_text("utf-8"))
        now=datetime.now(timezone.utc)
        result=validate(data) if a.command=="validate" else replay(
            data,as_of=a.as_of,mode=a.mode)
        result["report_generated_at_utc"]=now.isoformat(timespec="seconds")
        result["report_generated_at_Asia_Taipei"]=now.astimezone(
            ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
        result["clock_source"]="local OS clock, not historical publication time"
        if a.command=="csv":
            rows=[]
            for x in result["cases"]:
                rows.append({
                  "case_id":x["case_id"],
                  "company_or_speaker":x["company_or_speaker"],
                  "baseline_day":x["baseline_day"],
                  "scope_relation":x["scope_relation"],
                  "as_of":result["as_of"],"mode":result["mode"],
                  "time_bounded_classification":x["time_bounded_classification"],
                  "provider_documented_state_transition":
                    x["documented_state_transition_from_sources"],
                  "provider_reported_unexpected_effect":
                    x["provider_reports_intent_outcome_gap"],
                  "independent_review_done":False,
                  "causality_established":False,
                  "strategic_reversal_established":False,
                  "first_FSL_capture_day":data["first_FSL_reviewed_on"],
                })
            path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("w",encoding="utf-8",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=COLUMNS)
                writer.writeheader();writer.writerows(rows)
            print(json.dumps({"cases_exported":len(rows),
                "independent_causal_links_certified":0,
                "private_belief_changes_certified":0},ensure_ascii=False))
        else:
            raw=json.dumps(result,ensure_ascii=False,indent=2,
                           sort_keys=True,allow_nan=False)+"\n"
            if a.output:
                path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(raw,encoding="utf-8")
            else:
                print(raw,end="")
    except (DivergenceError,ValueError,TypeError,KeyError,OSError) as ex:
        p.exit(2,"documentary divergence error: "+str(ex)+"\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
