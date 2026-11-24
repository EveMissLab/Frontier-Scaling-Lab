"""KIF conditional trial, flow and population models. Apache-2.0."""
from collections import Counter
from fractions import Fraction
from itertools import combinations
from .constants import CHECKS, BUDGET, STAGES, FLOW_COUNTS, POP_COUNTS, POP_SUMS, COMPUTABLE, STATES
from .common import (require, exact, choice, integer, boolean, sha, ratio, pack,
                     gate, test_gate, le)

TRIAL = "arm_id case_id disposition checks resources full_cost_attested leakage review_blinding reviewer_count reviewer_disagreement adjudication_sha256 output_sha256 formal_receipt_sha256 originality_receipt_sha256".split()


def validate_trial(d, case):
    exact(d, TRIAL, "trial")
    choice(d["disposition"], {"answer", "abstain", "escalate", "no_delivery"}, "disposition")
    exact(d["checks"], CHECKS, "checks")
    for k, v in d["checks"].items():
        choice(v, STATES, k)
        require(k not in case["required_checks"] or v != "not_applicable",
                "required check cannot be N/A")
    exact(d["resources"], BUDGET, "resources")
    for k, v in d["resources"].items():
        integer(v, k, nullable=True)
    boolean(d["full_cost_attested"], "full cost", nullable=True)
    choice(d["leakage"], {"clear", "suspected", "confirmed", "unknown", "not_applicable"}, "leakage")
    require(case["novelty"] == "seen" or d["leakage"] != "not_applicable",
            "holdout integrity cannot be N/A")
    choice(d["review_blinding"], {"blinded", "unblinded", "unknown"}, "blinding")
    integer(d["reviewer_count"], "reviewer_count", nullable=True)
    boolean(d["reviewer_disagreement"], "reviewer_disagreement", nullable=True)
    if d["reviewer_disagreement"] is not None:
        require(d["reviewer_count"] is not None and d["reviewer_count"] >= 2,
                "agreement needs at least two reviewers")
    for k in ("adjudication_sha256", "output_sha256", "formal_receipt_sha256", "originality_receipt_sha256"):
        sha(d[k], k, nullable=True)
    if d["disposition"] == "no_delivery":
        require(d["output_sha256"] is None, "no delivery cannot have an output receipt")
        require(not any(v == "passed" for v in d["checks"].values()),
                "no delivery cannot pass a quality check")
    if d["checks"]["formal_validity"] == "passed":
        sha(d["formal_receipt_sha256"], "formal validity receipt")
    if d["checks"]["scoped_originality"] == "passed":
        sha(d["originality_receipt_sha256"], "frozen-corpus originality receipt")


def validate_flow(d, frame):
    exact(d, FLOW_COUNTS + ["stage_capacities"], "flow")
    for k in FLOW_COUNTS:
        integer(d[k], k, nullable=True)
    exact(d["stage_capacities"], STAGES, "stage capacities")
    for k, v in d["stage_capacities"].items():
        integer(v, k, nullable=True)
    for a, b in (("valid_candidates", "raw_candidates"),
                 ("deduplicated_valid", "valid_candidates"),
                 ("new_demand_units", "deduplicated_valid"),
                 ("completed", "qualified_capacity")):
        le(d[a], d[b], a)
    opening, arrivals, done, cancel, closing, capacity = (d[k] for k in
        ("opening_backlog", "new_demand_units", "completed", "cancelled", "closing_backlog", "qualified_capacity"))
    if frame["queue_model"] == "work_conserving_homogeneous":
        require(cancel in (None, 0), "homogeneous queue requires no cancellations")
    if opening is not None and arrivals is not None:
        available = opening + arrivals
        partial = sum(x for x in (done, cancel, closing) if x is not None)
        require(partial <= available, "queue mass exceeds available work")
        if None not in (done, cancel, closing):
            require(closing == available-done-cancel, "queue conservation")
        if frame["queue_model"] == "work_conserving_homogeneous":
            if None not in (done, capacity):
                require(done == min(available, capacity), "work-conserving model contradiction")
            if None not in (closing, capacity):
                require(closing == max(0, available-capacity), "work-conserving backlog contradiction")
    if frame["serial_model"] == "serial_same_unit":
        # Every known stage is a necessary upper bound under this specific model.
        for x in d["stage_capacities"].values():
            le(d["terminal_outputs"], x, "conditional serial capacity")


def validate_population(d, frame, data_class):
    exact(d, POP_COUNTS + POP_SUMS, "population")
    for k, v in d.items():
        integer(v, k, nullable=True)
    keys = ("baseline_n", "retained_n", "exited_n", "lost_n", "entrant_n")
    n, r, e, l, b = (d[k] for k in keys)
    minimum = frame["min_public_cell"]
    if data_class == "observational":
        for k in (*keys, "role_transition_n", "baseline_formal_employed", "followup_formal_employed"):
            x = d[k]
            require(x is None or x == 0 or x >= minimum,
                    "small observed population cells must be suppressed")
    if n is not None:
        known = sum(x for x in (r,e,l) if x is not None)
        require(known <= n, "population partition exceeds baseline")
        if None not in (r,e,l):
            require(known == n, "population conservation")
        if data_class == "observational" and (r,e,l).count(None) == 1:
            require(n-known == 0 or n-known >= minimum, "small cell inferable from partition")
    le(d["role_transition_n"], r, "role transitions among retained")
    le(d["baseline_formal_employed"], n, "baseline formal employment")
    if None not in (r,b,l):
        le(d["followup_formal_employed"], r+b+l, "followup formal employment")
    if data_class == "observational":
        for total, subset in ((n,d["baseline_formal_employed"]), (r,d["role_transition_n"])):
            if total is not None and subset is not None:
                require(total-subset == 0 or total-subset >= minimum, "small complement must be suppressed")
        if l == 0 and None not in (r,b,d["followup_formal_employed"]):
            comp = r+b-d["followup_formal_employed"]
            require(comp == 0 or comp >= minimum, "small followup employment complement")
    maxscore = frame["score_max"]
    for key, count in zip(POP_SUMS, (n,r,r,e,l,b)):
        value = d[key]
        if value is not None:
            require(count is not None and value <= count*maxscore, f"{key}: missing or invalid denominator")
    parts = [d[k] for k in ("retained_baseline_sum","exit_baseline_sum","lost_baseline_sum")]
    if d["baseline_sum"] is not None:
        require(sum(x for x in parts if x is not None) <= d["baseline_sum"],
                "score mass exceeds baseline")
        if None not in parts:
            require(sum(parts) == d["baseline_sum"], "baseline score conservation")


def receipt(e):
    if e is None:
        return None
    return {k:e[k] for k in ("event_id","evidence_tier","source_url","artifact_sha256","assessor_ref")}


def measured(e):
    return e is not None and e["evidence_tier"] in COMPUTABLE


def assess_trial(case, arm, e):
    eligible = measured(e)
    d = e["data"] if eligible else {}
    checks = d.get("checks", {k:"unknown" for k in CHECKS})
    resources = d.get("resources", {k:None for k in BUDGET})
    budget = gate([test_gate(resources[k], lambda x,k=k:x<=arm["budget"][k]) for k in BUDGET]
                  + ["passed" if d.get("full_cost_attested") is True else "unknown"])
    leak = d.get("leakage")
    if leak == "confirmed":
        integrity = "failed"
    elif leak == "suspected":
        integrity = "unknown"
    elif case["novelty"] == "seen":
        integrity = "passed"
    else:
        integrity = "passed" if leak == "clear" else "unknown"
    blinded = ("passed" if not case["blind_review_required"] else
               {"blinded":"passed","unblinded":"failed"}.get(d.get("review_blinding"),"unknown"))
    review = test_gate(d.get("reviewer_count"), lambda x:x>=1)
    if d.get("reviewer_count") is not None and d["reviewer_count"]>=2:
        if d.get("reviewer_disagreement") is None or (d["reviewer_disagreement"] and d.get("adjudication_sha256") is None):
            review = gate([review,"unknown"])
    if eligible and e["evidence_tier"] in {"independent_repeated","longitudinal_independent"}:
        review = gate([review,test_gate(d.get("reviewer_count"),lambda x:x>=2)])
    quality = gate([checks[k] for k in case["required_checks"]])
    # Optional safety/authorization may be N/A, never explicit failures.
    safety = gate([checks[k] if k in case["required_checks"] else
                   ("failed" if checks[k]=="failed" else "passed") for k in ("safety","authorization")])
    disposition = d.get("disposition")
    decision = test_gate(disposition, lambda x:x==case["expected_disposition"])
    artifact = "passed" if d.get("output_sha256") else "unknown"
    common = gate([quality,budget,integrity,blinded,review,safety,decision,artifact])
    if not eligible:
        quality=budget=integrity=blinded=review=safety=decision=artifact=common="unknown"
    # Raw assertions may still be visible when evidence integrity is unresolved;
    # do not promote them to accepted per-coordinate measurements.
    admissible = eligible and gate([integrity,blinded,review,artifact])=="passed"
    checked = {k:(v if admissible or v=="not_applicable" else "unknown") for k,v in checks.items()}
    return {"case_id":case["case_id"],"domain_id":case["domain_id"],"arm_id":arm["arm_id"],
            "actor":arm["actor"],"task_kind":case["task_kind"],"novelty":case["novelty"],
            "expected_disposition":case["expected_disposition"],"disposition":disposition,
            "recorded_quality_checks":checks,"admissible_quality_checks":checked,
            "required_quality_state":quality,"budget_state":budget,"holdout_integrity_state":integrity,
            "blinding_state":blinded,"review_state":review,"safety_authorization_state":safety,
            "decision_state":decision,"artifact_state":artifact,
            "qualified_answer":common if case["expected_disposition"]=="answer" else "not_applicable",
            "qualified_abstain_or_escalate":common if case["expected_disposition"]!="answer" else "not_applicable",
            "resources":resources,"full_cost_attested":d.get("full_cost_attested"),"receipt":receipt(e)}


def summarize_states(states):
    c=Counter(states)
    n=c["passed"]+c["failed"]+c["unknown"]
    known=c["passed"]+c["failed"]
    return {"passed":c["passed"],"failed":c["failed"],"unknown":c["unknown"],"not_applicable":c["not_applicable"],
            "frame_n":n,"known_share":pack(ratio(c["passed"],known)),"coverage":pack(ratio(known,n)),
            "lower_bound":pack(ratio(c["passed"],n)),"upper_bound":pack(ratio(c["passed"]+c["unknown"],n))}


def arm_summary(rows):
    answer=[r for r in rows if r["expected_disposition"]=="answer"]
    accepted=sum(r["qualified_answer"]=="passed" for r in answer)
    cost=None
    if answer and all(r["qualified_answer"] in {"passed","failed"} and r["full_cost_attested"] is True
                      and r["resources"]["cost_minor"] is not None for r in answer):
        cost=sum(r["resources"]["cost_minor"] for r in answer)
    return {"answer_quality":summarize_states([r["qualified_answer"] for r in rows]),
            "appropriate_non_answer":summarize_states([r["qualified_abstain_or_escalate"] for r in rows]),
            "quality_coordinates":{k:summarize_states([r["admissible_quality_checks"][k] for r in rows]) for k in CHECKS},
            "complete_answer_frame_cost_minor":cost,"cost_per_qualified_answer_minor":pack(ratio(cost,accepted))}


def paired(rows, arms):
    by={(r["case_id"],r["arm_id"]):r for r in rows}
    cases=sorted({r["case_id"] for r in rows})
    out=[]
    for a,b in combinations(sorted(arms),2):
        for field in ("qualified_answer","qualified_abstain_or_escalate"):
            c=Counter()
            for cid in cases:
                x,y=by[cid,a][field],by[cid,b][field]
                label=("not_applicable" if x==y=="not_applicable" else
                       "unknown_pairs" if "unknown" in (x,y) else
                       "both_pass" if x==y=="passed" else "both_fail" if x==y=="failed" else
                       "only_a_pass" if x=="passed" else "only_b_pass")
                c[label]+=1
            out.append({"arm_a":a,"arm_b":b,"outcome":field,**{k:c[k] for k in
                       ("both_pass","both_fail","only_a_pass","only_b_pass","unknown_pairs","not_applicable")}})
    return out


def flow_summary(f,e):
    d=e["data"] if measured(e) else {**dict.fromkeys(FLOW_COUNTS),"stage_capacities":dict.fromkeys(STAGES)}
    caps=d["stage_capacities"]
    serial=min(caps.values()) if f["serial_model"]=="serial_same_unit" and None not in caps.values() else None
    opening,arrivals,done,cancelled,closing,capacity=(d[k] for k in
        ("opening_backlog","new_demand_units","completed","cancelled","closing_backlog","qualified_capacity"))
    ideal=None
    if f["queue_model"]=="work_conserving_homogeneous" and None not in (opening,arrivals,capacity,cancelled) and cancelled==0:
        ideal=max(0,opening+arrivals-capacity)
    return {"frame_id":f["frame_id"],"domain_id":f["domain_id"],"receipt":receipt(e),"counts":d,
            "valid_per_raw":pack(ratio(d["valid_candidates"],d["raw_candidates"])),
            "deduplicated_per_valid":pack(ratio(d["deduplicated_valid"],d["valid_candidates"])),
            "demand_per_deduplicated":pack(ratio(arrivals,d["deduplicated_valid"])),
            "observed_backlog_change":None if None in (opening,closing) else closing-opening,
            "queue_balance_checked":None not in (opening,arrivals,done,cancelled,closing),
            "conditional_ideal_closing":ideal,"conditional_serial_capacity":serial,
            "conditional_bottleneck_stages":None if serial is None else [s for s in STAGES if caps[s]==serial]}


def population_summary(f,e):
    d=e["data"] if measured(e) else dict.fromkeys(POP_COUNTS+POP_SUMS)
    n,r,ex,l,b=(d[k] for k in ("baseline_n","retained_n","exited_n","lost_n","entrant_n"))
    base=ratio(d["baseline_sum"],n)
    retained=ratio(d["retained_baseline_sum"],r)
    known_followup=None if None in (r,b) else r+b
    upper_followup=None if None in (known_followup,l) else known_followup+l
    lower_retention=ratio(r,n)
    upper_retention=ratio(r+l,n) if None not in (r,l) else None
    decomp=None
    if l==0 and None not in (n,r,ex,b) and n>0 and r+b>0:
        values=list(zip((d[k] for k in POP_SUMS),(n,r,r,ex,l,b)))
        norm=[0 if count==0 and val is None else val for val,count in values]
        if None not in norm:
            sb,sr0,sr1,se,sl,sb_new=norm
            base=Fraction(sb,n)
            mu1=Fraction(sr1+sb_new,r+b)
            exit_term=(ex*base-se)/(r+b)
            entry_term=(sb_new-b*base)/(r+b)
            individual_term=Fraction(sr1-sr0,r+b)
            require(mu1-base==exit_term+entry_term+individual_term,"population decomposition identity")
            decomp={"baseline_mean":pack(base),"followup_mean":pack(mu1),"mean_change":pack(mu1-base),
                    "exit_selection":pack(exit_term),"entry_selection":pack(entry_term),"retained_individual_change":pack(individual_term)}
    return {"frame_id":f["frame_id"],"domain_id":f["domain_id"],"receipt":receipt(e),"counts_and_score_sums":d,
            "score_max":f["score_max"],"known_followup_active":known_followup,"upper_followup_active":upper_followup,
            "retention_lower":pack(lower_retention),"retention_upper":pack(upper_retention),
            "baseline_mean":pack(base),"confirmed_retained_baseline_mean":pack(retained),
            "confirmed_retained_baseline_mean_difference":pack(retained-base if retained is not None and base is not None else None),
            "complete_case_population_decomposition":decomp,"motivation_inferred_from_exit":False,"causal_effect_certified":False}
