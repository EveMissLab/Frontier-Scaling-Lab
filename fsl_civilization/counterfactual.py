"""GICCF v0.14: read-only counterfactual capability & definition evolution audit.

Only validates structural consistency and provenance, not actual scientific
counterfactuals, future dates, human impossibility or AI capability.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import re
from typing import Any

from .registry import load_catalog, validate_catalog

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "data" / "giccf_counterfactual_protocol_v0.14.json"


class CounterfactualError(ValueError):
    """An invalid counterfactual research assertion or revision."""


def utc_timestamp(value: str, date_cutoff: bool = False) -> datetime:
    """Parse precise offset-aware timestamps (or date-only audit cutoffs)."""
    if not isinstance(value, str):
        raise CounterfactualError("timestamp must be a string")
    try:
        if date_cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            result = datetime.combine(
                date.fromisoformat(value), time.max, tzinfo=timezone.utc
            )
        else:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CounterfactualError(f"invalid timestamp: {value}") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise CounterfactualError("timestamp requires explicit UTC offset")
    return result.astimezone(timezone.utc)


def required(obj: dict, names: list[str], context: str) -> None:
    if not isinstance(obj, dict):
        raise CounterfactualError(f"{context} must be a JSON object")
    missing = sorted(set(names) - set(obj))
    if missing:
        raise CounterfactualError(f"{context} missing fields {missing}")


def stable_id(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9._-]{2,127}", value
    ) is not None


def load_protocol(path: str | Path = PROTOCOL_PATH) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != "0.14.0" or data.get("protocol_id") != "GICCF-CCCL-DE":
        raise CounterfactualError("wrong protocol version or ID")
    if data.get("framework_anchor") != {"catalog_id": "GICCF", "version": "0.13.0"}:
        raise CounterfactualError("framework must refer to frozen GICCF v0.13")
    for key in ("scenario_kinds", "ai_evidence_levels", "lead_labels",
                "required_definition_fields", "required_assessment_fields"):
        if not isinstance(data.get(key), list) or not data[key]:
            raise CounterfactualError(f"missing protocol enumeration {key}")
    return data


def _validate_definitions(definitions: list, protocol: dict, indicator_ids: set):
    by_id: dict[str, dict] = {}
    for event in definitions:
        required(event, protocol["required_definition_fields"], "definition event")
        eid = event["definition_event_id"]
        if not stable_id(eid) or eid in by_id or not stable_id(event["concept_id"]):
            raise CounterfactualError("bad or duplicate definition identifier")
        if event["event_type"] not in protocol["event_types"]:
            raise CounterfactualError("unsupported definition event kind")
        if type(event["version"]) is not int or event["version"] < 1:
            raise CounterfactualError("definition version must be a positive integer")
        if not isinstance(event["scope_zh"], str) or not event["scope_zh"].strip():
            raise CounterfactualError("definition requires stated scope")
        if not isinstance(event["reason_zh"], str) or not event["reason_zh"].strip():
            raise CounterfactualError("definition revision reason is required")
        linked = event["linked_indicator_ids"]
        if not isinstance(linked, list) or any(x not in indicator_ids for x in linked):
            raise CounterfactualError("unknown GICCF indicator link")
        prior = event["supersedes"]
        if not isinstance(prior, list) or len(prior) != len(set(prior)):
            raise CounterfactualError("invalid definition supersession links")
        if event["event_type"] == "introduced":
            if prior or event["version"] != 1:
                raise CounterfactualError("introductions start at version 1 without prior events")
            if any(p["concept_id"] == event["concept_id"] for p in by_id.values()):
                raise CounterfactualError("concept already introduced")
        else:
            if not prior:
                raise CounterfactualError("revision/split/merge/retirement needs preceding event")
            if len(prior) != 1 and event["event_type"] not in {"merged"}:
                raise CounterfactualError("multiple prior definitions require explicit merge")
        created = utc_timestamp(event["recorded_at"])
        predecessor = []
        for pred_id in prior:
            if pred_id not in by_id:
                raise CounterfactualError("definition event must point to earlier existing event")
            pred = by_id[pred_id]
            if utc_timestamp(pred["recorded_at"]) >= created:
                raise CounterfactualError("new definition recorded before predecessor")
            predecessor.append(pred)
        if event["event_type"] in {"revised", "reclassified", "retired"}:
            prev = predecessor[0]
            if (prev["concept_id"] != event["concept_id"]
                    or prev["version"] + 1 != event["version"]):
                raise CounterfactualError("same-concept revision version chain mismatch")
        if event["event_type"] in {"split", "merged"}:
            if event["version"] != 1 and event["concept_id"] not in {
                    p["concept_id"] for p in predecessor}:
                raise CounterfactualError("new concept produced by split/merge starts at version 1")
        by_id[eid] = event
    return by_id


def _validate_assessments(assessments: list, protocol: dict, definition_map: dict,
                          indicator_ids: set, domain_ids: set):
    by_id: dict[str, dict] = {}
    for a in assessments:
        required(a, protocol["required_assessment_fields"], "assessment event")
        aid = a["assessment_id"]
        if not stable_id(aid) or aid in by_id:
            raise CounterfactualError("invalid or duplicate assessment ID")
        d = definition_map.get(a["definition_event_id"])
        if d is None:
            raise CounterfactualError("assessment references nonexistent definition")
        if not stable_id(a["subject_id"]) or not stable_id(a["task_id"]):
            raise CounterfactualError("invalid task or subject")
        if a["domain_id"] not in domain_ids:
            raise CounterfactualError("domain reference not in frozen GICCF catalog")
        if a["task_kind"] not in protocol["task_kinds"]:
            raise CounterfactualError("unknown task-kind classification")
        if a["data_class"] not in protocol["evidence_classes"]:
            raise CounterfactualError("unrecognized evidence class")
        if a["lead_label"] not in protocol["lead_labels"]:
            raise CounterfactualError("unrecognized capability lead label")
        if not isinstance(a["reason_zh"], str) or not a["reason_zh"].strip():
            raise CounterfactualError("an assessment needs a reason")
        dates = [utc_timestamp(a[k]) for k in (
            "event_occurred_at", "source_published_at", "recorded_at"
        )]
        if not dates[0] <= dates[1] <= dates[2]:
            raise CounterfactualError("actual event, publication, recording chronology reversed")
        if utc_timestamp(d["recorded_at"]) > dates[2]:
            raise CounterfactualError("assessment cites a not-yet-recorded definition")
        task = a["comparison_contract"]
        if not isinstance(task, dict):
            raise CounterfactualError("missing task comparison contract")
        for name in ("acceptance_criteria", "time_budget", "resource_budget",
                     "algorithm_boundary", "human_assistance_policy"):
            if not isinstance(task.get(name), str) or not task[name].strip():
                raise CounterfactualError(f"comparison contract missing {name}")
        if (not isinstance(task.get("linked_indicator_ids"), list)
                or any(x not in indicator_ids for x in task["linked_indicator_ids"])):
            raise CounterfactualError("unknown indicator in task comparison contract")
        scn = a["scenario"]
        if not isinstance(scn, dict) or scn.get("kind") not in protocol["scenario_kinds"]:
            raise CounterfactualError("invalid or missing no-AI world")
        if scn.get("human_substrate") != protocol["natural_human_substrate"]:
            raise CounterfactualError("main comparator requires unaltered human cognitive substrate")
        if scn.get("ai_allowed") is not False or scn.get("non_ai_science_progress") is not True:
            raise CounterfactualError("counterfactual must allow evolving non-AI science and exclude AI")
        if scn.get("knowledge_policy") not in protocol["knowledge_policies"]:
            raise CounterfactualError("knowledge-dependency policy not declared")
        if (scn["kind"] == "never_ai_trajectory"
                and scn["knowledge_policy"] == "ai_legacy_explicitly_acknowledged"):
            raise CounterfactualError("historical AI legacy is incompatible with never-AI trajectory")
        if not isinstance(scn.get("allowed_support"), list) or not scn["allowed_support"]:
            raise CounterfactualError("non-AI support scope must be specified")
        if any(x not in protocol["allowed_support_categories"]
               for x in scn["allowed_support"]):
            raise CounterfactualError("unknown non-AI support category")
        anchor = scn.get("anchor_year")
        if type(anchor) is not int or not 1800 <= anchor <= 2200:
            raise CounterfactualError("scenario anchor year must be stated")
        ai = a["ai_capability"]
        hum = a["no_ai_human_current"]
        fut = a["no_ai_human_future"]
        if not all(isinstance(x, dict) for x in (ai, hum, fut)):
            raise CounterfactualError("AI/human/future facets require separate objects")
        if (ai.get("evidence_level") not in protocol["ai_evidence_levels"]
                or ai.get("outcome") not in protocol["ai_outcomes"]
                or hum.get("status") not in protocol["human_baseline_statuses"]
                or fut.get("status") not in protocol["future_no_ai_statuses"]):
            raise CounterfactualError("unrecognized facet status")
        if ai["evidence_level"] in {"unassessed", "provider_claim"} and ai["outcome"] != "not_tested":
            raise CounterfactualError("provider claim cannot be treated as completed test")
        if a["data_class"] == "synthetic":
            if a["source_url"] is not None or a["lead_label"] != "unassessed":
                raise CounterfactualError("synthetic fixtures cannot make real capability lead claims")
        elif (not isinstance(a["source_url"], str)
              or not a["source_url"].startswith("https://")):
            raise CounterfactualError("observational claim requires HTTPS evidence source")
        if (hum["status"] == "documented_feasible"
                and a["lead_label"] in {"candidate_possible_lead", "plausible_contemporary_lead"}):
            raise CounterfactualError("same-contract human feasibility contradicts lead classification")
        if a["lead_label"] == "plausible_contemporary_lead":
            if (a["data_class"] != "observational"
                    or ai["evidence_level"] != "independent_replication"
                    or ai["outcome"] != "passed"
                    or hum["status"] != "plausibly_hard_under_contract"
                    or scn["knowledge_policy"] == "historical_dependency_unresolved"):
                raise CounterfactualError("plausible lead requires independently verified and comparable evidence")
        years = fut.get("conditional_year_range")
        if years is not None:
            if not isinstance(years, dict):
                raise CounterfactualError("future-year estimate must be null or explicit scenario range")
            for name in ("earliest_year", "latest_year"):
                if type(years.get(name)) is not int:
                    raise CounterfactualError("scenario year bounds must be integer years")
            if not (anchor <= years["earliest_year"] <= years["latest_year"]):
                raise CounterfactualError("future years must be ordered and after scenario anchor")
            if not isinstance(years.get("method_id"), str) or not years["method_id"].strip():
                raise CounterfactualError("year range requires explicit method")
            if not isinstance(years.get("assumptions"), list) or not years["assumptions"]:
                raise CounterfactualError("year range requires scientific scenario assumptions")
            if scn["knowledge_policy"] == "historical_dependency_unresolved":
                raise CounterfactualError("cannot present year range while historical dependencies unresolved")
        pred = a["revision_of"]
        if pred is not None:
            previous = by_id.get(pred)
            if previous is None:
                raise CounterfactualError("assessment revision must follow an existing event")
            if (previous["subject_id"] != a["subject_id"]
                    or previous["task_id"] != a["task_id"]
                    or previous["domain_id"] != a["domain_id"]):
                raise CounterfactualError("revision cannot silently switch subject, task or domain")
            if utc_timestamp(previous["recorded_at"]) >= dates[2]:
                raise CounterfactualError("assessment revision must be recorded later")
        by_id[aid] = a
    return by_id


def audit(payload: dict, *, as_of: str | None = None,
          protocol: dict | None = None, catalog: dict | None = None) -> dict:
    """Append-only source replay; no counterfactual dates are inferred."""
    if protocol is None:
        protocol = load_protocol()
    if catalog is None:
        catalog = load_catalog()
    meta = validate_catalog(catalog)
    if not isinstance(payload, dict) or payload.get("protocol_version") != "0.14.0":
        raise CounterfactualError("incorrect research protocol version")
    if payload.get("framework_version") != "0.13.0":
        raise CounterfactualError("incorrect frozen GICCF parent version")
    definitions = payload.get("definition_events")
    assessments = payload.get("assessment_events")
    if not isinstance(definitions, list) or not isinstance(assessments, list):
        raise CounterfactualError("missing event streams")
    defmap = _validate_definitions(definitions, protocol, meta["indicator_ids"])
    _validate_assessments(assessments, protocol, defmap,
                          meta["indicator_ids"], meta["domain_ids"])
    cutoff = utc_timestamp(as_of, date_cutoff=True) if as_of else None
    visible_defs = [d for d in definitions
                    if cutoff is None or utc_timestamp(d["recorded_at"]) <= cutoff]
    visible_def_ids = {d["definition_event_id"] for d in visible_defs}
    visible = [a for a in assessments
               if a["definition_event_id"] in visible_def_ids
               and (cutoff is None
                    or max(*(utc_timestamp(a[f]) for f in (
                        "event_occurred_at", "source_published_at", "recorded_at"))) <= cutoff)]
    superseded = {a["revision_of"] for a in visible if a["revision_of"] is not None}
    active = [a for a in visible if a["assessment_id"] not in superseded]
    flags = Counter(a["lead_label"] for a in active)
    return {
        "framework": "GICCF v0.13 + CCCL-DE v0.14",
        "as_of": as_of,
        "catalog_indicator_count": meta["indicator_count"],
        "catalog_domain_count": meta["domain_count"],
        "all_definition_events": len(definitions),
        "visible_definition_events": len(visible_defs),
        "all_assessment_events": len(assessments),
        "visible_assessment_events": len(visible),
        "current_assessments_after_revision": len(active),
        "lead_label_counts": dict(sorted(flags.items())),
        "active_assertions": [{
            "assessment_id": a["assessment_id"],
            "definition_event_id": a["definition_event_id"],
            "subject_id": a["subject_id"],
            "task_id": a["task_id"],
            "scenario": a["scenario"]["kind"],
            "lead_label": a["lead_label"],
            "future_year_range": a["no_ai_human_future"]["conditional_year_range"],
            "synthetic": a["data_class"] == "synthetic"
        } for a in active],
        "certified_counterfactual_year": None,
        "universal_superhuman_score": None,
        "external_certification": False,
        "limits": "This is structural, as-of, definition-lineage validation, not verification of counterfactual science or AI performance."
    }
