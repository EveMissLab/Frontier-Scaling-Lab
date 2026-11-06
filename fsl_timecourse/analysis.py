"""Temporal analysis of public AI model metrics, with methodological break guards.

An Arena rating, IPS score, Hub popularity counter, benchmark submission score
and independently controlled task success rate have DIFFERENT estimands.

This module never computes "cognitive multiplier" from a leaderboard.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import date
import math
import statistics

from fsl_sources.catalog import CatalogError, iso_day

# Official historical methodology changes, see:
# https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset
# These are conservatively treated as non-comparable across the boundary.
ARENA_METHOD_BREAKS = (
    ("2024-01-09", "raw_text_elo_to_bradley_terry"),
    ("2025-05-16", "style_control_default_and_scale_adjustment"),
    ("2025-07-23", "frequency_based_reweighting"),
    ("2026-10-12", "agent_bash_signal_definition_change"),
)


def arena_regime(methodology, published):
    """Return conservative historical measurement regime, not a capability era."""
    iso_day(published)
    if not methodology.startswith("arena-dataset:"):
        return "non_arena_unversioned"
    parts = methodology.split(":")
    if len(parts) != 3:
        return "arena_unrecognized_methodology"
    config, metric = parts[1:]
    if metric == "arena_rating":
        if config == "text":
            if published < "2024-01-09":
                return "raw_elo_pre_2024_01_09"
            if published < "2025-05-16":
                return "raw_bt_pre_style_shift"
            if published < "2025-07-23":
                return "raw_bt_after_style_shift"
            return "raw_bt_reweighted_2025_07_23"
        if config.endswith("_style_control"):
            if published < "2025-05-16":
                return "style_control_pre_default"
            if published < "2025-07-23":
                return "style_control_pre_reweight"
            return "style_control_reweighted_2025_07_23"
        if published < "2025-07-23":
            return "rating_pre_reweight"
        return "rating_reweighted_2025_07_23"
    if metric == "ips_score":
        if config == "agent_bash_recovery_steps":
            return ("bash_recovery_pre_switch" if published < "2026-10-12"
                    else "bash_recovery_post_switch_incompatible")
        if config == "agent_bash_reliability":
            return "bash_reliability_post_switch"
        return "agent_ips_" + config
    return "arena_unrecognized_metric"


def _fetch_rows(db, *, model_id, measure, category, methodology, channel,
                as_of, mode):
    if mode not in ("strict_asof", "retrospective"):
        raise CatalogError("mode must be strict_asof or retrospective")
    iso_day(as_of, "as_of")
    required = (model_id, measure, category, methodology, channel)
    if not all(isinstance(x, str) and x for x in required):
        raise CatalogError("all stratum identifiers are required")
    if channel not in ("metadata", "preference", "benchmark", "community"):
        raise CatalogError("unrecognized channel")
    query = """SELECT o.observation_id,o.external_model_id,o.measure,o.value,o.unit,
           o.channel,o.category,o.methodology,o.sample_size,o.ci_low,o.ci_high,
           o.published_on,o.provenance_flags,
           s.source_type,s.source_url,s.source_license,s.retrieved_on,s.snapshot_id
        FROM public_observations o JOIN public_snapshots s
          ON o.snapshot_id=s.snapshot_id
        WHERE o.external_model_id=? AND o.measure=?
          AND o.category=? AND o.methodology=? AND o.channel=?
          AND (o.published_on IS NOT NULL AND o.published_on<=?)
          """
    args = [model_id,measure,category,methodology,channel,as_of]
    if mode == "strict_asof":
        query += "AND s.retrieved_on<=? "
        args.append(as_of)
    query += "ORDER BY o.published_on,s.retrieved_on,s.snapshot_id"
    return [dict(row) for row in db.execute(query, args)]


def _resolve_publication_date(rows):
    """For revised snapshots, choose latest *retrieval* of each publication.

    Same-day competing source values cannot be resolved by lexicographic SHA.
    Prefer an explicit audit rather than silently keeping a convenient score.
    """
    grouped = {}
    for row in rows:
        grouped.setdefault(row["published_on"], []).append(row)
    chosen, conflicts = [], []
    for published, items in sorted(grouped.items()):
        latest = max(x["retrieved_on"] for x in items)
        candidates = [x for x in items if x["retrieved_on"] == latest]
        values = {(round(float(x["value"]), 12), x["unit"],
                   x["sample_size"], x["ci_low"], x["ci_high"]) for x in candidates}
        if len(values) != 1:
            conflicts.append({"published_on": published,
                              "retrieved_on": latest, "records": len(candidates)})
            continue
        row = dict(candidates[0])
        row["repeated_retrieval_records"] = len(items)
        chosen.append(row)
    return chosen, conflicts


def _delta(first, last):
    if first["unit"] != last["unit"]:
        raise CatalogError("cannot compare observations with different units")
    days = (date.fromisoformat(last["published_on"]) -
            date.fromisoformat(first["published_on"])).days
    if days <= 0:
        raise CatalogError("delta needs distinct chronological publication dates")
    difference = last["value"] - first["value"]
    naive_interval = None
    if (first["ci_low"] is not None and first["ci_high"] is not None and
        last["ci_low"] is not None and last["ci_high"] is not None):
        naive_interval = [
            last["ci_low"] - first["ci_high"],
            last["ci_high"] - first["ci_low"],
        ]
    return {
        "start": first["published_on"], "end": last["published_on"],
        "interval_days": days,
        "level_change": difference,
        "unit": first["unit"],
        "naive_interval_difference_envelope": naive_interval,
        "note": ("A difference in leaderboard LEVEL, not a parameter or capability "
                 "multiplier; intervals ignore covariance/repeated-voter dependence."),
    }


def _slope(points):
    """Robust Theil–Sen descriptive slope per 90 days (no fit without 4 dates)."""
    if len(points) < 4:
        return None
    span = (date.fromisoformat(points[-1]["published_on"]) -
            date.fromisoformat(points[0]["published_on"])).days
    if span < 60:
        return None
    slopes = []
    for i, a in enumerate(points):
        for b in points[i+1:]:
            days = (date.fromisoformat(b["published_on"]) -
                    date.fromisoformat(a["published_on"])).days
            if days > 0:
                slopes.append((b["value"] - a["value"]) * 90 / days)
    return statistics.median(slopes) if slopes else None


def analyze_series(db, *, model_id, measure, category, methodology, channel,
                   as_of, mode="strict_asof", min_samples=100):
    """Report only within-stratum temporal *levels* and methodological regimes.

    Retrospective mode may read a 2024 leaderboard archived in 2026, but is
    prohibited from being used as a 2024 prequential validation snapshot.
    """
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 0:
        raise CatalogError("min_samples must be a nonnegative integer")
    rows = _fetch_rows(
        db, model_id=model_id, measure=measure, category=category,
        methodology=methodology, channel=channel, as_of=as_of, mode=mode)
    observations, conflicts = _resolve_publication_date(rows)
    dropped = []
    kept = []
    for row in observations:
        n = row["sample_size"]
        if min_samples and (n is None or n < min_samples):
            dropped.append({"published_on": row["published_on"], "sample_size": n})
        else:
            kept.append(row)
    eras = {}
    for item in kept:
        regime = arena_regime(methodology, item["published_on"])
        eras.setdefault(regime, []).append(item)

    segments = []
    for regime, points in eras.items():
        points.sort(key=lambda x: x["published_on"])
        first, last = points[0], points[-1]
        interval = _delta(first,last) if len(points)>=2 else None
        segments.append({
            "regime": regime,
            "n_dates": len(points),
            "first_date": first["published_on"],
            "last_date": last["published_on"],
            "first_value": first["value"],
            "last_value": last["value"],
            "level_difference": interval,
            "theil_sen_level_change_per_90d": _slope(points),
            "status": ("descriptive_temporal_series" if len(points) >= 3
                       else "insufficient_longitudinal_evidence"),
            "retrieved_after_publication": any(
                p["retrieved_on"] > p["published_on"] for p in points),
            "points": [
                {"published_on": p["published_on"], "retrieved_on": p["retrieved_on"],
                 "value": p["value"], "unit": p["unit"],
                 "sample_size": p["sample_size"], "ci_low": p["ci_low"],
                 "ci_high": p["ci_high"], "source_url": p["source_url"],
                 "snapshot_id": p["snapshot_id"]}
                for p in points
            ],
        })
    segments.sort(key=lambda s: s["first_date"])
    return {
        "schema": "fsl/timecourse/0.4",
        "as_of": as_of, "mode": mode,
        "model_id": model_id,
        "stratum": {
            "measure": measure, "category": category,
            "methodology": methodology, "channel": channel,
            "min_samples": min_samples,
        },
        "raw_rows": len(rows),
        "unique_published_dates": len(observations),
        "excluded_low_samples": dropped,
        "same_day_conflicts": conflicts,
        "segments": segments,
        "historical_forecast_admissibility": (
            "known_at_cutoff" if mode == "strict_asof" else "NOT_prequential"),
        "capability_multiplier": None,
        "compute_parameter_conversion": None,
        "warnings": [
            "Arena and benchmark score levels are not ratios of cognitive ability.",
            "Methodology regime boundaries forbid unqualified across-era growth claims.",
            "A fixed model's changing Arena rating can reflect changing opponents/voters.",
            "A retrospective history fetched later cannot validate an earlier issued prediction.",
            "Independent training compute and matched inference budgets are required for causal scaling claims.",
        ],
    }


def study_readiness(db, *, as_of):
    """Audit what longitudinal evidence is missing instead of inventing an index."""
    iso_day(as_of, "as_of")
    rows = db.execute("""SELECT o.channel,s.source_type,o.measure,
             o.methodology,o.external_model_id,o.published_on,
             s.retrieved_on
           FROM public_observations o JOIN public_snapshots s
             ON o.snapshot_id=s.snapshot_id
           WHERE s.retrieved_on<=? AND
                 (o.published_on IS NULL OR o.published_on<=?)""",
           (as_of,as_of)).fetchall()
    counts = {}
    distinct = {}
    for row in rows:
        channel = row["channel"]
        counts[channel] = counts.get(channel,0)+1
        if row["published_on"]:
            k=(row["source_type"],row["external_model_id"],channel,
               row["measure"],row["methodology"])
            distinct.setdefault(k,set()).add(row["published_on"])
    repeated = sum(len(dates)>=3 for dates in distinct.values())
    return {
        "as_of": as_of, "source_observations": counts,
        "longitudinal_candidate_strata_with_3_dates": repeated,
        "parameter_disclosure_pairs_verified": False,
        "matched_task_budget_trials": False,
        "can_identify_2_to_3x_cognition": False,
        "can_identify_5_to_10x_parameters": False,
        "status": "measurement_only_not_causal_identification",
        "next_data_needs": [
            "At least three time points within the same methodology era.",
            "Stable model aliases, benchmark protocol and independent task budgets.",
            "Comparable public total/active parameter disclosures across model versions.",
            "Connected training-run hardware evidence rather than campus-count sums.",
            "An external held-out, versioned task success study for effective capabilities.",
        ],
    }
