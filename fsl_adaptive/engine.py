"""Adaptive scenario ensemble for delayed hardware realization and parameter plateaus.

SPDX-License-Identifier: Apache-2.0

This module predicts *conditional model-parameter multipliers*, not real secret
weights, universal cognition, or verified future commissioning. Weights can be
updated only from later, independently disclosed observational outcomes.
"""
from __future__ import annotations

import copy
import math

from .registry import DataError, as_date, digest, finite_positive, snapshot, training_feedback


def _num(value, name):
    return finite_positive(value, name)


def validate_config(config):
    if config.get("schema_version") != "fsl-adaptive/0.2":
        raise DataError("expected schema_version=fsl-adaptive/0.2")
    if config.get("data_classification") not in ("synthetic", "observational"):
        raise DataError("data_classification must be synthetic or observational")
    as_date(config["baseline"]["as_of"])
    year = _num(config["baseline"]["year"], "baseline.year")
    if not 2000 <= year <= 2100:
        raise DataError("invalid baseline year")
    if config.get("calibration_group") is None:
        raise DataError("calibration_group is required")
    cohorts = config.get("cohorts")
    variants = config.get("hypotheses")
    if not isinstance(cohorts, list) or not cohorts:
        raise DataError("at least one site cohort is needed")
    if not isinstance(variants, list) or len(variants) < 2:
        raise DataError("at least two alternative hypotheses are needed")
    site_ids = [c["site_id"] for c in cohorts]
    variant_ids = [v["id"] for v in variants]
    if len(set(site_ids)) != len(site_ids) or len(set(variant_ids)) != len(variant_ids):
        raise DataError("site and hypothesis identifiers must be unique")
    for cohort in cohorts:
        if cohort["stage"] not in ("operational", "construction", "planned", "cancelled"):
            raise DataError("unknown cohort stage")
        for field in ("gpus", "ready_year", "peak_flops_gpu", "connected_fraction"):
            _num(cohort[field], field)
        if cohort["connected_fraction"] > 1:
            raise DataError("connected_fraction must be <= 1")
    for variant in variants:
        for field in ("installation_lag_years", "maturation_tau_years",
                      "release_lag_years", "parameter_elasticity",
                      "parameter_ceiling", "training_fraction", "mfu",
                      "annual_algorithmic_yield"):
            value = variant.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise DataError(f"{field}: expected finite number")
        if variant["installation_lag_years"] < 0 or variant["release_lag_years"] < 0:
            raise DataError("lags cannot be negative")
        if variant["maturation_tau_years"] <= 0 or variant["parameter_elasticity"] <= 0:
            raise DataError("maturation and elasticity must be positive")
        if variant["parameter_ceiling"] <= 1:
            raise DataError("parameter_ceiling must exceed 1")
        if not (0 < variant["mfu"] <= 1 and 0 < variant["training_fraction"] <= 1):
            raise DataError("training share/MFU must lie in (0,1]")
        if variant["annual_algorithmic_yield"] <= -1:
            raise DataError("algorithmic yield cannot decrease by 100% or more annually")


def _overlay_cohorts(config, facts):
    cohorts = copy.deepcopy(config["cohorts"])
    by_id = {site["site_id"]: site for site in cohorts}
    used = []
    for (entity_id, field), record in facts.items():
        if entity_id not in by_id or not field.startswith("site."):
            continue
        key = field[5:]
        if key == "status":  # Historical synonym is not legal evidence field.
            raise DataError("site.status is not supported; use site.stage")
        old = by_id[entity_id].get(key)
        value = record["value"]
        if key == "stage" and value not in ("operational","construction","planned","cancelled"):
            raise DataError("a vendor reference may not be treated as an operating cohort")
        if key in ("gpus", "ready_year", "peak_flops_gpu", "connected_fraction"):
            _num(value, key)
            if key == "connected_fraction" and value > 1:
                raise DataError("connected_fraction must be <= 1")
        by_id[entity_id][key] = value
        used.append({"site_id": entity_id, "field": field, "old": old,
                     "new": value, "event_id": record["event_id"]})
    return cohorts, used


def _compute_sites(cohorts, year, variant, *, allow_planned):
    """Compute feasible one-site connected peak FLOP/s (NOT pooled fleet FLOPs)."""
    rows = []
    for site in cohorts:
        stage = site["stage"]
        if stage == "cancelled":
            continue
        is_plan = stage != "operational"
        if is_plan and not allow_planned:
            continue
        ready = float(site["ready_year"])
        if is_plan:
            ready += variant["installation_lag_years"]
        age = year - ready
        if age < 0:
            continue
        # Late realization of past physical investment: available hardware can
        # gradually reach sustained utilization as cooling, network and software mature.
        maturity = 0.5 + 0.5 * (1 - math.exp(-age / variant["maturation_tau_years"]))
        connected_peak = (float(site["gpus"]) * float(site["peak_flops_gpu"])
                          * float(site["connected_fraction"]) * maturity)
        rows.append({
            "site_id": site["site_id"],
            "site_stage": stage,
            "hardware_peak_flops_per_second": connected_peak,
            "maturity_fraction": maturity,
            "conditional_planned": is_plan,
            "ready_year_conditional": ready,
        })
    return sorted(rows, key=lambda x: (-x["hardware_peak_flops_per_second"], x["site_id"]))


def forecast_variant(config, cohorts, variant, target_year, *, allow_planned=False):
    baseline_year = float(config["baseline"]["year"])
    if target_year < baseline_year:
        raise DataError("target year predates the baseline")
    # Only operational hardware in the baseline, never unbuilt/announced campus MW.
    old_sites = _compute_sites(cohorts, baseline_year, variant, allow_planned=False)
    if not old_sites:
        raise DataError("baseline must include an operational connected site")
    usable_year = target_year - variant["release_lag_years"]
    projected = _compute_sites(cohorts, usable_year, variant, allow_planned=allow_planned)
    if not projected:
        raise DataError("no eligible sites for target horizon")
    old_peak = old_sites[0]["hardware_peak_flops_per_second"]
    new_peak = projected[0]["hardware_peak_flops_per_second"]
    # Assumed MFU/training allocation are visible, but with a fixed fraction
    # in each variant they cancel in the *ratio*. Absolute FLOPs require run duration.
    old_training = old_peak * variant["training_fraction"] * variant["mfu"]
    new_training = new_peak * variant["training_fraction"] * variant["mfu"]
    capacity_ratio = new_training / old_training
    elapsed = target_year - baseline_year
    yield_factor = (1 + variant["annual_algorithmic_yield"]) ** elapsed
    unbounded_ratio = max(0.0, capacity_ratio ** variant["parameter_elasticity"] * yield_factor)
    # Smooth saturation under a *hypothesized* model-specific upper ratio.
    ceiling = variant["parameter_ceiling"]
    excess = max(0.0, unbounded_ratio - 1.0)
    parameter_multiplier = 1 + (ceiling - 1) * (-math.expm1(-excess / (ceiling - 1)))
    return {
        "id": variant["id"],
        "assumed_parameter_ceiling": ceiling,
        "parameter_multiplier": parameter_multiplier,
        "unbounded_parameter_ratio": unbounded_ratio,
        "single_run_compute_ratio": capacity_ratio,
        "matured_training_peak_flops_per_second": new_training,
        "baseline_training_peak_flops_per_second": old_training,
        "selected_site_id": projected[0]["site_id"],
        "selected_site_stage": projected[0]["site_stage"],
        "selected_site_conditional": projected[0]["conditional_planned"],
        "eligible_site_count_not_fleet_pool": len(projected),
        "available_hardware_year_after_release_lag": usable_year,
        "conditional_installed_stage_lag_years": variant["installation_lag_years"],
        "maturation_tau_years": variant["maturation_tau_years"],
        "algorithmic_yield_factor": yield_factor,
    }


def _huber_log_error(actual, predicted, delta=0.45):
    e = abs(math.log(actual / predicted))
    return (0.5 * (e / delta) ** 2 if e <= delta
            else e / delta - 0.5), e


def posterior(db, as_of, group, ids, *, learning_rate=0.6):
    """Prequential exponential-weights update with heavy-tail robust loss.

    Weights are *relative hypothesis weights*, not probabilities of model
    truth or calibrated confidence intervals. Feedback is only admitted for
    independently sourced outcomes published after its stored forecast.
    """
    if not 0 < learning_rate <= 2:
        raise DataError("learning_rate must lie in (0,2]")
    weights = {key: 1 / len(ids) for key in ids}
    pairs = training_feedback(db, as_of, group)
    evaluated, drift_count, drift = 0, 0, False
    for published_forecast, actual, feedback_id in pairs:
        estimates = {
            item["id"]: item["parameter_multiplier"]
            for item in published_forecast.get("hypotheses", [])
        }
        if not all(key in estimates for key in ids):
            continue
        losses = {}
        abs_errors = []
        for key in ids:
            loss, err = _huber_log_error(actual, estimates[key])
            losses[key] = loss
            abs_errors.append(err)
        for key in ids:
            weights[key] *= math.exp(-learning_rate * min(10.0, losses[key]))
        total = sum(weights.values())
        if not total or not math.isfinite(total):
            weights = {key: 1 / len(ids) for key in ids}
        else:
            # Small uniform mixture prevents irreversible hypothesis extinction.
            weights = {key: 0.99 * weights[key] / total + 0.01 / len(ids) for key in ids}
        evaluated += 1
        # Not an automatic retraining claim: flag sustained bad fit for audit.
        if min(abs_errors) > math.log(2.5):
            drift_count += 1
        else:
            drift_count = 0
        if drift_count >= 2:
            drift = True
    return {
        "weights": weights,
        "n_disclosed_outcomes": evaluated,
        "drift_alert": drift,
        "state": "uncalibrated" if evaluated == 0 else "heuristically_updated",
        "note": "Weights are online relative loss scores, not calibrated probabilities.",
    }


def forecast(db, config, *, as_of, target_year, target_key,
             target_class="synthetic", allow_planned=False):
    validate_config(config)
    as_date(as_of)
    if as_of < config["baseline"]["as_of"]:
        raise DataError("cannot issue predictions before scenario baseline was authored")
    if target_class not in ("synthetic", "observational"):
        raise DataError("target_class must be synthetic or observational")
    if target_class == "observational":
        if config["data_classification"] != "observational":
            raise DataError("synthetic configuration cannot be scored as real observations")
        from .registry import https_url
        https_url(config["baseline"].get("source_url"))
        for item in config["cohorts"]:
            if item["stage"] == "operational":
                https_url(item.get("source_url"))
    if not isinstance(target_key, str) or not target_key:
        raise DataError("target_key cannot be blank")
    if isinstance(target_year, bool) or not isinstance(target_year, (int, float)):
        raise DataError("target_year must be numeric")
    if not math.isfinite(target_year) or target_year <= 0:
        raise DataError("target_year must be positive")
    facts, provenance = snapshot(db, as_of)
    cohorts, changes = _overlay_cohorts(config, facts)
    variants = [
        forecast_variant(config, cohorts, h, float(target_year), allow_planned=allow_planned)
        for h in config["hypotheses"]
    ]
    ids = [v["id"] for v in variants]
    updated = posterior(db, as_of, config["calibration_group"], ids)
    weights = updated["weights"]
    mean = sum(weights[v["id"]] * v["parameter_multiplier"] for v in variants)
    predicted_range = [min(v["parameter_multiplier"] for v in variants),
                       max(v["parameter_multiplier"] for v in variants)]
    return {
        "schema_version": "fsl-adaptive/forecast/0.2",
        "as_of": as_of,
        "target_year": float(target_year),
        "target_key": target_key,
        "target_class": target_class,
        "calibration_group": config["calibration_group"],
        "scenario_mode": "include_unbuilt_conditionally" if allow_planned else "operational_only",
        "input_sha256": digest({"config": config, "effective_cohorts": cohorts,
                                "evidence_ids": provenance["event_ids"]}),
        "evidence_sha256": provenance["sha256"],
        "changed_fields": changes,
        "hypotheses": variants,
        "ensemble": {
            "weighted_parameter_multiplier": mean,
            "hypothesis_envelope": predicted_range,
            "weights": weights,
            "online_update": updated,
        },
        "cognition": {
            "user_proposed_capability_range": config.get("cognitive_multiplier_hypothesis", [2, 3]),
            "inferred_from_model_size": False,
            "measured": False,
        },
        "limitations": [
            "This is a conditional engineering model, not a forecast confidence interval.",
            "The parameter ceiling is a scenario hypothesis, not an empirical law.",
            "Public model release dates are not parameter disclosures or training timestamps.",
            "New hardware only contributes after a scenario-specific assumed availability lag.",
            "One connected site is selected for a training run; fleet capacity is never pooled.",
            "Cognitive performance requires separately measured budget-matched benchmarks.",
        ],
    }
