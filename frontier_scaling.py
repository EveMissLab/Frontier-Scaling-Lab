"""Frontier Scaling Lab v0.1: reproducible interval inference, not model disclosure."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "data" / "scenarios.json"
EVIDENCE = ROOT / "data" / "evidence.jsonl"
FIELDS = {
    "site.gpu_count", "site.site_count", "site.power_mw", "site.pue",
    "site.it_system_share", "site.system_w_per_gpu", "site.stage",
    "hardware.peak_flops_per_gpu",
    "run.connected_fraction", "run.training_fraction", "run.days",
    "run.mfu", "run.pretraining_fraction", "run.tokens",
    "run.overhead", "run.active_ratio", "run.cross_site_fabric",
}


class ResearchError(ValueError):
    pass


def span(value, name, *, positive=True, fraction=False):
    """Get a finite ordered [low, high] interval. No probabilities are assumed."""
    if isinstance(value, bool):
        raise ResearchError(f"{name}: boolean is not numeric")
    pair = [value, value] if isinstance(value, (float, int)) else value
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ResearchError(f"{name}: expected a number or [low, high]")
    if any(isinstance(x, bool) or not isinstance(x, (float, int)) for x in pair):
        raise ResearchError(f"{name}: nonnumeric bound")
    lo, hi = map(float, pair)
    if not (math.isfinite(lo) and math.isfinite(hi) and 0 <= lo <= hi):
        raise ResearchError(f"{name}: invalid interval")
    if positive and lo <= 0:
        raise ResearchError(f"{name}: expected a positive interval")
    if fraction and hi > 1:
        raise ResearchError(f"{name}: a fraction must be <= 1")
    return [lo, hi]


def estimate(case, *, include_unbuilt=False):
    """Conservative independent-assumption box (not confidence interval)."""
    site, hardware, run = case["site"], case["hardware"], case["run"]
    stage = site["stage"]
    kind = case["kind"]
    if kind not in ("reference_simulation", "counterfactual", "observational"):
        raise ResearchError("unknown scenario kind")
    if stage not in ("reference", "planned", "construction", "operational", "cancelled"):
        raise ResearchError("unknown site stage")
    if stage == "cancelled":
        raise ResearchError("cancelled projects cannot provide compute")
    if stage in ("planned", "construction") and not include_unbuilt:
        raise ResearchError("site is unbuilt: use --include-unbuilt for a conditional estimate")
    if kind == "observational" and stage != "operational" and not include_unbuilt:
        raise ResearchError("an unbuilt site is not an observed deployment")
    if kind == "observational" and stage == "reference":
        raise ResearchError("a vendor reference design is not an observed facility")
    sites = span(site.get("site_count", 1), "site_count")
    if "gpu_count" in site and "power_mw" in site:
        raise ResearchError("select GPU count OR power conversion, not both")
    if "gpu_count" in site:
        gpus = span(site["gpu_count"], "gpu_count")
        gpu_method = "direct_count"
    else:
        power = span(site["power_mw"], "power_mw")
        pue = span(site["pue"], "pue")
        if pue[0] < 1:
            raise ResearchError("PUE cannot be below 1")
        it_fraction = span(site["it_system_share"], "it_system_share", fraction=True)
        system_watts = span(site["system_w_per_gpu"], "system_w_per_gpu")
        # AC site MW -> IT MW -> proportional GPU systems.
        # The per-GPU system watts must include hosts and networking.
        gpus = [
            power[0] * 1e6 / pue[1] * it_fraction[0] / system_watts[1],
            power[1] * 1e6 / pue[0] * it_fraction[1] / system_watts[0],
        ]
        gpu_method = "power_to_systems"
    peak = span(hardware["peak_flops_per_gpu"], "peak_flops_per_gpu")
    connected = span(run["connected_fraction"], "connected_fraction", fraction=True)
    training = span(run["training_fraction"], "training_fraction", fraction=True)
    days = span(run["days"], "days")
    mfu = span(run["mfu"], "mfu", fraction=True)
    pretrain = span(run["pretraining_fraction"], "pretraining_fraction", fraction=True)
    tokens = span(run["tokens"], "tokens")
    overhead = span(run["overhead"], "overhead")
    if overhead[0] < 1:
        raise ResearchError("overhead must be >= 1")
    active_ratio = span(run["active_ratio"], "active_ratio", fraction=True)
    if not isinstance(run.get("cross_site_fabric", False), bool):
        raise ResearchError("cross_site_fabric must be boolean")

    # A global facility count is NOT one connected training cluster. The latter
    # requires explicit evidence/assumption of cross-site synchronous fabric.
    fabric_sites = sites if run.get("cross_site_fabric", False) else [1, 1]
    fleet = [gpus[0] * sites[0], gpus[1] * sites[1]]
    run_gpus = [gpus[i] * fabric_sites[i] * connected[i] for i in (0, 1)]
    allocated = [run_gpus[i] * training[i] for i in (0, 1)]
    compute = [
        allocated[i] * peak[i] * mfu[i] * days[i] * 86400
        for i in (0, 1)
    ]
    pretraining_compute = [compute[i] * pretrain[i] for i in (0, 1)]
    # Baseline 6 * N_active * D * overhead; highly approximate for MoE,
    # long context, non-transformer models, multimodality and RL.
    active_params = [
        pretraining_compute[0] / (6 * tokens[1] * overhead[1]),
        pretraining_compute[1] / (6 * tokens[0] * overhead[0]),
    ]
    total_params = [
        active_params[0] / active_ratio[1],
        active_params[1] / active_ratio[0],
    ]
    ability = case.get("capability_hypothesis_multiplier")
    if ability is not None:
        ability = span(ability, "capability_hypothesis_multiplier")

    return {
        "scenario_id": case["id"],
        "kind": kind,
        "site_stage": stage,
        "target_year": case.get("target_year"),
        "estimate_type": "conditional_assumption_extrema_not_confidence_interval",
        "capacity_is_observed": kind == "observational" and stage == "operational",
        "gpu_method": gpu_method,
        "cross_site_fabric": run.get("cross_site_fabric", False),
        "bounds": {
            "gpus_per_site": gpus, "fleet_gpus": fleet,
            "connected_run_gpus": run_gpus, "allocated_training_gpus": allocated,
            "single_run_flops": compute, "pretraining_flops": pretraining_compute,
            "active_parameters": active_params, "total_parameters": total_params,
        },
        "capability_hypothesis": {
            "multiplier": ability,
            "identification": "UNMEASURED_NOT_DERIVED_FROM_PARAMETERS",
        },
        "warnings": [
            "Vendor peak is not sustained throughput; MFU and precision must be compatible.",
            "Parameter estimates require strong assumptions on tokens and architecture.",
            "Multi-campus capacity is not one training run absent a specified fabric.",
            "No proprietary AI model parameters or cognitive ability are inferred as facts.",
        ],
    }


def canonical_hash(obj):
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def timestamp(value, *, end_of_day=False):
    try:
        if len(value) == 10:
            return dt.datetime.combine(dt.date.fromisoformat(value),
                                       dt.time.max if end_of_day else dt.time.min,
                                       tzinfo=dt.timezone.utc)
        when = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("timezone required")
        return when.astimezone(dt.timezone.utc)
    except (AttributeError, ValueError) as exc:
        raise ResearchError(f"invalid timestamp: {value}") from exc


def validate_event(event):
    required = ("id", "recorded_at", "scenario_id", "field", "source_kind", "state")
    if not isinstance(event, dict) or any(not event.get(k) for k in required):
        raise ResearchError("missing event fields")
    if event["field"] not in FIELDS:
        raise ResearchError("unsupported evidence field")
    if event["source_kind"] not in ("manufacturer", "filing", "public_record",
                                    "research", "press_release", "assumption"):
        raise ResearchError("invalid source kind")
    if event["state"] not in ("asserted", "retracted"):
        raise ResearchError("invalid evidence state")
    timestamp(event["recorded_at"])
    if event["source_kind"] != "assumption":
        source = event.get("source_url", "")
        url = urlsplit(source)
        if url.scheme != "https" or not url.netloc:
            raise ResearchError("non-assumption evidence must have HTTPS source_url")
    value = event.get("value")
    if event["state"] == "retracted":
        if value is not None:
            raise ResearchError("retraction value must be null")
    elif event["field"] == "site.stage":
        if value not in ("reference", "planned", "construction", "operational", "cancelled"):
            raise ResearchError("invalid stage")
    elif event["field"] == "run.cross_site_fabric":
        if not isinstance(value, bool):
            raise ResearchError("cross-site fabric must be true or false")
    else:
        span(value, event["field"])


def read_evidence(path):
    file = Path(path)
    if not file.exists():
        return []
    results, seen = [], set()
    for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            validate_event(event)
            if event["id"] in seen:
                raise ResearchError("duplicate evidence ID")
            seen.add(event["id"])
            results.append(event)
        except (ResearchError, ValueError) as exc:
            raise ResearchError(f"{file}:{number}: {exc}") from exc
    return results


def append_evidence(path, event):
    validate_event(event)
    if event["id"] in {row["id"] for row in read_evidence(path)}:
        raise ResearchError("duplicate evidence ID")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def asof_events(events, as_of):
    cutoff = timestamp(as_of, end_of_day=True)
    latest = {}
    for index, event in sorted(enumerate(events),
                               key=lambda x: (timestamp(x[1]["recorded_at"]), x[0])):
        if timestamp(event["recorded_at"]) <= cutoff:
            latest[(event["scenario_id"], event["field"])] = event
    return list(latest.values())


def overlay_evidence(case, events, as_of):
    result = copy.deepcopy(case)
    applied = []
    for event in asof_events(events, as_of):
        if event["scenario_id"] != case["id"]:
            continue
        if event["state"] == "asserted":
            section, field = event["field"].split(".")
            result[section][field] = copy.deepcopy(event["value"])
        applied.append({
            "id": event["id"], "state": event["state"], "field": event["field"],
            "source_url": event.get("source_url"),
        })
    return result, applied


def backtest(forecast, actuals):
    """Assess only disclosed later parameter outcomes, never inferred ability."""
    cutoff = timestamp(forecast["as_of"], end_of_day=True)
    records = []
    for obs in actuals:
        if obs.get("scenario_id") != forecast["scenario_id"]:
            continue
        source = urlsplit(obs.get("source_url", ""))
        if source.scheme != "https" or not source.netloc:
            raise ResearchError("outcome requires a cited HTTPS source")
        if timestamp(obs["published_at"]) <= cutoff:
            raise ResearchError("future outcome already known at forecast cutoff")
        metric = obs["metric"]
        if metric not in ("active_parameters", "total_parameters"):
            raise ResearchError("backtest supports disclosed parameter values only")
        value = float(obs["value"])
        if not math.isfinite(value) or value <= 0:
            raise ResearchError("invalid observed parameter value")
        low, high = forecast["bounds"][metric]
        records.append({
            "metric": metric, "within_interval": low <= value <= high,
            "absolute_log_midpoint_error": abs(math.log(value / math.sqrt(low * high))),
            "source_url": obs["source_url"],
        })
    return {
        "scenario_id": forecast["scenario_id"], "n_observations": len(records),
        "interval_coverage": (
            sum(x["within_interval"] for x in records) / len(records) if records else None
        ),
        "details": records,
        "warning": "Small-sample coverage is not probabilistic forecast calibration.",
    }


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def output_json(obj, path=None):
    content = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False,
                         allow_nan=False) + "\n"
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Frontier Scaling Lab v0.1")
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("forecast")
    f.add_argument("--config", default=str(CONFIG))
    f.add_argument("--evidence", default=str(EVIDENCE))
    f.add_argument("--scenario", required=True)
    f.add_argument("--as-of")
    f.add_argument("--include-unbuilt", action="store_true")
    f.add_argument("--output")
    e = sub.add_parser("evidence")
    e.add_argument("--evidence", default=str(EVIDENCE))
    e.add_argument("--as-of")
    r = sub.add_parser("record")
    r.add_argument("--evidence", default=str(EVIDENCE))
    r.add_argument("--event", required=True)
    b = sub.add_parser("backtest")
    b.add_argument("--forecast", required=True)
    b.add_argument("--actuals", required=True)
    b.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        if args.command == "forecast":
            config = read_json(args.config)
            as_of = args.as_of or today
            if timestamp(as_of, end_of_day=True) < timestamp(config["as_of"]):
                raise ResearchError("cannot backdate a newer scenario baseline")
            cases = [case for case in config["scenarios"] if case["id"] == args.scenario]
            if len(cases) != 1:
                raise ResearchError("scenario not uniquely found")
            events = read_evidence(args.evidence)
            case, audit = overlay_evidence(cases[0], events, as_of)
            result = estimate(case, include_unbuilt=args.include_unbuilt)
            result.update({
                "as_of": as_of,
                "schema": "fsl/forecast/0.1",
                "baseline_as_of": config["as_of"],
                "effective_input_sha256": canonical_hash(case),
                "evidence_asof_sha256": canonical_hash(asof_events(events, as_of)),
                "applied_evidence": audit,
            })
            output_json(result, args.output)
        elif args.command == "evidence":
            output_json(asof_events(read_evidence(args.evidence), args.as_of or today))
        elif args.command == "record":
            event = read_json(args.event)
            append_evidence(args.evidence, event)
            output_json({"appended": event["id"]})
        elif args.command == "backtest":
            actuals = read_json(args.actuals)
            output_json(backtest(read_json(args.forecast), actuals["outcomes"]), args.output)
    except (ResearchError, ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
