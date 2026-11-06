"""FSL v0.8.3: calendar-day evidence vintage and UTC mission clocks.

Every source has at least THREE temporal meanings:
 (1) event/effective date,
 (2) original publication date,
 (3) date FSL actually captured the source.
Neither a new reading of a 2024 article nor a Git commit author timestamp
can be represented as 2024 collector-held evidence.

Publisher date precision is CALENDAR DAY; never fake 00:00 UTC release time.
Mission execution fields instead require timezone-aware ISO-8601 instants.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
import hashlib
import json
import re
from urllib.parse import urlsplit


class TemporalError(ValueError):
    pass


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
_IDENT_RE = re.compile(r"[A-Za-z0-9_.:-]{1,120}\Z")
CATEGORIES = frozenset({
    "model_release", "model_shutdown", "service_access", "access_restriction",
    "price_quote", "tool_availability", "quota_policy", "evaluation_protocol",
})
SOURCE_TIERS = frozenset({
    "provider_primary", "documented_third_party", "self_report", "synthetic",
})


def _date(value, field):
    if not isinstance(value, str) or _DATE_RE.fullmatch(value) is None:
        raise TemporalError(field + " requires exact YYYY-MM-DD date precision")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise TemporalError(field + " is not a valid calendar date") from exc
    if parsed.isoformat() != value:
        raise TemporalError(field + " must be canonical YYYY-MM-DD")
    return value


def _instant(value, field):
    if not isinstance(value, str):
        raise TemporalError(field + " requires timezone-aware ISO-8601 instant")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("missing timezone")
    except ValueError as exc:
        raise TemporalError(field + " missing/invalid timezone") from exc
    return d.astimezone(timezone.utc)


def _identity(value, field):
    if not isinstance(value, str) or _IDENT_RE.fullmatch(value) is None:
        raise TemporalError(field + " needs bounded stable ASCII ID")
    return value


def _url(value, field):
    if not isinstance(value, str):
        raise TemporalError(field + " requires source URL")
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise TemporalError(field + " must be HTTPS without credentials")
    return value


def _sha(value, field):
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise TemporalError(field + " needs lowercase SHA256")
    return value


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def validate_catalog(data):
    if not isinstance(data, dict) or data.get("schema") != "fsl/vintage-catalog/0.8.3":
        raise TemporalError("unknown temporal source catalog")
    if data.get("calendar_timezone") != "Asia/Taipei":
        raise TemporalError("source review calendar must declare Asia/Taipei explicitly")
    checked = _date(data.get("catalog_checked_on"), "catalog_checked_on")
    _identity(data.get("catalog_id"), "catalog_id")
    rows = data.get("assertions")
    if not isinstance(rows, list) or not rows:
        raise TemporalError("at least one dated evidence assertion required")
    ids = set()
    validated = []
    for r in rows:
        required = (
            "assertion_id", "kind", "subject_id", "event_effective_on",
            "published_on", "first_captured_on", "source_url",
            "source_grade", "evidence_status", "claim_summary",
        )
        if not isinstance(r, dict) or any(k not in r for k in required):
            raise TemporalError("dated assertion missing required time/provenance fields")
        id_ = _identity(r["assertion_id"], "assertion_id")
        if id_ in ids:
            raise TemporalError("duplicate evidence assertion")
        ids.add(id_)
        _identity(r["subject_id"], "subject_id")
        if r["kind"] not in CATEGORIES:
            raise TemporalError("unrecognized evidence assertion kind")
        if r["source_grade"] not in SOURCE_TIERS:
            raise TemporalError("unrecognized source tier")
        if r["evidence_status"] not in ("public_page_read_now", "local_fixture"):
            raise TemporalError("assertion must identify independent versus synthetic source")
        if r["source_grade"] == "synthetic" and r["evidence_status"] != "local_fixture":
            raise TemporalError("synthetic material cannot pretend official live retrieval")
        if r["source_grade"] != "synthetic" and r["evidence_status"] == "local_fixture":
            raise TemporalError("fixture cannot receive official source grade")
        _url(r["source_url"], "source_url")
        for f in ("event_effective_on", "published_on", "first_captured_on"):
            _date(r[f], f)
        if r["published_on"] > r["first_captured_on"]:
            raise TemporalError("source cannot be captured before its publication")
        if r["first_captured_on"] > checked:
            raise TemporalError("catalog cannot contain future-observed evidence")
        end = r.get("effective_until")
        if end is not None:
            _date(end, "effective_until")
            if end < r["event_effective_on"]:
                raise TemporalError("effective interval ends before it begins")
        if not isinstance(r["claim_summary"], str) or not r["claim_summary"].strip():
            raise TemporalError("claim_summary required")
        if len(r["claim_summary"]) > 500:
            raise TemporalError("claim_summary must not contain full copied source")
        if r["kind"] == "price_quote":
            quote = r.get("price")
            if not isinstance(quote, dict) or set(quote) != {
                    "input_usd_per_million", "output_usd_per_million", "service"}:
                raise TemporalError("price quote needs input/output unit plus service")
            for k in ("input_usd_per_million", "output_usd_per_million"):
                v = quote[k]
                try:
                    p = Decimal(str(v))
                except Exception as exc:
                    raise TemporalError("invalid price rate") from exc
                if not p.is_finite() or p < 0:
                    raise TemporalError("price rate must be nonnegative finite")
            if quote["service"] not in ("api", "other_metered"):
                raise TemporalError("price route must remain explicit")
        validated.append(dict(r))
    return validated


def audit_asof(data, *, as_of, mode="strict_known_at_time"):
    """Display what was *known to this study* at an as-of calendar day.

    strict_known_at_time: requires first_captured_on <= as_of and publication
       no later than cutoff; appropriate for genuinely previously issued models.
    retrospective_reconstruction: may display a historical publication later
       captured by FSL; explicitly NOT evidence possessed at historical cutoff.

    As-of dates are calendar-day intervals. No intraday order is asserted.
    """
    _date(as_of, "as_of")
    if mode not in ("strict_known_at_time", "retrospective_reconstruction"):
        raise TemporalError("unsupported temporal audit mode")
    rows = validate_catalog(data)
    out = []
    for r in rows:
        event = r["event_effective_on"] <= as_of and (
            r.get("effective_until") is None or as_of <= r["effective_until"])
        # A provider quoted a USD price on its launch day. This does NOT
        # certify that the same rate remained available years later.
        quote_point_only = (r["kind"]=="price_quote" and
                            r.get("effective_until") is None and
                            as_of > r["event_effective_on"])
        if quote_point_only:
            event=False
        published = r["published_on"] <= as_of
        captured = r["first_captured_on"] <= as_of
        if not event:
            status = ("historical_point_price_not_verified_for_later_date"
                      if quote_point_only else
                      "not_yet_effective" if r["event_effective_on"] > as_of
                      else "effective_period_expired")
        elif not published:
            status = "not_published_at_cutoff"
        elif captured:
            status = "known_to_fsl_at_cutoff"
        else:
            status = "published_then_but_captured_by_fsl_later"
        admissible = bool(event and published and captured
                          and r["source_grade"] != "synthetic")
        retrospective = bool(event and published
                             and r["source_grade"] != "synthetic")
        out.append({
            "assertion_id":r["assertion_id"],
            "subject_id":r["subject_id"],
            "kind":r["kind"],
            "event_effective_on":r["event_effective_on"],
            "effective_until":r.get("effective_until"),
            "published_on":r["published_on"],
            "first_captured_on":r["first_captured_on"],
            "source_url":r["source_url"],
            "claim_summary":r["claim_summary"],
            "source_grade":r["source_grade"],
            "asof_status":status,
            "admissible_to_previously_issued_forecast":admissible,
            "retrospective_historical_publication_supported":retrospective,
            "day_precision_ambiguous_within_same_day":as_of==r["published_on"],
            "included_for_requested_mode":(
                admissible if mode == "strict_known_at_time" else retrospective),
        })
    return {
        "schema": "fsl/vintage-audit/0.8.3",
        "as_of": as_of,
        "date_precision": "calendar_day_not_invented_utc_midnight",
        "mode": mode,
        "catalog_id": data["catalog_id"],
        "catalog_reviewed_on_Asia_Taipei": data["catalog_checked_on"],
        "rows": out,
        "historical_forecast_reconstruction_permitted":
            mode == "strict_known_at_time",
        "warning": (
            "A source published in 2024 but first captured by FSL in 2026 "
            "may be studied retrospectively but cannot pretend to be known "
            "to a forecast issued in 2024."
        ),
    }


def validate_mission_clock(data, *, checked_at=None):
    """Validate fully specified UTC instants for an attempted functional task.

    Unknown event time is NULL, NEVER today's date or an inferred zero.
    Unlike source articles, machine timestamps are second-precision ISO8601.
    """
    if not isinstance(data, dict) or data.get("schema") != "fsl/mission-clock/0.8.3":
        raise TemporalError("unknown mission-time input")
    run = _identity(data.get("run_id"), "run_id")
    if data.get("evidence_class") not in ("synthetic", "observational"):
        raise TemporalError("evidence_class required")
    _sha(data.get("task_contract_sha256"), "task_contract_sha256")
    _sha(data.get("runtime_manifest_sha256"), "runtime_manifest_sha256")
    for x in ("model_id", "model_revision", "provider", "access_route"):
        _identity(data.get(x), x)
    fields = (
        "goal_frozen_at", "execution_started_at", "last_progress_at",
        "execution_finished_at", "accepted_at", "captured_at",
    )
    times = {}
    for key in fields:
        val = data.get(key)
        times[key] = _instant(val, key) if val is not None else None
    for key in ("goal_frozen_at", "execution_started_at", "captured_at"):
        if times[key] is None:
            raise TemporalError(f"{key} required for even an incomplete run")
    start=times["execution_started_at"]
    if times["goal_frozen_at"]>start:
        raise TemporalError("task goal must be frozen before execution")
    if start>times["captured_at"]:
        raise TemporalError("mission cannot start after observer capture")
    if times["last_progress_at"] is not None and not (
            start<=times["last_progress_at"]<=times["captured_at"]):
        raise TemporalError("progress cannot precede start or postdate collection")
    if times["execution_finished_at"] is not None and not (
            start<=times["execution_finished_at"]<=times["captured_at"]):
        raise TemporalError("finished time cannot precede start or postdate capture")
    if times["accepted_at"] is not None:
        if times["execution_finished_at"] is None:
            raise TemporalError("cannot accept an uncompleted mission")
        if not times["execution_finished_at"]<=times["accepted_at"]<=times["captured_at"]:
            raise TemporalError("acceptance must follow finish and precede capture")
    if times["execution_finished_at"] is not None and times["last_progress_at"] is not None:
        if times["last_progress_at"]>times["execution_finished_at"]:
            raise TemporalError("latest progress after finished task")
    if checked_at is not None and (data["evidence_class"] == "observational"
                                   and times["captured_at"] > _instant(checked_at, "checked_at")):
        raise TemporalError("observational evidence cannot be captured in the future")
    model_first = data.get("model_first_available_on")
    if model_first is not None:
        _date(model_first,"model_first_available_on")
        if model_first>start.date().isoformat():
            raise TemporalError("model had not been made available by execution date")
    pricing_effective = data.get("pricing_effective_on")
    if pricing_effective is not None:
        _date(pricing_effective,"pricing_effective_on")
        if pricing_effective>start.date().isoformat():
            raise TemporalError("price snapshot became effective only after the run")
    price_captured = data.get("price_first_captured_on")
    if price_captured is not None:
        _date(price_captured,"price_first_captured_on")
        # The price source catalog uses Asia/Taipei calendar dates, whereas
        # machine timestamps have an exact UTC instant. Converting the UTC
        # instant to its declared calendar timezone prevents off-by-one-day
        # errors around local midnight.
        captured_taipei=times["captured_at"].astimezone(
            ZoneInfo("Asia/Taipei")).date()
        if date.fromisoformat(price_captured)>captured_taipei:
            raise TemporalError("cannot record a price that was captured after this mission report")
    if data.get("price_source_url") is not None:
        _url(data["price_source_url"],"price_source_url")
    duration=(times["execution_finished_at"]-start).total_seconds()/3600 if (
        times["execution_finished_at"] is not None) else None
    goal_to_accept=(times["accepted_at"]-times["goal_frozen_at"]).total_seconds()/3600 if (
        times["accepted_at"] is not None) else None
    backfilled=bool(price_captured and price_captured>start.date().isoformat())
    return {
        "schema":"fsl/mission-clock-result/0.8.3",
        "run_id":run,
        "evidence_class":data["evidence_class"],
        "model_id":data["model_id"],
        "model_revision":data["model_revision"],
        "provider":data["provider"],
        "access_route":data["access_route"],
        "original_timestamps":{k:data.get(k) for k in fields},
        "utc_timestamps":{k:v.isoformat() if v is not None else None
                          for k,v in times.items()},
        "goal_to_outcome_hours":goal_to_accept,
        "elapsed_execution_hours":duration,
        "source_vintage_calendar_timezone":"Asia/Taipei",
        "price_vintage_backfilled_from_after_run_start":backfilled,
        "price_vintage_admissible_at_run_start":(
            bool(price_captured and not backfilled and pricing_effective
                 and pricing_effective<=start.date().isoformat())),
        "24h_continuous_autonomy_certified":False,
        "48h_continuous_autonomy_certified":False,
        "final_functional_work_independently_verified":False,
        "clock_precision":"timezone_aware_instant_not_a_day_level_release_date",
        "warnings":[
            "One claimed execution interval is not a continuous work/progress certificate.",
            "Provider model availability and historical plan entitlement need their own evidence.",
            "Time of an event, publication of its source and retrieval by this study are different.",
            "An acceptance time alone does not verify product quality or math-proof correctness.",
        ],
    }
