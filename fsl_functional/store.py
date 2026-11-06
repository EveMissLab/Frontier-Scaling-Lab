"""Append-only mission evidence log. All external claims remain unverified claims.

This engine records weeks/months of *real wall-clock* mission evidence produced
outside ChatGPT. Synthetic fixtures cannot certify a real multi-month mission.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit


class MissionError(ValueError):
    pass


KINDS = {"game", "app", "art", "general_digital", "embodied"}
EVENTS = {
    "intent", "progress", "checkpoint", "goal_revision", "environment_change",
    "strategy_decision", "adaptation_judgement", "human_assist",
    "exception_escalation", "deliverable", "final_acceptance",
    "quality_review", "style_review", "task_switch", "domain_outcome",
    "safety_incident", "safety_resolution", "correction", "user_round",
}
ACTORS = {"user", "ai", "evaluator", "environment", "operator", "system"}
BANDS = {"days": 2.0, "weeks": 7.0, "months": 28.0}
MANDATORY = {
    "game": {"playable_end_to_end", "integrated_world_systems",
             "visual_or_distinctive_style", "stability_performance",
             "independent_user_acceptance", "rights_provenance"},
    "app": {"installable_functional_product", "integrated_workflows",
            "usability", "stability_security_privacy",
            "reference_quality", "independent_user_acceptance"},
    "art": {"finished_artifact", "style_coherence", "rights_provenance",
            "independent_review"},
    "general_digital": {"end_to_end_functionality", "integrated_delivery",
                        "independent_user_acceptance"},
    "embodied": {"physical_safety", "cross_domain_completion",
                 "goal_reinterpretation"},
}
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS functional_specs(
 spec_id TEXT PRIMARY KEY,
 track TEXT NOT NULL CHECK(track IN ('digital','embodied')),
 kind TEXT NOT NULL,
 title TEXT NOT NULL,
 reference_url TEXT NOT NULL,
 reference_date TEXT NOT NULL,
 created_at TEXT NOT NULL,
 min_duration_days REAL NOT NULL,
 max_user_rounds INTEGER NOT NULL,
 required_criteria_json TEXT NOT NULL,
 evidence_class TEXT NOT NULL CHECK(evidence_class IN ('synthetic','observational')),
 spec_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS functional_runs(
 run_id TEXT PRIMARY KEY,
 spec_id TEXT NOT NULL REFERENCES functional_specs(spec_id),
 system_key TEXT NOT NULL,
 system_revision TEXT NOT NULL,
 initiated_at TEXT NOT NULL,
 evidence_class TEXT NOT NULL CHECK(evidence_class IN ('synthetic','observational'))
);
CREATE TABLE IF NOT EXISTS functional_events(
 event_id TEXT PRIMARY KEY,
 run_id TEXT NOT NULL REFERENCES functional_runs(run_id),
 kind TEXT NOT NULL,
 actor TEXT NOT NULL,
 occurred_at TEXT NOT NULL,
 recorded_at TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 source_url TEXT,
 event_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS functional_events_by_run
 ON functional_events(run_id,occurred_at,recorded_at,event_id);
CREATE TRIGGER IF NOT EXISTS functional_specs_no_update
 BEFORE UPDATE ON functional_specs BEGIN SELECT RAISE(ABORT,'immutable spec'); END;
CREATE TRIGGER IF NOT EXISTS functional_specs_no_delete
 BEFORE DELETE ON functional_specs BEGIN SELECT RAISE(ABORT,'immutable spec'); END;
CREATE TRIGGER IF NOT EXISTS functional_runs_no_update
 BEFORE UPDATE ON functional_runs BEGIN SELECT RAISE(ABORT,'immutable run'); END;
CREATE TRIGGER IF NOT EXISTS functional_runs_no_delete
 BEFORE DELETE ON functional_runs BEGIN SELECT RAISE(ABORT,'immutable run'); END;
CREATE TRIGGER IF NOT EXISTS functional_events_no_update
 BEFORE UPDATE ON functional_events BEGIN SELECT RAISE(ABORT,'append-only events'); END;
CREATE TRIGGER IF NOT EXISTS functional_events_no_delete
 BEFORE DELETE ON functional_events BEGIN SELECT RAISE(ABORT,'append-only events'); END;
"""


def moment(value):
    if not isinstance(value, str):
        raise MissionError("UTC or offset-aware ISO-8601 timestamp required")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("missing timezone")
        return d.astimezone(timezone.utc)
    except ValueError as exc:
        raise MissionError(f"invalid timestamp: {value!r}") from exc


def day(value):
    try:
        d = datetime.fromisoformat(value)
        if d.date().isoformat() != value:
            raise ValueError("not a canonical date")
        return value
    except (ValueError, TypeError) as exc:
        raise MissionError("expected canonical YYYY-MM-DD") from exc


def https(value):
    if not isinstance(value, str):
        raise MissionError("source URL must use HTTPS")
    u = urlsplit(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        raise MissionError("source URL must use HTTPS without credentials")
    return value


def sha256(value):
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise MissionError("a lowercase 64-character SHA-256 is required")
    return value


def identifier(value, field):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", value) is None:
        raise MissionError(f"{field} needs stable ASCII identifier")
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def connect(path="data/fsl_adaptive.sqlite"):
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def add_spec(db, spec):
    required = ("spec_id", "track", "kind", "title", "reference_url",
                "reference_date", "created_at", "min_duration_days",
                "max_user_rounds", "required_criteria", "evidence_class")
    if not isinstance(spec, dict) or any(x not in spec for x in required):
        raise MissionError("incomplete functional benchmark specification")
    identifier(spec["spec_id"], "spec_id")
    if spec["track"] not in ("digital", "embodied") or spec["kind"] not in KINDS:
        raise MissionError("invalid track/kind")
    if (spec["track"] == "embodied") != (spec["kind"] == "embodied"):
        raise MissionError("embodied and digital tracks must remain separate")
    if spec["evidence_class"] not in ("synthetic", "observational"):
        raise MissionError("unknown evidence class")
    https(spec["reference_url"])
    day(spec["reference_date"])
    moment(spec["created_at"])
    duration = spec["min_duration_days"]
    if (isinstance(duration, bool) or not isinstance(duration, (int, float)) or
            not math.isfinite(duration) or duration < (0 if spec["track"] == "embodied" else 2)):
        raise MissionError("digital missions must target >=2 days; physical track is separate")
    rounds = spec["max_user_rounds"]
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 1 <= rounds <= 6:
        raise MissionError("max_user_rounds must be an integer 1..6")
    criteria = spec["required_criteria"]
    if not isinstance(criteria, list) or len(set(criteria)) != len(criteria):
        raise MissionError("required_criteria must be a unique list")
    if not all(isinstance(x, str) and re.fullmatch(r"[a-z_]{3,64}", x) for x in criteria):
        raise MissionError("invalid criterion name")
    if not MANDATORY[spec["kind"]].issubset(criteria):
        raise MissionError("critical integration/quality requirements cannot be omitted")
    with db:
        db.execute("""INSERT INTO functional_specs
          (spec_id,track,kind,title,reference_url,reference_date,created_at,
           min_duration_days,max_user_rounds,required_criteria_json,evidence_class,spec_sha256)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
          (spec["spec_id"],spec["track"],spec["kind"],spec["title"],
           spec["reference_url"],spec["reference_date"],spec["created_at"],
           float(duration),rounds,json.dumps(criteria),spec["evidence_class"],
           fingerprint(spec)))
    return spec["spec_id"]


def add_run(db, run):
    required = ("run_id", "spec_id", "system_key", "system_revision",
                "initiated_at", "evidence_class")
    if not isinstance(run, dict) or any(x not in run for x in required):
        raise MissionError("incomplete mission run")
    for key in ("run_id", "spec_id"):
        identifier(run[key], key)
    if not all(isinstance(run[x], str) and run[x].strip()
               for x in ("system_key","system_revision")):
        raise MissionError("model/system identity required")
    moment(run["initiated_at"])
    spec = db.execute("SELECT * FROM functional_specs WHERE spec_id=?",
                      (run["spec_id"],)).fetchone()
    if spec is None or spec["evidence_class"] != run["evidence_class"]:
        raise MissionError("run must match a registered spec and evidence class")
    if moment(run["initiated_at"]) < moment(spec["created_at"]):
        raise MissionError("run cannot start before specification")
    with db:
        db.execute("""INSERT INTO functional_runs
          (run_id,spec_id,system_key,system_revision,initiated_at,evidence_class)
          VALUES (?,?,?,?,?,?)""",
          tuple(run[k] for k in required))
    return run["run_id"]


def _required(p, fields):
    if not isinstance(p, dict) or any(k not in p for k in fields):
        raise MissionError(f"event payload missing required fields: {fields}")


def validate_event(event):
    required = ("event_id","run_id","kind","actor","occurred_at","recorded_at","payload")
    if not isinstance(event, dict) or any(k not in event for k in required):
        raise MissionError("missing event fields")
    for key in ("event_id","run_id"):
        identifier(event[key],key)
    k=event["kind"]
    if k not in EVENTS or event["actor"] not in ACTORS:
        raise MissionError("unsupported event kind or actor")
    occurred,recorded=moment(event["occurred_at"]),moment(event["recorded_at"])
    if occurred>recorded:
        raise MissionError("recording cannot precede occurrence")
    if event.get("source_url"):
        https(event["source_url"])
    p=event["payload"]
    if not isinstance(p, dict):
        raise MissionError("event payload must be a JSON object")
    if k=="intent":
        _required(p,("goal_sha256",))
        sha256(p["goal_sha256"])
        if event["actor"]!="user":
            raise MissionError("initial intent must be user-authored")
    if k=="goal_revision":
        _required(p,("goal_sha256",))
        sha256(p["goal_sha256"])
        if event["actor"]!="user":
            raise MissionError("goal revision must be user-authored")
    if k in ("progress","checkpoint"):
        _required(p,("evidence_sha256",))
        sha256(p["evidence_sha256"])
    if k=="strategy_decision":
        _required(p,("change_event_id","choice","reason_sha256"))
        identifier(p["change_event_id"],"change_event_id")
        sha256(p["reason_sha256"])
        if p["choice"] not in ("replan","maintain","clarify","escalate"):
            raise MissionError("strategy decision must distinguish change vs no-change")
        if event["actor"]!="ai":
            raise MissionError("only AI may assert a strategy decision")
    if k=="adaptation_judgement":
        _required(p,("decision_event_id","correct","revised_goal_met"))
        identifier(p["decision_event_id"],"decision_event_id")
        if not all(isinstance(p[x],bool) for x in ("correct","revised_goal_met")):
            raise MissionError("adaptation review must be boolean")
        if event["actor"]!="evaluator" or not event.get("source_url"):
            raise MissionError("adaptation review needs an identified external reference")
    if k=="deliverable":
        _required(p,("artifact_sha256","artifact_type"))
        sha256(p["artifact_sha256"])
        if not isinstance(p["artifact_type"],str) or not p["artifact_type"]:
            raise MissionError("deliverable must identify output type")
        if not event.get("source_url"):
            raise MissionError("deliverable needs a referenced build/media artifact")
    if k=="final_acceptance":
        _required(p,("deliverable_event_id","accepted","goal_sha256"))
        identifier(p["deliverable_event_id"],"deliverable_event_id")
        sha256(p["goal_sha256"])
        if not isinstance(p["accepted"],bool) or event["actor"]!="evaluator":
            raise MissionError("final acceptance must be evaluator-recorded")
        if not event.get("source_url"):
            raise MissionError("acceptance needs independent evidence URL")
    if k=="quality_review":
        _required(p,("criterion","passed","reviewer"))
        if not isinstance(p["passed"],bool) or event["actor"]!="evaluator":
            raise MissionError("quality review must be evaluator-recorded boolean")
        if not isinstance(p["reviewer"],str) or not p["reviewer"].strip() or not event.get("source_url"):
            raise MissionError("quality review needs reviewer and external source")
    if k=="style_review":
        _required(p,("axis","passed","reviewer"))
        if p["axis"] not in ("personal_author","ai_native") or not isinstance(p["passed"],bool):
            raise MissionError("invalid distinct style axis")
        if event["actor"]!="evaluator" or not p["reviewer"] or not event.get("source_url"):
            raise MissionError("style review needs reviewer and source")
    if k=="human_assist":
        _required(p,("level",))
        if p["level"] not in ("clarification","exception","direct_execution"):
            raise MissionError("human assistance must be explicitly classified")
    if k=="task_switch":
        _required(p,("from_domain","to_domain"))
        if p["from_domain"]==p["to_domain"] or event["actor"]!="ai":
            raise MissionError("switch must change a real task domain")
    if k=="domain_outcome":
        _required(p,("domain","accepted"))
        if not isinstance(p["accepted"],bool) or event["actor"]!="evaluator" or not event.get("source_url"):
            raise MissionError("physical domain result requires evaluator and external evidence")
    if k=="safety_incident":
        _required(p,("severity",))
        if p["severity"] not in ("minor","major","critical"):
            raise MissionError("invalid safety incident severity")
    if k=="safety_resolution":
        _required(p,("incident_event_id","resolved"))
        identifier(p["incident_event_id"],"incident_event_id")
        if not isinstance(p["resolved"],bool) or event["actor"]!="evaluator":
            raise MissionError("independent safety resolution required")
    if k=="correction":
        _required(p,("supersedes_event_id",))
        identifier(p["supersedes_event_id"],"supersedes_event_id")
    return occurred,recorded


def add_event(db,event):
    occurred,recorded=validate_event(event)
    run=db.execute("SELECT * FROM functional_runs WHERE run_id=?",
                   (event["run_id"],)).fetchone()
    if run is None:
        raise MissionError("event references unknown mission")
    if occurred < moment(run["initiated_at"]):
        raise MissionError("event predates mission start")
    if event["kind"]=="correction":
        prev=db.execute("SELECT kind,run_id FROM functional_events WHERE event_id=?",
                        (event["payload"]["supersedes_event_id"],)).fetchone()
        if prev is None or prev["run_id"]!=event["run_id"] or prev["kind"]=="correction":
            raise MissionError("correction must reference same-run noncorrection event")
    with db:
        db.execute("""INSERT INTO functional_events
          (event_id,run_id,kind,actor,occurred_at,recorded_at,payload_json,
           source_url,event_sha256) VALUES(?,?,?,?,?,?,?,?,?)""",
          (event["event_id"],event["run_id"],event["kind"],event["actor"],
           occurred.isoformat(),recorded.isoformat(),
           json.dumps(event["payload"],ensure_ascii=False,allow_nan=False),
           event.get("source_url"),fingerprint(event)))
    return event["event_id"]


def events_asof(db,run_id,as_of):
    cutoff=moment(as_of)
    rows=db.execute("""SELECT * FROM functional_events
      WHERE run_id=? AND occurred_at<=? AND recorded_at<=?
      ORDER BY occurred_at,recorded_at,event_id""",
      (run_id,cutoff.isoformat(),cutoff.isoformat())).fetchall()
    all_events=[{**dict(r),"payload":json.loads(r["payload_json"])} for r in rows]
    corrected={e["payload"]["supersedes_event_id"] for e in all_events
               if e["kind"]=="correction"}
    return [e for e in all_events if e["kind"]!="correction" and e["event_id"] not in corrected]


def read_spec_run(db,run_id):
    row=db.execute("""SELECT r.*,s.track,s.kind,s.title,s.reference_url,
       s.reference_date,s.min_duration_days,s.max_user_rounds,
       s.required_criteria_json,s.spec_sha256
      FROM functional_runs r JOIN functional_specs s USING(spec_id)
      WHERE r.run_id=?""",(run_id,)).fetchone()
    if row is None:
        raise MissionError("unknown mission")
    result=dict(row)
    result["required_criteria"]=json.loads(result.pop("required_criteria_json"))
    return result
