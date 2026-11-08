"""FSL-NET v0.16: additive, read-only continuity study auditor.

A reported route, satellite signal, API event or vendor performance statement
is not an externally verified AI capability. The tool checks only the shape
and temporal consistency of records.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timezone
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "ai_connectivity_capability_catalog_v0.16.json"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
METRIC = re.compile(r"NET-[A-Z]{3}-[0-9]{2}\Z")

DATA_CLASSES = {"synthetic", "observational"}
EVIDENCE_KINDS = {"synthetic_test", "provider_assertion",
                  "field_receipt", "independent_field"}
PATH_STATE = {"up", "down", "unknown"}
ACCESS_STATE = {"allowed", "blocked_policy", "unreachable", "unknown"}
OUTCOME = {"passed", "partial", "failed", "not_tested"}
SAFETY = {"safe", "unsafe", "unknown", "not_applicable"}
INDEPENDENCE = {"verified_distinct_failure_domains", "shared_dependency",
                "unverified", "no_backup"}
INCIDENT = {
    "subsea_cable", "terrestrial_fiber", "mobile_handover",
    "satellite_link", "satellite_gateway", "common_power", "dns",
    "route_peering", "api_auth_403", "model_service",
    "reconnect_consistency", "no_fault_control", "other"
}

REQUIRED = {
    "event_id", "subject_id", "task_contract_id", "site_ref",
    "metric_id", "system_stack_sha256", "event_at",
    "source_published_at", "recorded_at", "data_class",
    "evidence_kind", "source_url", "receipt_sha256",
    "incident_type", "primary_path", "backup_path",
    "path_independence", "shared_dependencies", "service_access",
    "task_outcome", "local_safety", "human_core_work",
    "failover_rto_seconds", "revision_of", "explanation_zh"
}


class NetworkStudyError(ValueError):
    """Validation error. No external capability should be inferred."""


def moment(value, *, cutoff=False):
    if not isinstance(value, str):
        raise NetworkStudyError("timestamps must be strings")
    try:
        if cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            t = datetime.combine(date.fromisoformat(value),
                                 time.max, tzinfo=timezone.utc)
        else:
            t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NetworkStudyError("invalid timestamp") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise NetworkStudyError("missing timezone in timestamp")
    return t.astimezone(timezone.utc)


def load_catalog(path=CATALOG_PATH):
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    if catalog.get("catalog_id") != "FSL-NET" or catalog.get("version") != "0.16.0":
        raise NetworkStudyError("unknown version of connectivity catalog")
    axes = catalog.get("research_axes")
    if not isinstance(axes, list) or not axes:
        raise NetworkStudyError("missing research axes")
    ids, axis_ids = set(), set()
    for a in axes:
        aid = a.get("id")
        if not isinstance(aid, str) or not re.fullmatch(r"[A-Z]{3}", aid):
            raise NetworkStudyError("invalid axis")
        if aid in axis_ids:
            raise NetworkStudyError("duplicate axis")
        axis_ids.add(aid)
        indicators = a.get("indicators")
        if not isinstance(indicators, list) or not indicators:
            raise NetworkStudyError("axis must have testable indicators")
        for item in indicators:
            code = item.get("id")
            if (not isinstance(code, str) or not METRIC.fullmatch(code)
                    or item.get("axis_id") != aid
                    or not code.startswith("NET-" + aid + "-")
                    or code in ids):
                raise NetworkStudyError("bad or duplicate metric identifier")
            if not all(isinstance(item.get(k), str) and item[k].strip()
                       for k in ("label_zh", "probe_zh", "measurement")):
                raise NetworkStudyError("incomplete measurement description")
            ids.add(code)
    return catalog, ids


def validate_event(rec, ids):
    if not isinstance(rec, dict):
        raise NetworkStudyError("event must be an object")
    if set(rec) != REQUIRED:
        raise NetworkStudyError("event fields missing or extra: " +
                                repr(sorted(REQUIRED ^ set(rec))))
    if any(not isinstance(rec[k], str) or not ID.fullmatch(rec[k])
           for k in ("event_id", "subject_id", "task_contract_id", "site_ref")):
        raise NetworkStudyError("invalid stable identifier")
    if rec["metric_id"] not in ids:
        raise NetworkStudyError("unknown connectivity metric")
    if not isinstance(rec["system_stack_sha256"], str) or not HASH.fullmatch(rec["system_stack_sha256"]):
        raise NetworkStudyError("system stack must have a lowercase SHA256")
    timestamps = [moment(rec[k]) for k in ("event_at", "source_published_at", "recorded_at")]
    if not timestamps[0] <= timestamps[1] <= timestamps[2]:
        raise NetworkStudyError("events must precede source and FSL capture")
    if rec["data_class"] not in DATA_CLASSES or rec["evidence_kind"] not in EVIDENCE_KINDS:
        raise NetworkStudyError("invalid evidence class or kind")
    if rec["primary_path"] not in PATH_STATE:
        raise NetworkStudyError("invalid primary-path state")
    if rec["backup_path"] not in PATH_STATE | {"none"}:
        raise NetworkStudyError("invalid backup-path state")
    if rec["service_access"] not in ACCESS_STATE:
        raise NetworkStudyError("invalid application access")
    if rec["task_outcome"] not in OUTCOME or rec["local_safety"] not in SAFETY:
        raise NetworkStudyError("invalid task or safety status")
    if rec["path_independence"] not in INDEPENDENCE:
        raise NetworkStudyError("invalid independence status")
    if rec["incident_type"] not in INCIDENT:
        raise NetworkStudyError("invalid fault classification")
    deps = rec["shared_dependencies"]
    if not isinstance(deps, list) or len(deps) != len(set(deps)) or any(
            not isinstance(d, str) or not d.strip() for d in deps):
        raise NetworkStudyError("invalid shared dependency list")
    if deps and rec["path_independence"] == "verified_distinct_failure_domains":
        raise NetworkStudyError("an independent path cannot contain an acknowledged shared failure domain")
    if rec["path_independence"] == "no_backup" and rec["backup_path"] != "none":
        raise NetworkStudyError("no_backup independence status requires no backup")
    if rec["backup_path"] == "none" and rec["path_independence"] != "no_backup":
        raise NetworkStudyError("a missing backup cannot have a verified backup independence")
    if type(rec["human_core_work"]) is not bool:
        raise NetworkStudyError("human core work must be a boolean")
    rto = rec["failover_rto_seconds"]
    if rto is not None and (type(rto) not in (int, float) or rto < 0 or rto > 10**9):
        raise NetworkStudyError("RTO must be a nonnegative number or null")
    if rto is not None and rec["backup_path"] != "up":
        raise NetworkStudyError("RTO implies a demonstrated available backup, not merely a planned path")
    if rec["incident_type"] == "api_auth_403":
        if rec["primary_path"] != "up" or rec["service_access"] != "blocked_policy":
            raise NetworkStudyError("an HTTP 403 control needs an up network with service denied")
        if rec["failover_rto_seconds"] is not None:
            raise NetworkStudyError("permission denial cannot masquerade as repaired network outage")
    if rec["service_access"] == "allowed" and not (
            rec["primary_path"] == "up" or rec["backup_path"] == "up"):
        raise NetworkStudyError("service cannot be reachable if no link is available")
    if not isinstance(rec["explanation_zh"], str) or not rec["explanation_zh"].strip():
        raise NetworkStudyError("explanation required")
    if rec["data_class"] == "synthetic":
        if (rec["evidence_kind"] != "synthetic_test"
                or rec["source_url"] is not None or rec["receipt_sha256"] is not None):
            raise NetworkStudyError("synthetic trials cannot pretend external sources")
    else:
        if (rec["evidence_kind"] == "synthetic_test"
                or not isinstance(rec["source_url"], str)
                or not rec["source_url"].startswith("https://")):
            raise NetworkStudyError("observational evidence needs a real HTTPS source")
        if rec["evidence_kind"] in {"field_receipt", "independent_field"} and (
                not isinstance(rec["receipt_sha256"], str)
                or not HASH.fullmatch(rec["receipt_sha256"])):
            raise NetworkStudyError("field results need inspectable receipt checksum")
    if rec["evidence_kind"] == "provider_assertion" and rec["task_outcome"] != "not_tested":
        raise NetworkStudyError("vendor claim is not an independent task completion")
    if rec["revision_of"] is not None and not (
            isinstance(rec["revision_of"], str) and ID.fullmatch(rec["revision_of"])):
        raise NetworkStudyError("revision pointer must be an event id")
    return timestamps


def audit(payload, *, cutoff=None, catalog_path=CATALOG_PATH):
    catalog, ids = load_catalog(catalog_path)
    if not isinstance(payload, dict) or payload.get("schema") != "fsl/ai-connectivity-observations/0.16":
        raise NetworkStudyError("wrong connectivity trial schema")
    events = payload.get("events")
    if not isinstance(events, list):
        raise NetworkStudyError("events must be a list")
    asof = moment(cutoff, cutoff=True) if cutoff else None
    by_id = {}
    for event in events:
        stamps = validate_event(event, ids)
        eid = event["event_id"]
        if eid in by_id:
            raise NetworkStudyError("duplicate append-only event id")
        if event["revision_of"] is not None:
            past = by_id.get(event["revision_of"])
            if past is None:
                raise NetworkStudyError("revision must refer to a previous recorded event")
            if (past["subject_id"], past["task_contract_id"], past["metric_id"]) != (
                    event["subject_id"], event["task_contract_id"], event["metric_id"]):
                raise NetworkStudyError("revision cannot silently change the observation identity")
            if moment(past["recorded_at"]) >= stamps[2]:
                raise NetworkStudyError("revision must follow original record date")
        by_id[eid] = event
    visible = [
        ev for ev in events
        if asof is None or max(moment(ev[k]) for k in (
            "event_at", "source_published_at", "recorded_at")) <= asof
    ]
    shadowed = {ev["revision_of"] for ev in visible if ev["revision_of"] is not None}
    active = [ev for ev in visible if ev["event_id"] not in shadowed]
    kinds = Counter(ev["incident_type"] for ev in active)
    split = Counter(
        "physical_up_service_denied" if ev["primary_path"] == "up" and ev["service_access"] == "blocked_policy"
        else "both_network_paths_down" if ev["primary_path"] == "down" and ev["backup_path"] in {"down", "none"}
        else "other" for ev in active
    )
    return {
        "catalog": catalog["catalog_id"],
        "catalog_version": catalog["version"],
        "axes": len(catalog["research_axes"]),
        "indicator_count": len(ids),
        "as_of": cutoff,
        "archived_event_count": len(events),
        "events_visible": len(visible),
        "active_event_count": len(active),
        "by_incident": dict(sorted(kinds.items())),
        "failure_scope_counts": dict(sorted(split.items())),
        "active_cases": [
            {"event_id":ev["event_id"],
             "incident_type":ev["incident_type"],
             "primary_path":ev["primary_path"],
             "backup_path":ev["backup_path"],
             "service_access":ev["service_access"],
             "task_outcome":ev["task_outcome"],
             "path_independence":ev["path_independence"],
             "local_safety":ev["local_safety"],
             "human_core_work":ev["human_core_work"],
             "data_class":ev["data_class"]}
            for ev in active
        ],
        "aggregated_network_intelligence_score": None,
        "ai_capability_independently_certified": False,
        "limitations": "Structural checks and synthetic fixtures cannot establish actual independent links, provider availability, local autonomy or real-world safety."
    }
