"""Append-only multichannel SQLite catalog.

Source records are only observations made available by external providers; source
claims, AI ratings and subjective comments must never train the parameter
inversion model as though they were ground-truth parameter disclosures.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from fsl_adaptive.registry import connect as connect_adaptive


class CatalogError(ValueError):
    pass


SQL = """
CREATE TABLE IF NOT EXISTS public_snapshots (
 snapshot_id TEXT PRIMARY KEY,
 source_type TEXT NOT NULL,
 resource_id TEXT NOT NULL,
 source_url TEXT NOT NULL,
 published_on TEXT,
 retrieved_on TEXT NOT NULL,
 source_license TEXT NOT NULL,
 attribution TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 note TEXT
);
CREATE TABLE IF NOT EXISTS public_observations (
 observation_id TEXT PRIMARY KEY,
 snapshot_id TEXT NOT NULL REFERENCES public_snapshots(snapshot_id),
 external_model_id TEXT NOT NULL,
 measure TEXT NOT NULL,
 value REAL NOT NULL,
 unit TEXT NOT NULL,
 channel TEXT NOT NULL,
 methodology TEXT NOT NULL,
 category TEXT NOT NULL,
 published_on TEXT,
 sample_size INTEGER,
 ci_low REAL,
 ci_high REAL,
 provenance_flags TEXT NOT NULL,
 CHECK(channel IN ('metadata','preference','benchmark','community')),
 CHECK(sample_size IS NULL OR sample_size >= 0),
 CHECK(ci_low IS NULL OR ci_low <= value),
 CHECK(ci_high IS NULL OR ci_high >= value)
);
CREATE INDEX IF NOT EXISTS public_observations_lookup
 ON public_observations(external_model_id,channel,measure,category,published_on);
CREATE TABLE IF NOT EXISTS public_aliases (
 alias_id TEXT PRIMARY KEY,
 source_type TEXT NOT NULL,
 external_model_id TEXT NOT NULL,
 canonical_model_key TEXT NOT NULL,
 source_url TEXT NOT NULL,
 recorded_on TEXT NOT NULL,
 note TEXT,
 UNIQUE(source_type, external_model_id)
);
CREATE TRIGGER IF NOT EXISTS public_snapshots_immutable_update
 BEFORE UPDATE ON public_snapshots BEGIN
 SELECT RAISE(ABORT,'public snapshots are append-only'); END;
CREATE TRIGGER IF NOT EXISTS public_snapshots_immutable_delete
 BEFORE DELETE ON public_snapshots BEGIN
 SELECT RAISE(ABORT,'public snapshots are append-only'); END;
CREATE TRIGGER IF NOT EXISTS public_observations_immutable_update
 BEFORE UPDATE ON public_observations BEGIN
 SELECT RAISE(ABORT,'public observations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS public_observations_immutable_delete
 BEFORE DELETE ON public_observations BEGIN
 SELECT RAISE(ABORT,'public observations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS public_aliases_immutable_update
 BEFORE UPDATE ON public_aliases BEGIN
 SELECT RAISE(ABORT,'public aliases are append-only'); END;
CREATE TRIGGER IF NOT EXISTS public_aliases_immutable_delete
 BEFORE DELETE ON public_aliases BEGIN
 SELECT RAISE(ABORT,'public aliases are append-only'); END;
"""


def stable_hash(data):
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def iso_day(value, label="date"):
    if not isinstance(value, str):
        raise CatalogError(f"{label} must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"{label} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise CatalogError(f"{label} must be canonical YYYY-MM-DD")
    return value


def source_url(value):
    if not isinstance(value, str):
        raise CatalogError("source_url must be HTTPS")
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise CatalogError("source_url must be an HTTPS URL without embedded credentials")
    return value


def finite_value(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CatalogError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise CatalogError(f"{label} must be finite")
    return result


def connect(path="data/fsl_adaptive.sqlite"):
    """Extend the existing v0.2 database without deleting prior history."""
    db = connect_adaptive(path)
    db.executescript(SQL)
    return db


def save_snapshot(db, *, source_type, resource_id, url, license_name,
                  attribution, retrieved_on, published_on, raw_document,
                  observations, note=None):
    """Store source hashes and whitelisted numeric observations; no raw text.

    The source response is NOT re-licensed under this repository's Apache-2.0.
    Same-day identical fetches are idempotent; new days retain new dated
    observation records, even when the external payload has not changed.
    """
    if source_type not in ("hf_model", "arena", "hf_benchmark", "community_rollup"):
        raise CatalogError("unrecognized source_type")
    if not isinstance(resource_id, str) or not resource_id:
        raise CatalogError("resource_id is required")
    source_url(url)
    iso_day(retrieved_on, "retrieved_on")
    if published_on is not None:
        iso_day(published_on, "published_on")
        if published_on > retrieved_on:
            raise CatalogError("published_on cannot be after retrieved_on")
    if not isinstance(license_name, str) or not license_name.strip():
        raise CatalogError("source_license is required, use unknown when undisclosed")
    if not isinstance(attribution, str) or not attribution.strip():
        raise CatalogError("source attribution is required")
    raw_hash = stable_hash(raw_document)
    snapshot_id = stable_hash([source_type, resource_id, url, raw_hash, retrieved_on])
    if not isinstance(observations, list):
        raise CatalogError("observations must be a list")
    prepared = []
    seen = set()
    for index, item in enumerate(observations):
        required = ("external_model_id", "measure", "value", "unit", "channel",
                    "methodology", "category")
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or
                                            not item[k].strip()
                                            for k in required if k != "value"):
            raise CatalogError(f"observation {index} has missing labels")
        if item.get("channel") not in ("metadata", "preference", "benchmark", "community"):
            raise CatalogError("invalid observation channel")
        val = finite_value(item.get("value"), "observation value")
        n = item.get("sample_size")
        if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 0):
            raise CatalogError("sample_size must be a nonnegative integer")
        lo, hi = item.get("ci_low"), item.get("ci_high")
        if lo is not None:
            lo = finite_value(lo, "ci_low")
            if lo > val:
                raise CatalogError("ci_low cannot exceed observation value")
        if hi is not None:
            hi = finite_value(hi, "ci_high")
            if hi < val:
                raise CatalogError("ci_high cannot be below observation value")
        day = item.get("published_on", published_on)
        if day is not None:
            iso_day(day, "observation published_on")
            if day > retrieved_on:
                raise CatalogError("observation publication is in the future")
        flags = item.get("provenance_flags", [])
        if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
            raise CatalogError("flags must be a list of strings")
        dedup = [item["external_model_id"], item["measure"], item["category"],
                 item["methodology"], day]
        if stable_hash(dedup) in seen:
            raise CatalogError("duplicate observation key inside snapshot")
        seen.add(stable_hash(dedup))
        record_id = stable_hash([snapshot_id, dedup, val])
        prepared.append((record_id, snapshot_id, item["external_model_id"],
                         item["measure"], val, item["unit"], item["channel"],
                         item["methodology"], item["category"], day, n, lo, hi,
                         json.dumps(flags, ensure_ascii=False)))
    with db:
        db.execute("""INSERT OR IGNORE INTO public_snapshots
          (snapshot_id,source_type,resource_id,source_url,published_on,
           retrieved_on,source_license,attribution,content_sha256,note)
          VALUES(?,?,?,?,?,?,?,?,?,?)""",
          (snapshot_id, source_type, resource_id, url, published_on,
           retrieved_on, license_name, attribution, raw_hash, note))
        db.executemany("""INSERT OR IGNORE INTO public_observations
          (observation_id,snapshot_id,external_model_id,measure,value,unit,
           channel,methodology,category,published_on,sample_size,ci_low,ci_high,
           provenance_flags) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", prepared)
    return {"snapshot_id": snapshot_id, "observation_count": len(prepared),
            "source_url": url, "raw_sha256": raw_hash}


def add_alias(db, *, source_type, external_model_id, canonical_model_key,
              source, recorded_on, note=None):
    """Manual, auditable identity crosswalk; never guess model matches."""
    if not all(isinstance(x, str) and x.strip() for x in
               (source_type, external_model_id, canonical_model_key)):
        raise CatalogError("alias identifiers must be nonempty strings")
    if source_type not in ("hf_model", "arena", "hf_benchmark", "community_rollup"):
        raise CatalogError("invalid alias source")
    source_url(source)
    iso_day(recorded_on, "recorded_on")
    prior = db.execute("""SELECT canonical_model_key FROM public_aliases
        WHERE source_type=? AND external_model_id=?""",
        (source_type, external_model_id)).fetchone()
    if prior is not None and prior["canonical_model_key"] != canonical_model_key:
        raise CatalogError("conflicting model identity: review before changing mapping")
    alias_id = stable_hash([source_type, external_model_id, canonical_model_key])
    with db:
        db.execute("""INSERT OR IGNORE INTO public_aliases
          (alias_id,source_type,external_model_id,canonical_model_key,
           source_url,recorded_on,note) VALUES (?,?,?,?,?,?,?)""",
           (alias_id, source_type, external_model_id, canonical_model_key,
            source, recorded_on, note))
    return alias_id


def list_observations(db, *, model_id=None, channel=None, limit=200, as_of=None):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise CatalogError("limit must be 1..1000")
    query = """SELECT o.*,s.source_type,s.resource_id,s.source_url,s.source_license,
       s.attribution,s.retrieved_on
       FROM public_observations o JOIN public_snapshots s USING(snapshot_id) WHERE 1=1"""
    args = []
    if as_of is not None:
        iso_day(as_of, "as_of")
        query += " AND s.retrieved_on<=? AND (o.published_on IS NULL OR o.published_on<=?)"
        args.extend([as_of, as_of])
    if model_id is not None:
        query += " AND o.external_model_id=?"
        args.append(model_id)
    if channel is not None:
        query += " AND o.channel=?"
        args.append(channel)
    query += " ORDER BY s.retrieved_on DESC,o.observation_id LIMIT ?"
    args.append(limit)
    return [dict(row) for row in db.execute(query, args)]


def trend(db, *, model_id, measure, category, methodology, channel, as_of=None):
    """A series is meaningful only within a declared methodological stratum.

    No cross-benchmark normalizations, capability multipliers, regression,
    causal inference or direct parameter-to-capability conversions are made.
    """
    if not all(isinstance(x, str) and x.strip()
               for x in (model_id, measure, category, methodology, channel)):
        raise CatalogError("trend requires exact source model and stratum")
    if as_of is not None:
        iso_day(as_of, "as_of")
    rows = db.execute("""SELECT o.*,s.retrieved_on,s.source_type,s.source_url
      FROM public_observations o JOIN public_snapshots s USING(snapshot_id)
      WHERE o.external_model_id=? AND o.measure=? AND o.category=?
        AND o.methodology=? AND o.channel=?
        AND (? IS NULL OR (s.retrieved_on<=?
             AND (o.published_on IS NULL OR o.published_on<=?)))
      ORDER BY o.published_on,s.retrieved_on""",
      (model_id, measure, category, methodology, channel,
       as_of, as_of, as_of)).fetchall()
    # Multiple captures of the same published leaderboard should not overweight
    # a single published score. Latest capture of each publication date wins.
    by_date = {}
    for row in rows:
        by_date[row["published_on"] or row["retrieved_on"]] = dict(row)
    series = [by_date[d] for d in sorted(by_date)]
    return {
        "external_model_id": model_id, "measure": measure, "category": category,
        "methodology": methodology, "channel": channel, "points": series,
        "n_distinct_dates": len(series),
        "status": "insufficient_for_trend" if len(series) < 3 else "descriptive_only",
        "caveat": ("Within-source published history only; methodology changes, "
                   "model aliasing, inference budgets and selection bias remain confounders.")
    }


def model_dossier(db, *, canonical_model_key, as_of):
    """Build separated latest-metric views; never average unlike benchmarks.

    Only explicit, reviewable aliases may unify different provider names.
    Future-observed data is excluded from historical as-of requests.
    """
    if not isinstance(canonical_model_key, str) or not canonical_model_key.strip():
        raise CatalogError("canonical_model_key must be a nonempty string")
    iso_day(as_of, "as_of")
    aliases = [dict(row) for row in db.execute("""
      SELECT source_type,external_model_id,source_url,recorded_on
      FROM public_aliases WHERE canonical_model_key=? AND recorded_on<=?
      ORDER BY source_type,external_model_id""", (canonical_model_key, as_of))]
    rows = db.execute("""SELECT o.*, s.source_type,s.retrieved_on,s.source_url,
           s.source_license,s.attribution
      FROM public_observations o
      JOIN public_snapshots s ON s.snapshot_id=o.snapshot_id
      JOIN public_aliases a ON
         a.source_type=s.source_type AND a.external_model_id=o.external_model_id
      WHERE a.canonical_model_key=?
        AND a.recorded_on<=? AND s.retrieved_on<=?
        AND (o.published_on IS NULL OR o.published_on<=?)
      ORDER BY o.published_on,s.retrieved_on,o.observation_id""",
      (canonical_model_key, as_of, as_of, as_of)).fetchall()
    latest = {}
    for row in rows:
        item = dict(row)
        key = (item["channel"],item["source_type"],item["external_model_id"],
               item["measure"],item["category"],item["methodology"])
        latest[key] = item
    channels = {"metadata": [], "preference": [], "benchmark": [], "community": []}
    for key in sorted(latest):
        item = latest[key]
        channels[item["channel"]].append(item)
    return {
        "canonical_model_key": canonical_model_key,
        "as_of": as_of, "manually_reviewed_aliases": aliases,
        "channels": channels,
        "total_latest_metrics": sum(len(rows) for rows in channels.values()),
        "warning": ("A dossier is not a composite intelligence index. "
                    "Cross-provider aliases require explicit grounded matches; "
                    "HF popularity and user sentiment are not parameter measurements."),
    }
