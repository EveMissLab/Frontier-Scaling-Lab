"""ASSO v0.21: source-faithful, read-only substitution observations.
Recorded assertions and synthetic scenarios are not empirical certification.
SPDX-License-Identifier: Apache-2.0
"""
from collections import defaultdict
from datetime import datetime, timezone, time, date
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data/asso_indicator_catalog_v0.21.json"
GICCF_PATH = ROOT / "data/giccf_capability_catalog_v0.13.json"
SCHEMA = "fsl/asso/0.21"
MODES = {"strict_known_at_time", "retrospective_reconstruction"}
TIERS = {"unobserved", "provider_claim", "provider_demo", "repeatable_test",
         "independent_repeated", "longitudinal_independent", "synthetic_fixture"}
COMPUTABLE = {"repeatable_test", "independent_repeated", "longitudinal_independent",
              "synthetic_fixture"}
GATES = {"passed", "failed", "unknown", "not_applicable"}
ENVIRONMENTS = {"controlled_simulation", "sandbox_tools", "live_digital", "live_physical"}
FIELDS = {"trial":["attempts","delivered","accepted","top_quality","raw_error_trials","accepted_error_trials","human_core_minutes","safety","authorization","physical_receipt_sha256"],"economics":["baseline_cost_minor","alternative_cost_minor","incremental_value_minor","cost_basis","full_cost_attested"],"deployment":["eligible_units","active_units","prior_human_task_units","transferred_prior_task_units","prior_paid_minutes","post_paid_minutes","prior_fte_milli","post_fte_milli","prior_accepted_output","post_accepted_output","hires","exits","involuntary_exits","new_task_families","new_paid_orders","constraints"],"augmentation":["baseline_accepted","baseline_human_minutes","assisted_accepted","assisted_human_minutes"]}
TOP = set("schema_version catalog_version study_id data_class system_stack_sha256 registration_sha256 registered_at baseline_window_start baseline_window_end window_start window_end currency contracts events".split())
CONTRACT = set("contract_id domain_id context_id comparison_group weight environment task_set_sha256 acceptance_sha256 baseline_sha256 min_acceptance_bps max_delivered_error_bps max_core_minutes_per_attempt output_unit organization_unit".split())
EVENT = set("event_id contract_id event_occurred_at source_published_at fsl_recorded_at evidence_tier source_url artifact_sha256 assessor_ref supersedes_event_id kind data".split())
SHA = re.compile(r"[0-9a-f]{64}\Z")


class ASSOError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ASSOError(message)


def exact(x, keys, where):
    require(isinstance(x, dict) and set(x) == set(keys), f"{where}: unexpected or missing fields")


def nonempty(x, where, nullable=False):
    require((nullable and x is None) or (isinstance(x, str) and 0 < len(x.strip()) <= 2048), f"{where}: expected nonempty string")


def fingerprint(x, where, nullable=False):
    require((nullable and x is None) or (isinstance(x, str) and SHA.fullmatch(x)), f"{where}: SHA-256 required")


def integer(x, where, *, nullable=False, signed=False):
    require((nullable and x is None) or (type(x) is int and (signed or x >= 0)), f"{where}: invalid integer")


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, f"duplicate JSON key: {k}")
        result[k] = v
    return result


def load_json(path):
    def invalid_constant(x):
        raise ASSOError(f"non-finite JSON number: {x}")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)


def timestamp(value, *, cutoff=False):
    require(isinstance(value, str), "timestamp must be a string")
    try:
        if cutoff and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.combine(date.fromisoformat(value), time.max, timezone.utc)
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(result.tzinfo is not None and result.utcoffset() is not None,
                "timestamp requires offset")
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ASSOError(f"invalid timestamp: {value}") from exc


def load_catalog(path=CATALOG_PATH):
    c = load_json(path)
    require(c.get("catalog_id") == "ASSO" and c.get("version") == "0.21.0", "catalog version")
    axes = c.get("axes")
    require(isinstance(axes, list) and len(axes) == 12, "expected 12 axes")
    require([a.get("id") for a in axes] == [f"SUB-{i:02d}" for i in range(1, 13)], "axis identifiers")
    for a in axes:
        require("value" in a and a["value"] is None and a.get("status") == "not_measured",
                "definitions must not contain measured values")
        for k in ("label_zh", "label_en", "event_kind", "measurement", "source"):
            nonempty(a.get(k), f"axis {k}")
    return c


def domain_ids():
    return {d["id"] for d in load_json(GICCF_PATH)["civilization_domains"]}


def ratio(n, d):
    if n is None or d is None or d == 0:
        return None
    return Fraction(n, d)


def pack(v):
    return None if v is None else {"numerator": v.numerator, "denominator": v.denominator}


def ge_le(a, b, where):
    if a is not None and b is not None:
        require(a <= b, f"{where}: numerator exceeds denominator")


def validate_data(kind, data):
    exact(data, FIELDS[kind], kind)
    if kind == "trial":
        for k in FIELDS[kind][:7]:
            integer(data[k], k, nullable=True)
        for k in ("safety", "authorization"):
            require(isinstance(data[k], str) and data[k] in GATES, f"invalid {k}")
        fingerprint(data["physical_receipt_sha256"], "physical receipt", nullable=True)
        for a, b in (("delivered", "attempts"), ("accepted", "delivered"),
                     ("accepted", "attempts"), ("top_quality", "accepted"),
                     ("top_quality", "attempts"),
                     ("raw_error_trials", "attempts"), ("accepted_error_trials", "delivered"),
                     ("accepted_error_trials", "attempts")):
            ge_le(data[a], data[b], a)
        if all(data[k] is not None for k in ("accepted", "accepted_error_trials", "delivered")):
            require(data["accepted"] + data["accepted_error_trials"] <= data["delivered"],
                    "valid and erroneous delivered results must be disjoint")
        if data["attempts"] == 0:
            require(data["human_core_minutes"] in (None, 0), "zero attempts with human trial time")
    elif kind == "economics":
        for k in FIELDS[kind][:3]:
            integer(data[k], k, nullable=True, signed=k == "incremental_value_minor")
        require(isinstance(data["cost_basis"], str) and data["cost_basis"] in {"actual", "estimate", "unknown"}, "cost basis")
        require(data["full_cost_attested"] is None or type(data["full_cost_attested"]) is bool,
                "full-cost attestation must be boolean or null")
    elif kind == "deployment":
        for k in FIELDS[kind][:-1]:
            integer(data[k], k, nullable=True)
        for a, b in (("active_units", "eligible_units"),
                     ("transferred_prior_task_units", "prior_human_task_units"),
                     ("involuntary_exits", "exits")):
            ge_le(data[a], data[b], a)
        cs = data["constraints"]
        require(cs is None or isinstance(cs, list), "constraints must be list or null")
        if cs is not None:
            for c in cs:
                nonempty(c, "constraint")
            require(len(cs) == len(set(cs)), "duplicate constraint")
    else:
        for k in FIELDS[kind]:
            integer(data[k], k, nullable=True)


def validate(payload):
    exact(payload, TOP, "study")
    require(payload["schema_version"] == SCHEMA and payload["catalog_version"] == "0.21.0",
            "study version mismatch")
    nonempty(payload["study_id"], "study id")
    dc = payload["data_class"]
    require(isinstance(dc, str) and dc in {"synthetic", "observational"}, "data classification")
    for k in ("system_stack_sha256", "registration_sha256"):
        fingerprint(payload[k], k)
    require(isinstance(payload["currency"], str) and re.fullmatch(r"[A-Z]{3}", payload["currency"]), "currency must be one ISO-style code; monetary units are minor units")
    reg, bs, be, start, end = [timestamp(payload[k]) for k in
                               ("registered_at", "baseline_window_start", "baseline_window_end",
                                "window_start", "window_end")]
    require(reg <= start and bs < be <= start < end and be - bs == end - start,
            "registration, nonoverlap or matched-window duration invalid")
    require(isinstance(payload["contracts"], list) and payload["contracts"], "nonempty contract frame")
    known_domains = domain_ids()
    contracts = {}
    for c in payload["contracts"]:
        exact(c, CONTRACT, "contract")
        for k in ("contract_id", "context_id", "comparison_group", "output_unit", "organization_unit"):
            nonempty(c[k], k, nullable=k == "comparison_group")
        require(c["contract_id"] not in contracts, "duplicate contract")
        require(isinstance(c["domain_id"], str) and c["domain_id"] in known_domains, "unknown GICCF domain")
        require(isinstance(c["environment"], str) and c["environment"] in ENVIRONMENTS, "invalid environment")
        for k in ("task_set_sha256", "acceptance_sha256", "baseline_sha256"):
            fingerprint(c[k], k)
        for k in ("weight", "min_acceptance_bps", "max_delivered_error_bps", "max_core_minutes_per_attempt"):
            integer(c[k], k)
        require(c["weight"] > 0 and 1 <= c["min_acceptance_bps"] <= 10000
                and c["max_delivered_error_bps"] <= 10000, "invalid frozen thresholds")
        contracts[c["contract_id"]] = c
    require(isinstance(payload["events"], list), "events must be a list")
    by_id, latest, events = {}, {}, []
    for e in payload["events"]:
        exact(e, EVENT, "event")
        for k in ("event_id", "contract_id", "supersedes_event_id", "source_url", "assessor_ref"):
            nonempty(e[k], k, nullable=k in {"supersedes_event_id", "source_url", "assessor_ref"})
        eid = e["event_id"]
        require(eid not in by_id and e["contract_id"] in contracts, "duplicate event or unknown contract")
        kind = e["kind"]
        require(isinstance(kind, str) and kind in FIELDS, "unknown event kind")
        tier = e["evidence_tier"]
        require(isinstance(tier, str) and tier in TIERS, "unknown evidence tier")
        fingerprint(e["artifact_sha256"], "artifact", nullable=True)
        require((dc == "synthetic") == (tier == "synthetic_fixture"), "synthetic/observational mixing")
        if dc == "synthetic":
            require(e["source_url"] is None and e["assessor_ref"] is None,
                    "synthetic record cannot present external source or assessor")
        elif tier != "unobserved":
            try:
                u = urlsplit(e["source_url"] or "")
                require(u.scheme == "https" and u.hostname and u.username is None and u.password is None,
                        "observational source requires HTTPS URL without credentials")
            except ValueError as exc:
                raise ASSOError("invalid source URL") from exc
            if tier in COMPUTABLE:
                fingerprint(e["artifact_sha256"], "computable assertion artifact")
            if tier in {"independent_repeated", "longitudinal_independent"}:
                nonempty(e["assessor_ref"], "claimed independent assessor")
        occurred, published, recorded = [timestamp(e[k]) for k in
                                         ("event_occurred_at", "source_published_at", "fsl_recorded_at")]
        require(end <= occurred <= published <= recorded, "event chronology or incomplete window")
        key = (e["contract_id"], kind)
        prev_id = latest.get(key)
        require(e["supersedes_event_id"] == prev_id, "duplicate active event or invalid correction target")
        if prev_id is not None:
            prev = by_id[prev_id]
            require(recorded > prev[2] and published >= prev[1] and occurred >= prev[0],
                    "correction chronology")
        validate_data(kind, e["data"])
        by_id[eid] = (occurred, published, recorded)
        latest[key] = eid
        events.append((key, e, occurred, published, recorded))
    return contracts, events, reg


def combined(*states):
    if "failed" in states:
        return "failed"
    if "unknown" in states:
        return "unknown"
    return "passed"


def test_gate(value, predicate):
    return "unknown" if value is None else ("passed" if predicate(value) else "failed")


def change(prior, post, compression=False):
    if prior is None or post is None or prior == 0:
        return None
    return Fraction(prior-post if compression else post-prior, prior)


def row_metrics(contract, active):
    d = {k: (active[k]["data"] if k in active and active[k]["evidence_tier"] in COMPUTABLE
             else {}) for k in FIELDS}
    t, e, p, a = (d[k] for k in ("trial", "economics", "deployment", "augmentation"))
    q = ratio(t.get("accepted"), t.get("attempts"))
    high = ratio(t.get("top_quality"), t.get("attempts"))
    raw = ratio(t.get("raw_error_trials"), t.get("attempts"))
    escaped = ratio(t.get("accepted_error_trials"), t.get("delivered"))
    human = ratio(t.get("human_core_minutes"), t.get("attempts"))
    delivery = ratio(t.get("delivered"), t.get("attempts"))
    tech = combined(test_gate(q, lambda x: x*10000 >= contract["min_acceptance_bps"]),
                    test_gate(escaped, lambda x: x*10000 <= contract["max_delivered_error_bps"]),
                    test_gate(human, lambda x: x <= contract["max_core_minutes_per_attempt"]))
    env = contract["environment"]
    safety = t.get("safety", "unknown")
    auth = t.get("authorization", "unknown")
    safety_state = ("unknown" if safety == "not_applicable" and env == "live_physical"
                    else "passed" if safety == "not_applicable" else safety)
    auth_state = ("unknown" if auth == "not_applicable" and env.startswith("live_")
                  else "passed" if auth == "not_applicable" else auth)
    physical_state = ("unknown" if env == "live_physical" and not t.get("physical_receipt_sha256")
                      else "passed")
    gates = combined(safety_state, auth_state, physical_state)
    readiness = combined(tech, gates)
    net = None
    basis = e.get("cost_basis", "unknown")
    if (basis != "unknown" and e.get("full_cost_attested") is True
            and all(e.get(k) is not None for k in FIELDS["economics"][:3])):
        net = e["baseline_cost_minor"] - e["alternative_cost_minor"] + e["incremental_value_minor"]
    econ = combined(readiness, test_gate(net if basis == "actual" else None, lambda x: x > 0))
    estimate = combined(readiness, test_gate(net if basis == "estimate" else None, lambda x: x > 0))
    base_productivity = ratio(a.get("baseline_accepted"), a.get("baseline_human_minutes"))
    assisted_productivity = ratio(a.get("assisted_accepted"), a.get("assisted_human_minutes"))
    uplift = None
    if base_productivity is not None and base_productivity > 0 and assisted_productivity is not None:
        uplift = assisted_productivity / base_productivity - 1
    metrics = {
        "SUB-01": {"valid_acceptance_per_attempt": pack(q), "technical_qualification": tech},
        "SUB-02": {"top_quality_per_attempt": pack(high)},
        "SUB-03": {"raw_error_trials_per_attempt": pack(raw), "erroneous_deliveries_per_delivery": pack(escaped), "delivery_coverage": pack(delivery)},
        "SUB-04": {"human_core_minutes_per_attempt": pack(human)},
        "SUB-05": {"net_benefit_minor": net, "cost_basis": basis, "operational_readiness": readiness,
                   "actual_economic_qualification": econ, "estimated_economic_qualification": estimate},
        "SUB-06": {"comparison_group": contract["comparison_group"]},
        "SUB-07": {"active_per_eligible_unit": pack(ratio(p.get("active_units"), p.get("eligible_units")))},
        "SUB-08": {"transferred_per_prior_human_task_unit": pack(ratio(p.get("transferred_prior_task_units"), p.get("prior_human_task_units")))},
        "SUB-09": {"human_ai_productivity_uplift": pack(uplift)},
        "SUB-10": {"paid_minutes_compression": pack(change(p.get("prior_paid_minutes"), p.get("post_paid_minutes"), True)),
                   "fte_compression": pack(change(p.get("prior_fte_milli"), p.get("post_fte_milli"), True)),
                   "hires": p.get("hires"), "exits": p.get("exits"), "involuntary_exits": p.get("involuntary_exits")},
        "SUB-11": {"accepted_output_change": pack(change(p.get("prior_accepted_output"), p.get("post_accepted_output"))),
                   "new_task_families": p.get("new_task_families"), "new_paid_orders": p.get("new_paid_orders")},
        "SUB-12": {"environment": env, "safety_assertion": safety, "authorization_assertion": auth,
                   "physical_receipt_present": bool(t.get("physical_receipt_sha256")), "deployment_gate": gates,
                   "constraints": p.get("constraints")}
    }
    receipts = {k: {"event_id": v["event_id"], "evidence_tier": v["evidence_tier"],
                    "eligible_for_calculation": v["evidence_tier"] in COMPUTABLE,
                    "source_url": v["source_url"], "artifact_sha256": v["artifact_sha256"],
                    "assessor_ref": v["assessor_ref"]} for k, v in sorted(active.items())}
    return {"contract_id": contract["contract_id"], "domain_id": contract["domain_id"],
            "context_id": contract["context_id"], "weight": contract["weight"],
            "output_unit": contract["output_unit"], "organization_unit": contract["organization_unit"],
            "metrics": metrics, "event_receipts": receipts}


def weighted(rows, axis, key):
    counts = {"passed": 0, "failed": 0, "unknown": 0}
    for row in rows:
        counts[row["metrics"][axis][key]] += row["weight"]
    known = counts["passed"] + counts["failed"]
    total = known + counts["unknown"]
    return {"weights": counts, "known_weight": known, "frame_weight": total,
            "known_share": pack(ratio(counts["passed"], known)),
            "coverage": pack(ratio(known, total)),
            "lower_bound": pack(ratio(counts["passed"], total)),
            "upper_bound": pack(ratio(counts["passed"]+counts["unknown"], total))}


def unpack(v):
    return None if v is None else Fraction(v["numerator"], v["denominator"])


def priority_pairs(rows):
    groups = defaultdict(list)
    for row in rows:
        group = row["metrics"]["SUB-06"]["comparison_group"]
        if group is not None:
            groups[group].append(row)
    result = []
    for group, members in sorted(groups.items()):
        for basis in ("actual", "estimate"):
            compared = inversions = ties = unavailable = 0
            for x, y in combinations(members, 2):
                mx, my = x["metrics"], y["metrics"]
                qx, qy = (unpack(m["SUB-01"]["valid_acceptance_per_attempt"]) for m in (mx, my))
                ex, ey = (m["SUB-05"] for m in (mx, my))
                bx, by = ex["net_benefit_minor"], ey["net_benefit_minor"]
                if (None in (qx, qy, bx, by) or ex["cost_basis"] != basis or ey["cost_basis"] != basis
                        or ex["operational_readiness"] != "passed" or ey["operational_readiness"] != "passed"):
                    unavailable += 1
                elif qx == qy or bx == by:
                    ties += 1
                else:
                    compared += 1
                    inversions += int((qx-qy)*(bx-by) < 0)
            result.append({"comparison_group": group, "cost_basis": basis,
                           "candidate_pairs": len(members)*(len(members)-1)//2,
                           "comparable_strict_pairs": compared, "ties": ties,
                           "unavailable_or_ineligible_pairs": unavailable,
                           "inverted_pairs": inversions, "inversion_share": pack(ratio(inversions, compared))})
    return result


def audit(payload, *, as_of, mode="strict_known_at_time"):
    require(isinstance(mode, str) and mode in MODES, "invalid replay mode")
    catalog = load_catalog()
    contracts, events, registered = validate(payload)
    cutoff = timestamp(as_of, cutoff=True)
    visible = {}
    seen = 0
    for (cid, kind), e, occurred, published, recorded in events:
        if registered <= cutoff and occurred <= cutoff and published <= cutoff and (mode == "retrospective_reconstruction" or recorded <= cutoff):
            visible.setdefault(cid, {})[kind] = e
            seen += 1
    rows = [row_metrics(c, visible.get(cid, {})) for cid, c in sorted(contracts.items()) if registered <= cutoff]
    by_domain = defaultdict(list)
    for row in rows:
        by_domain[row["domain_id"]].append(row)
    summaries = {k: {"technical": weighted(v, "SUB-01", "technical_qualification"),
                     "actual_economic": weighted(v, "SUB-05", "actual_economic_qualification")}
                 for k, v in sorted(by_domain.items())}
    computed = {"contract_rows": rows, "domain_frame_summaries": summaries, "priority_inversion_pairs": priority_pairs(rows)}
    synthetic = payload["data_class"] == "synthetic"
    return {"schema_version": SCHEMA, "catalog_axis_count": len(catalog["axes"]),
            "study_id": payload["study_id"], "system_stack_sha256": payload["system_stack_sha256"],
            "currency_minor_units": payload["currency"], "mode": mode, "as_of_utc": cutoff.isoformat(),
            "data_class": payload["data_class"], "visible_event_count": seen,
            "current_event_count": sum(map(len, visible.values())),
            "visible_contract_count": len(rows),
            "synthetic_scenario": computed if synthetic else None,
            "recorded_observational_assertions": None if synthetic else computed,
            "independent_empirical_certification": False, "causal_effect_certified": False,
            "global_occupation_replacement_rate": None, "universal_intelligence_score": None}
