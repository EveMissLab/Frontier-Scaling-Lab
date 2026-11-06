"""Evidence coverage audit for real attached mission runs and source-only pilots.

Does NOT upgrade a G1–G4/E1 candidate to certification.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json

from fsl_functional.audit import evaluate as functional_assessment
from fsl_functional.store import moment, events_asof
from .registry import (
    ObservatoryError, digest, read_session, records_asof,
)


def audit(db,session_id,*,as_of):
    session=read_session(db,session_id)
    cutoff=moment(as_of)
    if cutoff<moment(session["created_at"]):
        raise ObservatoryError("as-of date predates observation session")
    receipts,links=records_asof(db,session_id,as_of)
    kinds=Counter(r["kind"] for r in receipts)
    states=Counter(r["state"] for r in receipts)
    trust=Counter(r["time_trust"] for r in receipts)
    linked_ids={l["event_id"] for l in links}
    attached={r["receipt_id"]:r for r in receipts}
    provider_days=set()
    provider_weeks=set()
    successful_runs=[]
    local_files=[]
    for r in receipts:
        if r["time_trust"]=="provider_recorded" and r["provider_at"]:
            when=moment(r["provider_at"])
            provider_days.add(when.date().isoformat())
            provider_weeks.add(str(when.isocalendar()[:2]))
        if (r["kind"]=="github_workflow" and
            r["metadata"].get("status")=="completed" and
            r["metadata"].get("conclusion")=="success"):
            successful_runs.append(r["metadata"].get("run_id"))
        if r["kind"]=="local_file":
            local_files.append({
                "relative_file":r["source_ref"],
                "hash":r["content_sha256"],
                "observed_at":r["observed_at"],
            })
    base=None
    covered_events=0
    source_events_by_kind=Counter()
    if session["mission_run_id"] is not None:
        base=functional_assessment(
            db,session["mission_run_id"],as_of=cutoff.isoformat())
        events=events_asof(db,session["mission_run_id"],cutoff.isoformat())
        active_ids={x["event_id"] for x in events}
        covered_events=len(active_ids & linked_ids)
        event_by_id={x["event_id"]:x["kind"] for x in events}
        for event_id in active_ids & linked_ids:
            source_events_by_kind[event_by_id[event_id]]+=1

    return {
        "schema":"fsl/mission-observatory/v0.7",
        "session_id":session_id,
        "linked_functional_run":session["mission_run_id"],
        "project_ref":session["project_ref"],
        "as_of":cutoff.isoformat(),
        "receipt_count":len(receipts),
        "source_types":dict(sorted(kinds.items())),
        "collection_states":dict(sorted(states.items())),
        "time_trust_classes":dict(sorted(trust.items())),
        "distinct_provider_recorded_dates":len(provider_days),
        "distinct_provider_recorded_weeks":len(provider_weeks),
        "successful_github_workflow_runs":sorted(set(successful_runs)),
        "local_file_hash_receipts":local_files,
        "mission_links":{
            "total":len(links),
            "covered_unique_events":covered_events,
            "kinds_covered":dict(sorted(source_events_by_kind.items())),
            "examples":[
                {"event_id":l["event_id"],"role":l["role"],
                 "receipt_kind":attached[l["receipt_id"]]["kind"],
                 "receipt_state":attached[l["receipt_id"]]["state"]}
                for l in links[:25]
            ],
        },
        "functional_claim_assessment":base,
        "certification":{
            "provider_metadata_checked":bool(receipts),
            "real_elapsed_autonomous_work_verified":False,
            "real_finished_product_quality_verified":False,
            "ai_only_causal_attribution_verified":False,
            "G1_G4_or_E1_certified":False,
        },
        "remaining_independent_checks":[
            "Confirm independent trusted wall-clock/work-duration records beyond user-authored Git commit dates.",
            "Verify checkpoints represent meaningful progress rather than idle CI activity.",
            "Replay the finished artifact and inspect end-to-end functional acceptance.",
            "Review actual Agent/model/runtime source versions and human interventions.",
            "Get independent evaluators for product quality, original art and physical safety.",
            "Do not extrapolate a few collected receipts into days/weeks/months of autonomy.",
        ],
        "summary":"Immutable read-only evidence receipts; no certificate of autonomous AI task completion.",
    }
