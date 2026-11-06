"""Immutable, timestamped SQLite source registry for auditable AI scaling research.

SPDX-License-Identifier: Apache-2.0

No fetching or scraping occurs here. The submitter supplies a URL and its claim;
the database does not pretend the URL has been independently verified.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit


class DataError(ValueError):
    """Input violates the temporal, provenance, or type contract."""


SITE_FIELDS = {"stage", "gpus", "ready_year", "peak_flops_gpu", "connected_fraction"}
KINDS = {"site", "accelerator", "model", "evaluation", "organization"}
SOURCES = {"manufacturer", "filing", "model_card", "research_paper", "press_release",
           "public_record", "assumption"}
STAGES = {"operational", "construction", "planned", "reference", "cancelled"}
DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS evidence_events(
 event_id TEXT PRIMARY KEY,
 entity_id TEXT NOT NULL,
 entity_kind TEXT NOT NULL,
 field TEXT NOT NULL,
 value_json TEXT,
 unit TEXT,
 state TEXT NOT NULL CHECK(state IN ('asserted','retracted')),
 source_kind TEXT NOT NULL,
 source_url TEXT,
 published_on TEXT NOT NULL,
 recorded_on TEXT NOT NULL,
 effective_on TEXT,
 supersedes_id TEXT,
 note TEXT,
 payload_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_asof ON evidence_events(recorded_on,published_on);
CREATE INDEX IF NOT EXISTS idx_evidence_entity ON evidence_events(entity_id,field);
CREATE TABLE IF NOT EXISTS forecasts(
 forecast_id TEXT PRIMARY KEY,
 as_of TEXT NOT NULL,
 target_year REAL NOT NULL,
 target_key TEXT NOT NULL,
 calibration_group TEXT NOT NULL,
 target_class TEXT NOT NULL CHECK(target_class IN ('synthetic','observational')),
 input_sha256 TEXT NOT NULL,
 output_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_forecasts_target ON forecasts(target_key,target_year);
CREATE TABLE IF NOT EXISTS feedback(
 feedback_id TEXT PRIMARY KEY,
 forecast_id TEXT NOT NULL REFERENCES forecasts(forecast_id),
 observed_multiplier REAL NOT NULL CHECK(observed_multiplier>0),
 published_on TEXT NOT NULL,
 recorded_on TEXT NOT NULL,
 model_source_url TEXT NOT NULL,
 baseline_source_url TEXT NOT NULL,
 note TEXT
);
CREATE INDEX IF NOT EXISTS idx_feedback_asof ON feedback(recorded_on,published_on);
CREATE TRIGGER IF NOT EXISTS no_evidence_update BEFORE UPDATE ON evidence_events
BEGIN SELECT RAISE(ABORT,'append-only evidence'); END;
CREATE TRIGGER IF NOT EXISTS no_evidence_delete BEFORE DELETE ON evidence_events
BEGIN SELECT RAISE(ABORT,'append-only evidence'); END;
CREATE TRIGGER IF NOT EXISTS no_forecast_update BEFORE UPDATE ON forecasts
BEGIN SELECT RAISE(ABORT,'immutable forecast'); END;
CREATE TRIGGER IF NOT EXISTS no_forecast_delete BEFORE DELETE ON forecasts
BEGIN SELECT RAISE(ABORT,'immutable forecast'); END;
CREATE TRIGGER IF NOT EXISTS no_feedback_update BEFORE UPDATE ON feedback
BEGIN SELECT RAISE(ABORT,'append-only feedback'); END;
CREATE TRIGGER IF NOT EXISTS no_feedback_delete BEFORE DELETE ON feedback
BEGIN SELECT RAISE(ABORT,'append-only feedback'); END;
"""


def as_date(value):
    if not isinstance(value, str):
        raise DataError("expected ISO date YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise DataError(f"invalid date: {value!r}") from exc
    if parsed.isoformat() != value:
        raise DataError(f"noncanonical date: {value!r}")
    return value


def https_url(value):
    if not isinstance(value, str):
        raise DataError("a source URL is required")
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname:
        raise DataError("a source URL must be HTTPS")
    return value


def finite_positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataError(f"{name} must be finite and positive")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise DataError(f"{name} must be finite and positive")
    return number


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def connect(path="data/fsl_adaptive.sqlite"):
    db_path = Path(path)
    if str(path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    return db


def add_evidence(db, event):
    required = {"event_id", "entity_id", "entity_kind", "field", "state",
                "source_kind", "published_on", "recorded_on"}
    if not isinstance(event, dict) or any(not event.get(key) for key in required):
        raise DataError("evidence requires event_id/entity_id/entity_kind/field/state/source_kind/dates")
    if not all(isinstance(event[key], str) for key in required):
        raise DataError("evidence identifiers and dates must be strings")
    if event["entity_kind"] not in KINDS or event["source_kind"] not in SOURCES:
        raise DataError("unknown entity kind or source kind")
    if event["state"] not in {"asserted", "retracted"}:
        raise DataError("unknown state")
    if event["field"].startswith("site.") and event["field"][5:] not in SITE_FIELDS:
        raise DataError("unrecognized site field")
    if event["entity_kind"] != "site" and event["field"].startswith("site."):
        raise DataError("site fields require a site entity")
    published = as_date(event["published_on"])
    recorded = as_date(event["recorded_on"])
    if published > recorded:
        raise DataError("recorded_on predates publication")
    effective = event.get("effective_on")
    if effective is not None:
        as_date(effective)
    if event["source_kind"] != "assumption":
        https_url(event.get("source_url"))
    value = event.get("value")
    if event["state"] == "retracted":
        if value is not None or not event.get("supersedes_id"):
            raise DataError("retractions require a supersedes_id and null value")
    else:
        if value is None:
            raise DataError("assertions require a value")
        field = event["field"]
        if field == "site.stage":
            if value not in STAGES:
                raise DataError("invalid site.stage")
        if field in {"site.gpus", "site.peak_flops_gpu", "site.ready_year",
                     "site.connected_fraction"}:
            finite_positive(value, field)
        if field == "site.connected_fraction" and value > 1:
            raise DataError("connected_fraction must be <= 1")
        if field == "site.ready_year" and not 2000 <= value <= 2100:
            raise DataError("ready_year must be in 2000..2100")
    if event.get("supersedes_id"):
        original = db.execute(
            "SELECT entity_id,field,recorded_on FROM evidence_events WHERE event_id=?",
            (event["supersedes_id"],)).fetchone()
        if original is None:
            raise DataError("supersedes_id must reference a stored event")
        if original["entity_id"] != event["entity_id"] or original["field"] != event["field"]:
            raise DataError("supersession must concern the same entity and field")
        if original["recorded_on"] > recorded:
            raise DataError("supersession cannot predate the original record")
    payload_hash = digest(event)
    with db:
        db.execute("""INSERT INTO evidence_events
          (event_id,entity_id,entity_kind,field,value_json,unit,state,
           source_kind,source_url,published_on,recorded_on,effective_on,
           supersedes_id,note,payload_sha256)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (event["event_id"], event["entity_id"], event["entity_kind"], event["field"],
           json.dumps(value, ensure_ascii=False, allow_nan=False),
           event.get("unit"), event["state"], event["source_kind"], event.get("source_url"),
           published, recorded, effective, event.get("supersedes_id"),
           event.get("note"), payload_hash))
    return event["event_id"]


def snapshot(db, cutoff):
    """Read only events publicly published AND recorded by the cutoff date.

    A planned future milestone can be known now, but is always a *plan*;
    it does not turn into evidence of future operational status.
    """
    cutoff = as_date(cutoff)
    rows = db.execute("""SELECT * FROM evidence_events
      WHERE published_on<=? AND recorded_on<=?
      ORDER BY recorded_on,published_on,event_id""", (cutoff, cutoff)).fetchall()
    state, used = {}, []
    for row in rows:
        key = (row["entity_id"], row["field"])
        used.append(row["event_id"])
        if row["state"] == "retracted":
            state.pop(key, None)
        else:
            state[key] = {"value": json.loads(row["value_json"]), "event_id": row["event_id"],
                          "entity_kind": row["entity_kind"], "unit": row["unit"],
                          "source_url": row["source_url"], "effective_on": row["effective_on"],
                          "source_kind": row["source_kind"]}
    return state, {"event_ids": used, "sha256": digest(used)}


def insert_forecast(db, result):
    forecast_id = digest(result)
    with db:
        db.execute("""INSERT OR IGNORE INTO forecasts
          (forecast_id,as_of,target_year,target_key,calibration_group,
           target_class,input_sha256,output_json) VALUES (?,?,?,?,?,?,?,?)""",
           (forecast_id, result["as_of"], result["target_year"], result["target_key"],
            result["calibration_group"], result["target_class"],
            result["input_sha256"], json.dumps(result, sort_keys=True, ensure_ascii=False,
                                               allow_nan=False)))
    return forecast_id


def insert_feedback(db, entry):
    required = ("feedback_id", "forecast_id", "observed_multiplier", "published_on",
                "recorded_on", "model_source_url", "baseline_source_url")
    if any(key not in entry for key in required):
        raise DataError("missing feedback fields")
    https_url(entry["model_source_url"])
    https_url(entry["baseline_source_url"])
    published, recorded = as_date(entry["published_on"]), as_date(entry["recorded_on"])
    if published > recorded:
        raise DataError("feedback publication cannot occur after recording")
    number = finite_positive(entry["observed_multiplier"], "observed_multiplier")
    row = db.execute("SELECT as_of,target_class FROM forecasts WHERE forecast_id=?",
                     (entry["forecast_id"],)).fetchone()
    if row is None:
        raise DataError("unknown forecast_id")
    if row["target_class"] != "observational":
        raise DataError("cannot calibrate on a synthetic forecast")
    if published <= row["as_of"]:
        raise DataError("look-ahead leakage: outcome known at issuance")
    with db:
        db.execute("""INSERT INTO feedback
          (feedback_id,forecast_id,observed_multiplier,published_on,recorded_on,
           model_source_url,baseline_source_url,note) VALUES (?,?,?,?,?,?,?,?)""",
           (entry["feedback_id"], entry["forecast_id"], number, published, recorded,
            entry["model_source_url"], entry["baseline_source_url"], entry.get("note")))
    return entry["feedback_id"]


def training_feedback(db, cutoff, group):
    """Exclude future observations and deduplicate observations of the same target."""
    cutoff = as_date(cutoff)
    rows = db.execute("""SELECT y.*,f.as_of,f.target_key,f.target_year,f.output_json
      FROM feedback y JOIN forecasts f ON y.forecast_id=f.forecast_id
      WHERE y.published_on<=? AND y.recorded_on<=? AND f.calibration_group=?
      ORDER BY y.published_on,y.recorded_on,y.feedback_id""",
      (cutoff, cutoff, group)).fetchall()
    seen, pairs = set(), []
    for row in rows:
        # Multiple forecasts of one released result are correlated, not independent trials.
        identity = (row["target_key"], row["target_year"], row["published_on"])
        if identity in seen:
            continue
        seen.add(identity)
        pairs.append((json.loads(row["output_json"]), float(row["observed_multiplier"]),
                      row["feedback_id"]))
    return pairs
