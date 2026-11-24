"""Registered reflexive handoff trials (ASTT-EX01, RTA-M). Apache-2.0."""
from collections import Counter, defaultdict
from .common import (require, exact, choice, ident, integer, boolean, sha, index_rows,
                     gate, test_gate, pack, ratio)

LEVELS={
    "faithful_replay":["source_fidelity","replay"],
    "independent_reconstruction":["source_fidelity","reconstruction","substantive_validity"],
    "heldout_application":["source_fidelity","application","substantive_validity"],
    "revision_refutation":["source_fidelity","defect_disposition","substantive_validity","regression","negative_results_logged"],
    "autonomous_generation":["problem_value","scoped_novelty","substantive_validity","negative_results_logged"]
}
CHECKS=["source_fidelity","replay","reconstruction","application","substantive_validity",
        "defect_disposition","regression","problem_value","scoped_novelty","negative_results_logged",
        "authorization","attribution","governance"]
COMMON_CHECKS={"authorization","attribution","governance"}
TARGETS={"author","ai_collaborator","theory","method","institution","knowledge_carrier"}
MODES={"original_supported","public_only","full_handoff","independent_team","autonomous_agenda"}
RESOURCES=["cost_minor","wall_seconds","human_core_minutes","compute_units"]
HUMAN=["author_core_steps","author_new_direction_steps","author_contacts","other_human_core_steps",
       "approval_steps","initial_intent_steps"]
ARM="arm_id configuration actor stack_sha256 input_manifest_sha256 tool_policy_sha256 rights_manifest_sha256 budget".split()
CASE="case_id target_type target_ref level contract_sha256 source_sha256 reference_corpus_sha256 holdout_commitment_sha256 expected_outcome required_checks blind_review_required weight".split()
DESIGN="comparison_mode compute_meter_sha256 arms cases".split()
TRIAL="arm_id case_id outcome checks resources full_cost_attested human goal_source leakage original_solver_access input_scope_compliance review_blinding reviewer_count reviewer_disagreement adjudication_sha256 output_sha256 verification_receipt_sha256 novelty_receipt_sha256".split()


def validate_design(d):
    exact(d,DESIGN,"trial design")
    choice(d["comparison_mode"],{"equal_budget","actual_cost"},"comparison")
    sha(d["compute_meter_sha256"],"common compute meter")
    arms=index_rows(d["arms"],ARM,"arm_id","arm")
    cases=index_rows(d["cases"],CASE,"case_id","case")
    require(2<=len(arms)<=16 and 0<len(cases)<=128,"trial frame limit")
    for a in arms.values():
        choice(a["configuration"],MODES,"configuration")
        choice(a["actor"],{"human_non_ai","ai_system","human_ai"},"actor")
        for k in ("stack_sha256","input_manifest_sha256","tool_policy_sha256","rights_manifest_sha256"):sha(a[k],k)
        exact(a["budget"],RESOURCES,"arm budget")
        for k,v in a["budget"].items():integer(v,k)
        require(a["budget"]["wall_seconds"]>0,"positive time budget")
    bases=[a["arm_id"] for a in arms.values() if a["configuration"]=="original_supported"]
    require(len(bases)==1,"exactly one original-supported comparison arm")
    if d["comparison_mode"]=="equal_budget":
        first=next(iter(arms.values()))["budget"]
        require(all(a["budget"]==first for a in arms.values()),"equal-budget caps must match")
    for c in cases.values():
        choice(c["target_type"],TARGETS,"target type")
        ident(c["target_ref"],"non-identifying target reference")
        choice(c["level"],LEVELS,"function level")
        for k in ("contract_sha256","source_sha256","reference_corpus_sha256"):sha(c[k],k)
        sha(c["holdout_commitment_sha256"],"sealed holdout reference",
            nullable=c["level"]=="faithful_replay")
        choice(c["expected_outcome"],{"qualified_result","sound_negative_result","appropriate_escalation"},"expected outcome")
        if c["level"]=="autonomous_generation":
            require(c["expected_outcome"]=="qualified_result","new agenda case must demand an accepted contribution")
        boolean(c["blind_review_required"],"blinding required")
        integer(c["weight"],"case weight",minimum=1)
        rs=c["required_checks"]
        require(isinstance(rs,list) and all(isinstance(x,str) and x in CHECKS for x in rs)
                and len(rs)==len(set(rs)),"required checks")
        require(set(LEVELS[c["level"]])|COMMON_CHECKS <= set(rs),"missing substantive or governance check")
    return arms,cases,bases[0]


def validate_trial(d,case):
    exact(d,TRIAL,"trial")
    choice(d["outcome"],{"qualified_result","sound_negative_result","appropriate_escalation","failed","no_delivery"},"outcome")
    exact(d["checks"],CHECKS,"checks")
    for k,v in d["checks"].items():
        choice(v,{"passed","failed","unknown","not_applicable"},k)
        require(k not in case["required_checks"] or v!="not_applicable","required check cannot be N/A")
    exact(d["resources"],RESOURCES,"resources")
    for k,v in d["resources"].items():integer(v,k,nullable=True)
    boolean(d["full_cost_attested"],"full cost",nullable=True)
    exact(d["human"],HUMAN,"human involvement")
    for k,v in d["human"].items():integer(v,k,nullable=True)
    choice(d["goal_source"],{"preregistered","agent_generated","author_new_direction","other_human_new_direction","unknown"},"goal source")
    choice(d["leakage"],{"clear","suspected","confirmed","unknown","not_applicable"},"leakage")
    require(case["level"]=="faithful_replay" or d["leakage"]!="not_applicable","non-replay leakage cannot be N/A")
    choice(d["original_solver_access"],{"isolated","accessed","unknown","not_applicable"},"original solver access")
    choice(d["input_scope_compliance"],{"passed","failed","unknown"},"input scope")
    choice(d["review_blinding"],{"blinded","unblinded","unknown"},"review blinding")
    integer(d["reviewer_count"],"reviewers",nullable=True)
    boolean(d["reviewer_disagreement"],"reviewer disagreement",nullable=True)
    if d["reviewer_disagreement"] is not None:
        require(d["reviewer_count"] is not None and d["reviewer_count"]>=2,"disagreement needs two reviewers")
    for k in ("adjudication_sha256","output_sha256","verification_receipt_sha256","novelty_receipt_sha256"):sha(d[k],k,nullable=True)
    if d["outcome"]=="no_delivery":
        require(d["output_sha256"] is None and not any(v=="passed" for v in d["checks"].values()),
                "no delivery cannot pass checks or carry output")
    if d["checks"]["scoped_novelty"]=="passed":sha(d["novelty_receipt_sha256"],"scoped novelty receipt")


def assess(case,arm,d,tier):
    if d is None:
        return {"case_id":case["case_id"],"arm_id":arm["arm_id"],"configuration":arm["configuration"],
                "actor":arm["actor"],"target_type":case["target_type"],"level":case["level"],
                "weight":case["weight"],"artifact_qualification":"unknown","author_independent":"unknown",
                "human_core_independent":"unknown","autonomous_generation":"unknown" if case["level"]=="autonomous_generation" else "not_applicable",
                "checks":None,"gates":None,"human":None,"resources":None,"full_cost_attested":None}
    check=d["checks"]
    quality=gate([check[k] for k in case["required_checks"]])
    budget=gate([test_gate(d["resources"][k],lambda x,k=k:x<=arm["budget"][k]) for k in RESOURCES]
                +["passed" if d["full_cost_attested"] is True else "unknown"])
    leak=d["leakage"]
    integrity="failed" if leak=="confirmed" else "unknown" if leak=="suspected" else (
        "passed" if leak=="clear" or case["level"]=="faithful_replay" and leak=="not_applicable" else "unknown")
    isolation="passed"
    if case["level"]=="independent_reconstruction":
        isolation={"isolated":"passed","accessed":"failed"}.get(d["original_solver_access"],"unknown")
    blind="passed" if not case["blind_review_required"] else {"blinded":"passed","unblinded":"failed"}.get(d["review_blinding"],"unknown")
    review=test_gate(d["reviewer_count"],lambda x:x>=2)
    if d["reviewer_count"] is not None and d["reviewer_count"]>=2 and (
        d["reviewer_disagreement"] is None or d["reviewer_disagreement"] and not d["adjudication_sha256"]):
        review=gate([review,"unknown"])
    evidence="passed" if d["output_sha256"] and d["verification_receipt_sha256"] else "unknown"
    outcome=test_gate(d["outcome"],lambda x:x==case["expected_outcome"])
    safety=gate([check[k] for k in ("authorization","governance")])
    core=gate([quality,budget,integrity,isolation,blind,review,evidence,outcome,d["input_scope_compliance"],safety])
    # The baseline is a comparison arm, not a candidate for author-cut coverage.
    author=gate([core]+[test_gate(d["human"][k],lambda x:x==0) for k in HUMAN[:3]]
                +["failed" if d["goal_source"]=="author_new_direction" else
                  "unknown" if d["goal_source"]=="unknown" else "passed"])
    if case["level"]=="autonomous_generation":
        author=gate([author,"passed" if d["goal_source"] in {"agent_generated","other_human_new_direction"} else
                     "unknown" if d["goal_source"]=="unknown" else "failed"])
    human=gate([author,test_gate(d["human"]["other_human_core_steps"],lambda x:x==0),
                test_gate(d["resources"]["human_core_minutes"],lambda x:x==0),
                "failed" if arm["actor"]!="ai_system" or d["goal_source"]=="other_human_new_direction" else "passed"])
    auto=(gate([human,"passed" if d["goal_source"]=="agent_generated" else
               "unknown" if d["goal_source"]=="unknown" else "failed"])
          if case["level"]=="autonomous_generation" else "not_applicable")
    return {"case_id":case["case_id"],"arm_id":arm["arm_id"],"configuration":arm["configuration"],
            "actor":arm["actor"],"target_type":case["target_type"],"level":case["level"],"weight":case["weight"],
            "artifact_qualification":core,"author_independent":author,"human_core_independent":human,
            "autonomous_generation":auto,"checks":check,
            "gates":{"quality":quality,"budget":budget,"integrity":integrity,"original_solver_isolation":isolation,
                     "blinding":blind,"review":review,"output_receipts":evidence,"expected_outcome":outcome,
                     "input_scope":d["input_scope_compliance"]},"human":d["human"],
            "resources":d["resources"],"full_cost_attested":d["full_cost_attested"]}


def bounds(states):
    # states are weighted (state, weight) entries under one fixed frame.
    c=Counter()
    for s,w in states:c[s]+=w
    known=c["passed"]+c["failed"];n=known+c["unknown"]
    return {"passed_weight":c["passed"],"failed_weight":c["failed"],"unknown_weight":c["unknown"],
            "frame_weight":n,"lower_bound":pack(ratio(c["passed"],n)),
            "upper_bound":pack(ratio(c["passed"]+c["unknown"],n)),
            "known_share":pack(ratio(c["passed"],known)),"coverage":pack(ratio(known,n))}


def exists_state(states):
    return "passed" if "passed" in states else "unknown" if "unknown" in states else "failed"


def trials(data,design,tier):
    arms,cases,base=validate_design(design)
    exact(data,["trials"],"trial snapshot")
    require(isinstance(data["trials"],list) and len(data["trials"])<=len(arms)*len(cases),"trial snapshot size")
    observed={}
    for d in data["trials"]:
        exact(d,TRIAL,"trial")
        choice(d["arm_id"],arms,"arm")
        choice(d["case_id"],cases,"case")
        k=(d["case_id"],d["arm_id"])
        require(k not in observed,"duplicate arm/case")
        validate_trial(d,cases[k[0]])
        observed[k]=d
    rows=[assess(c,arms[a],observed.get((cid,a)),tier)
          for cid,c in sorted(cases.items()) for a in sorted(arms)]
    indexed={(r["case_id"],r["arm_id"]):r for r in rows}
    coverage=[]
    candidates=sorted(set(arms)-{base})
    for cid,c in sorted(cases.items()):
        b=indexed[cid,base]["artifact_qualification"]
        xs=[indexed[cid,a] for a in candidates]
        alternatives=exists_state([x["author_independent"] for x in xs])
        hum=exists_state([x["human_core_independent"] for x in xs])
        coverage.append({"case_id":cid,"level":c["level"],"target_type":c["target_type"],"weight":c["weight"],
                         "baseline":b,"author_free_candidate_exists":alternatives,"human_core_free_candidate_exists":hum})
    # No single cross-level/target score. Candidate coverage is stratified.
    strata=[]
    for typ,level in sorted({(c["target_type"],c["level"]) for c in cases.values()}):
        rs=[r for r in coverage if (r["target_type"],r["level"])==(typ,level)]
        strata.append({"target_type":typ,"level":level,
                       "all_registered_cases_author_free":bounds([(r["author_free_candidate_exists"],r["weight"]) for r in rs]),
                       "baseline_qualified_cases_author_free":bounds([(r["author_free_candidate_exists"],r["weight"]) for r in rs if r["baseline"]=="passed"]),
                       "all_registered_cases_human_core_free":bounds([(r["human_core_free_candidate_exists"],r["weight"]) for r in rs])})
    summaries=[]
    for a in sorted(arms):
        for typ,level in sorted({(c["target_type"],c["level"]) for c in cases.values()}):
            rs=[r for r in rows if r["arm_id"]==a and (r["target_type"],r["level"])==(typ,level)]
            paid=None
            # All attempted cases including known failures are included; missing cost/outcome blocks.
            if all(r["artifact_qualification"]!="unknown" and r["full_cost_attested"] is True
                   and r["resources"] is not None and r["resources"]["cost_minor"] is not None for r in rs):
                paid=sum(r["resources"]["cost_minor"] for r in rs)
            accepted=sum(r["artifact_qualification"]=="passed" for r in rs)
            summaries.append({"arm_id":a,"target_type":typ,"level":level,
                **{k:bounds([(r[k],r["weight"]) for r in rs]) for k in
                   ("artifact_qualification","author_independent","human_core_independent","autonomous_generation")},
                "complete_frame_cost_minor":paid,"cost_per_qualified_artifact_minor":pack(ratio(paid,accepted))})
    return {"trial_rows":rows,"candidate_coverage":coverage,"strata":strata,"arm_strata":summaries,
            "baseline_arm":base,"registered_candidate_arms":candidates,"global_author_replacement_rate":None,
            "new_theory_or_autonomy_certified":False}
