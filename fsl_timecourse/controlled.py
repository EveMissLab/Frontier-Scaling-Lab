"""Matched evaluation protocol and non-scalar task-capability vectors.

This is a PRE-REGISTRATION/VALIDATION mechanism, not a new benchmark and
not proof of 2–3x general cognition. Only later real controlled trials can
be used to populate the observational study layer.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
import json
import math
import sqlite3
from urllib.parse import urlsplit

from fsl_sources.catalog import connect as connect_catalog, stable_hash, iso_day


class TrialError(ValueError):
    pass


DDL = """
CREATE TABLE IF NOT EXISTS controlled_protocols (
 protocol_id TEXT PRIMARY KEY,
 axis TEXT NOT NULL,
 benchmark_key TEXT NOT NULL,
 benchmark_version TEXT NOT NULL,
 task_set_sha256 TEXT NOT NULL,
 scoring TEXT NOT NULL CHECK(scoring='binary_task_success'),
 max_tokens_per_task INTEGER NOT NULL CHECK(max_tokens_per_task>0),
 model_prompt_policy TEXT NOT NULL,
 tool_setup TEXT NOT NULL,
 source_url TEXT NOT NULL,
 recorded_on TEXT NOT NULL,
 protocol_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS controlled_trials (
 trial_id TEXT PRIMARY KEY,
 protocol_id TEXT NOT NULL REFERENCES controlled_protocols(protocol_id),
 model_key TEXT NOT NULL,
 model_version TEXT NOT NULL,
 run_mode TEXT NOT NULL CHECK(run_mode IN ('base','agent')),
 evaluated_on TEXT NOT NULL,
 published_on TEXT NOT NULL,
 recorded_on TEXT NOT NULL,
 data_class TEXT NOT NULL CHECK(data_class IN ('synthetic','observational')),
 verification TEXT NOT NULL CHECK(verification IN ('reported','independently_verified','synthetic')),
 success_count INTEGER NOT NULL CHECK(success_count>=0),
 task_count INTEGER NOT NULL CHECK(task_count>0),
 source_url TEXT NOT NULL,
 trial_sha256 TEXT NOT NULL,
 CHECK(success_count<=task_count)
);
CREATE TRIGGER IF NOT EXISTS controlled_protocols_no_update
 BEFORE UPDATE ON controlled_protocols BEGIN
 SELECT RAISE(ABORT,'immutable protocol'); END;
CREATE TRIGGER IF NOT EXISTS controlled_protocols_no_delete
 BEFORE DELETE ON controlled_protocols BEGIN
 SELECT RAISE(ABORT,'immutable protocol'); END;
CREATE TRIGGER IF NOT EXISTS controlled_trials_no_update
 BEFORE UPDATE ON controlled_trials BEGIN
 SELECT RAISE(ABORT,'immutable evaluation trial'); END;
CREATE TRIGGER IF NOT EXISTS controlled_trials_no_delete
 BEFORE DELETE ON controlled_trials BEGIN
 SELECT RAISE(ABORT,'immutable evaluation trial'); END;
"""


def connect(path="data/fsl_adaptive.sqlite"):
    db=connect_catalog(path)
    db.executescript(DDL)
    return db


def _url(value):
    p=urlsplit(value) if isinstance(value,str) else None
    if p is None or p.scheme!="https" or not p.hostname or p.password or p.username:
        raise TrialError("source_url must be HTTPS without credentials")
    return value


def _text(value,key):
    if not isinstance(value,str) or not value.strip():
        raise TrialError(f"{key} must be nonempty text")
    return value


def _int(value,key,*,min_value=0):
    if isinstance(value,bool) or not isinstance(value,int) or value<min_value:
        raise TrialError(f"{key} must be integer >= {min_value}")
    return value


def insert_protocol(db, protocol):
    required=(
        "protocol_id","axis","benchmark_key","benchmark_version",
        "task_set_sha256","scoring","max_tokens_per_task",
        "model_prompt_policy","tool_setup","source_url","recorded_on",
    )
    if not isinstance(protocol,dict) or not all(k in protocol for k in required):
        raise TrialError("missing controlled protocol fields")
    for field in required:
        if field not in ("max_tokens_per_task",):
            _text(protocol[field],field)
    if protocol["scoring"]!="binary_task_success":
        raise TrialError("v0.4 only supports counted binary task success")
    sha=protocol["task_set_sha256"]
    if len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        raise TrialError("task set must have a real lowercase SHA256")
    _url(protocol["source_url"])
    iso_day(protocol["recorded_on"])
    _int(protocol["max_tokens_per_task"],"max_tokens_per_task",min_value=1)
    fingerprint=stable_hash(protocol)
    with db:
        db.execute("""INSERT INTO controlled_protocols
          (protocol_id,axis,benchmark_key,benchmark_version,task_set_sha256,
           scoring,max_tokens_per_task,model_prompt_policy,tool_setup,
           source_url,recorded_on,protocol_sha256)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          tuple(protocol[k] for k in required)+(fingerprint,))
    return protocol["protocol_id"]


def insert_trial(db, trial):
    keys=(
        "trial_id","protocol_id","model_key","model_version","run_mode",
        "evaluated_on","published_on","recorded_on",
        "data_class","verification","success_count","task_count","source_url"
    )
    if not isinstance(trial,dict) or any(k not in trial for k in keys):
        raise TrialError("missing controlled trial fields")
    for key in keys:
        if key not in ("success_count","task_count"):
            _text(trial[key],key)
    if trial["run_mode"] not in ("base","agent"):
        raise TrialError("run_mode must be base or agent")
    if trial["data_class"] not in ("synthetic","observational"):
        raise TrialError("data_class must be synthetic or observational")
    if trial["verification"] not in ("reported","independently_verified","synthetic"):
        raise TrialError("invalid verification state")
    if trial["data_class"]=="synthetic" and trial["verification"]!="synthetic":
        raise TrialError("synthetic trial cannot claim verification")
    if trial["data_class"]=="observational" and trial["verification"]=="synthetic":
        raise TrialError("observations cannot be synthetic-labelled")
    _url(trial["source_url"])
    for k in ("evaluated_on","published_on","recorded_on"):
        iso_day(trial[k])
    if not trial["evaluated_on"]<=trial["published_on"]<=trial["recorded_on"]:
        raise TrialError("evaluation, publication, recording dates must be ordered")
    success=_int(trial["success_count"],"success_count")
    n=_int(trial["task_count"],"task_count",min_value=1)
    if success>n:
        raise TrialError("success_count cannot exceed task_count")
    proto=db.execute("""SELECT * FROM controlled_protocols WHERE protocol_id=?""",
                     (trial["protocol_id"],)).fetchone()
    if proto is None:
        raise TrialError("unknown task protocol")
    if proto["recorded_on"]>trial["recorded_on"]:
        raise TrialError("cannot record trial before its protocol was registered")
    fingerprint=stable_hash(trial)
    with db:
        db.execute("""INSERT INTO controlled_trials
          (trial_id,protocol_id,model_key,model_version,run_mode,
           evaluated_on,published_on,recorded_on,data_class,verification,
           success_count,task_count,source_url,trial_sha256)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          tuple(trial[k] for k in keys)+(fingerprint,))
    return trial["trial_id"]


def _wilson(success,n,z=1.96):
    p=success/n
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return [max(0.0,center-half),min(1.0,center+half)]


def compare(db, *, baseline_id, target_id, as_of):
    iso_day(as_of)
    if baseline_id==target_id:
        raise TrialError("baseline and target must be separate trials")
    cur=db.execute("""SELECT t.*,p.axis,p.benchmark_key,p.benchmark_version,
        p.task_set_sha256,p.max_tokens_per_task,p.model_prompt_policy,p.tool_setup,
        p.scoring,p.protocol_sha256
       FROM controlled_trials t JOIN controlled_protocols p USING(protocol_id)
       WHERE t.trial_id IN (?,?)""",(baseline_id,target_id)).fetchall()
    table={r["trial_id"]:dict(r) for r in cur}
    if baseline_id not in table or target_id not in table:
        raise TrialError("unknown baseline/target trial")
    baseline,target=table[baseline_id],table[target_id]
    for x in (baseline,target):
        if max(x["published_on"],x["recorded_on"])>as_of:
            raise TrialError("as-of cutoff forbids future publication/recording")
    if baseline["protocol_sha256"]!=target["protocol_sha256"]:
        raise TrialError("task sets, tool setup, scoring and token caps must match")
    if baseline["task_count"]!=target["task_count"]:
        raise TrialError("task_count mismatch: use paired registered task panels")
    if baseline["data_class"]!=target["data_class"]:
        raise TrialError("do not compare synthetic samples with real observations")
    if baseline["run_mode"] != target["run_mode"]:
        if baseline["model_key"]!=target["model_key"] or baseline["model_version"]!=target["model_version"]:
            raise TrialError("agent ablation must keep exact base model version fixed")
        comparison="agent_system_change"
    else:
        comparison="model_or_version_change"
    low=_wilson(baseline["success_count"],baseline["task_count"])
    high=_wilson(target["success_count"],target["task_count"])
    p0=baseline["success_count"]/baseline["task_count"]
    p1=target["success_count"]/target["task_count"]
    return {
        "schema":"fsl/controlled-pair/0.4",
        "axis":baseline["axis"],
        "benchmark":baseline["benchmark_key"],
        "protocol_id":baseline["protocol_id"],
        "protocol_sha256":baseline["protocol_sha256"],
        "task_set_sha256":baseline["task_set_sha256"],
        "as_of":as_of,
        "baseline_id":baseline_id,"target_id":target_id,
        "data_class":baseline["data_class"],
        "verification":[baseline["verification"],target["verification"]],
        "comparison_kind":comparison,
        "matched_token_cap_per_task":baseline["max_tokens_per_task"],
        "baseline":{"value":p0,"wilson":low,"n":baseline["task_count"]},
        "target":{"value":p1,"wilson":high,"n":target["task_count"]},
        "task_success_percentage_point_change":(p1-p0)*100,
        "task_success_rate_ratio_descriptive":(p1/p0 if p0>0 else None),
        "capability_multiplier":None,
        "cognitive_2_to_3x_claim_licensed":False,
        "limits":[
            "Same task set and resource ceiling do not prove identical actual token spend.",
            "Paired tasks may correlate: separate Wilson bounds are not a CI for a paired effect.",
            "Agent-system changes are not base-model-weight-only effects.",
            "Task success ratio is not a scalar measure of general intelligence.",
            "v0.4 validates protocol metadata but does not independently verify linked source text.",
        ],
    }


def vector(db, *, comparisons, as_of):
    """One entry per measured task axis/protocol, no weighted global score."""
    if not isinstance(comparisons,list) or not comparisons:
        raise TrialError("comparisons must be a nonempty list")
    entries=[]
    seen=set()
    for case in comparisons:
        if not isinstance(case,dict) or set(case)!={"baseline_id","target_id"}:
            raise TrialError("comparison entry needs baseline_id and target_id only")
        result=compare(db,baseline_id=case["baseline_id"],
                       target_id=case["target_id"],as_of=as_of)
        unique=(result["axis"],result["protocol_id"])
        if unique in seen:
            raise TrialError("duplicate task axis/protocol pair: no artificial replication")
        seen.add(unique)
        entries.append(result)
    return {
        "schema":"fsl/capability-vector/0.4",
        "as_of":as_of,"dimensions":len(entries),"axes":entries,
        "global_intelligence_score":None,
        "estimated_model_parameter_multiplier":None,
        "summary":"Observed task-wise success comparisons, not general cognition or parameter estimates.",
        "identification":("synthetic_demonstration_only"
                          if all(x["data_class"]=="synthetic" for x in entries)
                          else "source_reported_trials_require_independent_audit"),
    }
