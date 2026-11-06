"""Small, timestamped public case-status matrix for v0.11 narrative replay.

Counts describe WHAT DOCUMENTS WERE VISIBLE AT THE OBSERVATION CUTOFF,
not intent accuracy, an AGI score, or a causal effect.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

from .replay import replay_all


COLUMNS=[
    "case_id","speaker_id","historical_baseline_day",
    "observation_as_of","mode",
    "visible_baseline_statements","visible_later_statements",
    "visible_later_model_events","analyst_hypotheses_visible",
    "candidate_interpretations","undetermined_choice_routes",
    "independent_quality_tests_completed","forecast_status",
    "private_belief_changed_verified","causal_effect_verified",
    "strategic_reversal_verified",
]


def rows_from_report(report):
    if not isinstance(report,dict) or report.get("schema")!=(
            "fsl/narrative-replay-multi-case/0.11"):
        raise ValueError("v0.11 replay report required")
    rows=[]
    for case in report["cases"]:
        rev=case["reversibility_probe"]
        status=";".join(x["status"] for x in case["dated_forecast_statuses"])
        rows.append({
            "case_id":case["case_id"],"speaker_id":case["speaker_id"],
            "historical_baseline_day":case["baseline_cutoff"],
            "observation_as_of":report["as_of"],
            "mode":report["mode"],
            "visible_baseline_statements":sum(
                x["is_visible_at_requested_cutoff"] for x in case["baseline_utterances"]),
            "visible_later_statements":sum(
                x["is_visible_at_requested_cutoff"] for x in case["later_utterances"]),
            "visible_later_model_events":sum(
                x["visible_at_asof"] for x in case["later_official_product_events"]),
            "analyst_hypotheses_visible":case["analyst_interpretations_visible_at_cutoff"],
            "candidate_interpretations":len(case["alternative_interpretations"]),
            "undetermined_choice_routes":len(rev["alternative_routes"]) if rev else 0,
            "independent_quality_tests_completed":0,
            "forecast_status":status,
            "private_belief_changed_verified":False,
            "causal_effect_verified":False,
            "strategic_reversal_verified":False,
        })
    return rows


def main(argv=None):
    p=argparse.ArgumentParser(description="FSL v0.11: export status, not propaganda")
    p.add_argument("--as-of",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--mode",choices=("retrospective","strict_known_at_time"),
                   default="retrospective")
    p.add_argument("--discourse",default="data/agi_asi_public_interviews_seed_2026-11-07.json")
    p.add_argument("--market",default="data/official_ai_history_2024_2026_v0.9.json")
    p.add_argument("--cases",default="data/longitudinal_narrative_cases_v0.11.json")
    args=p.parse_args(argv)
    read=lambda x:json.loads(Path(x).read_text("utf-8"))
    result=replay_all(read(args.discourse),read(args.market),read(args.cases),
                      as_of=args.as_of,mode=args.mode)
    rows=rows_from_report(result)
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"exported_case_count":len(rows),
                      "verified_causal_effect_count":0,
                      "verified_strategic_reversal_count":0},
                     ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
