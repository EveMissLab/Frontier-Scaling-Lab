"""Historical AI task costs: observed-at-time, modern replay, counterfactual.

The strongest historical failure mode is to quote 2026 token prices for a
2024 model and claim that a 2024 user could buy a completed 2026 Agent task.
Historical tool availability, quality gate feasibility and success frequency
must be independently grounded. Unidentifiable is an explicit finding.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from decimal import Decimal
from .comparison import (
    EconomicsError, _date, _url, _sha, _usd, _text, _strmoney, validate_task
)

MODES = (
    "contemporaneous_historical_observation",
    "present_day_legacy_replay",
    "historical_counterfactual"
)


def _tri_bool(x, key):
    if x is not True and x is not False and x is not None:
        raise EconomicsError(key+" must be true/false/null")
    return x


def _prob(x,key):
    if x is None: return None
    n=_usd(x,key)
    if n>1:raise EconomicsError("probability cannot exceed 1")
    return n


def historical_scenarios(data):
    """Give cost ranges only when all hard availability and assumption gates pass.

    Probabilities are explicitly hypothetical, even if a model release and a
    historical price source are authentic. A counterfactual model cannot be
    replayed by this function; it only checks and propagates assumptions.
    """
    if not isinstance(data,dict) or data.get("schema")!="fsl/historical-task-cost/0.8.2":
        raise EconomicsError("unknown historical study schema")
    task=validate_task(data.get("task"))
    _date(data.get("study_as_of"),"study_as_of")
    scenarios=data.get("scenarios")
    if not isinstance(scenarios,list) or not scenarios:
        raise EconomicsError("historical study needs >=1 named scenario")
    output=[]
    seen=set()
    for c in scenarios:
        keys=("scenario_id","model_id","model_revision","model_class_at_date",
              "historical_date","model_release_on","study_mode",
              "price_reference_on","price_source_url","price_basis",
              "model_accessible_then","required_tools_accessible_then",
              "task_spec_feasible_then","trial_success_probability",
              "attempt_cash_usd_interval","evidence_class",
              "assumptions_source_url")
        if not isinstance(c,dict) or any(k not in c for k in keys):
            raise EconomicsError("scenario lacks historical/financial/probability dimensions")
        sid=_text(c["scenario_id"],"scenario_id")
        if sid in seen:raise EconomicsError("duplicate historical scenario")
        seen.add(sid)
        for k in ("model_id","model_revision"):_text(c[k],k)
        if c["model_class_at_date"] not in ("frontier_at_time","other_at_time","unknown"):
            raise EconomicsError("historical frontier is a time-dependent classification")
        _date(c["historical_date"],"historical_date")
        _date(c["model_release_on"],"model_release_on")
        _date(c["price_reference_on"],"price_reference_on")
        if c["historical_date"]>data["study_as_of"]:
            raise EconomicsError("cannot project a future year as historical")
        if c["model_release_on"]>c["historical_date"] and c["model_accessible_then"] is True:
            raise EconomicsError("system cannot be available before model release")
        if c["study_mode"] not in MODES:
            raise EconomicsError("invalid historical observation/replay/counterfactual mode")
        if c["price_basis"] not in ("historical_at_time","present_day_replay","unavailable"):
            raise EconomicsError("historical and replay price bases must remain separate")
        if c["study_mode"]=="present_day_legacy_replay":
            if c["price_basis"] not in ("present_day_replay","unavailable"):
                raise EconomicsError("modern replay cannot quietly use historical billing as current")
        else:
            if c["price_basis"]=="present_day_replay":
                raise EconomicsError("present-day rates are not historical prices")
            if c["price_basis"]=="historical_at_time" and c["price_reference_on"]>c["historical_date"]:
                raise EconomicsError("later price list cannot prove historical price")
        if c["study_mode"]=="contemporaneous_historical_observation":
            # Real completed work requires individual attempt/acceptance receipts
            # rather than probability assumptions. Reuse the same-period panel.
            raise EconomicsError("observed historical trials belong in dated compare_cohorts panels")
        if c["evidence_class"] not in ("synthetic","hypothesis_with_sources"):
            raise EconomicsError("not an observational study, only a labeled hypothesis")
        _url(c["price_source_url"],"price_source_url")
        _url(c["assumptions_source_url"],"assumptions_source_url")
        availability={
            "model_accessible_then":_tri_bool(c["model_accessible_then"],"model_accessible_then"),
            "required_tools_accessible_then":_tri_bool(
                c["required_tools_accessible_then"],"required_tools_accessible_then"),
            "task_spec_feasible_then":_tri_bool(
                c["task_spec_feasible_then"],"task_spec_feasible_then"),
        }
        probs=c["trial_success_probability"]
        costs=c["attempt_cash_usd_interval"]
        if not isinstance(probs,dict) or set(probs)!={"low","high"}:
            raise EconomicsError("success probability needs low/high or null")
        if not isinstance(costs,dict) or set(costs)!={"low","high"}:
            raise EconomicsError("attempt cost needs low/high or null")
        lo_p=_prob(probs["low"],"p_low")
        hi_p=_prob(probs["high"],"p_high")
        if (lo_p is None)!=(hi_p is None):
            raise EconomicsError("success range must be both provided or both null")
        if lo_p is not None and lo_p>hi_p:
            raise EconomicsError("invalid probability interval ordering")
        if (costs["low"] is None)!=(costs["high"] is None):
            raise EconomicsError("attempt cost range must be both available or both null")
        lo_cost=hi_cost=None
        if costs["low"] is not None:
            lo_cost=_usd(costs["low"],"low attempt cost")
            hi_cost=_usd(costs["high"],"high attempt cost")
            if hi_cost<lo_cost:raise EconomicsError("attempt cost interval not ordered")
        missing=[]
        if c["price_basis"]=="unavailable" or lo_cost is None:
            missing.append("matched historical/priced attempt cost and billing route")
        if lo_p is None:
            missing.append("observed or explicitly assumed completion probability range")
        for key,value in availability.items():
            if value is None:missing.append("historical tool/model/task availability "+key)
        if c["study_mode"]=="present_day_legacy_replay":
            # The counterfactual engine is not a modern replay execution engine.
            # Even if a model is available, it needs a repeatable real trial.
            status="modern_replay_requires_real_trials"
        elif any(x is False for x in availability.values()):
            status="not_feasible_in_original_historical_environment"
        elif missing:
            status="historical_cost_unidentifiable"
        else:
            status="conditional_counterfactual_range_not_observed"
        expected_interval=None
        unbounded=False
        if status=="conditional_counterfactual_range_not_observed":
            if hi_p==0:
                status="hypothesis_assumes_zero_success_no_finite_completed_cost"
            else:
                # Repeated independent, equally distributed trials with constant
                # unit cost: E[cost/success] = C/p. This is an assumed retry model.
                lower=lo_cost/hi_p
                upper=hi_cost/lo_p if lo_p>0 else None
                expected_interval={
                    "lower_usd":_strmoney(lower),
                    "upper_usd":_strmoney(upper) if upper is not None else None,
                    "upper_not_finitely_bounded":upper is None
                }
                unbounded=upper is None
        output.append({
            "scenario_id":sid,
            "model_id":c["model_id"],
            "model_revision":c["model_revision"],
            "model_class_at_date":c["model_class_at_date"],
            "historical_date":c["historical_date"],
            "study_mode":c["study_mode"],
            "price_reference_on":c["price_reference_on"],
            "price_basis":c["price_basis"],
            "historical_availability":availability,
            "status":status,
            "missing_evidence":missing,
            "hypothetical_success_probability_interval":{
                "low":str(lo_p) if lo_p is not None else None,
                "high":str(hi_p) if hi_p is not None else None,
            },
            "hypothetical_attempt_cost_usd_interval":{
                "low":_strmoney(lo_cost) if lo_cost is not None else None,
                "high":_strmoney(hi_cost) if hi_cost is not None else None,
            },
            "conditional_expected_cost_per_accepted_outcome_usd":expected_interval,
            "assumed_retries_independent_and_identically_distributed":True,
            "human_rescue_cost_included":False,
            "actual_trial_was_replayed":False,
            "independently_verified_completion":False,
            "not_a_model_capability_proof":True,
        })
    return {
        "schema":"fsl/historical-task-result/0.8.2",
        "task_id":task["task_id"],
        "fixed_task_revision_sha256":task["task_revision_sha256"],
        "fixed_quality_gate_sha256":task["quality_gate_sha256"],
        "study_as_of":data["study_as_of"],
        "scenarios":output,
        "historical_cash_price_not_modern_substitution":True,
        "warnings":[
            "A historical model's tokenizer/rate does not establish ability to finish today's task.",
            "Modern replay uses contemporary runtime/tooling and is not historical availability.",
            "Unobservable legacy success rates MUST remain null rather than fabricated.",
            "Assumed iid retries are not valid for long, stateful autonomous work without evidence.",
            "If tools or task prerequisites did not exist, an at-time completed cost is not available.",
            "No proof of a task's historical feasibility, external product acceptance or AI autonomy.",
        ]
    }
