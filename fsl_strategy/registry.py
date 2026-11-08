"""FSL v0.19: source-dated geopolitical and frontier-cost research registry.

Read-only bibliographic and schema validation. Not a geopolitical winner,
national economic policy recommendation, training cost estimate or ROI engine.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import math
import re


ROOT = Path(__file__).resolve().parent.parent
GEO_PATH = ROOT / "data" / "ai_geopolitical_frontier_competition_v0.19.json"
COST_PATH = ROOT / "data" / "frontier_participation_cost_opportunity_v0.19.json"
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
ISO_MONTH = re.compile(r"\d{4}-\d{2}\Z")
VALID_COUNTRY_KEYS = {"US", "CN", "TW"}


class StrategyStudyError(ValueError):
    """Invalid source scope or unsupported strategic inference."""


def _day(v, field):
    if not isinstance(v, str) or ISO_DAY.fullmatch(v) is None:
        raise StrategyStudyError(f"{field} must be YYYY-MM-DD")
    try:
        if date.fromisoformat(v).isoformat() != v:
            raise StrategyStudyError(f"{field} not canonical")
    except ValueError as exc:
        raise StrategyStudyError(f"{field} invalid day") from exc
    return v


def _published(source):
    exact, period = source["publication_date"], source["publication_period"]
    if (exact is None) == (period is None):
        raise StrategyStudyError("publication day and month cannot both be set or absent")
    if exact is not None:
        return _day(exact, "publication_date")
    if not isinstance(period, str) or ISO_MONTH.fullmatch(period) is None:
        raise StrategyStudyError("month-precision publication must be YYYY-MM")
    try:
        y, m = (int(x) for x in period.split("-"))
        if not 1 <= m <= 12 or not 1 <= y <= 9999:
            raise ValueError("out of range")
    except ValueError as exc:
        raise StrategyStudyError("invalid publication month") from exc
    # We do NOT backfill a fictional first-day or precise publication date.
    # known_by is an upper bound, NOT a historical publication day claim.
    return None


def _presence(obj, fields, context):
    if not isinstance(obj, dict) or any(k not in obj for k in fields):
        raise StrategyStudyError(f"{context} incomplete")


def _all_ids(seq, *, field="id", label="items"):
    vals = [obj.get(field) for obj in seq]
    if any(not isinstance(x, str) or not x for x in vals) or len(set(vals)) != len(vals):
        raise StrategyStudyError(f"{label} IDs must be unique nonempty strings")
    return set(vals)


def _indicators(axes, *, prefix, expected_count):
    if not isinstance(axes, list) or not axes:
        raise StrategyStudyError("missing research axes")
    axis_ids = _all_ids(axes, label="axes")
    ids = set()
    for ax in axes:
        metrics = ax.get("indicators")
        if not isinstance(metrics, list) or len(metrics) != 5:
            raise StrategyStudyError("each research axis needs five exploratory indicators")
        for indicator in metrics:
            code = indicator.get("id")
            if (not isinstance(code, str)
                    or re.fullmatch(rf"{prefix}-[A-Z]{{3}}-[0-9]{{2}}", code) is None
                    or not code.startswith(prefix + "-" + ax["id"] + "-")
                    or code in ids
                    or not isinstance(indicator.get("probe_zh"), str)
                    or not indicator["probe_zh"].strip()):
                raise StrategyStudyError("unknown or duplicate research indicator")
            ids.add(code)
    if len(ids) != expected_count:
        raise StrategyStudyError("wrong number of indicators")
    return len(axis_ids), len(ids)


def validate(geo, cost):
    if not isinstance(geo, dict) or geo.get("schema") != "fsl/geopolitical-frontier-competition/0.19":
        raise StrategyStudyError("wrong geopolitical schema")
    if not isinstance(cost, dict) or cost.get("schema") != "fsl/frontier-participation-economics/0.19":
        raise StrategyStudyError("wrong frontier cost schema")
    for p in (geo, cost):
        if p.get("version") != "0.19.0" or p.get("timezone") != "Asia/Taipei":
            raise StrategyStudyError("study version or time convention mismatch")
        if _day(p["first_created_on"], "first_created_on") != "2026-11-08":
            raise StrategyStudyError("source-study origin must match 2026-11-08")
    ga, gm = _indicators(geo["axes"], prefix="GEO", expected_count=40)
    ca, cm = _indicators(cost["cost_axes"], prefix="FEC", expected_count=45)
    if ga != 8 or ca != 9:
        raise StrategyStudyError("original 8+9 axis split changed")
    sources = geo.get("source_registry")
    if not isinstance(sources, list) or not sources:
        raise StrategyStudyError("missing original source registry")
    src_ids = _all_ids(sources, label="sources")
    srci = {}
    for s in sources:
        _presence(s, ["id", "title", "publisher", "url", "publication_date",
                      "publication_period", "known_by", "source_kind", "scope_limit",
                      "first_FSL_captured_on"], "source")
        if (not isinstance(s["url"], str) or not s["url"].startswith("https://")
                or any(x.isspace() for x in s["url"])):
            raise StrategyStudyError("source needs credential-free HTTPS location")
        for field in ("title", "publisher", "scope_limit"):
            if not isinstance(s[field], str) or not s[field].strip():
                raise StrategyStudyError("source descriptions must not be empty")
        pub = _published(s)
        known = _day(s["known_by"], "known_by")
        cap = _day(s["first_FSL_captured_on"], "first capture")
        if pub is not None and pub > known:
            raise StrategyStudyError("source known-by before exact publication")
        if s["publication_period"] is not None:
            if not known.startswith(s["publication_period"]):
                raise StrategyStudyError("month precision publication inconsistent with known-by")
        if known > cap or cap > geo["first_created_on"]:
            raise StrategyStudyError("publication/capture chronology inconsistent")
        srci[s["id"]] = s

    cases = geo.get("cases")
    if not isinstance(cases, list) or not cases:
        raise StrategyStudyError("missing geopolitical cases")
    _all_ids(cases, label="geopolitical cases")
    for c in cases:
        _presence(c, ["id", "source_id", "region", "type", "reference_period",
                      "metric_name", "measured_values", "interpretation_zh",
                      "verified_independent_outcome"], "geopolitical observation")
        if c["source_id"] not in src_ids:
            raise StrategyStudyError("geopolitical observation lacks source")
        if c["verified_independent_outcome"] is not False:
            raise StrategyStudyError("source statement cannot masquerade as independently verified outcome")
        if not isinstance(c["measured_values"], list):
            raise StrategyStudyError("metric values must remain typed")
        for v in c["measured_values"]:
            _presence(v, ["region", "value", "unit"], "numeric observation")
            if (v["region"] not in VALID_COUNTRY_KEYS or type(v["value"]) not in (int, float)
                    or not math.isfinite(v["value"]) or v["value"] < 0
                    or not isinstance(v["unit"], str) or not v["unit"]):
                raise StrategyStudyError("bad region, unit or numeric value")
        if c["metric_name"] == "private_AI_investment":
            if (c["type"] != "observed_statistical_estimate"
                    or len(c["measured_values"]) != 2
                    or {v["region"] for v in c["measured_values"]} != {"US", "CN"}
                    or any(v["unit"] != "USD_billion" for v in c["measured_values"])):
                raise StrategyStudyError("private-investment denominator, years and regions may not be conflated")
        if "verified" in c["type"] and c["verified_independent_outcome"] is False:
            raise StrategyStudyError("unverified source description disguised as outcome verification")

    buckets = cost.get("accounting_buckets")
    routes = cost.get("policy_strategy_options")
    if not isinstance(buckets, list) or not isinstance(routes, list):
        raise StrategyStudyError("missing cost buckets or strategic alternatives")
    bucket_ids = _all_ids(buckets, label="accounting buckets")
    route_ids = _all_ids(routes, label="research strategies")
    if len(bucket_ids) != 13 or len(route_ids) != 8:
        raise StrategyStudyError("cost / strategy taxonomy count changed")
    for b in buckets:
        _presence(b, ["class", "cost_type", "source_or_assumption",
                      "avoid_double_count"], "accounting bucket")
        if not isinstance(b["avoid_double_count"], str) or not b["avoid_double_count"]:
            raise StrategyStudyError("each cost item must declare its accounting double-count rule")
    for r in routes:
        _presence(r, ["zh", "base_model_route", "intended_scope", "actual_country_choice",
                      "questions"], "strategy")
        if not isinstance(r["questions"], list) or len(r["questions"]) < 3:
            raise StrategyStudyError("strategy requires explicit open questions")
        if r["actual_country_choice"] not in {
                "not_asserted", "counterfactual_option_only",
                "documented_taiwan_TAIDE_example",
                "documented_TW_semiconductor_strength"}:
            raise StrategyStudyError("no invented committed national AI strategy")

    observations = cost.get("dated_cost_observations")
    if not isinstance(observations, list):
        raise StrategyStudyError("cost observations must be list")
    _all_ids(observations, label="cost observations")
    for o in observations:
        _presence(o, ["id", "source_id", "kind", "event_period", "value",
                      "unit", "time_semantics", "financial_scope", "scope_limit"],
                  "dated cost observation")
        if o["source_id"] not in src_ids:
            raise StrategyStudyError("cost claim has unknown source")
        if o["value"] is not None:
            if (type(o["value"]) not in (float, int) or not math.isfinite(o["value"])
                    or o["value"] < 0 or not o["unit"]):
                raise StrategyStudyError("metric requires typed value and unit")
        elif o["unit"] is not None:
            raise StrategyStudyError("unit without measured value")
        if o["id"] == "epoch-2024-training-trend":
            if o["kind"] != "historical_cost_model" or o["event_period"] != "2016–2024 estimated":
                raise StrategyStudyError("Epoch historical projection cannot be recast as actual 2027 spending")

    if len(cost.get("policy_analysis_constraints", [])) < 12:
        raise StrategyStudyError("cost-interpretation and risk guardrails missing")
    if cost.get("synthetic_strategic_question", {}).get("example_only") is not True:
        raise StrategyStudyError("synthetic national case is not observed policy decision")
    return {
        "geo_axes":ga, "geo_indicators":gm, "cost_axes":ca,
        "cost_indicators":cm, "source_count":len(src_ids), "cases":len(cases),
        "cost_buckets":len(buckets), "strategies":len(routes),
        "cost_observations":len(observations), "source_index":srci
    }


def load_data(geo_path=GEO_PATH, cost_path=COST_PATH):
    geo = json.loads(Path(geo_path).read_text(encoding="utf-8"))
    cost = json.loads(Path(cost_path).read_text(encoding="utf-8"))
    validate(geo, cost)
    return geo, cost


def replay(geo, cost, *, as_of, mode="strict_known_at_time"):
    meta = validate(geo, cost)
    cutoff = _day(as_of, "as_of")
    if mode not in {"strict_known_at_time", "retrospective_reconstruction"}:
        raise StrategyStudyError("replay requires provenance mode")
    src = meta["source_index"]
    def seen(source_id):
        s = src[source_id]
        if s["known_by"] > cutoff:
            return False
        if mode == "strict_known_at_time" and s["first_FSL_captured_on"] > cutoff:
            return False
        return True
    gc = [e for e in geo["cases"] if seen(e["source_id"])]
    ec = [e for e in cost["dated_cost_observations"] if seen(e["source_id"])]
    return {
        "version":geo["version"],"as_of":cutoff,"mode":mode,
        "geo_axis_count":meta["geo_axes"],"geo_indicator_count":meta["geo_indicators"],
        "economics_axis_count":meta["cost_axes"],"economics_indicator_count":meta["cost_indicators"],
        "visible_geopolitical_claims":len(gc),"visible_cost_source_claims":len(ec),
        "geopolitical_claim_ids":[x["id"] for x in gc],
        "cost_claim_ids":[x["id"] for x in ec],
        "reported_private_2025_investment":next(
            (x["measured_values"] for x in gc
             if x["metric_name"] == "private_AI_investment"), None),
        "frontier_model_training_roi_estimate":None,
        "taiwan_country_policy_recommendation":None,
        "us_china_global_capability_winner":None,
        "full_country_AI_spending_estimate":None,
        "sovereign_value_converted_to_company_cashflow":False,
        "frontier_model_vs_hardware_non_equivalence_preserved":True,
        "non_empirical_value_judgment":None,
        "limitations":("Observational source snapshots and research choices; "
                       "no policy endorsement, closed-world country rank or "
                       "cost-return calculation without audited cash flows.")
    }
