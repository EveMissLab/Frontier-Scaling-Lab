"""FSL v0.12 — documentary divergence, changed deployment, reversibility scope.

This is a historiographic adjudicator, NOT a mind-reading or agent capability
benchmark. A provider's published statement can support "provider reports a
rollback" while NOT independently proving the exact online state, motive,
underlying weight identity, psychological belief, AGI status or general
irreversibility.

Source publication, described event and first FSL capture have separate
dates. 2026 collection must never become historical 2019/2025 knowledge.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlsplit
import hashlib
import json
import re

SCHEMA="fsl/documented-divergence/0.12"
IDENT=re.compile(r"[a-z][a-z0-9._:-]{2,95}\Z")
DATE=re.compile(r"\d{4}-\d{2}-\d{2}\Z")
SOURCE_GRADES={"provider_primary","contemporaneous_reporting",
               "original_interview_publisher"}
FOOTPRINTS={"same_model_weights","same_serving_snapshot_family",
            "same_product_feature","different_model_family",
            "one_speaker_statements","unknown_comparability"}
EVENT_STATES={
    "withheld","weights_released","deployed","rolled_back",
    "roadmap_announced","roadmap_revised","available_to_paying_users",
    "different_open_weight_family_released",
    "public_assertion","later_public_assertion",
    "unresolved","not_due",
}
EVENT_KINDS={"access_state","deployment","product_schedule","open_weight_family",
             "public_narrative","forecast"}
INTERPRETATIONS={
    "documented_access_change","documented_local_rollback",
    "provider_reported_rollback_missing_original_deploy_day",
    "documented_roadmap_revision","cross_family_difference_not_reversal",
    "possible_continuity_not_contradiction","forecast_not_due",
    "underidentified_direction",
}
VALID_REVIEW_GATES={
    "release_artifact_and_license","original_deployment_logs",
    "exact_rollout_cohorts","independent_behavior_evaluation",
    "published_strategy_authorization","licensing_revision_archive",
    "same_scope_interview_semantics","future_forecast_adjudication",
    "verified_user_outcome",
}

class DivergenceError(ValueError): pass


def _day(v,field):
    if not isinstance(v,str) or DATE.fullmatch(v) is None:
        raise DivergenceError(field+" needs YYYY-MM-DD")
    try:d=date.fromisoformat(v)
    except ValueError as e:raise DivergenceError(field+" invalid day") from e
    if d.isoformat()!=v:raise DivergenceError(field+" noncanonical day")
    return v


def _id(v,field):
    if not isinstance(v,str) or IDENT.fullmatch(v) is None:
        raise DivergenceError(field+" invalid stable ID")
    return v


def _text(v,field,max_len=580):
    if not isinstance(v,str) or not v.strip() or len(v)>max_len:
        raise DivergenceError(field+" must be short nonempty original prose")
    return v


def _url(v):
    if not isinstance(v,str):raise DivergenceError("source URL must be HTTPS")
    u=urlsplit(v)
    if u.scheme!="https" or not u.hostname or u.username or u.password:
        raise DivergenceError("source URL must be HTTPS and credential-free")
    return v


def _sha(data):
    return hashlib.sha256(json.dumps(
        data,sort_keys=True,ensure_ascii=False,separators=(",",":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def validate(data):
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA:
        raise DivergenceError("unknown documentary divergence schema")
    if data.get("time_zone")!="Asia/Taipei":
        raise DivergenceError("review calendar must specify Asia/Taipei")
    reviewed=_day(data.get("first_FSL_reviewed_on"),"first_FSL_reviewed_on")
    sources=data.get("sources")
    cases=data.get("cases")
    if not isinstance(sources,list) or not sources or not isinstance(cases,list) or not cases:
        raise DivergenceError("nonempty sources and cases are required")
    src={}
    for s in sources:
        req=("source_id","publisher","title","url","grade","published_on",
             "first_captured_on","date_basis","scope_limit")
        if not isinstance(s,dict) or any(k not in s for k in req):
            raise DivergenceError("source record must have original publication/capture date")
        sid=_id(s["source_id"],"source_id")
        if sid in src:raise DivergenceError("duplicate source ID")
        _text(s["publisher"],"publisher",140)
        _text(s["title"],"title",240)
        _text(s["scope_limit"],"scope_limit",400)
        _url(s["url"])
        if s["grade"] not in SOURCE_GRADES:raise DivergenceError("unknown evidence tier")
        p=_day(s["published_on"],"published_on")
        c=_day(s["first_captured_on"],"first_captured_on")
        if p>c or c>reviewed:raise DivergenceError("source publication/capture out of order")
        if s["date_basis"] not in ("publisher_release_day",
                                  "dated_section_mutable_page",
                                  "original_episode_publication"):
            raise DivergenceError("publisher date precision/semantics required")
        src[sid]=s

    seen=set()
    verified_verb_counts={}
    for c in cases:
        req=("case_id","company_or_speaker","baseline_day","scope_relation",
             "scope_key","event_kind","candidate_interpretation",
             "documented_events","falsification_questions","unknowns",
             "reversal_scope","review_gate","fsl_analyst_status")
        if not isinstance(c,dict) or any(k not in c for k in req):
            raise DivergenceError("case missing comparability, dates or evidence gates")
        cid=_id(c["case_id"],"case_id")
        if cid in seen:raise DivergenceError("duplicate case ID")
        seen.add(cid)
        _text(c["company_or_speaker"],"company_or_speaker",160)
        _text(c["scope_key"],"scope_key",160)
        baseline=_day(c["baseline_day"],"baseline_day")
        if baseline>reviewed:raise DivergenceError("cannot start case in future")
        if c["scope_relation"] not in FOOTPRINTS:raise DivergenceError("unknown scope relation")
        if c["event_kind"] not in EVENT_KINDS:raise DivergenceError("unsupported event kind")
        interpretation=c["candidate_interpretation"]
        if interpretation not in INTERPRETATIONS:raise DivergenceError("unsupported interpretation")
        if c["fsl_analyst_status"]!="provisional_not_independently_adjudicated":
            raise DivergenceError("cannot elevate documentary action to independent certification")
        events=c["documented_events"]
        if not isinstance(events,list) or not events or len(events)>8:
            raise DivergenceError("case must cite 1-8 dated events")
        event_ids=set()
        for e in events:
            keys=("event_id","source_id","occurred_on","state","locating_heading",
                  "factual_paraphrase","source_corroboration")
            if not isinstance(e,dict) or set(e)!=set(keys):
                raise DivergenceError("event needs exact source/date/status/locator")
            eid=_id(e["event_id"],"event_id")
            if eid in event_ids:raise DivergenceError("duplicate event")
            event_ids.add(eid)
            original=src.get(e["source_id"])
            if original is None:raise DivergenceError("unknown source ref")
            if e["state"] not in EVENT_STATES:
                raise DivergenceError("unknown operational/epistemic state")
            occurred=e["occurred_on"]
            if occurred is not None:
                _day(occurred,"event occurred_on")
                if occurred>reviewed:raise DivergenceError("case event in the future")
                if occurred<baseline:raise DivergenceError("event before case baseline")
            if e["source_corroboration"] not in ("provider_direct",
                 "third_party_attribution","original_interview"):
                raise DivergenceError("must specify independent evidence tier")
            if (original["grade"]=="provider_primary") != (
                 e["source_corroboration"]=="provider_direct"):
                if not (original["grade"]=="original_interview_publisher" and
                        e["source_corroboration"]=="original_interview") and not (
                    original["grade"]=="contemporaneous_reporting" and
                    e["source_corroboration"]=="third_party_attribution"):
                    raise DivergenceError("source evidence grade mismatch")
            _text(e["locating_heading"],"locating_heading",220)
            _text(e["factual_paraphrase"],"factual_paraphrase",480)
        for f in ("falsification_questions","unknowns"):
            v=c[f]
            if not isinstance(v,list) or not v:
                raise DivergenceError(f+" must preserve uncertainties")
            for x in v:_text(x,f,550)
        _text(c["reversal_scope"],"reversal_scope",490)
        if c["review_gate"] not in VALID_REVIEW_GATES:
            raise DivergenceError("independent evidence gate missing")
        if interpretation in ("documented_local_rollback","documented_access_change"):
            if len(events)<2 or c["scope_relation"] not in (
                 "same_serving_snapshot_family","same_model_weights"):
                raise DivergenceError("local operational transition requires two same-object states")
            states=[e["state"] for e in events]
            if interpretation=="documented_local_rollback":
                if "deployed" not in states or "rolled_back" not in states:
                    raise DivergenceError("operational rollback must have deployment and rollback")
            elif "withheld" not in states or "weights_released" not in states:
                raise DivergenceError("access change must have withheld and release")
        if interpretation=="provider_reported_rollback_missing_original_deploy_day":
            if (not any(e["state"]=="rolled_back" for e in events)
                or all(e["occurred_on"] is not None for e in events)):
                raise DivergenceError("unknown original deployment day must remain null")
        if interpretation=="documented_roadmap_revision":
            if c["scope_relation"]!="same_product_feature" or not {
                 "roadmap_announced","roadmap_revised"}<=set(e["state"] for e in events):
                raise DivergenceError("schedule revision needs original plan plus revised plan")
        if interpretation=="cross_family_difference_not_reversal":
            if c["scope_relation"]!="different_model_family":
                raise DivergenceError("cross-family development cannot be same model rollback")
        if interpretation=="forecast_not_due":
            if c["event_kind"]!="forecast" or c.get("forecast_target_by") is None:
                raise DivergenceError("forecast control needs explicit target date")
            _day(c["forecast_target_by"],"forecast_target_by")
            if c["forecast_target_by"]<=reviewed:
                raise DivergenceError("control forecast already due")
        if interpretation in ("possible_continuity_not_contradiction",
                              "underidentified_direction"):
            if c["event_kind"] not in ("public_narrative","forecast"):
                raise DivergenceError("non-causal controls need discourse or forecast class")
        if interpretation=="documented_local_rollback" and (
            c["scope_relation"]=="different_model_family"):
            raise DivergenceError("mixed model versions cannot imply snapshot rollback")
        # Order must respect the observed event dates; a retrospective account
        # published in May about Apr-28 remains an Apr-28 event.
        dated=[e["occurred_on"] for e in events if e["occurred_on"] is not None]
        if dated!=sorted(dated):
            raise DivergenceError("events must be chronologically sorted")
    return {
        "schema":"fsl/documented-divergence-validated/0.12",
        "case_count":len(cases),"source_count":len(sources),
        "case_types":dict(sorted(
            (k,sum(x["candidate_interpretation"]==k for x in cases))
            for k in sorted(set(x["candidate_interpretation"] for x in cases)))),
        "first_FSL_reviewed_on":reviewed,
        "canonical_sha256":_sha(data),
        "independent_behavior_or_decision_verifications_completed":0,
        "speaker_private_belief_reversals_proved":0,
        "AGI_ASI_attainments_proved":0,
    }


def replay(data,*,as_of,mode="retrospective"):
    validate(data)
    _day(as_of,"as_of")
    if mode not in ("retrospective","strict_known_at_time"):
        raise DivergenceError("unknown historical source-vintage mode")
    sources={s["source_id"]:s for s in data["sources"]}
    results=[]
    for c in data["cases"]:
        if c["baseline_day"]>as_of:continue
        observed=[]
        for e in c["documented_events"]:
            s=sources[e["source_id"]]
            happened=e["occurred_on"] is None or e["occurred_on"]<=as_of
            published=s["published_on"]<=as_of
            captured=s["first_captured_on"]<=as_of
            available=bool(happened and published and (
                mode=="retrospective" or captured))
            observed.append({
                "event_id":e["event_id"],
                "state":e["state"] if available else None,
                "occurred_on":e["occurred_on"],
                "original_published_on":s["published_on"],
                "first_FSL_captured_on":s["first_captured_on"],
                "source_url":s["url"],
                "source_grade":s["grade"],
                "locating_heading":e["locating_heading"],
                "factual_paraphrase":e["factual_paraphrase"] if available else None,
                "included_at_cutoff":available,
                "strict_original_study_possessed_source":bool(happened and published and captured),
                "later_report_can_describe_earlier_event":bool(
                    e["occurred_on"] and s["published_on"]>e["occurred_on"]),
            })
        available=[x for x in observed if x["included_at_cutoff"]]
        states=[e["state"] for e in available]
        typ=c["candidate_interpretation"]
        label="evidence_not_yet_visible"
        documented=False
        if typ=="documented_access_change" and {"withheld","weights_released"}<=set(states):
            label="provider_documented_access_change"
            documented=True
        elif typ=="documented_local_rollback" and {"deployed","rolled_back"}<=set(states):
            label="provider_documented_local_model_rollback"
            documented=True
        elif typ=="provider_reported_rollback_missing_original_deploy_day" and "rolled_back" in states:
            label="provider_reported_rollback_original_deploy_day_unknown"
            documented=True
        elif typ=="documented_roadmap_revision" and {"roadmap_announced","roadmap_revised"}<=set(states):
            label="documented_same_feature_schedule_revision"
            documented=True
        elif typ=="cross_family_difference_not_reversal" and len(available)>=2:
            label="two_distinct_model_families_not_a_rollback"
        elif typ=="forecast_not_due" and len(available)>=1:
            label=("forecast_not_yet_due" if as_of<=c["forecast_target_by"]
                   else "forecast_due_no_independent_adjudication")
        elif typ=="possible_continuity_not_contradiction" and len(available)>=2:
            label="public_wording_may_be_compatible"
        elif typ=="underidentified_direction" and available:
            label="claimed_direction_vs_actual_state_not_yet_resolved"
        # Even strong official documentation is not an externally authenticated
        # release artifact/rollback provenance certificate or company-intent proof.
        results.append({
            "case_id":c["case_id"],
            "company_or_speaker":c["company_or_speaker"],
            "baseline_day":c["baseline_day"],
            "scope_relation":c["scope_relation"],
            "scope_key":c["scope_key"],
            "claim_or_event_kind":c["event_kind"],
            "visible_events":observed,
            "documented_state_transition_from_sources":documented,
            "time_bounded_classification":label,
            "classification_is_limited_to_provider_reports":documented,
            "reversal_scope":c["reversal_scope"],
            "analyst_interpretation_authored_on":data["first_FSL_reviewed_on"],
            "analyst_interpretation_visible_at_asof":(
                data["first_FSL_reviewed_on"]<=as_of),
            "independent_review_gate":c["review_gate"],
            "independent_review_done":False,
            "predictive_correctness_verified":False,
            "technical_irreversibility_verified":False,
            "corporate_strategic_reversal_verified":False,
            "speaker_belief_change_verified":False,
            "causal_influence_identified":False,
            "unanswered_questions":(
                c["falsification_questions"]+c["unknowns"]
                if data["first_FSL_reviewed_on"]<=as_of else []),
        })
    return {
        "schema":"fsl/documented-divergence-replay/0.12",
        "as_of":as_of,"mode":mode,
        "cases":results,
        "provider_documented_state_transitions":sum(
            x["documented_state_transition_from_sources"] for x in results),
        "fully_independently_adjudicated_direction_changes":0,
        "scientifically_verified_personal_belief_change":0,
        "AGI_ASI_or_general_irreversibility_proved":0,
        "limits":[
            "Provider self-reports are documentary evidence, not independent runtime validation.",
            "A rollback of one serving snapshot does not reverse broader AI research or public knowledge.",
            "Staged release is not a broken promise to withhold weights permanently.",
            "Product scope, population and deployment phase differences prevent naive schedule-delta claims.",
            "A 2026 annotation cannot enter an original 2019 or 2025 prospective prediction.",
        ],
    }
