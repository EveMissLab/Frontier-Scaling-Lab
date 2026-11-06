"""Measured H50/H80 human-task time horizons on a preregistered task panel.

No secret model parameter inference or universal intelligence score is made.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import date
import hashlib
import json
import math
import random
import statistics
from urllib.parse import urlsplit


class HorizonError(ValueError):
    pass


def _prob(z):
    if z >= 0:
        q = math.exp(-min(z, 700.0))
        return 1.0/(1.0+q)
    q = math.exp(max(z, -700.0))
    return q/(1.0+q)


def _date(x):
    if not isinstance(x, str) or date.fromisoformat(x).isoformat() != x:
        raise HorizonError("expected canonical YYYY-MM-DD")
    return x


def _positive(x, field):
    if (isinstance(x, bool) or not isinstance(x, (int, float)) or
            not math.isfinite(x) or x <= 0):
        raise HorizonError(f"{field} must be positive finite")
    return float(x)


def _url(x):
    if not isinstance(x, str):
        raise HorizonError("source_url missing")
    p = urlsplit(x)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise HorizonError("source_url must be HTTPS without credentials")


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != "fsl/horizon-input/0.5":
        raise HorizonError("expected fsl/horizon-input/0.5")
    p = data.get("protocol")
    if not isinstance(p, dict):
        raise HorizonError("protocol missing")
    names = ("task_set_sha256","benchmark_version","domain","model_key",
             "model_revision","scaffold_key","tool_policy_sha256","prompt_sha256",
             "source_url","published_on","recorded_on","evaluation_mode")
    for name in names:
        if not isinstance(p.get(name), str) or not p[name].strip():
            raise HorizonError(f"protocol.{name} missing")
    for key in ("task_set_sha256","tool_policy_sha256","prompt_sha256"):
        val = p[key]
        if len(val) != 64 or any(c not in "0123456789abcdef" for c in val):
            raise HorizonError(f"{key} must be lowercase SHA-256")
    if p["evaluation_mode"] not in ("synthetic", "observational"):
        raise HorizonError("evaluation_mode must be synthetic or observational")
    _url(p["source_url"])
    _date(p["published_on"])
    _date(p["recorded_on"])
    if p["published_on"] > p["recorded_on"]:
        raise HorizonError("published_on exceeds recorded_on")
    budget = p.get("budget")
    if not isinstance(budget, dict) or set(budget) != {
        "max_total_tokens_per_task","max_wall_seconds_per_task","max_usd_per_task"}:
        raise HorizonError("budget needs fixed token, time and USD limits")
    for name,value in budget.items():
        _positive(value, "budget."+name)
    rows=data.get("tasks")
    if not isinstance(rows, list) or len(rows)<12:
        raise HorizonError("at least 12 independently defined tasks are required")
    seen=set()
    durations=set()
    total_s=total_n=0
    for row in rows:
        if not isinstance(row, dict):
            raise HorizonError("task must be an object")
        task_id=row.get("task_id")
        if not isinstance(task_id,str) or not task_id.strip() or task_id in seen:
            raise HorizonError("task_id must be nonempty and unique")
        seen.add(task_id)
        durations.add(_positive(row.get("human_expert_minutes"),"human_expert_minutes"))
        n,s = row.get("attempts"),row.get("successes")
        if any(isinstance(x,bool) or not isinstance(x,int) for x in (n,s)):
            raise HorizonError("attempts and successes must be integers")
        if n<3 or s<0 or s>n:
            raise HorizonError("need >=3 attempts and successes within [0,attempts]")
        total_s+=s
        total_n+=n
    if len(durations)<4 or max(durations)/min(durations)<4:
        raise HorizonError("need 4+ distinct task difficulties spanning at least 4x")
    if total_s==0 or total_s==total_n:
        raise HorizonError("all-fail/all-pass sample cannot identify horizon")
    return data


def _fit(rows):
    """Penalized binomial logistic fit against centered log human-task duration."""
    x=[math.log(t["human_expert_minutes"]) for t in rows]
    center=statistics.mean(x)
    x=[v-center for v in x]
    n=[t["attempts"] for t in rows]
    y=[t["successes"] for t in rows]
    total=sum(n)
    p=min(0.999,max(0.001,sum(y)/total))
    a,b=math.log(p/(1-p)),-1.0
    ridge=0.15
    for _ in range(100):
        ps=[_prob(a+b*xi) for xi in x]
        w=[ni*max(1e-9,pi*(1-pi)) for ni,pi in zip(n,ps)]
        g0=sum(yi-ni*pi for yi,ni,pi in zip(y,n,ps))-ridge*a
        g1=sum((yi-ni*pi)*xi for yi,ni,pi,xi in zip(y,n,ps,x))-ridge*b
        h00=sum(w)+ridge
        h01=sum(wi*xi for wi,xi in zip(w,x))
        h11=sum(wi*xi*xi for wi,xi in zip(w,x))+ridge
        det=h00*h11-h01*h01
        if det<=1e-10:
            return None
        da=(h11*g0-h01*g1)/det
        db=(h00*g1-h01*g0)/det
        da=max(-1,min(1,da))
        db=max(-1,min(1,db))
        a+=da
        b+=db
        if max(abs(da),abs(db))<1e-8:
            break
    if not math.isfinite(a+b) or b>=-0.03:
        return None
    return (a,b,center)


def _horizon(fit,q,*,duration_range):
    if fit is None:
        return None
    a,b,center=fit
    logtime=center+(math.log(q/(1-q))-a)/b
    if not math.log(duration_range[0])<=logtime<=math.log(duration_range[1]):
        return None
    value=math.exp(logtime)
    return value if math.isfinite(value) and value>0 else None


def horizon_estimate(data, *, bootstrap=200, seed=20261107):
    validate(data)
    if isinstance(bootstrap,bool) or not isinstance(bootstrap,int) or not 0<=bootstrap<=2000:
        raise HorizonError("bootstrap must be 0..2000")
    tasks=data["tasks"]
    drange=(min(t["human_expert_minutes"] for t in tasks),
            max(t["human_expert_minutes"] for t in tasks))
    fit=_fit(tasks)
    point={str(q):_horizon(fit,q,duration_range=drange) for q in (0.5,0.8)}
    samples={"0.5":[],"0.8":[]}
    if bootstrap:
        rng=random.Random(seed)
        for _ in range(bootstrap):
            draw=[tasks[rng.randrange(len(tasks))] for __ in tasks]
            f=_fit(draw)
            for q in (0.5,0.8):
                value=_horizon(f,q,duration_range=drange)
                if value is not None:
                    samples[str(q)].append(value)
    summary={}
    for q in ("0.5","0.8"):
        s=sorted(samples[q])
        ci=None if not bootstrap or len(s)<max(30,bootstrap//2) else [
            s[int(0.025*(len(s)-1))],s[int(0.975*(len(s)-1))]]
        summary[q]={
            "human_expert_minutes":point[q],
            "task_cluster_bootstrap_95_percentile_interval":ci,
            "bootstrap_usable":len(s),
            "status":"within_observed_duration_support" if point[q] is not None
                     else "not_identified_within_task_duration_range",
        }
    p=data["protocol"]
    protocol_abstract={k:v for k,v in p.items() if k not in ("model_key","model_revision")}
    phash=hashlib.sha256(json.dumps(protocol_abstract,sort_keys=True,
                                    ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "schema":"fsl/horizon-estimate/0.5",
        "model_key":p["model_key"],"model_revision":p["model_revision"],
        "domain":p["domain"],"scaffold":p["scaffold_key"],
        "published_on":p["published_on"],"recorded_on":p["recorded_on"],
        "evaluation_mode":p["evaluation_mode"],"protocol_hash":phash,
        "n_tasks":len(tasks),"n_attempts":sum(t["attempts"] for t in tasks),
        "total_success_fraction":sum(t["successes"] for t in tasks)/sum(t["attempts"] for t in tasks),
        "observed_human_duration_minutes":list(drange),"horizon":summary,
        "identification":"descriptive_task_distribution_specific_not_general_cognition",
        "limits":[
            "H50/H80 are HUMAN task durations, not AI wall-clock runtime.",
            "No extrapolation beyond task duration support is reported.",
            "Cluster bootstrap assumes resampled tasks represent the task distribution.",
            "Check task contamination, human-duration baselines and selection bias.",
            "Cannot infer proprietary model weights, capacity causality or universal cognition.",
        ],
    }


def compare_matched(baseline,candidate,*,bootstrap=200,seed=20261107):
    validate(baseline)
    validate(candidate)
    p0,p1=baseline["protocol"],candidate["protocol"]
    same=("task_set_sha256","benchmark_version","domain",
          "tool_policy_sha256","prompt_sha256","budget","evaluation_mode")
    if any(p0[k]!=p1[k] for k in same):
        raise HorizonError("different task sets/protocol/budgets cannot be compared")
    a={t["task_id"]:t for t in baseline["tasks"]}
    b={t["task_id"]:t for t in candidate["tasks"]}
    if a.keys()!=b.keys() or any(a[k]["human_expert_minutes"]!=b[k]["human_expert_minutes"] for k in a):
        raise HorizonError("task IDs and human difficulty anchors must match")
    if p0["scaffold_key"] != p1["scaffold_key"]:
        kind=("scaffold_or_agent_difference" if
              (p0["model_key"],p0["model_revision"])==
              (p1["model_key"],p1["model_revision"]) else "model_and_scaffold_confounded")
    else:
        kind="model_revision_difference" if (
            p0["model_key"],p0["model_revision"]) != (
            p1["model_key"],p1["model_revision"]) else "retest_only"
    a0=horizon_estimate(baseline,bootstrap=bootstrap,seed=seed)
    a1=horizon_estimate(candidate,bootstrap=bootstrap,seed=seed)
    metrics={}
    for q in ("0.5","0.8"):
        h0=a0["horizon"][q]["human_expert_minutes"]
        h1=a1["horizon"][q]["human_expert_minutes"]
        metrics[q]={
            "baseline_human_minutes":h0,"candidate_human_minutes":h1,
            "task_horizon_ratio":h1/h0 if h0 is not None and h1 is not None else None,
            "status":"paired_protocol_descriptive" if h0 is not None and h1 is not None
                     else "not_identified",
        }
    return {
        "schema":"fsl/horizon-comparison/0.5",
        "matched_task_count":len(a),"attribution":kind,
        "reliability_horizon_ratios":metrics,
        "general_intelligence_multiplier":None,
        "is_synthetic":p0["evaluation_mode"]=="synthetic",
        "warning":"Domain-specific observed task horizon only, not cognitive IQ or causal compute effect.",
    }
