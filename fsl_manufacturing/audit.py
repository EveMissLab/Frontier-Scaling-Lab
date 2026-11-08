"""FSL v0.20 physical manufacturing quality evidence auditor.

The results are evidence-state summaries, not certifications of quality,
AI production supremacy, product safety or novel physical properties.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
from collections import Counter
import json
import re
import math

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "ai_physical_manufacturing_quality_catalog_v0.20.json"
SOURCE_PATH = ROOT / "data" / "ai_physical_manufacturing_quality_sources_v0.20.json"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
METRIC = re.compile(r"PMQ-[A-Z]{3}-[0-9]{2}\Z")
EVENT_FIELDS = {
    "event_id","revision_of","subject_id","product_id","study_id",
    "product_spec_revision","quality_definition_version",
    "metric_id","baseline_mode","ai_role","evidence_class",
    "evidence_tier","physical_stage","claim_label",
    "human_core_work","safety_status","comparison_contract",
    "measurement","counterfactual_human_current","future_no_ai_year",
    "event_at","source_published_at","recorded_at","source_url",
    "receipt_sha256","notes_zh"
}
ROLES = {"inspection_only","design_only","planning_only",
         "process_control","physical_executing","human_ai_hybrid"}
CLASSES = {"synthetic","observational"}
SAFETY = {"not_tested","passed","failed","not_applicable"}
HUMAN_CURRENT = {"documented_possible","possibly_possible","unknown",
                 "plausibly_difficult_under_contract","not_comparable"}
MEAS_FIELDS = {"metric_name","unit","baseline_value","ai_value",
               "uncertainty","sample_size","calibrated"}
CONTRACT_FIELDS = {"material_batch","equipment_and_tooling","resource_budget",
                   "time_horizon","product_acceptance","safety_conditions",
                   "baseline_comparison","predeclared_metric"}


class ManufacturingStudyError(ValueError):
    """Invalid research event or unsupported physical-quality claim."""


def moment(v, *, date_cutoff=False):
    if not isinstance(v, str):
        raise ManufacturingStudyError("time must be a string")
    try:
        if date_cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            d = datetime.combine(date.fromisoformat(v), time.max, tzinfo=timezone.utc)
        else:
            d = datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as exc:
        raise ManufacturingStudyError("invalid time") from exc
    if d.tzinfo is None or d.utcoffset() is None:
        raise ManufacturingStudyError("time requires explicit offset")
    return d.astimezone(timezone.utc)


def calendar_day(v, field):
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise ManufacturingStudyError(f"{field} must be YYYY-MM-DD")
    try:
        if date.fromisoformat(v).isoformat() != v:
            raise ManufacturingStudyError("noncanonical day")
    except ValueError as exc:
        raise ManufacturingStudyError(f"{field} invalid calendar day") from exc
    return v


def load_catalog(path=CATALOG_PATH):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if p.get("catalog_id") != "FSL-PMQ" or p.get("version") != "0.20.0":
        raise ManufacturingStudyError("wrong manufacturing quality version")
    axes = p.get("axes")
    if not isinstance(axes,list) or len(axes) != 16:
        raise ManufacturingStudyError("16 quality axes expected")
    names, ids = set(), set()
    for ax in axes:
        code = ax.get("id")
        if (not isinstance(code,str) or re.fullmatch(r"[A-Z]{3}",code) is None
                or code in names):
            raise ManufacturingStudyError("duplicate or invalid axis")
        names.add(code)
        if not isinstance(ax.get("indicators"),list) or len(ax["indicators"]) != 5:
            raise ManufacturingStudyError("five metrics per axis expected")
        for ind in ax["indicators"]:
            mid = ind.get("id")
            if (not isinstance(mid,str) or METRIC.fullmatch(mid) is None
                    or ind.get("axis_id") != code
                    or not mid.startswith("PMQ-"+code+"-")
                    or mid in ids
                    or not isinstance(ind.get("label_zh"),str)
                    or not ind["label_zh"]):
                raise ManufacturingStudyError("invalid/duplicate manufacturing indicator")
            ids.add(mid)
    if len(ids) != 80:
        raise ManufacturingStudyError("80 indicators expected")
    return p, ids


def load_sources(path=SOURCE_PATH):
    s = json.loads(Path(path).read_text(encoding="utf-8"))
    if s.get("schema") != "fsl/manufacturing-quality-sources/0.20":
        raise ManufacturingStudyError("wrong manufacturing sources schema")
    if s.get("version") != "0.20.0":
        raise ManufacturingStudyError("wrong provenance version")
    cutoff = calendar_day(s["research_cutoff"],"research_cutoff")
    index = {}
    for src in s.get("sources",[]):
        sid = src.get("id")
        if not isinstance(sid,str) or not sid or sid in index:
            raise ManufacturingStudyError("invalid/duplicate cited source")
        if not isinstance(src.get("url"),str) or not src["url"].startswith("https://"):
            raise ManufacturingStudyError("source URL should be HTTPS")
        captured = calendar_day(src.get("first_FSL_captured_on"),"source capture")
        if captured > cutoff:
            raise ManufacturingStudyError("source not yet captured")
        pub = src.get("published_on")
        precision = src.get("publication_precision")
        if precision == "day":
            pub = calendar_day(pub,"publication date")
            if pub > captured:
                raise ManufacturingStudyError("published after first capture")
        elif precision == "month":
            if not isinstance(pub,str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])",pub):
                raise ManufacturingStudyError("month-precision source must remain month-precision")
            if pub > captured[:7]:
                raise ManufacturingStudyError("publication month cannot follow capture")
        elif precision == "undated_webpage":
            if pub is not None:
                raise ManufacturingStudyError("undated webpage cannot invent publication date")
        else:
            raise ManufacturingStudyError("unknown source date precision")
        index[sid] = src
    if not index or len(index) != 9:
        raise ManufacturingStudyError("expected nine reference sources")
    claims = s.get("source_bound_claims")
    if not isinstance(claims,list) or len(claims) != 6:
        raise ManufacturingStudyError("six bounded research source statements expected")
    seen = set()
    for c in claims:
        cid = c.get("id")
        if not isinstance(cid,str) or cid in seen or c.get("source_id") not in index:
            raise ManufacturingStudyError("undocumented or duplicate source claim")
        seen.add(cid)
        if c.get("independent_physical_product_certification") is not False:
            raise ManufacturingStudyError("cited claims cannot certify physical manufacturing quality")
    if s.get("no_real_factory_benchmark_performed") is not True:
        raise ManufacturingStudyError("the source registry is not an independent factory trial")
    return s


def valid_event(e, catalog, indicators):
    if not isinstance(e,dict) or set(e) != EVENT_FIELDS:
        raise ManufacturingStudyError("missing/extra manufacturing observation fields")
    for field in ("event_id","subject_id","product_id","study_id",
                  "product_spec_revision","quality_definition_version"):
        if not isinstance(e[field],str) or ID.fullmatch(e[field]) is None:
            raise ManufacturingStudyError(f"invalid {field}")
    if e["metric_id"] not in indicators:
        raise ManufacturingStudyError("unknown quality metric ID")
    for key, opts in (
        ("baseline_mode",catalog["comparison_baselines"]),
        ("evidence_tier",catalog["evidence_tiers"]),
        ("physical_stage",catalog["physical_completion_stages"]),
        ("claim_label",catalog["candidate_claim_labels"])):
        if e[key] not in opts:
            raise ManufacturingStudyError(f"unrecognized {key}")
    if e["ai_role"] not in ROLES or e["evidence_class"] not in CLASSES:
        raise ManufacturingStudyError("unknown AI role or evidence class")
    if e["safety_status"] not in SAFETY or e["counterfactual_human_current"] not in HUMAN_CURRENT:
        raise ManufacturingStudyError("invalid safety or human baseline uncertainty")
    if type(e["human_core_work"]) is not bool:
        raise ManufacturingStudyError("human work attribution must be boolean")
    if e["future_no_ai_year"] is not None:
        raise ManufacturingStudyError("uncalibrated future no-AI year must remain null")
    stamps = [moment(e[key]) for key in ("event_at","source_published_at","recorded_at")]
    if not stamps[0] <= stamps[1] <= stamps[2]:
        raise ManufacturingStudyError("event, publication and capture time inverted")
    contract = e["comparison_contract"]
    if not isinstance(contract,dict) or set(contract) != CONTRACT_FIELDS:
        raise ManufacturingStudyError("incomplete comparability contract")
    if any(not isinstance(v,str) or not v.strip() for v in contract.values()):
        raise ManufacturingStudyError("comparability requirements must be explicit")
    m = e["measurement"]
    if not isinstance(m,dict) or set(m) != MEAS_FIELDS:
        raise ManufacturingStudyError("measurement schema incomplete")
    if type(m["calibrated"]) is not bool:
        raise ManufacturingStudyError("calibrated must be boolean, not a string")
    if m["sample_size"] is not None and (type(m["sample_size"]) is not int or m["sample_size"] <= 0):
        raise ManufacturingStudyError("sample size must be positive or unknown")
    for key in ("baseline_value","ai_value","uncertainty"):
        v = m[key]
        if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or (key == "uncertainty" and v < 0)):
            raise ManufacturingStudyError("invalid numeric measurement")
    if any(m[key] is not None for key in ("baseline_value","ai_value","uncertainty")):
        if not isinstance(m["unit"],str) or not m["unit"]:
            raise ManufacturingStudyError("measured quantity needs unit")
    if not isinstance(m["metric_name"],str) or not m["metric_name"].strip():
        raise ManufacturingStudyError("metric name required")
    if not isinstance(e["notes_zh"],str) or not e["notes_zh"].strip():
        raise ManufacturingStudyError("explanation required")
    receipt = e["receipt_sha256"]
    if receipt is not None and (not isinstance(receipt,str) or SHA256.fullmatch(receipt) is None):
        raise ManufacturingStudyError("invalid material/test receipt checksum")
    if e["evidence_class"] == "synthetic":
        if (e["evidence_tier"] != "unobserved" or e["source_url"] is not None
                or receipt is not None or e["claim_label"] != "unassessed"):
            raise ManufacturingStudyError("synthetic toy data cannot make real world quality claims")
    else:
        if not isinstance(e["source_url"],str) or not e["source_url"].startswith("https://"):
            raise ManufacturingStudyError("real study needs HTTPS evidence source")
        if e["evidence_tier"] in {"reproducible_physical_test",
                                  "independent_physical_replication",
                                  "longitudinal_field_validation"} and receipt is None:
            raise ManufacturingStudyError("physical evidence needs a receipt digest")
        if e["claim_label"] in {"quality_improvement_candidate",
                                "beyond_contemporary_quality_frontier_candidate"}:
            if (e["evidence_tier"] not in {"independent_physical_replication",
                                          "longitudinal_field_validation"}
                    or receipt is None or not m["calibrated"]
                    or m["uncertainty"] is None
                    or m["sample_size"] is None
                    or m["baseline_value"] is None or m["ai_value"] is None
                    or e["safety_status"] != "passed"
                    or e["physical_stage"] in {"design_only","physical_prototype"}):
                raise ManufacturingStudyError("candidate real quality superiority needs matched physical, calibrated, independently replicated safety/metric evidence")
            if (e["claim_label"] == "beyond_contemporary_quality_frontier_candidate"
                    and not e["metric_id"].startswith("PMQ-NOV-")):
                raise ManufacturingStudyError("novel quality dimension must be registered in NOV domain")
    if e["ai_role"] == "inspection_only" and e["claim_label"] in {
            "quality_improvement_candidate","beyond_contemporary_quality_frontier_candidate"}:
        raise ManufacturingStudyError("inspector performance alone cannot certify better manufactured goods")
    if e["claim_label"] == "beyond_contemporary_quality_frontier_candidate" and e["counterfactual_human_current"] != "plausibly_difficult_under_contract":
        raise ManufacturingStudyError("new physical property needs scoped current human-feasibility comparison")
    prior = e["revision_of"]
    if prior is not None and (not isinstance(prior,str) or ID.fullmatch(prior) is None):
        raise ManufacturingStudyError("invalid revision link")
    return stamps


def audit(payload, *, as_of=None, catalog_path=CATALOG_PATH):
    catalog, indicators = load_catalog(catalog_path)
    if not isinstance(payload,dict) or payload.get("schema") != "fsl/manufacturing-quality-observations/0.20":
        raise ManufacturingStudyError("observation stream schema mismatch")
    if payload.get("version") != "0.20.0":
        raise ManufacturingStudyError("wrong observation version")
    records = payload.get("events")
    if not isinstance(records,list):
        raise ManufacturingStudyError("events must be an array")
    indexed = {}
    for e in records:
        t = valid_event(e,catalog,indicators)
        eid=e["event_id"]
        if eid in indexed:
            raise ManufacturingStudyError("duplicate append-only event")
        prior=e["revision_of"]
        if prior is not None:
            p=indexed.get(prior)
            if p is None:
                raise ManufacturingStudyError("revision must refer to existing prior observation")
            if (p["subject_id"],p["product_id"],p["study_id"],p["metric_id"]) != (
                    e["subject_id"],e["product_id"],e["study_id"],e["metric_id"]):
                raise ManufacturingStudyError("new product or metric requires new observation identity")
            if moment(p["recorded_at"]) >= t[2]:
                raise ManufacturingStudyError("revision cannot precede original")
        indexed[eid]=e
    cutoff = moment(as_of,date_cutoff=True) if as_of is not None else None
    visible=[e for e in records if cutoff is None or max(
        moment(e[k]) for k in ("event_at","source_published_at","recorded_at")) <= cutoff]
    overwritten={e["revision_of"] for e in visible if e["revision_of"] is not None}
    active=[e for e in visible if e["event_id"] not in overwritten]
    counts=dict(sorted(Counter(e["physical_stage"] for e in active).items()))
    return {
        "catalog":catalog["catalog_id"],"version":catalog["version"],"as_of":as_of,
        "axes":len(catalog["axes"]),"indicators":len(indicators),
        "archived_observations":len(records),"visible_observations":len(visible),
        "active_after_revisions":len(active),
        "stage_counts":counts,
        "active_records":[{
            "event_id":e["event_id"],"metric_id":e["metric_id"],
            "ai_role":e["ai_role"],"physical_stage":e["physical_stage"],
            "claim_label":e["claim_label"],"evidence_class":e["evidence_class"],
            "safety_status":e["safety_status"],
            "measurement_uncertainty_known":e["measurement"]["uncertainty"] is not None
        } for e in active],
        "AI_manufacturing_quality_superiority_certified":False,
        "new_physical_quality_frontier_certified":False,
        "SAS_systemic_singularity_certified":False,
        "SAS_civilizational_positive_sum_certified":False,
        "future_no_AI_human_year":None,
        "universal_aggregate_quality_score":None,
        "limits":"Structural, source-time and physical-evidence preconditions only; not independent factory verification."
    }
