"""IPD-M purchasing power, demand, cash rights and physical limits. Apache-2.0."""
from fractions import Fraction
from .common import (require, exact, choice, integer, signed_integer, sha, bps,
                     numeric_fields, bounded_list, assumption, index_rows, pack, ratio)

FIELDS=["fixed_basket","income_routing","market_absorption","demand_feedback","cash_rights","physical_clearing"]


def fixed_basket(p):
    if p is None:return None
    exact(p,["assumed","quality_basket_sha256","income_before_minor","income_after_minor","items"],"fixed basket")
    enabled=assumption(p)
    sha(p["quality_basket_sha256"],"fixed quality basket")
    numeric_fields(p,["income_before_minor","income_after_minor"])
    items=index_rows(p["items"],["item_id","quantity","price_before_minor","price_after_minor"],"item_id","item")
    require(0<len(items)<=128,"basket items 1..128")
    for e in items.values():
        numeric_fields(e,["quantity","price_before_minor","price_after_minor"])
        for k in ("price_before_minor","price_after_minor"):
            if e[k] is not None:require(e[k]>0,"positive same-quality prices required; free/unavailable goods separate")
    y0,y1=p["income_before_minor"],p["income_after_minor"]
    if not enabled or None in (y0,y1) or any(None in (e["quantity"],e["price_before_minor"],e["price_after_minor"]) for e in items.values()):
        return {"conditional_result":None}
    e0=sum(e["quantity"]*e["price_before_minor"] for e in items.values())
    e1=sum(e["quantity"]*e["price_after_minor"] for e in items.values())
    require(e0>0 and e1>0,"basket must have positive cost")
    return {"conditional_result":{"basket_before_minor":e0,"basket_after_minor":e1,
        "affordable_baskets_before":pack(ratio(y0,e0)),"affordable_baskets_after":pack(ratio(y1,e1)),
        "relative_income_decline":pack(ratio(y0-y1,y0)),
        "relative_basket_price_decline":pack(ratio(e0-e1,e0)),
        "purchasing_power_not_declined":y1*e0>=y0*e1,
        "baseline_expenditure_shares":{k:pack(ratio(e["quantity"]*e["price_before_minor"],e0)) for k,e in items.items()},
        "nominal_cash_gap_before_minor":max(0,e0-y0),"nominal_cash_gap_after_minor":max(0,e1-y1),
        "not_complete_household_welfare":True}}


def income_routing(p):
    if p is None:return None
    exact(p,["assumed","expenditure_scope_sha256","groups"],"income routing")
    enabled=assumption(p);sha(p["expenditure_scope_sha256"],"marginal expenditure scope")
    gs=index_rows(p["groups"],["group_id","income_delta_minor","marginal_expenditure_bps"],"group_id","group")
    require(0<len(gs)<=128,"income groups 1..128")
    for g in gs.values():
        signed_integer(g["income_delta_minor"],"income change",nullable=True)
        bps(g["marginal_expenditure_bps"],"marginal propensity")
    if not enabled or any(None in (g["income_delta_minor"],g["marginal_expenditure_bps"]) for g in gs.values()):
        return {"conditional_result":None}
    changes={k:Fraction(g["income_delta_minor"]*g["marginal_expenditure_bps"],10000) for k,g in gs.items()}
    return {"conditional_result":{"total_income_change_minor":sum(g["income_delta_minor"] for g in gs.values()),
        "conditional_expenditure_change_minor":pack(sum(changes.values(),Fraction(0))),
        "group_expenditure_changes_minor":{k:pack(v) for k,v in changes.items()},
        "GDP_change":None,"marginal_propensity_causally_estimated":False}}


def market_absorption(p):
    if p is None:return None
    keys=["capacity","use_limit","budget_minor","price_before_minor","price_after_minor"]
    exact(p,["assumed",*keys],"market absorption")
    enabled=assumption(p);numeric_fields(p,keys)
    for k in keys[-2:]:
        if p[k] is not None:require(p[k]>0,"positive price required; free services separate")
    if not enabled or any(p[k] is None for k in keys):return {"conditional_result":None}
    k,a,b,pr0,pr1=(p[k] for k in keys)
    def row(pr):
        q=min(Fraction(k),Fraction(a),Fraction(b,pr))
        return {"quantity":pack(q),"revenue_minor":pack(pr*q),"capacity_utilization":pack(q/k if k else None)}
    return {"conditional_result":{"before":row(pr0),"after":row(pr1),"profit_minor":None}}


def demand_feedback(p):
    if p is None:return None
    keys=["capacity","autonomous_demand","feedback_bps","initial_output","periods"]
    exact(p,["assumed",*keys],"lagged demand")
    enabled=assumption(p);numeric_fields(p,keys[:-1])
    integer(p["periods"],"periods");require(p["periods"]<=60,"replay limit 60 periods")
    k,a,m,q=(p[x] for x in keys[:-1])
    if m is not None:require(m<10000,"contraction requires feedback in [0,1)")
    if None not in (q,k):require(q<=k,"initial output exceeds capacity")
    if not enabled or None in (k,a,m,q):return {"conditional_result":None}
    m=Fraction(m,10000);q=Fraction(q)
    equilibrium=min(Fraction(k),Fraction(a)/(1-m))
    err=abs(q-equilibrium);path=[pack(q)]
    for t in range(1,p["periods"]+1):
        q=min(Fraction(k),a+m*q)
        require(abs(q-equilibrium)<=m**t*err,"contraction check")
        path.append(pack(q))
    return {"conditional_result":{"output_path":path,"unique_fixed_point":pack(equilibrium),
        "capacity_utilization_at_fixed_point":pack(equilibrium/k if k else None),
        "not_macro_forecast":True}}


def cash_rights(p):
    if p is None:return None
    keys=["opening_available_minor","realized_net_receipts_minor","priority_due_minor",
          "committed_investment_minor","reserve_minor"]
    exact(p,["assumed","disjoint_cash_ledger_sha256","legally_distributable_attested",*keys,"groups"],"cash rights")
    enabled=assumption(p);sha(p["disjoint_cash_ledger_sha256"],"nonduplicated cash ledger")
    require(type(p["legally_distributable_attested"]) is bool,"lawful distribution attestation")
    numeric_fields(p,keys,signed=["realized_net_receipts_minor"])
    gs=index_rows(p["groups"],["group_id","cash_gap_minor","fixed_cash_share_bps"],"group_id","group")
    require(0<len(gs)<=128,"recipient groups 1..128")
    for g in gs.values():
        integer(g["cash_gap_minor"],"cash gap",nullable=True)
        bps(g["fixed_cash_share_bps"],"cash share")
    shares=[g["fixed_cash_share_bps"] for g in gs.values()]
    known=sum(s for s in shares if s is not None)
    require(known<=10000 and (None in shares or known==10000),"share conservation")
    cash=None
    if all(p[k] is not None for k in keys):
        o,r,d,i,minimum=(p[k] for k in keys)
        cash=o+r-d-i-minimum
    pool=max(0,cash) if cash is not None and p["legally_distributable_attested"] else None
    gaps=[g["cash_gap_minor"] for g in gs.values()]
    total=sum(gaps) if None not in gaps else None
    fixed=None;fixed_min=None;infeasible=None
    if enabled and pool is not None and total is not None and None not in shares:
        fixed={k:{"payout_minor":pack(Fraction(pool*g["fixed_cash_share_bps"],10000)),
                  "residual_gap_minor":pack(max(Fraction(0),g["cash_gap_minor"]-Fraction(pool*g["fixed_cash_share_bps"],10000)))}
               for k,g in gs.items()}
        infeasible=any(d>0 and w==0 for d,w in zip(gaps,shares))
        if not infeasible:fixed_min=max(Fraction(d*10000,w) for d,w in zip(gaps,shares) if w>0)
    return {"conditional_result":None if not enabled else {
        "signed_cash_after_obligations_and_reserve_minor":cash,
        "conditional_distributable_pool_minor":pool,"total_registered_cash_gap_minor":total,
        "arbitrary_targeting_minimum_residual_minor":None if None in (pool,total) else max(0,total-pool),
        "fixed_rights_full_pool_payout":fixed,
        "fixed_rights_any_finite_pool_infeasible":infeasible,
        "fixed_rights_minimum_pool_minor":pack(fixed_min),
        "legal_distribution_certified":False,"guaranteed_basic_service":False}}


def physical_clearing(p):
    if p is None:return None
    exact(p,["assumed","capacity","uniform_budget_scale_bps","groups"],"physical clearing")
    enabled=assumption(p)
    integer(p["capacity"],"fixed physical supply",nullable=True)
    integer(p["uniform_budget_scale_bps"],"uniform budget scale",nullable=True)
    for k in ("capacity","uniform_budget_scale_bps"):
        if p[k] is not None:require(p[k]>0,f"{k}: positive required")
    gs=index_rows(p["groups"],["group_id","budget_minor","physical_target"],"group_id","group")
    require(0<len(gs)<=128,"groups 1..128")
    for g in gs.values():numeric_fields(g,["budget_minor","physical_target"])
    q=p["capacity"];scale=p["uniform_budget_scale_bps"]
    if not enabled or q is None or any(g["budget_minor"] is None for g in gs.values()):
        return {"conditional_result":None}
    total=sum(g["budget_minor"] for g in gs.values())
    if total==0:return {"conditional_result":None}
    price=Fraction(total,q)
    amounts={k:Fraction(q*g["budget_minor"],total) for k,g in gs.items()}
    targets=[g["physical_target"] for g in gs.values()]
    complete=None not in targets
    feasible=sum(targets)<=q if complete else None
    shift=sum((max(Fraction(0),price*g["physical_target"]-g["budget_minor"]) for g in gs.values()),Fraction(0)) if feasible else None
    return {"conditional_result":{"conditional_unit_price_minor":pack(price),"physical_allocations":{k:pack(v) for k,v in amounts.items()},
        "scaled_unit_price_minor":pack(price*Fraction(scale,10000)) if scale is not None else None,
        "scaled_physical_allocations":{k:pack(v) for k,v in amounts.items()} if scale is not None else None,
        "all_targets_physically_feasible":feasible,"minimum_budget_transfer_at_fixed_total_minor":pack(shift),
        "not_inflation_forecast":True}}


def income(data,frame,dc):
    exact(data,FIELDS,"income")
    return {"fixed_basket":fixed_basket(data["fixed_basket"]),"income_routing":income_routing(data["income_routing"]),
            "market_absorption":market_absorption(data["market_absorption"]),"demand_feedback":demand_feedback(data["demand_feedback"]),
            "cash_rights":cash_rights(data["cash_rights"]),"physical_clearing":physical_clearing(data["physical_clearing"]),
            "causal_economic_effect_certified":False,"universal_welfare_score":None}
