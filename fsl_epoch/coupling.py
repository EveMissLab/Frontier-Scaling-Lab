"""Conditional cross-domain acceleration models (ASTT-08). Apache-2.0."""
from fractions import Fraction

from .common import (require, exact, choice, integer, boolean, sha, ident,
                     timestamp, ratio, pack, le)

FIELDS = ["source_domain","target_domain","pipeline","linear_feedback","bounded_stock","cycles"]


def pipeline(p):
    if p is None:
        return None
    exact(p, ["stages","serial_capacity_assumed","fixed_serial_cycle_assumed",
              "candidate_count","acceptance_chain"], "pipeline")
    boolean(p["serial_capacity_assumed"], "serial capacity model")
    boolean(p["fixed_serial_cycle_assumed"], "serial cycle model")
    ss=p["stages"]
    require(isinstance(ss,list) and 0<len(ss)<=64,"pipeline stages 1..64")
    names=set()
    for s in ss:
        exact(s,["stage_id","capacity","baseline_duration","candidate_duration"],"stage")
        ident(s["stage_id"],"stage id")
        require(s["stage_id"] not in names,"duplicate stage")
        names.add(s["stage_id"])
        for k in ("capacity","baseline_duration","candidate_duration"):
            integer(s[k],k,nullable=True)
    n=p["candidate_count"]
    integer(n,"candidate_count",nullable=True)
    chain=p["acceptance_chain"]
    require(isinstance(chain,list) and len(chain)==len(ss),"one nested acceptance count per stage")
    prev=n
    for v in chain:
        integer(v,"acceptance count",nullable=True)
        le(v,prev,"nested common-cohort acceptance")
        if v is not None:
            prev=v
    caps=[s["capacity"] for s in ss]
    base=[s["baseline_duration"] for s in ss]
    after=[s["candidate_duration"] for s in ss]
    m=min(caps) if p["serial_capacity_assumed"] and None not in caps else None
    b=sum(base) if p["fixed_serial_cycle_assumed"] and None not in base else None
    a=sum(after) if p["fixed_serial_cycle_assumed"] and None not in after else None
    # A zero duration denominator is not a measured infinite speedup.
    if a is not None and b is not None and a>0:
        speed=pack(ratio(b,a))
    else:
        speed=None
    conditional=[]
    prev=n
    for v in chain:
        conditional.append(pack(ratio(v,prev)))
        prev=v
    return {"stages":ss,"candidate_count":n,"nested_acceptance_counts":chain,
            "conditional_acceptance_rates":conditional,
            "joint_acceptance_per_candidate":pack(ratio(chain[-1],n)),
            "conditional_serial_capacity":m,
            "conditional_bottlenecks":None if m is None else [s["stage_id"] for s in ss if s["capacity"]==m],
            "conditional_baseline_serial_duration":b,"conditional_candidate_serial_duration":a,
            "conditional_serial_speedup":speed,
            "independent_stage_success_assumed":False}


def linear(p):
    if p is None:
        return None
    exact(p,["a_bps","b_bps","c_bps","d_bps","normalization_sha256",
             "fixed_no_external_input_or_delay"],"linear model")
    sha(p["normalization_sha256"],"domain normalization")
    boolean(p["fixed_no_external_input_or_delay"],"linear assumptions")
    for k in ("a_bps","b_bps","c_bps","d_bps"):
        integer(p[k],k,nullable=True)
    for k in ("a_bps","d_bps"):
        if p[k] is not None:
            require(p[k]<10000,"self retention must be < 1 in ASTT-08 T4")
    vals=[p[k] for k in ("a_bps","b_bps","c_bps","d_bps")]
    gap=None
    regime=None
    if p["fixed_no_external_input_or_delay"] and None not in vals:
        a,b,c,d=(Fraction(v,10000) for v in vals)
        gap=b*c-(1-a)*(1-d)
        regime="supercritical" if gap>0 else "critical" if gap==0 else "subcritical"
    return {"parameters":p,"conditional_regime":regime,"exact_threshold_gap":pack(gap),
            "direction_convergence_conditions":None if regime is None else (b>0 and c>0 and a+d>0),
            "strong_RSI_certified":False}


def bounded(p):
    if p is None:
        return None
    exact(p,["initial","delta_bps","gamma_bps","capacity","periods","fixed_no_external_input"],"bounded stock")
    for k in ("initial","delta_bps","gamma_bps","capacity"):
        integer(p[k],k,nullable=True)
    integer(p["periods"],"periods")
    require(p["periods"]<=60,"bounded-stock replay limit 60 periods")
    boolean(p["fixed_no_external_input"],"fixed stock assumptions")
    if p["delta_bps"] is not None:
        require(0<p["delta_bps"]<=10000,"depreciation in (0,1]")
    if p["capacity"] is not None:
        require(p["capacity"]>0,"capacity must be positive")
    x,delta,gamma,cap=(p[k] for k in ("initial","delta_bps","gamma_bps","capacity"))
    if not p["fixed_no_external_input"] or None in (x,delta,gamma,cap):
        return {"parameters":p,"conditional_path":None,"positive_equilibrium":None,"limit_from_initial":None}
    delta,gamma=Fraction(delta,10000),Fraction(gamma,10000)
    x=Fraction(x)
    initial=x
    path=[pack(x)]
    for _ in range(p["periods"]):
        x=(1-delta)*x+min(gamma*x,cap)
        path.append(pack(x))
    positive=Fraction(cap)/delta if gamma>delta else None
    if initial==0 or gamma<delta:
        limit=Fraction(0)
    elif gamma==delta:
        # Equality has a continuum of fixed points from 0 through C/delta.
        limit=min(initial,Fraction(cap)/delta)
    else:
        limit=positive
    return {"parameters":p,"conditional_path":path,"positive_equilibrium":pack(positive),
            "limit_from_initial":pack(limit),"zero_is_absorbing":True,
            "regeneration_or_civilizational_gain_certified":False}


def cycle_summary(cs, window_start, window_end, data_class):
    require(isinstance(cs,list) and len(cs)<=128,"cycle records must be array <=128")
    ids=set()
    end_before=window_start
    previous=None
    links=[]
    for c in cs:
        exact(c,["cycle_id","started_at","ended_at","input_sha256","output_sha256",
                 "acceptance_receipt_sha256","actual_use_receipt_sha256",
                 "external_dependency_ledger_sha256","control_design_sha256",
                 "safety","authorization","qualified","transfer_class"],"cycle")
        ident(c["cycle_id"],"cycle")
        require(c["cycle_id"] not in ids,"duplicate cycle")
        ids.add(c["cycle_id"])
        start,end=timestamp(c["started_at"]),timestamp(c["ended_at"])
        require(window_start<=end_before<=start<end<=window_end,"ordered nonoverlapping cycles within frame")
        end_before=end
        for k in ("input_sha256","output_sha256","acceptance_receipt_sha256",
                  "actual_use_receipt_sha256","external_dependency_ledger_sha256","control_design_sha256"):
            sha(c[k],k,nullable=True)
        choice(c["safety"],{"passed","failed","unknown"},"cycle safety")
        choice(c["authorization"],{"passed","failed","unknown"},"cycle authorization")
        choice(c["qualified"],{"passed","failed","unknown"},"cycle qualification")
        choice(c["transfer_class"],{"synthetic","planned","simulated","recorded_actual"},"cycle transfer class")
        require((data_class=="synthetic")==(c["transfer_class"]=="synthetic"),"cycle classification mismatch")
        if c["qualified"]=="passed":
            sha(c["output_sha256"],"qualified output")
            sha(c["acceptance_receipt_sha256"],"acceptance")
        if c["transfer_class"]=="recorded_actual" and c["actual_use_receipt_sha256"] is not None:
            sha(c["input_sha256"],"actual use input")
        if previous is not None:
            match=(previous["output_sha256"] is not None and
                   previous["output_sha256"]==c["input_sha256"])
            gates=all(x["qualified"]==x["safety"]==x["authorization"]=="passed"
                      for x in (previous,c))
            actual=(previous["transfer_class"]==c["transfer_class"]=="recorded_actual"
                    and c["actual_use_receipt_sha256"] is not None)
            deps=all(x["external_dependency_ledger_sha256"] is not None for x in (previous,c))
            controls=all(x["control_design_sha256"] is not None for x in (previous,c))
            links.append({"from":previous["cycle_id"],"to":c["cycle_id"],
                          "artifact_hash_matches":match,"all_recorded_gates_pass":gates,
                          "actual_use_receipt_assertion":bool(actual),
                          "external_dependency_ledger_refs_present":deps,
                          "control_design_refs_present":controls,
                          "candidate_recorded_link":bool(match and gates and actual and deps),
                          "causal_effect_certified":False})
        previous=c
    return {"records":cs,"consecutive_links":links,
            "independent_cycle_verification":False,
            "attribution_certified":False,"systemic_singularity_certified":False}


def coupling(data,frame,window_start,window_end,data_class):
    exact(data,FIELDS,"coupling")
    choice(data["source_domain"],frame["domain_ids"],"source domain")
    choice(data["target_domain"],frame["domain_ids"],"target domain")
    require(data["source_domain"]!=data["target_domain"],"two distinct domains required")
    return {"source_domain":data["source_domain"],"target_domain":data["target_domain"],
            "pipeline":pipeline(data["pipeline"]),
            "linear_feedback_model":linear(data["linear_feedback"]),
            "bounded_stock_model":bounded(data["bounded_stock"]),
            "cycle_evidence":cycle_summary(data["cycles"],window_start,window_end,data_class),
            "conditional_models_not_calibrated":True,
            "causal_acceleration_certified":False,"strong_RSI_certified":False,
            "Sigma_sys_certified":False,"Sigma_civ_certified":False}
