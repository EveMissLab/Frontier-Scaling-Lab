"""G1/G2 cost panels must carry exact execution and evidence time (v0.8.3).

Extends the v0.8.2 economic comparators; legacy undated reports remain
readable for historical reference but cannot masquerade as time-anchored
experiments. Required trial timestamps are collected in a separate manifest.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .comparison import EconomicsError, compare_cohorts
from .timeaxis import (
    TemporalError, _instant, validate_mission_clock
)


def _local_day(instant):
    return instant.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat()


def compare_time_anchored(data, *, checked_at=None):
    if not isinstance(data,dict) or data.get("schema")!="fsl/time-anchored-panel/0.8.3":
        raise TemporalError("time-anchored economic panel schema is required")
    cutoff=_instant(data.get("cutoff_at"),"cutoff_at")
    panel=data.get("panel")
    if not isinstance(panel,dict):
        raise TemporalError("underlying v0.8.2 task and prices required")
    base=compare_cohorts(panel)
    raw=data.get("mission_clocks")
    if not isinstance(raw,list):
        raise TemporalError("all task attempts must have exact mission timestamp records")
    indexed={}
    for entry in raw:
        if not isinstance(entry,dict) or set(entry)!={"cohort_id","trial_id","clock"}:
            raise TemporalError("mission clocks must specify cohort/trial/clock only")
        key=(entry["cohort_id"],entry["trial_id"])
        if key in indexed:
            raise TemporalError("duplicate mission clock")
        indexed[key]=entry["clock"]
    all_keys={
        (c["cohort_id"], t["trial_id"])
        for c in panel["cohorts"] for t in c["trials"]
    }
    if set(indexed)!=all_keys:
        raise TemporalError("every reported accepted, failed and censored trial needs a time spine")
    for c in panel["cohorts"]:
        for trial in c["trials"]:
            key=(c["cohort_id"],trial["trial_id"])
            clock=indexed[key]
            if not isinstance(clock,dict):
                raise TemporalError("mission clock must be an object")
            if clock.get("task_contract_sha256")!=panel["task"]["task_revision_sha256"]:
                raise TemporalError("underlying task hash drifted within panel")
            if clock.get("runtime_manifest_sha256")!=c["runtime_sha256"]:
                raise TemporalError("clock runtime revision mismatches cohort")
            if clock.get("model_id")!=c["model_id"] or clock.get("model_revision")!=c["model_revision"]:
                raise TemporalError("model identity or revision drifted")
            if clock.get("provider")!=c["provider"]:
                raise TemporalError("wrong provider for trial")
            if clock.get("evidence_class")!=panel["evidence_class"]:
                raise TemporalError("time record and study evidence class mismatch")
            if clock.get("access_route")!=c["billing_route"]:
                raise TemporalError("billing route differs from temporal record")
            checked=cutoff.isoformat() if panel["evidence_class"]=="observational" else checked_at
            result=validate_mission_clock(clock,checked_at=checked)
            cap=_instant(clock["captured_at"],"captured_at")
            if cap>cutoff:
                raise TemporalError("observation first captured after study cutoff")
            if trial["outcome"]=="accepted_reported":
                if clock.get("accepted_at") is None:
                    raise TemporalError("accepted trial lacks recorded outcome timestamp")
                end=_instant(clock["accepted_at"],"accepted_at")
            elif trial["outcome"]=="failed_reported":
                if clock.get("execution_finished_at") is None or clock.get("accepted_at") is not None:
                    raise TemporalError("failed outcome must be finished but not accepted")
                end=_instant(clock["execution_finished_at"],"execution_finished_at")
            else:
                if clock.get("execution_finished_at") is not None or clock.get("accepted_at") is not None:
                    raise TemporalError("censored outcome cannot claim a completed task")
                end=_instant(clock["last_progress_at"],"last_progress_at") if (
                    clock.get("last_progress_at") is not None) else None
            if end is None:
                raise TemporalError("censored trial needs source-dated last progress")
            if _local_day(end)!=trial["evaluated_on"]:
                raise TemporalError("trial evaluation calendar date != last/finished/accepted outcome")
            if not c["price_snapshot_on"]<=_local_day(
                    _instant(clock["execution_started_at"],"execution_started_at")):
                raise TemporalError("cohort pricing snapshot is after task began")
            # Fee vintage may have been captured later and remains marked,
            # but never falsely described as available to the original user.
            result["price_quote_is_retrospective_only"] = bool(
                result["price_vintage_backfilled_from_after_run_start"]
            )
            result["outcome_record_date_Asia_Taipei"]=_local_day(end)
            indexed[key]=result
    observations=[]
    for c in base["cohorts"]:
        entries=[
            {"trial_id":trial["trial_id"],"outcome":trial["outcome"],
             "observed_time":indexed[(c["cohort_id"],trial["trial_id"])]}
            for trial in next(x for x in panel["cohorts"]
                              if x["cohort_id"]==c["cohort_id"])["trials"]
        ]
        observations.append({
            "cohort_id":c["cohort_id"],
            "trial_timestamps":entries,
            "n_backfilled_prices":sum(
                x["observed_time"]["price_vintage_backfilled_from_after_run_start"]
                for x in entries),
            "independent_temporal_attestation":False,
        })
    return {
        "schema":"fsl/time-anchored-economics-result/0.8.3",
        "cutoff_at_utc":cutoff.isoformat(),
        "cutoff_at_Asia_Taipei":cutoff.astimezone(
            ZoneInfo("Asia/Taipei")).isoformat(),
        "date_assignment":"outcome_acceptance_date_or_final_known_task_status_Asia_Taipei",
        "task_result":base,
        "observed_trial_clocks":observations,
        "all_attempts_have_valid_timestamps":True,
        "can_assert_24_48h_autonomy":False,
        "can_assert_historical_forecast_accuracy":False,
        "independently_verified_task_success":False,
        "caveats":[
            "Time-anchored self-reported activity is still not independent proof of working autonomy.",
            "Source and price dates are calendar dates; mission duration uses timezone-aware instants.",
            "A captured-after-start price may be a retrospective quote, not contemporaneous cost.",
            "Historical model release dates cannot substitute for historical tool availability.",
        ],
    }
