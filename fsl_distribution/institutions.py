"""CTI-M transitional institutions: conditional, non-executing audit. Apache-2.0."""
from fractions import Fraction
from .common import (RSDOError, require, exact, integer, signed_integer, boolean, sha, bps,
                     numeric_fields, bounded_list, assumption, index_rows, choice, pack, ratio, le)
from fsl_epoch.absorption import matching as grouped_matching

FIELDS=["delivery","funding","tax_benefits","service_access","backup_routes","hysteresis"]


def public_cells(values,dc,minimum):
    if dc=="observational":
        require(all(v is None or v==0 or v>=minimum for v in values),"small aggregate count or complement must be suppressed")


def delivery(p,dc,mincell):
    if p is None:return None
    keys=["timely","late","unmet","unknown"]
    exact(p,["cohort_n","deadline_contract_sha256",*keys],"protection delivery")
    sha(p["deadline_contract_sha256"],"eligibility and delivery deadline")
    n=p["cohort_n"]
    integer(n,"eligible cohort",minimum=1)
    numeric_fields(p,keys)
    values=[p[k] for k in keys]
    known=sum(v for v in values if v is not None)
    require(known<=n and (None in values or known==n),"eligible cohort partition")
    public_cells([n,*values,n-known if values.count(None)==1 else None],dc,mincell)
    a,b,c,u=values
    lo=0 if a is None else a
    hi=n-sum(v for v in (b,c) if v is not None)
    if a is not None and u is not None:hi=min(hi,a+u)
    # If the timely count is recorded, uncertain endpoint labels can still add successes.
    return {"eligible_cohort":n,"counts":{k:p[k] for k in keys},
            "timely_protection_lower":pack(ratio(lo,n)),"timely_protection_upper":pack(ratio(hi,n)),
            "received_not_merely_approved":True,"bounds_not_confidence_intervals":True}


def funding(p):
    if p is None:return None
    exact(p,["assumed","cash_ledger_sha256","opening_cash_minor","reserve_minor","fixed_obligations_minor","scenarios"],"funding")
    enabled=assumption(p);sha(p["cash_ledger_sha256"],"funding cash contract")
    numeric_fields(p,["opening_cash_minor","reserve_minor"])
    obligations=p["fixed_obligations_minor"]
    bounded_list(obligations,"fixed obligations",1,120)
    for v in obligations:integer(v,"due benefit",nullable=True)
    scenarios=index_rows(p["scenarios"],["scenario_id","net_receipts_minor","priority_due_minor"],"scenario_id","scenario")
    require(0<len(scenarios)<=64,"funding scenarios 1..64")
    horizon=len(obligations)
    rows=[]
    needed=[]
    for sid,s in sorted(scenarios.items()):
        r,c=s["net_receipts_minor"],s["priority_due_minor"]
        require(isinstance(r,list) and isinstance(c,list) and len(r)==len(c)==horizon,"fixed common horizon")
        for v in r:signed_integer(v,"realized net receipts",nullable=True)
        for v in c:integer(v,"other priority obligations",nullable=True)
        complete=all(None not in x for x in (r,c,obligations))
        start,minimum=p["opening_cash_minor"],p["reserve_minor"]
        if not enabled or not complete or minimum is None:
            required=None;path=None;passes=None
        else:
            deficit=0;max_deficit=0;path=[]
            for f,cost,due in zip(r,c,obligations):
                deficit+=cost+due-f
                max_deficit=max(max_deficit,deficit)
                path.append(None if start is None else start-deficit)
            required=minimum+max_deficit
            passes=None if start is None else start>=required
        needed.append(required)
        rows.append({"scenario_id":sid,"minimum_opening_cash_minor":required,
                     "period_end_cash_if_all_due_paid_minor":path,"reserve_and_due_payment_feasible":passes})
    required=max(needed) if None not in needed else None
    return {"conditional_result":None if not enabled else {"scenario_results":rows,
             "robust_minimum_opening_cash_minor":required,
             "extra_initial_cash_needed_minor":max(0,required-p["opening_cash_minor"]) if None not in (required,p["opening_cash_minor"]) else None,
             "all_registered_scenarios_pass":None if None in (required,p["opening_cash_minor"]) else p["opening_cash_minor"]>=required,
             "outside_registered_scenarios_guaranteed":False,"fiscal_certification":False}}


def tax_benefits(p):
    if p is None:return None
    exact(p,["assumed","tax_bps","programs","gross_income_grid_minor"],"joint tax benefits")
    enabled=assumption(p);bps(p["tax_bps"],"tax rate")
    ps=index_rows(p["programs"],["program_id","kind","max_benefit_minor","threshold_minor","withdrawal_bps"],"program_id","benefit")
    require(len(ps)<=64,"program count")
    for x in ps.values():
        choice(x["kind"],{"continuous","cliff"},"benefit kind")
        numeric_fields(x,["max_benefit_minor","threshold_minor","withdrawal_bps"])
        if x["kind"]=="cliff":require(x["withdrawal_bps"] is None,"cliff has no continuous withdrawal rate")
    grid=p["gross_income_grid_minor"]
    bounded_list(grid,"gross income grid",1,512)
    for y in grid:integer(y,"gross income")
    require(all(a<b for a,b in zip(grid,grid[1:])),"strict increasing income grid")
    complete=p["tax_bps"] is not None and all(
        x["max_benefit_minor"] is not None and x["threshold_minor"] is not None
        and (x["kind"]=="cliff" or x["withdrawal_bps"] is not None) for x in ps.values())
    if not enabled or not complete:return {"conditional_result":None}
    tax=Fraction(p["tax_bps"],10000)
    rows=[];prev=None;declines=[]
    for y in grid:
        benefits={}
        for k,x in ps.items():
            b,t=x["max_benefit_minor"],x["threshold_minor"]
            val=(Fraction(b if y<t else 0) if x["kind"]=="cliff" else
                 max(Fraction(0),b-Fraction(x["withdrawal_bps"],10000)*max(0,y-t)))
            benefits[k]=val
        net=(1-tax)*y+sum(benefits.values())
        if prev is not None and net<prev[1]:
            declines.append({"from_gross_minor":prev[0],"to_gross_minor":y,"net_change_minor":pack(net-prev[1])})
        rows.append({"gross_income_minor":y,"tax_minor":pack(tax*y),
                     "benefits_minor":{k:pack(v) for k,v in benefits.items()},"net_cash_minor":pack(net)})
        prev=(y,net)
    all_continuous=all(x["kind"]=="continuous" for x in ps.values())
    slope=1-tax-sum((Fraction(x["withdrawal_bps"],10000) for x in ps.values()),Fraction(0)) if all_continuous else None
    return {"conditional_result":{"income_grid":rows,"sampled_net_cash_declines":declines,
            "joint_continuous_lower_slope":pack(slope),
            "sufficient_global_nondecreasing_condition":slope>=0 if slope is not None else None,
            "absence_of_sampled_declines_is_global_proof":False,"not_policy_or_personal_eligibility_advice":True}}


def service_access(p,dc,mincell):
    if p is None:return None
    exact(p,["assumed","service_contract_sha256","grouped_compatibility"],"service access")
    enabled=assumption(p);sha(p["service_contract_sha256"],"one-unit same-quality voluntary service")
    try:
        m=grouped_matching(p["grouped_compatibility"],dc,mincell)
    except ValueError as exc:
        raise RSDOError(f"service compatibility: {exc}") from exc
    return {"conditional_result":None if not enabled or m is None else {
            "eligible_people":m["population"],"qualified_service_units":m["total_slots"],
            "certain_edge_count":m["certain_edge_count"],"possible_edge_count":m["possible_edge_count"],
            "serviceable_lower":m["conditional_matched_lower"],"serviceable_upper":m["conditional_matched_upper"],
            "unserved_lower":m["conditional_unmatched_lower"],"unserved_upper":m["conditional_unmatched_upper"],
            "not_actual_delivery_or_allocation_decision":True}}


def backup_routes(p,dc,mincell):
    if p is None:return None
    exact(p,["assumed","cohort_n","route_a","route_b","shared_gate","joint_success"],"backup paths")
    enabled=assumption(p)
    n=p["cohort_n"];integer(n,"cohort",minimum=1)
    for k in ("route_a","route_b","shared_gate","joint_success"):
        integer(p[k],k,nullable=True);le(p[k],n,k)
    a,b,g,j=(p[k] for k in ("route_a","route_b","shared_gate","joint_success"))
    for v in (a,b,j):le(v,g,"shared gate")
    le(j,a,"intersection a");le(j,b,"intersection b")
    cap=n if g is None else g
    lo=max([0]+[v for v in (a,b,j) if v is not None])
    hi=cap if None in (a,b) else min(cap,a+b)
    if None not in (a,b,j):
        u=a+b-j
        require(lo<=u<=hi,"union inconsistent with shared gate")
        lo=hi=u
        public_cells([a-j,b-j,n-u],dc,mincell)
    elif j is not None:
        # Known overlap and one unknown marginal still constrain the union lower bound.
        known_margins=[v for v in (a,b) if v is not None]
        require(j<=cap,"overlap exceeds gate")
        if len(known_margins)==2:hi=min(hi,sum(known_margins)-j)
    require(lo<=hi,"inconsistent union bounds")
    public_cells([n,a,b,g,j,*[n-x for x in (a,b,g,j) if x is not None]],dc,mincell)
    return {"conditional_result":None if not enabled else {"union_lower":pack(ratio(lo,n)),
             "union_upper":pack(ratio(hi,n)),"shared_gate_upper":pack(ratio(cap,n)),
             "independence_assumed":False,"joint_capacity_test_still_required":True}}


def hysteresis(p):
    if p is None:return None
    exact(p,["assumed","base_floor_protected","appeal_reference_sha256","low","high","error_bound",
             "initial_state","measured","true_values"],"optional support hysteresis")
    enabled=assumption(p);boolean(p["base_floor_protected"],"base floor protection")
    sha(p["appeal_reference_sha256"],"appeal and override reference",nullable=True)
    numeric_fields(p,["low","high","error_bound"])
    l,h,e=(p[k] for k in ("low","high","error_bound"))
    if None not in (l,h):require(h>l,"strict hysteresis thresholds")
    integer(p["initial_state"],"initial state");require(p["initial_state"] in (0,1),"binary initial state")
    z,x=p["measured"],p["true_values"]
    bounded_list(z,"measured values",1,512)
    require(isinstance(x,list) and len(x)==len(z),"matched truth and measurement window")
    for a,b in zip(z,x):
        integer(a,"measured",nullable=True);integer(b,"true pressure",nullable=True)
        if None not in (a,b,e):require(abs(a-b)<=e,"recorded measurement exceeds declared error bound")
    if not enabled or not p["base_floor_protected"] or p["appeal_reference_sha256"] is None or None in (l,h,e) or None in z:
        return {"conditional_result":None,"reason":"not eligible for optional-support model; no live action"}
    state=p["initial_state"];states=[];switches=0
    for v in z:
        after=1 if state==0 and v>=h else 0 if state==1 and v<=l else state
        switches+=after!=state;state=after;states.append(state)
    delta=h-l-2*e
    variation=sum(abs(a-b) for a,b in zip(x,x[1:])) if None not in x else None
    bound=max(0,switches-1)*delta if delta>0 else None
    if variation is not None and bound is not None:require(bound<=variation,"bounded-error variation inequality")
    return {"conditional_result":{"optional_support_states":states,"switch_count":switches,
            "positive_separation":delta if delta>0 else None,"true_pressure_total_variation":variation,
            "necessary_variation_for_switches":bound,"bound_checked":variation is not None and bound is not None,
            "base_floor_never_controlled":True,"automatic_policy_execution":False,"adequate_response_time_certified":False}}


def institutions(data,frame,dc):
    exact(data,FIELDS,"institutions")
    minimum=frame["min_public_cell"]
    return {"delivery":delivery(data["delivery"],dc,minimum),"funding":funding(data["funding"]),
            "tax_benefits":tax_benefits(data["tax_benefits"]),
            "service_access":service_access(data["service_access"],dc,minimum),
            "backup_routes":backup_routes(data["backup_routes"],dc,minimum),
            "hysteresis":hysteresis(data["hysteresis"]),
            "policy_certified":False,"legal_entitlement_certified":False,"civilizational_gain_certified":False}
