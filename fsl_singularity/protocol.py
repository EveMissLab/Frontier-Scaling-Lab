"""FSL v0.17: source-faithful systemic-singularity evidence reader.

This is NOT a detector of the singularity. It only checks typed, dated,
append-only claims and returns missing evidence. Claims are never
automatically promoted to real-world certification.

Original authority: SAS-01 (2026-08-18), EWDT-19 (2026-10-03).
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timezone
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "data" / "systemic_singularity_protocol_v0.17.json"
SCHEMA_ID = "fsl/systemic-singularity-evidence/0.17"

IDENT = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{2,127}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
ALLOWED_NONGLOBAL = {"I", "C", "E", "H", "M", "L", "R", "N"}
EXTRA_DIMENSIONS = {"KAI_effective_capacity", "network_reachability",
                    "civil_net_outcome"}

REQUIRED = {
    "event_id", "study_id", "subject_id", "cycle_id", "domain",
    "dimension", "assessment_state", "evidence_class",
    "source_class", "source_url", "receipt_sha256", "event_at",
    "source_published_at", "recorded_at", "study_contract_id",
    "comparison_basis", "human_core_work", "human_external_scaling",
    "observed_value", "observed_unit", "externality_categories",
    "supersedes_event_id", "notes_zh"
}


class SingularityStudyError(ValueError):
    """Invalid evidence assertion. No physical regime conclusion is implied."""


def parse_time(v, *, date_cutoff=False):
    if not isinstance(v, str):
        raise SingularityStudyError("timestamp must be a string")
    try:
        if date_cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            dt = datetime.combine(date.fromisoformat(v), time.max,
                                  tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SingularityStudyError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SingularityStudyError("timestamp needs a declared UTC offset")
    return dt.astimezone(timezone.utc)


def load_protocol(path=PROTOCOL_PATH):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if p.get("protocol_id") != "FSL-SAS-BRIDGE" or p.get("version") != "0.17.0":
        raise SingularityStudyError("protocol ID/version mismatch")
    auth = p.get("definition_priority")
    if (not isinstance(auth, list) or len(auth) != 3
            or auth[0].get("document_id") != "SAS-01"
            or auth[0].get("authority") != "primary_definition"
            or auth[1].get("document_id") != "EWDT-19"):
        raise SingularityStudyError("wrong canonical definition priority")
    layers = p.get("system_vector")
    dims = p.get("system_state_dimensions")
    if (not isinstance(layers, list) or not isinstance(dims, list)
            or [x.get("code") for x in layers] != list("ICEHMLRN")
            or [x.get("id") for x in dims] !=
            ["R_sys", "alpha_AI", "kappa_closure", "epsilon_H", "P_persist"]):
        raise SingularityStudyError("source vector and closure components must match canonical references")
    gates = p.get("boundary_gates")
    if [x.get("id") for x in gates] != ["Sigma_sys", "Sigma_civ"]:
        raise SingularityStudyError("canonical two-gate order changed")
    return p


def validate_event(e, protocol):
    if not isinstance(e, dict) or set(e) != REQUIRED:
        raise SingularityStudyError("missing or unrecognized fields in singularity event")
    if any(not isinstance(e[k], str) or IDENT.fullmatch(e[k]) is None
           for k in ("event_id", "study_id", "subject_id", "cycle_id",
                     "study_contract_id")):
        raise SingularityStudyError("bad stable id")
    if e["domain"] not in ALLOWED_NONGLOBAL | {"GLOBAL", "CIV"}:
        raise SingularityStudyError("unrecognized AI support domain")
    dims = {x["id"] for x in protocol["system_state_dimensions"]}
    if e["dimension"] not in dims | EXTRA_DIMENSIONS:
        raise SingularityStudyError("unknown singularity evidence dimension")
    if e["dimension"] == "civil_net_outcome" and e["domain"] != "CIV":
        raise SingularityStudyError("civilization welfare cannot be silently recorded as physical capacity")
    if e["domain"] == "CIV" and e["dimension"] != "civil_net_outcome":
        raise SingularityStudyError("civilian externalities must use the civil outcome dimension")
    if e["dimension"] == "network_reachability" and e["domain"] != "N":
        raise SingularityStudyError("network reachability belongs to the infrastructure domain")
    if e["dimension"] in dims and e["domain"] != "GLOBAL":
        raise SingularityStudyError("EWDT five-state components are global, not a single hardware unit")
    if e["evidence_class"] not in protocol["evidence_classes"]:
        raise SingularityStudyError("unsupported evidence class")
    if e["source_class"] not in protocol["source_classes"]:
        raise SingularityStudyError("unsupported provenance class")
    if e["assessment_state"] not in protocol["assessment_states"]:
        raise SingularityStudyError("unsupported assessment state")
    stamps = [parse_time(e[k]) for k in ("event_at", "source_published_at", "recorded_at")]
    if not stamps[0] <= stamps[1] <= stamps[2]:
        raise SingularityStudyError("source cannot predate event or be captured before publication")
    if e["comparison_basis"] not in protocol["counterfactual_quality"]:
        raise SingularityStudyError("unknown causal-comparison method")
    if e["human_external_scaling"] not in protocol["human_dependency_states"]:
        raise SingularityStudyError("human input dependence must be explicit")
    if type(e["human_core_work"]) is not bool:
        raise SingularityStudyError("human_core_work must be boolean")
    if not isinstance(e["notes_zh"], str) or not e["notes_zh"].strip():
        raise SingularityStudyError("evidence needs a scope/limitation explanation")
    cats = e["externality_categories"]
    if (not isinstance(cats, list) or len(cats) != len(set(cats))
            or any(x not in protocol["civilization_externality_categories"] for x in cats)):
        raise SingularityStudyError("invalid externality categories")
    if e["domain"] != "CIV" and cats:
        raise SingularityStudyError("externality accounting belongs to separate civilization evidence")
    v = e["observed_value"]
    unit = e["observed_unit"]
    if v is None:
        if unit is not None:
            raise SingularityStudyError("numeric unit without a real observed value")
    else:
        if (type(v) not in (float, int) or not math.isfinite(v)
                or v < 0 or not isinstance(unit, str) or not unit.strip()):
            raise SingularityStudyError("numeric value requires explicit unit and nonnegative finite quantity")
        if e["assessment_state"] == "unknown":
            raise SingularityStudyError("cannot attach measured number to unknown result")
    receipt = e["receipt_sha256"]
    if receipt is not None and (not isinstance(receipt, str) or not SHA.fullmatch(receipt)):
        raise SingularityStudyError("malformed external receipt hash")
    if e["evidence_class"] == "synthetic":
        if (e["source_class"] != "synthetic_fixture"
                or e["source_url"] is not None or receipt is not None):
            raise SingularityStudyError("synthetic evidence cannot be promoted to real evidence")
    else:
        if (e["source_class"] == "synthetic_fixture"
                or not isinstance(e["source_url"], str)
                or not e["source_url"].startswith("https://")):
            raise SingularityStudyError("observational assertion needs a real HTTPS source")
        if e["source_class"] == "independent_measurement" and receipt is None:
            raise SingularityStudyError("independently measured outcome requires a receipt digest")
    if (e["dimension"] == "alpha_AI"
            and e["source_class"] == "independent_measurement"
            and e["assessment_state"] == "candidate_positive"
            and e["comparison_basis"] != "external_controlled_comparison"):
        raise SingularityStudyError("positive independent AI attribution requires causal comparison controls")
    if e["source_class"] == "provider_claim" and e["assessment_state"] == "candidate_positive":
        # A provider may claim success, but this is not a verified outcome.
        # Keep its event as an attributed claim; it cannot enter review evidence.
        if e["comparison_basis"] == "external_controlled_comparison":
            raise SingularityStudyError("provider-only evidence cannot claim external causal control")
    previous = e["supersedes_event_id"]
    if previous is not None and (not isinstance(previous, str)
                                  or IDENT.fullmatch(previous) is None):
        raise SingularityStudyError("bad revision pointer")
    return stamps


def audit(data, *, as_of=None, protocol=None):
    """Pure structural, as-of historical audit; never certifies a singularity."""
    p = protocol or load_protocol()
    if not isinstance(data, dict) or data.get("schema") != SCHEMA_ID:
        raise SingularityStudyError("wrong evidence stream schema")
    if data.get("protocol_version") != p["version"]:
        raise SingularityStudyError("protocol mismatch")
    records = data.get("events")
    if not isinstance(records, list):
        raise SingularityStudyError("events must be a list")
    by_id = {}
    for e in records:
        stamps = validate_event(e, p)
        if e["event_id"] in by_id:
            raise SingularityStudyError("duplicate event (append-only assertion)")
        prev_id = e["supersedes_event_id"]
        if prev_id is not None:
            prev = by_id.get(prev_id)
            if prev is None:
                raise SingularityStudyError("correction must refer to an earlier event")
            if tuple(e[k] for k in ("study_id", "subject_id", "cycle_id", "dimension", "domain")) != tuple(
                prev[k] for k in ("study_id", "subject_id", "cycle_id", "dimension", "domain")
            ):
                raise SingularityStudyError("correction must not change subject/period/dimension")
            if parse_time(prev["recorded_at"]) >= stamps[2]:
                raise SingularityStudyError("correction cannot precede original record")
        by_id[e["event_id"]] = e

    cutoff = parse_time(as_of, date_cutoff=True) if as_of is not None else None
    visible = [e for e in records if cutoff is None or max(
        parse_time(e[k]) for k in ("event_at", "source_published_at", "recorded_at")
    ) <= cutoff]
    overridden = {e["supersedes_event_id"] for e in visible if e["supersedes_event_id"]}
    active = [e for e in visible if e["event_id"] not in overridden]
    supported_dims = {e["dimension"] for e in active
                      if e["evidence_class"] == "observational"
                      and e["source_class"] == "independent_measurement"
                      and e["assessment_state"] == "candidate_positive"}
    required_dims = [x["id"] for x in p["system_state_dimensions"]]
    covered_layers = {e["domain"] for e in active
                      if e["evidence_class"] == "observational"
                      and e["source_class"] == "independent_measurement"
                      and e["assessment_state"] == "candidate_positive"}
    cycles = {e["cycle_id"] for e in active
              if e["evidence_class"] == "observational"
              and e["source_class"] == "independent_measurement"
              and e["dimension"] == "P_persist"}
    return {
        "protocol_version": p["version"],
        "canonical_definition_source": p["definition_priority"][0]["document_id"],
        "canonical_two_gates": [g["id"] for g in p["boundary_gates"]],
        "as_of": as_of,
        "archived_events": len(records),
        "visible_events": len(visible),
        "current_assertions_after_correction": len(active),
        "record_types": dict(sorted(Counter(e["source_class"] for e in active).items())),
        "candidate_independently_sourced_system_components": sorted(
            x for x in supported_dims if x in required_dims
        ),
        "missing_independently_sourced_system_components": sorted(
            set(required_dims) - supported_dims
        ),
        "missing_independently_sourced_support_layers": sorted(
            set(x["code"] for x in p["system_vector"]) - covered_layers
        ),
        "number_of_distinct_source_documented_persistence_cycles": len(cycles),
        "multi_cycle_evidence_not_established": len(cycles) < 2,
        "civil_net_benefit_independently_documented": any(
            e["dimension"] == "civil_net_outcome"
            and e["assessment_state"] == "candidate_positive"
            and e["evidence_class"] == "observational"
            and e["source_class"] == "independent_measurement"
            and bool(e["externality_categories"])
            for e in active
        ),
        "systemic_singularity_certified": False,
        "civilizational_singularity_certified": False,
        "note": ("Input structural checks and reported evidence scope only; "
                 "never infers real causal attribution, physical loop closure, "
                 "civilizational net benefit or a singularity year.")
    }
