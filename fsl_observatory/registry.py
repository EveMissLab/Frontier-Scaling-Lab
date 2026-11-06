"""Read-only mission observatory: append-only external evidence receipts.

v0.7 separates *source metadata / local byte integrity* from genuine autonomous
mission completion. A GitHub Actions success is not a playable AAA game.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from fsl_functional.store import (
    MissionError, connect as functional_connect, events_asof,
    identifier, moment, read_spec_run,
)


class ObservatoryError(ValueError):
    """An observation, link, or time constraint failed validation."""


KINDS = {"github_commit", "github_workflow", "github_artifact", "local_file"}
TIME_TRUST = {"provider_recorded", "author_controlled", "collector_clock"}
LINK_ROLES = {"supports_progress", "supports_checkpoint",
              "supports_deliverable", "supports_ci", "supports_recovery"}
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS observer_sessions(
 session_id TEXT PRIMARY KEY,
 mission_run_id TEXT REFERENCES functional_runs(run_id),
 project_ref TEXT NOT NULL,
 created_at TEXT NOT NULL,
 purpose TEXT NOT NULL,
 session_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observer_receipts(
 receipt_id TEXT PRIMARY KEY,
 session_id TEXT NOT NULL REFERENCES observer_sessions(session_id),
 kind TEXT NOT NULL,
 subject TEXT NOT NULL,
 source_ref TEXT NOT NULL,
 observed_at TEXT NOT NULL,
 provider_at TEXT,
 time_trust TEXT NOT NULL,
 state TEXT NOT NULL,
 content_sha256 TEXT,
 metadata_json TEXT NOT NULL,
 receipt_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS observer_receipts_by_session
 ON observer_receipts(session_id,observed_at,receipt_id);
CREATE TABLE IF NOT EXISTS observer_links(
 link_id TEXT PRIMARY KEY,
 receipt_id TEXT NOT NULL REFERENCES observer_receipts(receipt_id),
 event_id TEXT NOT NULL REFERENCES functional_events(event_id),
 role TEXT NOT NULL,
 recorded_at TEXT NOT NULL,
 link_sha256 TEXT NOT NULL,
 UNIQUE(receipt_id,event_id,role)
);
CREATE INDEX IF NOT EXISTS observer_links_by_receipt
 ON observer_links(receipt_id,recorded_at);
CREATE TRIGGER IF NOT EXISTS observer_sessions_no_update
 BEFORE UPDATE ON observer_sessions BEGIN SELECT RAISE(ABORT,'immutable session'); END;
CREATE TRIGGER IF NOT EXISTS observer_sessions_no_delete
 BEFORE DELETE ON observer_sessions BEGIN SELECT RAISE(ABORT,'immutable session'); END;
CREATE TRIGGER IF NOT EXISTS observer_receipts_no_update
 BEFORE UPDATE ON observer_receipts BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER IF NOT EXISTS observer_receipts_no_delete
 BEFORE DELETE ON observer_receipts BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER IF NOT EXISTS observer_links_no_update
 BEFORE UPDATE ON observer_links BEGIN SELECT RAISE(ABORT,'immutable evidence link'); END;
CREATE TRIGGER IF NOT EXISTS observer_links_no_delete
 BEFORE DELETE ON observer_links BEGIN SELECT RAISE(ABORT,'immutable evidence link'); END;
"""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def connect(path="data/fsl_observatory.sqlite"):
    """Use same SQLite DB for functional mission and receipt relationship."""
    db=functional_connect(path)
    db.executescript(SCHEMA)
    return db


def add_session(db, *, session_id, project_ref, created_at,
                purpose="read_only_observation", mission_run_id=None):
    identifier(session_id,"session_id")
    if not isinstance(project_ref,str) or not project_ref.strip() or len(project_ref)>250:
        raise ObservatoryError("project_ref must be nonempty and <=250 chars")
    if not isinstance(purpose,str) or not purpose.strip() or len(purpose)>250:
        raise ObservatoryError("purpose must be a nonempty short description")
    created=moment(created_at).isoformat()
    if mission_run_id is not None:
        identifier(mission_run_id,"mission_run_id")
        run=read_spec_run(db,mission_run_id)
        if moment(created)<moment(run["initiated_at"]):
            raise ObservatoryError("session cannot predate its registered mission")
    payload={
        "session_id":session_id,"project_ref":project_ref,"created_at":created,
        "purpose":purpose,"mission_run_id":mission_run_id,
    }
    with db:
        db.execute("""INSERT INTO observer_sessions
         (session_id,mission_run_id,project_ref,created_at,purpose,session_sha256)
         VALUES(?,?,?,?,?,?)""",
         (session_id,mission_run_id,project_ref,created,purpose,digest(payload)))
    return session_id


def add_receipt(db, *, session_id, receipt):
    """Store a typed source receipt; internal evidence checks are separate.

    The collector reports externally observed metadata, but is not an
    independent third-party notarization service.
    """
    identifier(session_id,"session_id")
    if not isinstance(receipt,dict):
        raise ObservatoryError("receipt must be a JSON object")
    required=("kind","subject","source_ref","observed_at","time_trust",
              "state","metadata")
    if any(x not in receipt for x in required):
        raise ObservatoryError("incomplete evidence receipt")
    if receipt["kind"] not in KINDS or receipt["time_trust"] not in TIME_TRUST:
        raise ObservatoryError("unknown evidence kind/time trust")
    for k in ("subject","source_ref","state"):
        if not isinstance(receipt[k],str) or not receipt[k] or len(receipt[k])>2048:
            raise ObservatoryError(f"{k} must be nonempty and bounded")
    if not isinstance(receipt["metadata"],dict):
        raise ObservatoryError("metadata must be a JSON object")
    observed=moment(receipt["observed_at"]).isoformat()
    provider=receipt.get("provider_at")
    if provider is not None:
        provider=moment(provider).isoformat()
        if moment(provider)>moment(observed):
            raise ObservatoryError("source timestamp may not lie after collection")
    content=receipt.get("content_sha256")
    if content is not None and (not isinstance(content,str) or
                                len(content)!=64 or
                                any(ch not in "0123456789abcdef" for ch in content)):
        raise ObservatoryError("content_sha256 must be lowercase SHA256")
    session=db.execute("SELECT * FROM observer_sessions WHERE session_id=?",
                       (session_id,)).fetchone()
    if session is None:
        raise ObservatoryError("unknown session")
    if moment(observed)<moment(session["created_at"]):
        raise ObservatoryError("cannot collect evidence before session starts")
    data=dict(receipt,observed_at=observed,provider_at=provider)
    rid=digest({"session_id":session_id,"kind":data["kind"],"subject":data["subject"],
                "source_ref":data["source_ref"],"observed_at":observed,
                "content_sha256":content,"metadata":data["metadata"]})
    with db:
        db.execute("""INSERT OR IGNORE INTO observer_receipts
         (receipt_id,session_id,kind,subject,source_ref,observed_at,provider_at,
          time_trust,state,content_sha256,metadata_json,receipt_sha256)
         VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
         (rid,session_id,data["kind"],data["subject"],data["source_ref"],
          observed,provider,data["time_trust"],data["state"],content,
          json.dumps(data["metadata"],sort_keys=True,ensure_ascii=False,
                     allow_nan=False),digest(data)))
    return rid


def link_receipt(db, *, receipt_id, event_id, role, recorded_at):
    """Attach source evidence to an already-recorded mission claim.

    A CI passing does not independently verify final user acceptance.
    A local file hash must match the claimed output/checkpoint hash.
    """
    if role not in LINK_ROLES:
        raise ObservatoryError("unsupported evidence link role")
    identifier(event_id,"event_id")
    recorded=moment(recorded_at).isoformat()
    receipt=db.execute("SELECT * FROM observer_receipts WHERE receipt_id=?",
                       (receipt_id,)).fetchone()
    if receipt is None:
        raise ObservatoryError("unknown receipt")
    session=db.execute("SELECT * FROM observer_sessions WHERE session_id=?",
                       (receipt["session_id"],)).fetchone()
    if session["mission_run_id"] is None:
        raise ObservatoryError("pilot source session cannot be attached to a mission")
    event=db.execute("SELECT * FROM functional_events WHERE event_id=?",
                     (event_id,)).fetchone()
    if event is None or event["run_id"]!=session["mission_run_id"]:
        raise ObservatoryError("source/claim must belong to same registered mission")
    if moment(recorded)<moment(receipt["observed_at"]) or moment(recorded)<moment(event["recorded_at"]):
        raise ObservatoryError("source link cannot be backdated before collection or claim")
    allowed={
        "supports_progress":{"progress"},
        "supports_checkpoint":{"checkpoint"},
        "supports_deliverable":{"deliverable"},
        "supports_ci":{"progress","checkpoint","deliverable"},
        "supports_recovery":{"recovery"},
    }
    if event["kind"] not in allowed[role]:
        raise ObservatoryError("incompatible event kind for this evidence link")
    if role=="supports_ci":
        meta=json.loads(receipt["metadata_json"])
        if receipt["kind"]!="github_workflow" or meta.get("conclusion")!="success":
            raise ObservatoryError("CI support requires a concluded successful workflow")
        payload=json.loads(event["payload_json"])
        if payload.get("github_head_sha")!=meta.get("head_sha"):
            raise ObservatoryError("CI head SHA must match the event's declared target revision")
    if role=="supports_deliverable":
        if receipt["kind"]!="local_file":
            raise ObservatoryError("artifact byte support requires local-file digest")
        payload=json.loads(event["payload_json"])
        if payload.get("artifact_sha256")!=receipt["content_sha256"]:
            raise ObservatoryError("deliverable hash differs from actual bytes")
    if role in ("supports_progress","supports_checkpoint") and receipt["kind"]=="local_file":
        payload=json.loads(event["payload_json"])
        if payload.get("evidence_sha256")!=receipt["content_sha256"]:
            raise ObservatoryError("claimed progress/checkpoint bytes do not match SHA256")
    key={
        "receipt_id":receipt_id,"event_id":event_id,
        "role":role,"recorded_at":recorded,
    }
    lid=digest(key)
    with db:
        db.execute("""INSERT OR IGNORE INTO observer_links
           (link_id,receipt_id,event_id,role,recorded_at,link_sha256)
           VALUES(?,?,?,?,?,?)""",
           (lid,receipt_id,event_id,role,recorded,digest(key)))
    return lid


def records_asof(db, session_id, as_of):
    """No retroactive 'known at the time' claims for later collected sources."""
    cutoff=moment(as_of).isoformat()
    receipt_rows=db.execute("""SELECT * FROM observer_receipts
      WHERE session_id=? AND observed_at<=?
      ORDER BY observed_at,receipt_id""",(session_id,cutoff)).fetchall()
    receipts=[]
    for r in receipt_rows:
        d=dict(r)
        d["metadata"]=json.loads(d.pop("metadata_json"))
        receipts.append(d)
    ids={r["receipt_id"] for r in receipts}
    links=[]
    if ids:
        link_rows=db.execute("""SELECT l.*,e.run_id,e.kind AS event_kind
         FROM observer_links l JOIN functional_events e USING(event_id)
         JOIN observer_receipts r USING(receipt_id)
         WHERE r.session_id=? AND l.recorded_at<=?
           AND e.recorded_at<=? AND e.occurred_at<=?
         ORDER BY l.recorded_at,l.link_id""",
         (session_id,cutoff,cutoff,cutoff)).fetchall()
        links=[dict(x) for x in link_rows if x["receipt_id"] in ids]
        session=db.execute("SELECT mission_run_id FROM observer_sessions WHERE session_id=?",
                           (session_id,)).fetchone()
        if session is not None and session["mission_run_id"] is not None:
            currently_active={e["event_id"] for e in events_asof(
                db,session["mission_run_id"],as_of)}
            links=[x for x in links if x["event_id"] in currently_active]
    return receipts,links


def read_session(db,session_id):
    r=db.execute("SELECT * FROM observer_sessions WHERE session_id=?",
                 (session_id,)).fetchone()
    if r is None:
        raise ObservatoryError("unknown observation session")
    return dict(r)
