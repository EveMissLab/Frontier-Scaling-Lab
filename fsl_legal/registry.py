"""FSL v0.18 legal-infrastructure research: typed as-of event reader.

Does not adjudicate enforceability, litigation, project permits or legal advice.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ai_datacenter_legal_governance_2026-11-08_v0.18.json"
VALID = {
    "agency_order_issued": "binding_procedural_on_addressees",
    "signed": "enacted_effective_date_not_verified",
    "introduced_as_of_source": "not_enacted_in_record",
    "approved_unofficial_pending_certification": "binding_candidate_pending_certification_and_applicability",
    "advisory_approved_unofficial": "nonbinding_advice",
    "in_force_per_eurlex": "binding_reporting_scope_limited",
    "policy_plan_published": "policy_target_not_direct_permit_ban",
}
MODES = {"strict_known_at_time", "retrospective_reconstruction"}
EVENT_FIELDS = {
    "id", "jurisdiction", "jurisdiction_level", "authority", "jurisdiction_code",
    "instrument", "instrument_id", "source_id", "action_on", "status", "bindingness",
    "effect_on", "subject", "mechanism", "description_zh", "outcome_evidence",
    "project_applicability", "source_precision", "uncertainties", "recorded_on",
    "supersedes_event_id", "assessment_kind", "status_history_exhaustive",
}
SOURCE_FIELDS = {"id", "publisher", "title", "url", "published_on", "kind", "scope", "first_FSL_captured_on"}


class LegalStudyError(ValueError):
    pass


def day(d):
    if not isinstance(d, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        raise LegalStudyError("expected canonical YYYY-MM-DD")
    try:
        if date.fromisoformat(d).isoformat() != d:
            raise LegalStudyError("noncanonical date")
    except ValueError as e:
        raise LegalStudyError("invalid calendar date") from e
    return d


def load_data(path=DATA):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(record)
    return record


def validate(record):
    if not isinstance(record, dict) or record.get("schema") != "fsl/legal-governance-events/0.18":
        raise LegalStudyError("wrong legal protocol")
    if record.get("research_version") != "0.18.0" or record.get("timezone") != "Asia/Taipei":
        raise LegalStudyError("wrong research version/date convention")
    cutoff = day(record.get("recorded_on"))
    axes = record.get("legal_indicator_axes")
    if not isinstance(axes, list) or len(axes) != 12:
        raise LegalStudyError("expected 12 legal research axes")
    axis_ids, indicator_ids = set(), set()
    for a in axes:
        code = a.get("id")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{3}", code) or code in axis_ids:
            raise LegalStudyError("invalid/duplicate legal axis")
        axis_ids.add(code)
        if not isinstance(a.get("indicators"), list) or len(a["indicators"]) != 5:
            raise LegalStudyError("each axis needs 5 indicators")
        for m in a["indicators"]:
            mid = m.get("id")
            if (not isinstance(mid, str)
                    or not re.fullmatch(r"LAW-[A-Z]{3}-[0-9]{2}", mid)
                    or m.get("axis_id") != code or mid in indicator_ids
                    or not m.get("label_zh") or not m.get("measurement_key")):
                raise LegalStudyError("bad/duplicate legal indicator")
            indicator_ids.add(mid)
    if len(indicator_ids) != 60:
        raise LegalStudyError("60 unique legal indicators required")
    sources = record.get("sources")
    events = record.get("legal_events")
    if not isinstance(sources, list) or not isinstance(events, list) or not sources or not events:
        raise LegalStudyError("need source-linked legal events")
    source_index = {}
    for s in sources:
        if not isinstance(s, dict) or set(s) != SOURCE_FIELDS:
            raise LegalStudyError("missing/extra source fields")
        sid = s["id"]
        if sid in source_index or not isinstance(sid, str) or not sid.startswith("src-"):
            raise LegalStudyError("duplicate or invalid source id")
        if not isinstance(s["url"], str) or not s["url"].startswith("https://") or " " in s["url"]:
            raise LegalStudyError("primary source URL should be HTTPS")
        if day(s["published_on"]) > day(s["first_FSL_captured_on"]) or s["first_FSL_captured_on"] > cutoff:
            raise LegalStudyError("source cannot appear before publication/capture")
        source_index[sid] = s
    by_id = {}
    for e in events:
        if not isinstance(e, dict) or set(e) != EVENT_FIELDS:
            raise LegalStudyError("missing/extra legal event fields")
        eid = e["id"]
        if not isinstance(eid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._:-]{2,160}", eid) or eid in by_id:
            raise LegalStudyError("invalid or duplicate legal event")
        s = source_index.get(e["source_id"])
        if s is None:
            raise LegalStudyError("event uses unknown source")
        if e["status"] not in VALID or e["bindingness"] != VALID[e["status"]]:
            raise LegalStudyError("bindingness not aligned with legal stage")
        if e["instrument"] not in record["law_classes"] or e["jurisdiction_level"] not in record["jurisdiction_levels"]:
            raise LegalStudyError("invalid law instrument or jurisdiction")
        if day(e["action_on"]) > s["published_on"] or day(e["recorded_on"]) < s["first_FSL_captured_on"]:
            raise LegalStudyError("case event cannot postdate documentary source or predate FSL collection")
        if e["recorded_on"] > cutoff:
            raise LegalStudyError("case cannot be recorded in future relative to research version")
        if (e["status"] in {"introduced_as_of_source", "approved_unofficial_pending_certification",
                            "advisory_approved_unofficial", "policy_plan_published"}
                and e["effect_on"] is not None):
            raise LegalStudyError("proposals, advisory votes and uncertified ballots cannot invent effective dates")
        if e["effect_on"] is not None:
            day(e["effect_on"])
        if e["status"] == "advisory_approved_unofficial" and e["instrument"] != "nonbinding_advisory_ballot":
            raise LegalStudyError("advisory vote is not binding ban")
        if e["status"] == "approved_unofficial_pending_certification" and e["instrument"] != "ballot_charter_amendment":
            raise LegalStudyError("uncertified election cannot be a certified law")
        if (not isinstance(e["uncertainties"], list) or not e["uncertainties"]
                or e["status_history_exhaustive"] is not False
                or e["assessment_kind"] != "documented_source_status_not_project_impact"):
            raise LegalStudyError("legal status is a nonexhaustive documentary claim, not impact certification")
        prior = e["supersedes_event_id"]
        if prior is not None:
            old = by_id.get(prior)
            if old is None:
                raise LegalStudyError("revision must refer to prior archived legal event")
            if any(e[k] != old[k] for k in ("instrument_id", "jurisdiction_code", "jurisdiction_level")):
                raise LegalStudyError("legal revision changed jurisdiction or subject")
            if e["recorded_on"] <= old["recorded_on"]:
                raise LegalStudyError("revision must have later FSL recording date")
        by_id[eid] = e
    if [s["id"] for s in record["policy_scenarios"]] != [
            "unconditional_approval", "conditional_approval", "moratorium_or_prohibition"]:
        raise LegalStudyError("source's three policy counterfactual options must remain")
    if record["forecasts"].get("impact_causality_certified") is not False:
        raise LegalStudyError("source cases cannot certify causal effect")
    return {"axes":len(axis_ids),"indicators":len(indicator_ids),
            "sources":len(source_index),"events":len(by_id),
            "source_index":source_index}


def replay(record, as_of, mode="strict_known_at_time"):
    meta = validate(record)
    as_of = day(as_of)
    if mode not in MODES:
        raise LegalStudyError("unknown historical replay mode")
    src = meta["source_index"]
    visible = []
    for e in record["legal_events"]:
        s = src[e["source_id"]]
        if max(e["action_on"], s["published_on"]) > as_of:
            continue
        if mode == "strict_known_at_time" and max(e["recorded_on"], s["first_FSL_captured_on"]) > as_of:
            continue
        visible.append(e)
    superseded = {e["supersedes_event_id"] for e in visible if e["supersedes_event_id"] is not None}
    active = [e for e in visible if e["id"] not in superseded]
    return {
        "protocol":"FSL-LEGAL-v0.18",
        "as_of":as_of,"mode":mode,
        "source_total":meta["sources"],"archive_total":meta["events"],
        "visible_source_events":len(visible),"active_after_corrections":len(active),
        "legal_states":[{
            "id":e["id"],"jurisdiction":e["jurisdiction_code"],
            "status_at_source":e["status"],"bindingness":e["bindingness"],
            "effective_date_verified":e["effect_on"],
            "source_published_on":src[e["source_id"]]["published_on"],
            "FSL_first_captured_on":src[e["source_id"]]["first_FSL_captured_on"],
            "project_level_enforceability_certified":False
        } for e in active],
        "local_binding_candidate_pending_certification":sum(
            e["status"] == "approved_unofficial_pending_certification" for e in active),
        "nonbinding_advisory_votes":sum(e["status"] == "advisory_approved_unofficial" for e in active),
        "introduced_not_enacted_in_source":sum(e["status"] == "introduced_as_of_source" for e in active),
        "in_force_EU_reporting_instrument":sum(e["status"] == "in_force_per_eurlex" for e in active),
        "legal_impact_on_AI_compute":None,"legal_impact_on_energized_MW":None,
        "causal_effect_certified":False,"one_number_legal_ranking":None,
        "legal_advice_or_project_permit_certified":False,
        "limitations":"Dated status summaries, not live legal opinions, complete country law, project permission or causal impacts."
    }
