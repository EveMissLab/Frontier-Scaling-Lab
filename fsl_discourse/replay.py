"""FSL v0.11: longitudinal AI narrative replay with disciplined temporal cutoffs.

There are TWO distinct clocks:
- a historical perspective day on which a speaker publicly described AI;
- an observation cutoff on which later published speech/actions may be inspected.

The analyst authored the case interpretations later. They MUST NOT appear
as if the speaker, company, or FSL had already known them in 2023/2024.

No automatic: contradiction, private-belief change, strategic reversal,
counterfactual route feasibility, forecast accuracy, causal influence,
AGI/ASI attainment or verified autonomous ability.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import re

from .catalog import validate as validate_discourse
from fsl_history.catalog import validate as validate_history

SCHEMA = "fsl/narrative-replay-cases/0.11"
ALLOWED_SCOPES = frozenset((
    "public_definition", "epistemic", "research_strategy",
    "organizational_choice", "technical_deployment",
    "market_diffusion", "governance", "mixed",
))
ALLOWED_HYPOTHESES = frozenset((
    "possible_continuity", "possible_reframing",
    "possible_tension", "insufficient_evidence",
))
ALLOWED_VERIFICATION = frozenset((
    "external_functional_test", "original_public_document",
    "technical_artifact", "financial_receipt",
    "independent_model_replay", "governance_decision",
    "longitudinal_interview",
))
ID = re.compile(r"[a-z0-9][a-z0-9._-]{1,110}\Z")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class ReplayError(ValueError):
    pass


def _day(v, field):
    if not isinstance(v, str) or DAY.fullmatch(v) is None:
        raise ReplayError(field+" must be YYYY-MM-DD")
    try:
        dt = date.fromisoformat(v)
    except ValueError as e:
        raise ReplayError(field+" invalid calendar day") from e
    if dt.isoformat() != v:
        raise ReplayError(field+" must be canonical")
    return v


def _id(v, field):
    if not isinstance(v, str) or ID.fullmatch(v) is None:
        raise ReplayError(field+" must be a stable ASCII ID")
    return v


def _prose(v, field, limit=600):
    if not isinstance(v, str) or not v.strip() or len(v)>limit:
        raise ReplayError(field+" requires short, nonempty original prose")
    return v


def _sha(data):
    return hashlib.sha256(json.dumps(
        data, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def _index(discourse, market):
    speeches={c["claim_id"]:c for c in discourse["claims"]}
    interviews={s["source_id"]:s for s in discourse["sources"]}
    products={e["event_id"]:e for e in market["events"]}
    product_sources={s["source_id"]:s for s in market["sources"]}
    return speeches,interviews,products,product_sources


def validate_cases(data, *, discourse, market):
    """Reject invented early forecasts, mixed identities and closed interpretations.

    The source catalog already validates link format and first-capture day;
    this module independently checks the case-bound source date ordering.
    """
    validate_discourse(discourse)
    validate_history(market)
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA:
        raise ReplayError("unknown longitudinal case schema")
    if data.get("analysis_calendar_timezone")!="Asia/Taipei":
        raise ReplayError("explicit Taipei analysis-day semantics required")
    authored=_day(data.get("analyst_authored_on"),"analyst_authored_on")
    if authored > discourse["catalog_reviewed_on"] or authored>market["catalog_reviewed_on"]:
        raise ReplayError("analyst cannot predate or future-date source review")
    cases=data.get("cases")
    if not isinstance(cases,list) or not cases:
        raise ReplayError("at least one sourced case required")
    claims,interviews,events,event_sources=_index(discourse,market)
    speaker_ids={s["speaker_id"] for s in discourse["speakers"]}
    ids=set()
    for case in cases:
        req=("case_id","speaker_id","public_context_at_baseline","baseline_cutoff",
             "question","baseline_claim_ids","later_claim_ids",
             "external_event_ids","non_claims",
             "candidate_interpretations","reversibility_probe",
             "discriminating_evidence")
        if not isinstance(case,dict) or any(k not in case for k in req):
            raise ReplayError("missing case identity, evidence or openness contract")
        cid=_id(case["case_id"],"case_id")
        if cid in ids: raise ReplayError("duplicate case")
        ids.add(cid)
        if case["speaker_id"] not in speaker_ids:
            raise ReplayError("case uses unknown speaker")
        _prose(case["public_context_at_baseline"],"public context",250)
        _prose(case["question"],"research question")
        baseline=_day(case["baseline_cutoff"],"baseline_cutoff")
        if baseline>authored:
            raise ReplayError("baseline cannot be from after the analyst study")
        base=case["baseline_claim_ids"]
        later=case["later_claim_ids"]
        ext=case["external_event_ids"]
        if not isinstance(base,list) or not base:
            raise ReplayError("must preserve at least one public source statement")
        if not isinstance(later,list) or not isinstance(ext,list):
            raise ReplayError("comparison entries must be lists (empty supported)")
        if len(base)!=len(set(base)) or len(later)!=len(set(later)) or len(ext)!=len(set(ext)):
            raise ReplayError("duplicate source references in a single case")
        if set(base)&set(later):
            raise ReplayError("baseline and later speech must not overlap")
        for claim_id in base:
            claim=claims.get(claim_id)
            if claim is None or claim["speaker_id"]!=case["speaker_id"]:
                raise ReplayError("baseline claim must belong to the named speaker")
            src=interviews[claim["source_id"]]
            if src["published_on"]>baseline:
                raise ReplayError("baseline speech published after perspective day")
        for claim_id in later:
            claim=claims.get(claim_id)
            if claim is None or claim["speaker_id"]!=case["speaker_id"]:
                raise ReplayError("later speech must belong to the SAME speaker")
            src=interviews[claim["source_id"]]
            if src["published_on"]<=baseline:
                raise ReplayError("later speech must actually be later")
        for event_id in ext:
            event=events.get(event_id)
            if event is None:
                raise ReplayError("external event ID does not exist in v0.9 history")
            if event["occurred_on"]<=baseline:
                raise ReplayError("case must list downstream events after baseline")
            if event_sources[event["source_id"]]["published_on"]>authored:
                raise ReplayError("product source had not yet been published by this study")
        if not isinstance(case["non_claims"],list) or not case["non_claims"]:
            raise ReplayError("case must explicitly say what is NOT established")
        for x in case["non_claims"]:
            _prose(x,"non_claim",300)
        hypotheses=case["candidate_interpretations"]
        if not isinstance(hypotheses,list) or len(hypotheses)<2:
            raise ReplayError("at least two competing explanations required")
        hids=set()
        for h in hypotheses:
            needed=("hypothesis_id","kind","interpretation",
                    "discriminating_observation","potential_falsifier",
                    "inference_status")
            if not isinstance(h,dict) or any(k not in h for k in needed):
                raise ReplayError("alternative interpretation lacks falsifiability")
            hid=_id(h["hypothesis_id"],"hypothesis_id")
            if hid in hids:
                raise ReplayError("duplicate interpretation")
            hids.add(hid)
            if h["kind"] not in ALLOWED_HYPOTHESES:
                raise ReplayError("interpretation must allow unresolved alternatives")
            for name in ("interpretation","discriminating_observation",
                         "potential_falsifier"):
                _prose(h[name],name,650)
            if h["inference_status"]!="candidate_not_adjudicated":
                raise ReplayError("cannot pre-certify one interpretation")
        rev=case["reversibility_probe"]
        needed=("scope","question","target","horizon_end",
                "decision_authority","constraint_uncertainty",
                "alternative_routes","actual_reversal_observed")
        if not isinstance(rev,dict) or any(k not in rev for k in needed):
            raise ReplayError("reversibility needs explicit scope, horizon and alternatives")
        if rev["scope"] not in ALLOWED_SCOPES:
            raise ReplayError("reversibility scope must be declared")
        for name in ("question","target","constraint_uncertainty"):
            _prose(rev[name],name,450)
        horizon=_day(rev["horizon_end"],"horizon_end")
        if horizon<=baseline:
            raise ReplayError("reversibility horizon must extend beyond the baseline")
        if rev["decision_authority"]!="not_independently_verified":
            raise ReplayError("interview cannot authorize/certify company control rights")
        if rev["actual_reversal_observed"] is not None:
            raise ReplayError("actual reversal requires separately verified governance evidence")
        routes=rev["alternative_routes"]
        if not isinstance(routes,list) or len(routes)<2:
            raise ReplayError("at least two open alternative routes required")
        routes_seen=set()
        for route in routes:
            if not isinstance(route,dict) or set(route)!={
                "route_id","candidate_path","required_evidence",
                "feasibility_status","route_observed"}:
                raise ReplayError("candidate path incomplete")
            rid=_id(route["route_id"],"route_id")
            if rid in routes_seen:
                raise ReplayError("duplicate choice-space route")
            routes_seen.add(rid)
            _prose(route["candidate_path"],"candidate_path",500)
            _prose(route["required_evidence"],"required_evidence",500)
            if route["feasibility_status"]!="unknown" or route["route_observed"] is not None:
                raise ReplayError("hypothetical alternative route is not observed feasibility")
        gates=case["discriminating_evidence"]
        if not isinstance(gates,list) or not gates:
            raise ReplayError("must propose at least one independent discriminating test")
        gseen=set()
        for gate in gates:
            if not isinstance(gate,dict) or set(gate)!={
                "gate_id","kind","observation_needed",
                "quality_condition","status"}:
                raise ReplayError("independent evidence gate incomplete")
            gid=_id(gate["gate_id"],"gate_id")
            if gid in gseen: raise ReplayError("duplicate gate")
            gseen.add(gid)
            if gate["kind"] not in ALLOWED_VERIFICATION:
                raise ReplayError("unknown independent gate")
            _prose(gate["observation_needed"],"observation_needed",600)
            _prose(gate["quality_condition"],"quality_condition",550)
            if gate["status"]!="not_yet_verified":
                raise ReplayError("no fake real-world independent tests")
    return {
        "schema":"fsl/narrative-cases-validated/0.11",
        "case_count":len(cases),
        "analyst_authored_on":authored,
        "case_ids":sorted(ids),
        "first_interviews_retrieved_after_historical_baselines":True,
        "actual_causal_influences_certified":0,
        "actual_strategy_reversals_certified":0,
        "interpretation_winners_declared":0,
        "canonical_input_sha256":_sha(data),
    }


def replay_case(discourse,market,cases, *, case_id, as_of, mode="retrospective"):
    validate_cases(cases,discourse=discourse,market=market)
    _id(case_id,"case_id")
    _day(as_of,"as_of")
    if mode not in ("retrospective","strict_known_at_time"):
        raise ReplayError("unknown as-of evidence mode")
    case=next((x for x in cases["cases"] if x["case_id"]==case_id),None)
    if case is None:raise ReplayError("unknown longitudinal case")
    baseline=case["baseline_cutoff"]
    claims,interviews,events,event_sources=_index(discourse,market)
    if as_of<baseline:
        raise ReplayError("observation cutoff cannot be before public baseline")
    def _claim_item(claim_id):
        claim=claims[claim_id]; src=interviews[claim["source_id"]]
        released=src["published_on"]<=as_of
        received=src["first_captured_on"]<=as_of
        is_allowed=bool(released and (received or mode=="retrospective"))
        return {
            "claim_id":claim_id,"published_on":src["published_on"],
            "first_captured_on":src["first_captured_on"],
            "primary_source_url":src["transcript_url"] or src["url"],
            "source_locator":claim["source_locator"],
            "speaker":claim["speaker_id"],
            "paraphrase_zh_tw":claim["paraphrase_zh_tw"] if is_allowed else None,
            "modality":claim["modality"] if is_allowed else None,
            "topics":claim["topics"] if is_allowed else None,
            "is_visible_at_requested_cutoff":is_allowed,
            "publicly_published_as_of":released,
            "known_to_this_study_at_asof":bool(released and received),
            "retrospective_only":bool(released and not received),
            "historical_original_forecast_by_FSL":False,
        }
    base=[_claim_item(x) for x in case["baseline_claim_ids"]]
    later=[_claim_item(x) for x in case["later_claim_ids"]]
    ev=[]
    for eid in case["external_event_ids"]:
        item=events[eid]; src=event_sources[item["source_id"]]
        appeared=item["occurred_on"]<=as_of and src["published_on"]<=as_of
        known=src["first_captured_on"]<=as_of
        show=bool(appeared and (known or mode=="retrospective"))
        ev.append({
            "event_id":eid,"occurred_on":item["occurred_on"],
            "source_published_on":src["published_on"],
            "source_first_captured_on":src["first_captured_on"],
            "source_url":src["url"],
            "provider":item["provider"],
            "event_kind":item["kind"],
            "event_summary":item["claim"] if show else None,
            "source_proof_limit":item["proof_limit"] if show else None,
            "visible_at_asof":show,
            "retrospective_only":bool(appeared and not known),
            "proves_any_interview_intention":False,
            "proves_functional_AGI_ASI":False,
        })
    # The original speech is a historical observation; all alternative
    # interpretations below were authored by an analyst in 2026. If replayed
    # at an earlier cutoff they are hidden, even in retrospective mode.
    analysis_visible=cases["analyst_authored_on"]<=as_of
    probe=case["reversibility_probe"]
    forecast=[]
    for item in base+later:
        claim=claims[item["claim_id"]]
        due=claim.get("forecast")
        if not due or not item["is_visible_at_requested_cutoff"]:
            continue
        matured=as_of>due["target_by"]
        forecast.append({
            "claim_id":item["claim_id"],
            "target_by":due["target_by"],
            "speaker_probability":due["probability"],
            "definition_scope":due["definition_scope"],
            "status":"deadline_passed_needs_independent_adjudication" if matured
                     else "not_due",
            "predictive_success_known":None,
        })
    return {
        "schema":"fsl/longitudinal-narrative-replay/0.11",
        "case_id":case_id,"speaker_id":case["speaker_id"],
        "baseline_cutoff":baseline,"observation_as_of":as_of,
        "mode":mode,
        "baseline_utterances":base,
        "later_utterances":later,
        "later_official_product_events":ev,
        "analyst_interpretations_written_on":cases["analyst_authored_on"],
        "analyst_interpretations_visible_at_cutoff":analysis_visible,
        "alternative_interpretations":(
            case["candidate_interpretations"] if analysis_visible else []),
        "reversibility_probe":(probe if analysis_visible else None),
        "independent_evidence_requirements":(
            case["discriminating_evidence"] if analysis_visible else []),
        "explicit_non_claims":case["non_claims"] if analysis_visible else [],
        "dated_forecast_statuses":forecast,
        "new_independent_task_outcome_found":False,
        "actual_company_direction_identified":False,
        "private_belief_change_proved":False,
        "narrative_contradiction_proved":False,
        "causal_relation_proved":False,
        "reversal_or_irreversibility_proved":False,
        "documented_observation_count":sum(
            x["is_visible_at_requested_cutoff"] for x in base+later)+sum(
            x["visible_at_asof"] for x in ev),
        "warnings":[
            "Later source retrieval cannot be projected into original historical forecast knowledge.",
            "Later model/tool launches are not independent verification of AGI or the older speaker's criterion.",
            "No one interpretation wins without a preregistered independent discriminator.",
            "Choice-space counterfactual routes remain possible scenarios, not verified real options.",
            "A named technology or AGI label does not uniquely determine actual functional competence.",
        ],
    }


def replay_all(discourse,market,cases, *, as_of,mode="retrospective"):
    validate_cases(cases,discourse=discourse,market=market)
    _day(as_of,"as_of")
    rows=[]
    for item in cases["cases"]:
        if item["baseline_cutoff"]<=as_of:
            rows.append(replay_case(discourse,market,cases,case_id=item["case_id"],
                                    as_of=as_of,mode=mode))
    return {
        "schema":"fsl/narrative-replay-multi-case/0.11",
        "as_of":as_of,"mode":mode,
        "cases":rows,
        "identified_causal_effects":0,
        "actual_reversibility_certificates":0,
        "AGI_ASI_verified_claims":0,
    }
