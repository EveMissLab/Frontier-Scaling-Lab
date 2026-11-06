"""Subscription/API spend & quota interruptions for REAL or synthetic Agent runs.

Does not turn a higher plan price into measured model capability. Subscriptions,
purchased credits and API token billing are separate accounting treatments.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import json
import sqlite3

class CostError(ValueError): pass

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS affordability_runs (
 run_id TEXT PRIMARY KEY,
 evidence_class TEXT NOT NULL CHECK(evidence_class IN ('synthetic','observational')),
 provider TEXT NOT NULL,
 plan_id TEXT NOT NULL,
 billing_mode TEXT NOT NULL CHECK(billing_mode IN ('subscription','api','local','hybrid')),
 plan_price_usd TEXT NOT NULL,
 plan_source_url TEXT,
 price_as_of TEXT NOT NULL,
 starts_at TEXT NOT NULL,
 ends_at TEXT NOT NULL,
 usage_json TEXT NOT NULL,
 summary_sha256 TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS affordability_runs_no_update BEFORE UPDATE ON affordability_runs
 BEGIN SELECT RAISE(ABORT,'immutable cost run'); END;
CREATE TRIGGER IF NOT EXISTS affordability_runs_no_delete BEFORE DELETE ON affordability_runs
 BEGIN SELECT RAISE(ABORT,'immutable cost run'); END;
"""

def _dt(value):
    if not isinstance(value,str): raise CostError("ISO UTC or timezone-aware timestamp required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        if dt.tzinfo is None: raise ValueError("missing offset")
        return dt.astimezone(timezone.utc)
    except ValueError as exc: raise CostError("invalid timezone-aware timestamp") from exc

def _money(x,field):
    if isinstance(x,bool) or not isinstance(x,(str,int,float,Decimal)): raise CostError(field+" needs USD decimal")
    try: d=Decimal(str(x))
    except InvalidOperation as exc: raise CostError(field+" invalid decimal") from exc
    if not d.is_finite() or d<0: raise CostError(field+" must be nonnegative finite USD")
    return d

def _count(x,field):
    if isinstance(x,bool) or not isinstance(x,int) or x<0: raise CostError(field+" must be nonnegative int")
    return x

def _url(value):
    from urllib.parse import urlsplit
    if not isinstance(value,str): raise CostError("evidence URL required")
    u=urlsplit(value)
    if u.scheme!="https" or not u.hostname or u.username or u.password:
        raise CostError("evidence URL must be HTTPS")
    return value

def _hash(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,
                  separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()

def connect(path="data/affordability.sqlite"):
    path=Path(path) if path!=":memory:" else path
    if path!=":memory:": path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path))
    db.row_factory=sqlite3.Row
    db.executescript(SCHEMA)
    return db

def analyze(data):
    """Compute **observed** cash ledger, not unknown plan allowance token estimates.

    subscription_price_usd: full paid monthly outlay, not marginal run price.
    included_credit_consumed_usd: allocated entitlement usage, NOT new cash.
    purchased_credit_consumed_usd: cash-valued purchased credits consumed,
      excluding API events; only if independently billed.
    api event: explicit dated USD / 1M input, cached input and output rates.
    """
    if not isinstance(data,dict) or data.get("schema")!="fsl/affordability-input/0.8.1":
        raise CostError("invalid schema")
    p=data.get("access")
    if not isinstance(p,dict): raise CostError("access object required")
    required=("run_id","evidence_class","provider","plan_id","billing_mode",
              "price_as_of","starts_at","ends_at","monthly_subscription_usd")
    if any(x not in p for x in required): raise CostError("incomplete access identity")
    for k in ("run_id","provider","plan_id"):
        if not isinstance(p[k],str) or not p[k].strip(): raise CostError("missing "+k)
    if p["evidence_class"] not in ("synthetic","observational"): raise CostError("invalid evidence class")
    if p["billing_mode"] not in ("subscription","api","local","hybrid"):
        raise CostError("invalid billing route")
    begin,end=_dt(p["starts_at"]),_dt(p["ends_at"])
    if end<=begin: raise CostError("end must follow start")
    if p["billing_mode"] in ("subscription","hybrid"):
        _url(p.get("plan_source_url"))
    plan=_money(p["monthly_subscription_usd"],"monthly_subscription_usd")
    if p["billing_mode"] in ("api","local") and plan:
        raise CostError("subscription outlay must be zero on API/local-only runs")
    price_day=p["price_as_of"]
    if not isinstance(price_day,str) or len(price_day)!=10:
        raise CostError("price_as_of must be YYYY-MM-DD")
    try:
        if datetime.fromisoformat(price_day).date().isoformat()!=price_day:
            raise ValueError("noncanonical")
    except ValueError as exc: raise CostError("invalid price_as_of") from exc
    activity=data.get("activity_windows",[])
    costs=data.get("charges",[])
    interruptions=data.get("interruptions",[])
    if not all(isinstance(q,list) for q in (activity,costs,interruptions)):
        raise CostError("activity/charges/interruptions must be lists")
    # Activity windows count actual observed execution, not idle wall time.
    intervals=[]
    for x in activity:
        if not isinstance(x,dict) or set(x)!={"start","end","source_url"}:
            raise CostError("activity requires start/end/source_url only")
        _url(x["source_url"])
        a,b=_dt(x["start"]),_dt(x["end"])
        if not begin<=a<b<=end: raise CostError("activity interval lies outside run")
        intervals.append((a,b))
    intervals.sort()
    union=[]
    for a,b in intervals:
        if union and a<=union[-1][1]:
            union[-1]=(union[-1][0],max(union[-1][1],b))
        else:union.append((a,b))
    observed_hours=sum((b-a).total_seconds() for a,b in union)/3600
    wall_hours=(end-begin).total_seconds()/3600
    blocked_seconds=0
    quota_count=0
    reasons={}
    for x in interruptions:
        if not isinstance(x,dict) or set(x)!={"start","end","reason","source_url"}:
            raise CostError("interruptions need start/end/reason/source_url")
        _url(x["source_url"])
        a,b=_dt(x["start"]),_dt(x["end"])
        if not begin<=a<b<=end: raise CostError("interruption outside run")
        if x["reason"] not in ("quota_exhausted","rate_limit","tool_failure","other"):
            raise CostError("unknown interruption reason")
        if x["reason"] in ("quota_exhausted","rate_limit"):
            quota_count+=1
        reasons[x["reason"]]=reasons.get(x["reason"],0)+1
        blocked_seconds+=(b-a).total_seconds()
    # Blocked time can overlap; do not equate summed duration to unique downtime.
    api_usd=Decimal(0)
    paid_credits=Decimal(0)
    included_credits=Decimal(0)
    tool_usd=Decimal(0)
    infrastructure_usd=Decimal(0)
    seen=set()
    usage_records=[]
    for e in costs:
        if not isinstance(e,dict): raise CostError("each charge must be an object")
        typ=e.get("type")
        cid=e.get("id")
        if not isinstance(cid,str) or not cid or cid in seen: raise CostError("charge ids must be unique")
        seen.add(cid)
        timestamp=_dt(e.get("at"))
        if timestamp<begin or timestamp>end: raise CostError("charge outside run")
        _url(e.get("source_url"))
        if typ=="api_tokens":
            if p["billing_mode"] not in ("api","hybrid"):
                raise CostError("token API charges on non-API route")
            keys=("uncached_input_tokens","cached_input_tokens","output_tokens")
            n={k:_count(e.get(k),k) for k in keys}
            rates=e.get("usd_per_million")
            if not isinstance(rates,dict) or set(rates)!={"uncached_input","cached_input","output"}:
                raise CostError("token prices must explicitly have three rates")
            if "pricing_source_url" not in e:raise CostError("API price requires source")
            _url(e["pricing_source_url"])
            rate={k:_money(v,k) for k,v in rates.items()}
            value=(Decimal(n["uncached_input_tokens"])*rate["uncached_input"]
                   +Decimal(n["cached_input_tokens"])*rate["cached_input"]
                   +Decimal(n["output_tokens"])*rate["output"])/Decimal(1000000)
            api_usd+=value
            usage_records.append({"id":cid,"type":typ,"usd":str(value),
                                  "token_counts":n})
        elif typ=="purchased_credit":
            if p["billing_mode"] not in ("subscription","hybrid"):
                raise CostError("purchased plan credits require paid subscription route")
            amount=_money(e.get("usd"),"purchased_credit usd")
            paid_credits+=amount
            usage_records.append({"id":cid,"type":typ,"usd":str(amount)})
        elif typ=="included_credit":
            if p["billing_mode"] not in ("subscription","hybrid"):
                raise CostError("included plan credits require paid subscription route")
            value=_money(e.get("usd"),"included_credit usd")
            included_credits+=value
            usage_records.append({"id":cid,"type":typ,"usd":"0",
                                  "included_credit_used_usd_equivalent":str(value)})
        elif typ=="external_tool":
            value=_money(e.get("usd"),"tool charge usd")
            tool_usd+=value
            usage_records.append({"id":cid,"type":typ,"usd":str(value)})
        elif typ=="local_compute":
            value=_money(e.get("usd"),"local compute charge usd")
            infrastructure_usd+=value
            usage_records.append({"id":cid,"type":typ,"usd":str(value)})
        else:
            raise CostError("unknown charge type")
    variable=api_usd+paid_credits+tool_usd+infrastructure_usd
    # Cost to start/maintain subscription in that billing cycle is full price,
    # regardless of just 2 days of usage; allocation is a separately disclosed
    # accounting assumption (not an actual cash payment).
    allocation_fraction=_money(data.get("monthly_subscription_allocation_fraction","1"),
                              "allocation_fraction")
    if allocation_fraction>1:raise CostError("allocation fraction cannot exceed 1")
    allocated=plan*allocation_fraction
    total_cash=plan+variable
    allocated_cost=allocated+variable
    return {
        "schema":"fsl/affordability-result/0.8.1",
        "run_id":p["run_id"],"provider":p["provider"],"plan_id":p["plan_id"],
        "evidence_class":p["evidence_class"],"billing_mode":p["billing_mode"],
        "price_as_of":price_day,"plan_price_source":p.get("plan_source_url"),
        "wall_hours":round(wall_hours,4),
        "observed_active_hours":round(observed_hours,4),
        "observed_active_share_of_wall":round(observed_hours/wall_hours,5),
        "quota_interruptions":quota_count,
        "interruption_counts":reasons,
        "sum_interruption_hours_upper_bound":round(blocked_seconds/3600,4),
        "monthly_subscription_outlay_usd":str(plan),
        "included_credits_used_usd_equivalent_not_cash":str(included_credits),
        "paid_variable_usd":{
            "api_tokens":str(api_usd),"purchased_credits":str(paid_credits),
            "external_tools":str(tool_usd),"local_compute":str(infrastructure_usd),
            "total":str(variable),
        },
        "total_monthly_cash_outlay_plus_variable_usd":str(total_cash),
        "allocated_subscription_usd_not_cash_payment":str(allocated),
        "allocated_experiment_cost_usd":str(allocated_cost),
        "charges":usage_records,
        "mission_completed_and_independently_verified":False,
        "cost_per_independently_verified_result_usd":None,
        "can_sustain_24h_verified":False,
        "can_sustain_48h_verified":False,
        "remaining_plan_allowance":"unknown_not_inferred_from_price",
        "available_models_or_tools":"not_inferred_from_plan_name",
        "note":("No automatic plan-capacity prediction. 24/48h requires independently "
                "observed continuous progress and accepted outcome. Time elapsed ≠ active work."),
    }

def save(db, data):
    result=analyze(data)
    p=data["access"]
    with db:
        db.execute("""INSERT INTO affordability_runs
          (run_id,evidence_class,provider,plan_id,billing_mode,plan_price_usd,
           plan_source_url,price_as_of,starts_at,ends_at,usage_json,summary_sha256)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
          (p["run_id"],p["evidence_class"],p["provider"],p["plan_id"],p["billing_mode"],
           str(_money(p["monthly_subscription_usd"],"monthly_subscription_usd")),
           p.get("plan_source_url"),p["price_as_of"],_dt(p["starts_at"]).isoformat(),
           _dt(p["ends_at"]).isoformat(),json.dumps(data,ensure_ascii=False,
                                                    sort_keys=True,allow_nan=False),
           _hash(result)))
    return result
