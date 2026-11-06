"""Evidence-gated functional outcomes, NOT a universal IQ score.

G1: continuous extreme long-duration start-to-finished-outcome
G2: appropriate strategy change/maintain/clarify as real goals evolve
G3: one/few user rounds -> integrated world-class usable product
G4: distinctive personal-author AND AI-native stylistic work
E1: embodied cross-domain adaptive execution, separate acceptance bar

This is an *audit of event claims*, not external verification of game builds,
artistic originality, calendar-clock authenticity, or physical robot safety.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math

from .store import MissionError, events_asof, moment, read_spec_run


def _gate(ok, *, missing, evidence_class, measurements=None):
    """Never mark a benchmark 'certified' from a user-supplied evidence log."""
    return {
        "state": (
            ("simulated_candidate_not_empirical" if evidence_class == "synthetic"
             else "claimed_candidate_not_independently_verified")
            if ok else "not_yet_demonstrated"
        ),
        "recorded_conditions_satisfied": bool(ok),
        "independently_verified": False,
        "missing": sorted(set(missing)),
        "measurements": measurements or {},
    }


def _not_applicable():
    return {
        "state": "not_applicable_separate_track",
        "recorded_conditions_satisfied": False,
        "independently_verified": False,
        "missing": [],
        "measurements": {},
    }


def _events_of(events, kind):
    return [e for e in events if e["kind"] == kind]


def _after(event, origin):
    return moment(event["occurred_at"]) >= moment(origin["occurred_at"])


def _recorded_progress(events):
    """A dated event must carry a source and a state/artefact digest to count.

    This guards against purely idle elapsed time. It cannot verify the digest
    externally; evidence remains provisional until independently checked.
    """
    relevant = [e for e in events if e["kind"] in ("checkpoint", "progress")
                and e.get("source_url")]
    days = {moment(e["occurred_at"]).date().isoformat() for e in relevant}
    weeks = {moment(e["occurred_at"]).isocalendar()[:2] for e in relevant}
    return days, weeks


def _delivery(events):
    artifacts = {x["event_id"]:x for x in _events_of(events, "deliverable")}
    accepted = []
    for receipt in _events_of(events, "final_acceptance"):
        artifact = artifacts.get(receipt["payload"]["deliverable_event_id"])
        if artifact is not None and _after(receipt, artifact) and receipt["payload"]["accepted"]:
            accepted.append((artifact, receipt))
    accepted.sort(key=lambda pair: pair[1]["occurred_at"])
    return accepted[-1] if accepted else None


def _recovered(events):
    checkpoints = {x["event_id"]:x for x in _events_of(events, "checkpoint")}
    matched = []
    for e in _events_of(events, "recovery"):
        origin = checkpoints.get(e["payload"]["checkpoint_event_id"])
        if origin is not None and _after(e, origin):
            matched.append(e)
    return matched


def _adaptation(events):
    changes={x["event_id"]:x for x in events
             if x["kind"] in ("goal_revision", "environment_change")}
    decisions={}
    for d in _events_of(events, "strategy_decision"):
        ref=changes.get(d["payload"]["change_event_id"])
        if ref and _after(d,ref):
            decisions[d["event_id"]]=d
    by_decision={}
    for j in _events_of(events, "adaptation_judgement"):
        ref=decisions.get(j["payload"]["decision_event_id"])
        if ref and _after(j,ref):
            by_decision[j["payload"]["decision_event_id"]]=j
    resolved_change_ids=set()
    proper_replans=0
    proper_maintains=0
    false_decisions=[]
    for d in decisions.values():
        j=by_decision.get(d["event_id"])
        if j is None:
            continue
        if j["payload"]["correct"] and j["payload"]["revised_goal_met"]:
            resolved_change_ids.add(d["payload"]["change_event_id"])
            if d["payload"]["choice"]=="replan":
                proper_replans+=1
            if d["payload"]["choice"]=="maintain":
                proper_maintains+=1
        else:
            false_decisions.append(d["event_id"])
    return {
        "changes":len(changes),
        "user_goal_revisions":len(_events_of(events,"goal_revision")),
        "strategy_decisions":len(decisions),
        "independently_claimed_resolved":len(resolved_change_ids),
        "all_changes_reviewed_as_satisfied":bool(changes) and set(changes)==resolved_change_ids,
        "proper_replans":proper_replans,
        "proper_maintains":proper_maintains,
        "unsuccessful_or_misjudged_decisions":false_decisions,
    }


def _quality(events, expected_criteria, delivered):
    if delivered is None:
        return {"passed":[],"missing":list(expected_criteria),
                "reviewer_count":0,"conflicting":[]}
    artifact,receipt=delivered
    related=[r for r in _events_of(events,"quality_review")
             if r["payload"]["deliverable_event_id"]==artifact["event_id"]
             and _after(r,artifact)]
    reviewers={r["payload"]["reviewer"] for r in related}
    latest={}
    for r in related:
        latest[r["payload"]["criterion"]]=r["payload"]["passed"]
    passed=sorted(k for k in expected_criteria if latest.get(k) is True)
    missing=sorted(k for k in expected_criteria if latest.get(k) is not True)
    conflicting=sorted(k for k in latest if k not in expected_criteria)
    return {
        "passed":passed,"missing":missing,"reviewer_count":len(reviewers),
        "conflicting":conflicting,
        "final_deliverable_sha256":artifact["payload"]["artifact_sha256"],
    }


def _style(events, delivered):
    axes={"personal_author":set(),"ai_native":set()}
    if delivered is not None:
        artifact,_=delivered
        for review in _events_of(events,"style_review"):
            if (review["payload"]["deliverable_event_id"]==artifact["event_id"]
                    and _after(review,artifact) and review["payload"]["passed"]):
                axes[review["payload"]["axis"]].add(review["payload"]["reviewer"])
    return {axis:len(reviewers) for axis,reviewers in axes.items()}


def _embodied(events):
    outcomes = [x for x in _events_of(events, "domain_outcome")
                if x["payload"]["accepted"]]
    successful_domains=sorted({x["payload"]["domain"] for x in outcomes})
    switches=_events_of(events,"task_switch")
    valid_transitions=[
        x for x in switches if (
            x["payload"]["from_domain"] in successful_domains and
            x["payload"]["to_domain"] in successful_domains
        )
    ]
    incidents={e["event_id"]:e for e in _events_of(events, "safety_incident")}
    resolved={
        e["payload"]["incident_event_id"] for e in _events_of(events,"safety_resolution")
        if e["payload"]["resolved"] and e["payload"]["incident_event_id"] in incidents
        and _after(e,incidents[e["payload"]["incident_event_id"]])
    }
    outstanding=sorted(set(incidents)-resolved)
    return {
        "independently_claimed_completed_domains":successful_domains,
        "distinct_domain_count":len(successful_domains),
        "valid_cross_domain_switches":len(valid_transitions),
        "unresolved_safety_incidents":outstanding,
    }


def evaluate(db, run_id, *, as_of):
    """Return domain-aware pass CANDIDATES with explicit missing evidence.

    Source URLs and reviewers are logged but this code never visits source
    URLs, runs real software, verifies physical sensors, or validates signatures.
    No logged candidate is independently certified.
    """
    run=read_spec_run(db,run_id)
    cutoff=moment(as_of)
    if cutoff<moment(run["initiated_at"]):
        raise MissionError("as-of precedes run initiation")
    events=events_asof(db,run_id,as_of)
    start=_events_of(events,"intent")
    start=start[0] if len(start)==1 else None
    delivered=_delivery(events)
    end_time=moment(delivered[1]["occurred_at"]) if delivered else None
    goal_revisions=_events_of(events,"goal_revision")
    latest_goal=(
        goal_revisions[-1]["payload"]["goal_sha256"] if goal_revisions
        else start["payload"]["goal_sha256"] if start else None
    )
    acceptance_goal_matches=bool(delivered and latest_goal and
                                delivered[1]["payload"]["goal_sha256"]==latest_goal)
    duration=(end_time-moment(start["occurred_at"])).total_seconds()/86400.0 if (
              end_time and start and end_time>=moment(start["occurred_at"])) else None
    days,weeks=_recorded_progress(events)
    stack_changes=_events_of(events,"stack_change")
    stage=("multi_month_90d_plus" if duration is not None and duration>=90
           else "month_30d_plus" if duration is not None and duration>=30
           else "week_7d_plus" if duration is not None and duration>=7
           else "day_2d_plus" if duration is not None and duration>=2
           else "not_observed")
    if duration is not None:
        span_weeks=max(1,math.ceil(duration/7.0))
        min_checkpoint_weeks=(max(3,math.ceil(span_weeks*0.6)) if duration>=28
                              else 2 if duration>=7 else 1)
        min_checkpoint_days=(max(4,min_checkpoint_weeks) if duration>=28
                             else 3 if duration>=7 else 2)
    else:
        min_checkpoint_days=2
        min_checkpoint_weeks=1
    recovered=_recovered(events)
    intervention=_events_of(events,"human_assist")
    direct_execution=sum(e["payload"]["level"]=="direct_execution" for e in intervention)
    user_rounds=len(_events_of(events,"intent"))+len(goal_revisions)+len(_events_of(events,"user_round"))
    ad=_adaptation(events)
    q=_quality(events,run["required_criteria"],delivered)
    styles=_style(events,delivered)
    track=run["track"]
    eclass=run["evidence_class"]

    g1_missing=[]
    if start is None:
        g1_missing.append("one initial user-authored intent")
    if delivered is None:
        g1_missing.append("final artifact independently accepted as complete")
    if duration is None or duration < run["min_duration_days"]:
        g1_missing.append("actual dated end-to-end interval meeting specified duration")
    if len(days)<min_checkpoint_days or len(weeks)<min_checkpoint_weeks:
        g1_missing.append("distributed, source-backed progress checkpoints (not idle time)")
    if not recovered:
        g1_missing.append("successful return to a persistent checkpoint after restart/handoff")
    if not acceptance_goal_matches:
        g1_missing.append("final acceptance explicitly references latest user goal")
    if direct_execution:
        g1_missing.append("human did direct work; not autonomous end-to-end completion")
    g1={
        "state":"not_applicable_separate_track",
        "recorded_conditions_satisfied":False,"independently_verified":False,
        "missing":[],"measurements":{}
    } if track=="embodied" else _gate(
        not g1_missing,missing=g1_missing,evidence_class=eclass,
        measurements={"logged_days_to_acceptance":duration,
                      "source_backed_progress_days":len(days),
                      "progress_calendar_weeks":len(weeks),
                      "checkpoint_recoveries":len(recovered),
                      "min_required_progress_days":min_checkpoint_days,
                      "min_required_progress_weeks":min_checkpoint_weeks,
                      "runtime_stack_revisions_logged":len(stack_changes),
                      "human_direct_execution_events":direct_execution},
    )

    g2_missing=[]
    if track=="digital" and not g1["recorded_conditions_satisfied"]:
        g2_missing.append("G1 sustained autonomous completion prerequisite")
    if ad["user_goal_revisions"]<1:
        g2_missing.append("at least one actual user goal change")
    if not ad["all_changes_reviewed_as_satisfied"]:
        g2_missing.append("externally reviewed satisfactory response to every recorded change")
    if ad["proper_replans"]<1:
        g2_missing.append("correctly choose to revise strategy when needed")
    if ad["proper_maintains"]<1:
        g2_missing.append("correctly maintain a strategy when no change is warranted")
    if direct_execution:
        g2_missing.append("direct human execution substituted for AI adaptation")
    g2=_gate(not g2_missing,missing=g2_missing,evidence_class=eclass,
             measurements=ad)

    if track=="digital":
        # Only G2 is conditioned on G1 by the user. G3 is an independent
        # finished-product target; a valid one-round deliverable need not
        # consume several days or months.
        g3_missing=[]
        if not acceptance_goal_matches:
            g3_missing.append("user goal must match accepted finished product")
        if direct_execution:
            g3_missing.append("core implementation was directly executed by a human")
        if not 1<=user_rounds<=min(3,run["max_user_rounds"]):
            g3_missing.append("final result requires one to three substantive user instruction rounds")
        if q["missing"]:
            g3_missing.append("missing independently reported critical finished-product criteria")
        if q["reviewer_count"]<2:
            g3_missing.append("two distinct external quality reviewers")
        if not delivered:
            g3_missing.append("integrated deployable/playable artifact and independent acceptance")
        g3=(_not_applicable() if run["kind"]=="art" else
            _gate(not g3_missing,missing=g3_missing,evidence_class=eclass,
                 measurements={"substantive_user_rounds":user_rounds,
                               "reference_standard":run["reference_url"],
                               "reference_date":run["reference_date"],
                               "critical_quality_evidence":q}))
        # G4 is also independent of G3: a complete original animation
        # or other art need not be a AAA game or commercial application.
        g4_missing=[]
        if not delivered or not acceptance_goal_matches:
            g4_missing.append("completed, accepted, goal-aligned creative work")
        if direct_execution:
            g4_missing.append("creative core was directly executed by a human")
        if run["kind"]=="art" and (q["missing"] or q["reviewer_count"]<2):
            g4_missing.append("completed art and rights provenance require independent quality review")
        for axis,count in styles.items():
            if count<2:
                g4_missing.append(f"2 independent positive reviews for {axis} original style axis")
        g4=_gate(not g4_missing,missing=g4_missing,evidence_class=eclass,
                 measurements={"style_reviewers":styles,
                               "distinct_ai_style_not_metaphysically_certified":True})
        physical=_not_applicable()
    else:
        g3=g4=_not_applicable()
        data=_embodied(events)
        physical_missing=[]
        if data["distinct_domain_count"]<3:
            physical_missing.append("3 independently reported successful physical task domains")
        if data["valid_cross_domain_switches"]<2:
            physical_missing.append("2 deliberate AI-executed cross-domain switches")
        if not ad["all_changes_reviewed_as_satisfied"] or ad["user_goal_revisions"]<1:
            physical_missing.append("user goal revision with reviewed task reinterpretation")
        if direct_execution:
            physical_missing.append("direct human execution supplied task success")
        if data["unresolved_safety_incidents"]:
            physical_missing.append("all safety incidents resolved with external evidence")
        physical=_gate(not physical_missing,missing=physical_missing,evidence_class=eclass,
                       measurements=data)

    records=[
        {"id":e["event_id"],"kind":e["kind"],"sha256":e["event_sha256"]}
        for e in events
    ]
    evidence_sha256=hashlib.sha256(json.dumps(records,sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema":"fsl/functional-assessment/v0.6",
        "run_id":run_id,
        "as_of":cutoff.isoformat(),
        "track":track,"work_kind":run["kind"],
        "goal_title":run["title"],
        "user_instruction_rounds":user_rounds,
        "initial_system_manifest_sha256":run["system_manifest_sha256"],
        "runtime_stack_revisions_logged":len(stack_changes),
        "calendar_days_claimed":duration,
        "duration_stage_claimed":stage,
        "multi_month_frontier_recorded":bool(
            duration is not None and duration>=90 and
            g1["recorded_conditions_satisfied"]
        ) if track=="digital" else False,
        "human_interventions":{
            "total":len(intervention),
            "direct_execution":direct_execution,
            "clarifications":sum(e["payload"]["level"]=="clarification" for e in intervention),
            "exceptions":sum(e["payload"]["level"]=="exception" for e in intervention),
        },
        "evidence_class":eclass,"event_count":len(records),
        "evidence_manifest_sha256":evidence_sha256,
        "gates":{
            "G1_extreme_long_duration_completion":g1,
            "G2_dynamic_autonomous_adaptation":g2,
            "G3_few_round_world_class_usable_delivery":g3,
            "G4_personal_and_ai_native_creative_styles":g4,
            "E1_embodied_multi_domain_adaptation":physical,
        },
        "general_intelligence_score":None,
        "empirical_capability_ceiling_established":False,
        "externally_certified_result":False,
        "method_limits":[
            "A logged timestamp is not independent proof that a process ran over weeks/months.",
            "An artifact SHA-256 and HTTPS URL do not prove the artifact is runnable, world-class or original.",
            "Reviewer identity, benchmark comparators and physical safety need independent audit.",
            "Digital G1/G2/G3/G4 and embodied E1 have separate criteria; no one-number ranking.",
            "Synthetic event histories can test code but never demonstrate real model capability.",
        ],
    }
