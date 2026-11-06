"""Within-era task purchasing power, distinguished from general intelligence.

No fabricated prices, task success probabilities, or old-model availability.
The scoring unit is an independently defined accepted *functional outcome*,
not a token, rating point, or benchmark rank.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit


class EconomicsError(ValueError):
    pass


SHA = re.compile(r"[0-9a-f]{64}\Z")
YM = re.compile(r"\d{4}-\d{2}\Z")


def _hash(x):
    return sha256(json.dumps(x, sort_keys=True, ensure_ascii=False,
                 separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _date(x, field):
    if not isinstance(x, str):
        raise EconomicsError(f"{field} must be YYYY-MM-DD")
    try:
        if date.fromisoformat(x).isoformat() != x:
            raise ValueError()
    except ValueError as exc:
        raise EconomicsError(f"invalid {field}") from exc
    return x


def _stamp(x,field):
    from datetime import datetime, timezone
    if not isinstance(x,str):
        raise EconomicsError(field+" must include timezone")
    try:
        p=datetime.fromisoformat(x.replace("Z","+00:00"))
        if p.tzinfo is None: raise ValueError()
        return p.astimezone(timezone.utc)
    except ValueError as exc:
        raise EconomicsError(f"invalid {field}") from exc


def _url(x,field):
    if not isinstance(x,str): raise EconomicsError(field+" requires source URL")
    p=urlsplit(x)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise EconomicsError(field+" needs HTTPS source URL")
    return x


def _text(x,field):
    if not isinstance(x,str) or not x.strip() or len(x)>250:
        raise EconomicsError(f"{field} needs bounded nonempty text")
    return x


def _sha(x,field):
    if not isinstance(x,str) or SHA.fullmatch(x) is None:
        raise EconomicsError(field+" needs lowercase SHA256")
    return x


def _usd(x,field):
    if isinstance(x,bool) or not isinstance(x,(str,int,float,Decimal)):
        raise EconomicsError(f"{field} must be a nonnegative USD decimal")
    try:
        v=Decimal(str(x))
    except InvalidOperation as exc:raise EconomicsError(field+" invalid") from exc
    if not v.is_finite() or v<0: raise EconomicsError(field+" must be nonnegative finite")
    return v


def _strmoney(x):
    return format(x.quantize(Decimal("0.000001")),"f")


def validate_task(t):
    keys=("task_id","task_revision_sha256","quality_gate_sha256",
          "environment_sha256","budget_policy_sha256",
          "reference_source_url")
    if not isinstance(t,dict) or any(x not in t for x in keys):
        raise EconomicsError("task contract has missing controls")
    _text(t["task_id"],"task_id")
    for k in keys[1:5]:_sha(t[k],k)
    _url(t["reference_source_url"],"task reference")
    return t


def compare_cohorts(data):
    """Compare *reported* outcomes within one matched task and calendar month.

    Monetary amounts are USD and can use two distinct bases:
    full-cycle monthly cash obligation versus explicitly allocated costs.
    No run can be marked independently certified by this estimator alone.
    """
    if not isinstance(data,dict) or data.get("schema")!="fsl/task-purchasing-power/0.8.2":
        raise EconomicsError("unknown comparison input schema")
    task=validate_task(data.get("task"))
    period=data.get("evaluation_month")
    if not isinstance(period,str) or YM.fullmatch(period) is None:
        raise EconomicsError("evaluation_month must be YYYY-MM")
    _date(period+"-01","evaluation_month")
    if data.get("evidence_class") not in ("synthetic","observational"):
        raise EconomicsError("evidence class must be synthetic or observational")
    design=data.get("design")
    if design not in ("same_model_access","cross_model_matched_runtime","natural_product_path"):
        raise EconomicsError("invalid study design")
    candidates=data.get("cohorts")
    if not isinstance(candidates,list) or len(candidates)<2:
        raise EconomicsError("at least two access/model cohorts required")
    seen=set()
    results=[]
    identities=set()
    runtimes=set()
    for c in candidates:
        required=("cohort_id","model_id","model_revision","model_class",
                  "provider","plan_id","billing_route","runtime_sha256",
                  "price_snapshot_on","pricing_source_url","monthly_subscription_usd",
                  "subscription_allocation_fraction","trials")
        if not isinstance(c,dict) or any(k not in c for k in required):
            raise EconomicsError("candidate missing required source/model/billing fields")
        cid=_text(c["cohort_id"],"cohort_id")
        if cid in seen:raise EconomicsError("duplicate cohort")
        seen.add(cid)
        for key in ("model_id","model_revision","provider","plan_id"):
            _text(c[key],key)
        if c["model_class"] not in ("frontier_at_time","other_at_time","unknown"):
            raise EconomicsError("frontier is an as-of class, not a universal ranking")
        if c["billing_route"] not in ("subscription","api","local","hybrid"):
            raise EconomicsError("invalid billing route")
        _sha(c["runtime_sha256"],"runtime_sha256")
        _url(c["pricing_source_url"],"pricing_source_url")
        _date(c["price_snapshot_on"],"price_snapshot_on")
        if c["price_snapshot_on"] > period+"-28":
            # A source captured during the study month is admissible, not a
            # later retroactive catalogue update pretending to be earlier.
            if c["price_snapshot_on"][:7]!=period:
                raise EconomicsError("future pricing source cannot price an earlier cohort")
        if c["price_snapshot_on"][:7]>period:
            raise EconomicsError("pricing snapshot after study period")
        plan=_usd(c["monthly_subscription_usd"],"monthly_subscription_usd")
        if c["billing_route"] in ("api","local") and plan!=0:
            raise EconomicsError("API/local-only cohort cannot use subscription cash charge")
        share=_usd(c["subscription_allocation_fraction"],"subscription_allocation_fraction")
        if share>1:raise EconomicsError("subscription allocation must be <= 1")
        identities.add((c["model_id"],c["model_revision"]))
        runtimes.add(c["runtime_sha256"])
        trials=c["trials"]
        if not isinstance(trials,list) or not trials:
            raise EconomicsError("cohort needs actual attempts, including failures")
        ids=set()
        accepted=failed=censored=0
        variable=Decimal("0")
        assisted=Decimal("0")
        accepted_claim_ids=[]
        for t in trials:
            keys=("trial_id","evaluated_on","outcome","variable_cash_usd",
                  "human_assist_hours","evidence_url","outcome_sha256")
            if not isinstance(t,dict) or any(x not in t for x in keys):
                raise EconomicsError("trial requires money, outcome and source metadata")
            tid=_text(t["trial_id"],"trial_id")
            if tid in ids:raise EconomicsError("duplicate trial id")
            ids.add(tid)
            d=_date(t["evaluated_on"],"evaluated_on")
            if d[:7]!=period:raise EconomicsError("trial must be from the same evaluation month")
            _url(t["evidence_url"],"trial evidence_url")
            outcome=t["outcome"]
            if outcome not in ("accepted_reported","failed_reported","censored"):
                raise EconomicsError("trial outcome unknown")
            if outcome=="accepted_reported":
                _sha(t["outcome_sha256"],"outcome_sha256")
                accepted+=1;accepted_claim_ids.append(tid)
            elif outcome=="failed_reported":
                failed+=1
            else:
                censored+=1
            variable+=_usd(t["variable_cash_usd"],"variable_cash_usd")
            assisted+=_usd(t["human_assist_hours"],"human_assist_hours")
        full_cash=plan+variable
        allocated=plan*share+variable
        resolved=accepted+failed
        reported_cost_per=None
        capacity_per_100usd=None
        if censored==0 and accepted>0:
            reported_cost_per=_strmoney(allocated/accepted)
            if allocated>0:
                capacity_per_100usd=_strmoney(Decimal(100)*Decimal(accepted)/allocated)
        results.append({
            "cohort_id":cid,"model_id":c["model_id"],
            "model_revision":c["model_revision"],
            "model_class":c["model_class"],"provider":c["provider"],
            "plan_id":c["plan_id"],"billing_route":c["billing_route"],
            "runtime_sha256":c["runtime_sha256"],
            "pricing_snapshot_on":c["price_snapshot_on"],
            "reported_attempts":len(trials),"reported_accepted":accepted,
            "reported_failed":failed,"unresolved_censored":censored,
            "conditional_reported_success_rate":(accepted/resolved if resolved else None),
            "human_assistance_hours_claimed":_strmoney(assisted),
            "variable_cash_usd":_strmoney(variable),
            "subscription_monthly_cash_usd":_strmoney(plan),
            "total_cycle_cash_obligation_usd":_strmoney(full_cash),
            "subscription_allocation_fraction":str(share),
            "allocated_experiment_spend_usd":_strmoney(allocated),
            "reported_cost_per_accepted_usd":reported_cost_per,
            "reported_accepted_results_per_100_allocated_usd":capacity_per_100usd,
            "accepted_claim_trial_ids":accepted_claim_ids,
            "independent_verification_performed_by_this_code":False,
            "notes":["The acceptance evidence link was not visited or authenticated.",
                     "Cost per reported acceptance includes unsuccessful attempts.",
                     "Full subscription price is a monthly access obligation, not marginal task price.",
                     "Censored trials prevent a single definitive reported cost-per-success."]
        })
    if design=="same_model_access" and (len(identities)!=1 or len(runtimes)!=1):
        raise EconomicsError("same_model_access must fix model revision and runtime")
    if design=="cross_model_matched_runtime" and len(runtimes)!=1:
        raise EconomicsError("cross_model_matched_runtime must fix the runtime/scaffold")
    # Different runtimes in natural product access are valid, but confounded.
    valid=[r for r in results if r["reported_cost_per_accepted_usd"] is not None]
    best=None
    if valid and len(valid)>1:
        best=min(valid,key=lambda r:Decimal(r["reported_cost_per_accepted_usd"]))["cohort_id"]
    return {
        "schema":"fsl/task-purchasing-power-result/0.8.2",
        "task_id":task["task_id"],
        "fixed_quality_gate_sha256":task["quality_gate_sha256"],
        "fixed_budget_policy_sha256":task["budget_policy_sha256"],
        "evaluation_month":period,"evidence_class":data["evidence_class"],
        "study_design":design,
        "scope":"matched_model_and_runtime_access_comparison" if design=="same_model_access"
                else "matched_runtime_cross_model_comparison" if design=="cross_model_matched_runtime"
                else "product_access_package_confounded_by_model_tools_and_runtime",
        "cohorts":results,
        "lowest_reported_allocated_cost_cohort":best,
        "claim":"descriptive_reported_purchasing_power_not_verified_general_intelligence",
        "has_independently_certified_result":False,
        "historical_reconstruction":False,
        "limitations":[
            "Same-period comparison alone cannot isolate intrinsic model capability from access quotas.",
            "Do not compare studies with different quality gates, task, runtime or budgets as if identical.",
            "Different subscription prices do not imply known plan-token quotas.",
            "Reported acceptance must be independently reproduced before certification.",
            "Censoring, retries, varying human assistance and sampling uncertainty affect cost.",
            "Winning in a synthetic experiment is not an empirical provider recommendation."
        ],
    }
