"""FSL GICCF v0.13: catalog validation and honest as-of trial audit.

This tool validates structures and time ordering, not the truth of external
statements or any AI's consciousness, personhood or independent certification.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
import hashlib
import json
from pathlib import Path
import re


class GICCFError(ValueError):
    """Invalid research catalog or evidence assertion."""


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "giccf_capability_catalog_v0.13.json"
SCHEMA_PATH = ROOT / "data" / "giccf_observation_schema_v0.13.json"

HEX64 = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
INDICATOR = re.compile(r"^[A-Z]{3}-[0-9]{2}$")
DOMAIN = re.compile(r"^D[0-9]{2}$")
INDEPENDENT = {"independent_repeated", "longitudinal_independent"}


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _timestamp(s, *, cutoff=False):
    """UTC comparable, timezone-aware; date-only is accepted for cutoffs."""
    if not isinstance(s, str):
        raise GICCFError("timestamp must be a string")
    try:
        if cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            dt = datetime.combine(date.fromisoformat(s), time.max, tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GICCFError(f"invalid timestamp {s}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise GICCFError("timezone-aware timestamps are mandatory")
    return dt.astimezone(timezone.utc)


def validate_catalog(catalog):
    if not isinstance(catalog, dict) or catalog.get("version") != "0.13.0":
        raise GICCFError("unexpected catalog version")
    axes, domains = catalog.get("capability_axes"), catalog.get("civilization_domains")
    if not isinstance(axes, list) or not isinstance(domains, list) or not axes or not domains:
        raise GICCFError("missing capability axes or civilization domains")
    axis_ids, indicator_ids, domain_ids = set(), set(), set()
    for axis in axes:
        axis_id = axis.get("id")
        if not isinstance(axis_id, str) or not re.fullmatch(r"[A-Z]{3}", axis_id):
            raise GICCFError("bad capability axis")
        if axis_id in axis_ids:
            raise GICCFError("duplicate capability axis")
        axis_ids.add(axis_id)
        indicators = axis.get("indicators")
        if not isinstance(indicators, list) or not indicators:
            raise GICCFError("axis lacks indicators")
        for item in indicators:
            code = item.get("id")
            if (not isinstance(code, str) or not INDICATOR.fullmatch(code)
                    or item.get("axis_id") != axis_id or not code.startswith(axis_id + "-")):
                raise GICCFError("indicator id/axis mismatch")
            if code in indicator_ids:
                raise GICCFError("duplicate indicator")
            if not all(isinstance(item.get(k), str) and item[k].strip()
                       for k in ("label_zh", "operational_probe_zh", "expected_evidence")):
                raise GICCFError("missing operational indicator definition")
            indicator_ids.add(code)
    for domain in domains:
        code = domain.get("id")
        if not isinstance(code, str) or not DOMAIN.fullmatch(code) or code in domain_ids:
            raise GICCFError("invalid/duplicate domain")
        tasks = domain.get("example_task_families_zh")
        if (not isinstance(tasks, list) or not tasks
                or any(not isinstance(t, str) or not t.strip() for t in tasks)):
            raise GICCFError("domain lacks task families")
        if domain.get("coverage_status") != "unmeasured":
            raise GICCFError("definitions must not imply an existing measured coverage")
        domain_ids.add(code)
    dimensions = catalog.get("evaluation_dimensions")
    if not isinstance(dimensions, list) or len({x.get("id") for x in dimensions}) != len(dimensions):
        raise GICCFError("invalid evaluation dimensions")
    return {
        "axis_count": len(axis_ids),
        "indicator_count": len(indicator_ids),
        "domain_count": len(domain_ids),
        "example_task_family_count": sum(len(x["example_task_families_zh"]) for x in domains),
        "indicator_ids": indicator_ids,
        "domain_ids": domain_ids,
        "dimensions": {x["id"]: set(x["options"]) for x in dimensions},
        "negative_controls": set(catalog.get("negative_controls", [])),
    }


def load_catalog(path=CATALOG_PATH):
    catalog = _load(path)
    validate_catalog(catalog)
    return catalog


def _validate_trial(rec, idx):
    if not isinstance(rec, dict):
        raise GICCFError(f"observation {idx} is not an object")
    spec = _load(SCHEMA_PATH)
    required = spec["$defs"]["observation"]["required"]
    missing = set(required) - set(rec)
    extra = set(rec) - set(spec["$defs"]["observation"]["properties"])
    if missing or extra:
        raise GICCFError(f"observation {idx}: missing {sorted(missing)}, extra {sorted(extra)}")
    if not ID.fullmatch(str(rec["observation_id"])):
        raise GICCFError("invalid observation id")
    if not HEX64.fullmatch(str(rec["stack_sha256"])):
        raise GICCFError("invalid system stack fingerprint")
    if rec["artifact_sha256"] is not None and not HEX64.fullmatch(str(rec["artifact_sha256"])):
        raise GICCFError("invalid artifact fingerprint")
    for field in ("subject_id", "test_case_id", "acceptance_reference"):
        if not isinstance(rec[field], str) or not rec[field].strip():
            raise GICCFError(f"missing {field}")
    if (not isinstance(rec["wall_clock_seconds"], int)
            or isinstance(rec["wall_clock_seconds"], bool)
            or rec["wall_clock_seconds"] < 0):
        raise GICCFError("invalid wall-clock duration")
    human_steps = rec["human_substantive_steps"]
    if human_steps is not None and (type(human_steps) is not int or human_steps < 0):
        raise GICCFError("invalid human substantive step count")
    occurred = _timestamp(rec["event_occurred_at"])
    published = _timestamp(rec["source_published_at"])
    recorded = _timestamp(rec["fsl_recorded_at"])
    if not occurred <= published <= recorded:
        raise GICCFError("observation event/publication/recording order is impossible")
    if rec["evidence_tier"] == "provider_claim" and rec["outcome"] != "not_tested":
        raise GICCFError("a provider claim is not a tested outcome")
    if rec["data_class"] == "synthetic":
        if (rec["source_kind"] != "synthetic_fixture"
                or rec["source_url"] is not None
                or rec["evidence_tier"] in INDEPENDENT
                or rec["evidence_tier"] == "provider_claim"
                or rec["outcome_adjudication"] not in {"none", "self_report"}):
            raise GICCFError("synthetic evidence must not be promoted")
    else:
        if (rec["source_kind"] == "synthetic_fixture"
                or not isinstance(rec["source_url"], str)
                or not rec["source_url"].startswith("https://")):
            raise GICCFError("observational evidence requires a real HTTPS source")
    if rec["evidence_tier"] in INDEPENDENT:
        if (rec["data_class"] != "observational"
                or rec["artifact_sha256"] is None
                or rec["outcome_adjudication"] not in
                {"independent_evaluator", "external_receipt_plus_independent_evaluator"}):
            raise GICCFError("independent tier requires source and external audit record")
    return occurred, published, recorded


def audit_observations(payload, *, catalog=None, as_of=None):
    """As-of replay with structural evidence review gates, NEVER certification.

    This does not confirm that source URLs, fingerprints or independent
    evaluators are genuine. Synthetic data remain only test fixtures.
    """
    if catalog is None:
        catalog = load_catalog()
    index = validate_catalog(catalog)
    if not isinstance(payload, dict) or payload.get("schema_version") != "giccf-observations-v0.13":
        raise GICCFError("wrong observation schema version")
    if payload.get("catalog_version") != catalog["version"]:
        raise GICCFError("wrong catalog version")
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise GICCFError("observations must be an array")
    cutoff = _timestamp(as_of, cutoff=True) if as_of else None
    seen = {}
    all_records = []
    for i, rec in enumerate(observations):
        occurred, published, recorded = _validate_trial(rec, i)
        if rec["observation_id"] in seen:
            raise GICCFError("duplicate immutable observation id")
        seen[rec["observation_id"]] = rec
        if rec["indicator_id"] not in index["indicator_ids"] or rec["domain_id"] not in index["domain_ids"]:
            raise GICCFError("unknown capability/domain reference")
        for dim, opts in index["dimensions"].items():
            if dim in rec and rec[dim] not in opts:
                raise GICCFError(f"invalid {dim} value")
        control = rec.get("negative_control")
        if control is not None and control not in index["negative_controls"]:
            raise GICCFError("unrecognized negative control")
        all_records.append((rec, occurred, published, recorded))
    for rec, _, _, _ in all_records:
        prior = rec.get("supersedes_observation_id")
        if prior is not None:
            if prior == rec["observation_id"] or prior not in seen:
                raise GICCFError("invalid supersession pointer")
            predecessor = seen[prior]
            if predecessor["subject_id"] != rec["subject_id"] or predecessor["indicator_id"] != rec["indicator_id"]:
                raise GICCFError("a revision cannot silently switch subject or indicator")
            if _timestamp(predecessor["fsl_recorded_at"]) >= _timestamp(rec["fsl_recorded_at"]):
                raise GICCFError("revisions must be recorded later")
    visible = [rec for rec, occurred, published, recorded in all_records
               if cutoff is None or max(occurred, published, recorded) <= cutoff]
    shadowed = {r["supersedes_observation_id"] for r in visible
                if r.get("supersedes_observation_id") is not None}
    active = [r for r in visible if r["observation_id"] not in shadowed]
    by_key = defaultdict(list)
    for r in active:
        by_key[(r["subject_id"], r["stack_sha256"], r["indicator_id"], r["domain_id"])].append(r)
    entries = []
    for key, events in sorted(by_key.items()):
        passed = [x for x in events if x["outcome"] == "passed"]
        reviewable = [
            x for x in passed
            if x["data_class"] == "observational"
            and x["evidence_tier"] in INDEPENDENT
            and x["outcome_adjudication"] == "external_receipt_plus_independent_evaluator"
            and x["human_contribution"] in {"none", "clarification_only", "approval_or_adjudication"}
            and x["human_substantive_steps"] == 0
            and x["authorization"] in {"within_scope", "required_escalation", "revoked_and_stopped"}
            and x["source_url"] is not None and x["artifact_sha256"] is not None
        ]
        distinct = len({x["test_case_id"] for x in reviewable})
        entries.append({
            "subject_id": key[0], "stack_sha256": key[1],
            "indicator_id": key[2], "domain_id": key[3],
            "total_visible_observations": len(events),
            "passed": len(passed),
            "partial": sum(x["outcome"] == "partial" for x in events),
            "failed": sum(x["outcome"] == "failed" for x in events),
            "provider_claims_not_tested": sum(x["evidence_tier"] == "provider_claim" for x in events),
            "synthetic_records": sum(x["data_class"] == "synthetic" for x in events),
            "structurally_reviewable_observations": len(reviewable),
            "independent_review_candidate": len(reviewable) >= 3 and distinct >= 3,
            "external_certified": False
        })
    return {
        "framework": "GICCF v0.13",
        "as_of": as_of,
        "catalog_axes": index["axis_count"],
        "catalog_indicators": index["indicator_count"],
        "catalog_domains": index["domain_count"],
        "total_archive_records": len(all_records),
        "visible_at_cutoff": len(visible),
        "active_after_visible_supersessions": len(active),
        "sparse_results": entries,
        "global_intelligence_score": None,
        "independent_capability_certification": False,
        "limitation": "Structural and timestamp validation only; real external evidence must be checked independently."
    }


def catalog_sha256(path=CATALOG_PATH):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
