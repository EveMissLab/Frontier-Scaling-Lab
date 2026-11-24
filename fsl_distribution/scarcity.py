"""RSL-M conditional scarcity, capacity, and realized rent accounting. Apache-2.0."""
from collections import defaultdict, deque
from fractions import Fraction

from .common import (require, exact, choice, ident, integer, sha, bps,
                     numeric_fields, bounded_list, assumption, index_rows, pack, ratio)

FIELDS=["complement","network","competitive","outside_option","beneficiary_ledger","window"]


def complement(p):
    if p is None:
        return None
    exact(p,["assumed","target_capacity","other_capacity","other_expanded_capacity","net_values_minor"],"complement")
    enabled=assumption(p)
    keys=("target_capacity","other_capacity","other_expanded_capacity")
    numeric_fields(p,keys)
    b,m,m2=(p[k] for k in keys)
    if m is not None and m2 is not None:
        require(m2>=m,"other expanded capacity cannot shrink")
    ws=p["net_values_minor"]
    if ws is not None:
        bounded_list(ws,"net demand units",0,4096)
        for w in ws:
            integer(w,"net marginal value",nullable=True)
        known=[w for w in ws if w is not None]
        require(all(x>=y for x,y in zip(known,known[1:])),"net values must be nonincreasing")
    if not enabled or None in (b,m,m2,ws) or None in ws:
        return {"conditional_result":None}
    def value(x,y):
        return sum(ws[:min(x,y,len(ws))])
    before=value(b,m)
    after=value(b,m2)
    return {"conditional_result":{"before_net_surplus_minor":before,"after_net_surplus_minor":after,
            "target_unit_increment_before_minor":value(b+1,m)-before,
            "target_unit_increment_after_minor":value(b+1,m2)-after}}


def maxflow(nodes, edges, source, sink):
    """Integral directed capacities; residual handles antiparallel arcs."""
    residual=defaultdict(int)
    adj=defaultdict(set)
    for u,v,c in edges:
        residual[u,v]+=c
        adj[u].add(v);adj[v].add(u)
    flow=0
    while True:
        parent={source:None};todo=deque([source])
        while todo and sink not in parent:
            u=todo.popleft()
            for v in sorted(adj[u]):
                if v not in parent and residual[u,v]>0:
                    parent[v]=u;todo.append(v)
        if sink not in parent:
            return flow, sorted(parent)
        v=sink;amount=None
        while parent[v] is not None:
            u=parent[v]
            c=residual[u,v]
            amount=c if amount is None else min(amount,c)
            v=u
        v=sink
        while parent[v] is not None:
            u=parent[v]
            residual[u,v]-=amount;residual[v,u]+=amount
            v=u
        flow+=amount


def network(p):
    if p is None:
        return None
    exact(p,["assumed","nodes","source","sink","edges","joint_expansions"],"network")
    enabled=assumption(p)
    nodes=p["nodes"]
    bounded_list(nodes,"nodes",2,64)
    for x in nodes: ident(x,"node")
    require(len(set(nodes))==len(nodes),"duplicate node")
    s,t=p["source"],p["sink"]
    choice(s,nodes,"source");choice(t,nodes,"sink")
    require(s!=t,"distinct source and sink required")
    es=index_rows(p["edges"],["edge_id","source","target","capacity"],"edge_id","edge")
    require(len(es)<=128,"edge limit")
    endpoints=set()
    for e in es.values():
        u,v=e["source"],e["target"]
        choice(u,nodes,"edge source");choice(v,nodes,"edge target")
        require(u!=v and (u,v) not in endpoints,"self loop or parallel arc; aggregate same-unit arcs first")
        endpoints.add((u,v))
        integer(e["capacity"],"capacity",nullable=True)
    increments=index_rows(p["joint_expansions"],["edge_id","increment"],"edge_id","joint expansions")
    require(set(increments)<=set(es),"unknown expansion edge")
    for e in increments.values(): integer(e["increment"],"increment",nullable=True)
    if not enabled or any(e["capacity"] is None for e in es.values()):
        return {"conditional_result":None}
    def run(changes):
        return maxflow(nodes,[(e["source"],e["target"],e["capacity"]+changes.get(k,0))
                              for k,e in es.items()],s,t)
    q,cut=run({})
    crossing=[k for k,e in sorted(es.items()) if e["source"] in cut and e["target"] not in cut]
    require(sum(es[k]["capacity"] for k in crossing)==q,"cut certificate mismatch")
    marginal={k:run({k:1})[0]-q for k in sorted(es)}
    changes={k:e["increment"] for k,e in increments.items()}
    joint=None if None in changes.values() else run(changes)[0]-q
    return {"conditional_result":{"max_flow":q,"one_min_cut_source_side":cut,
        "one_min_cut_edge_ids":crossing,"unit_capacity_increase_gain":marginal,
        "edges_in_every_min_cut_by_unit_gain":[k for k,v in marginal.items() if v==1],
        "joint_expansion_gain":joint}}


def equilibrium(alpha,beta,capacity,ai_cost,opportunity_cost):
    q=min(Fraction(capacity),max(Fraction(0),Fraction(alpha-ai_cost-opportunity_cost,beta)))
    price=Fraction(alpha)-beta*q if q>0 else None
    rent=max(Fraction(0),Fraction(alpha-beta*capacity-ai_cost-opportunity_cost))
    total=capacity*rent
    consumer=Fraction(beta,2)*q*q
    surplus=(alpha-ai_cost-opportunity_cost)*q-Fraction(beta,2)*q*q
    require(surplus==consumer+total,"surplus identity")
    return {"quantity":q,"price_minor":price,"unit_rent_minor":rent,"rent_minor":total,
            "consumer_surplus_minor":consumer,"modeled_total_surplus_minor":surplus}


def competitive(p):
    if p is None:return None
    keys=["alpha_minor","beta_minor","capacity","opportunity_cost_minor","ai_before_minor","ai_after_minor"]
    exact(p,["assumed",*keys],"competitive benchmark")
    enabled=assumption(p)
    numeric_fields(p,keys)
    for k in ("alpha_minor","beta_minor","capacity"):
        if p[k] is not None:require(p[k]>0,f"{k}: positive required")
    if not enabled or any(p[k] is None for k in keys):
        return {"conditional_result":None}
    a,b,c,o,x,y=(p[k] for k in keys)
    before=equilibrium(a,b,c,x,o)
    after=equilibrium(a,b,c,y,o)
    delta={k:(None if before[k] is None or after[k] is None else after[k]-before[k]) for k in before}
    return {"conditional_result":{"before":{k:pack(v) for k,v in before.items()},
              "after":{k:pack(v) for k,v in after.items()},
              "change":{k:pack(v) for k,v in delta.items()},
              "incremental_rent_share_of_positive_surplus_gain":pack(
                  delta["rent_minor"]/delta["modeled_total_surplus_minor"] if delta["modeled_total_surplus_minor"]>0 else None),
              "initial_capacity_binding":before["quantity"]==c,
              "actual_market_power_identified":False}}


def outside_option(p):
    if p is None:return None
    keys=["value_minor","buyer_outside_before_minor","buyer_outside_after_minor","seller_outside_minor","seller_share_bps"]
    exact(p,["assumed",*keys],"outside option")
    enabled=assumption(p)
    numeric_fields(p,keys,signed=keys[:-1])
    bps(p["seller_share_bps"],"seller share")
    if not enabled or any(p[k] is None for k in keys):return {"conditional_result":None}
    v,u,u2,o,share=(p[k] for k in keys)
    def row(buyer):
        s=v-buyer-o
        rent=Fraction(share,10000)*max(0,s)
        return {"joint_gain_minor":s,"mutually_acceptable":s>=0,
                "acceptable_price_interval_minor":[o,v-buyer] if s>=0 else None,
                "conditional_seller_increment_minor":pack(rent)}
    return {"conditional_result":{"before":row(u),"after":row(u2)}}


def beneficiary_ledger(p):
    if p is None:return None
    exact(p,["assumed","nonduplicated_realized_rent_attested","beneficiary_contract_sha256",
             "beneficiary_ids","interfaces","merge_pair"],"rent beneficiary ledger")
    enabled=assumption(p)
    require(type(p["nonduplicated_realized_rent_attested"]) is bool,"nonduplication attestation")
    sha(p["beneficiary_contract_sha256"],"final cash rights reference")
    ids=p["beneficiary_ids"]
    bounded_list(ids,"beneficiary IDs",1,128)
    for k in ids:ident(k,"aggregate beneficiary ID")
    require(len(ids)==len(set(ids)),"duplicate beneficiary ID")
    es=index_rows(p["interfaces"],["interface_id","realized_rent_minor","final_shares_bps"],"interface_id","interface")
    require(0<len(es)<=128,"interfaces 1..128")
    for e in es.values():
        integer(e["realized_rent_minor"],"realized net rent",nullable=True)
        exact(e["final_shares_bps"],ids,"ultimate cash shares")
        ss=list(e["final_shares_bps"].values())
        for x in ss:bps(x,"final share")
        known=sum(x for x in ss if x is not None)
        require(known<=10000 and (None in ss or known==10000),"cash share column conservation")
    merge=p["merge_pair"]
    if merge is not None:
        bounded_list(merge,"merge pair",2,2)
        require(merge[0]!=merge[1] and all(x in ids for x in merge),"invalid merge pair")
    complete=all(e["realized_rent_minor"] is not None and None not in e["final_shares_bps"].values() for e in es.values())
    if not enabled or not p["nonduplicated_realized_rent_attested"] or not complete:
        return {"conditional_result":None}
    returns={g:sum((Fraction(e["realized_rent_minor"]*e["final_shares_bps"][g],10000)
                   for e in es.values()),Fraction(0)) for g in ids}
    total=sum(returns.values())
    require(total==sum(e["realized_rent_minor"] for e in es.values()),"final beneficiary rent mass")
    concentration=sum((r/total)**2 for r in returns.values()) if total>0 else None
    gain=(2*returns[merge[0]]*returns[merge[1]]/total**2
          if merge is not None and total>0 else None)
    return {"conditional_result":{"rent_minor":pack(total),"final_beneficiary_rent_minor":{g:pack(v) for g,v in returns.items()},
              "rent_share_concentration":pack(concentration),"fixed_ledger_merge_increment":pack(gain),
              "fixed_ledger_merged_concentration":pack(concentration+gain if gain is not None else None),
              "product_market_HHI":None,"actual_legal_control_certified":False}}


def window(p):
    if p is None:return None
    exact(p,["assumed","discount_bps","rent_before_minor","rent_after_minor","opening_periods"],"rent window")
    enabled=assumption(p)
    bps(p["discount_bps"],"discount")
    if p["discount_bps"] is not None:require(p["discount_bps"]>0,"discount must be positive")
    before,after=p["rent_before_minor"],p["rent_after_minor"]
    bounded_list(before,"before path",1,60)
    require(isinstance(after,list) and len(before)==len(after),"matched finite rent paths")
    for x,y in zip(before,after):
        integer(x,"before",nullable=True);integer(y,"after",nullable=True)
        if x is not None and y is not None:require(x>=y,"before rent must dominate after in T6 model")
    ts=p["opening_periods"]
    bounded_list(ts,"opening scenarios",1,61)
    for t in ts:
        integer(t,"opening",nullable=True)
        if t is not None:require(t<=len(before),"opening outside window; T is right-censored no opening")
    if not enabled or p["discount_bps"] is None or None in before or None in after:
        return {"conditional_result":None}
    d=Fraction(p["discount_bps"],10000)
    def pv(t):return sum((d**k*(before[k] if k<t else after[k]) for k in range(len(before))),Fraction(0))
    rows=[{"opening_period":t,"pv_minor":pack(pv(t)) if t is not None else None,
           "right_censored_in_window":t==len(before) if t is not None else None} for t in ts]
    return {"conditional_result":{"scenarios":rows,"unknown_opening_pv_bounds_minor":[pack(pv(0)),pack(pv(len(before)))],
              "not_social_welfare_or_investment_forecast":True}}


def scarcity(data,frame,dc):
    exact(data,FIELDS,"scarcity")
    return {"complement":complement(data["complement"]),"network":network(data["network"]),
            "competitive":competitive(data["competitive"]),"outside_option":outside_option(data["outside_option"]),
            "beneficiary_ledger":beneficiary_ledger(data["beneficiary_ledger"]),"window":window(data["window"]),
            "causal_rent_attribution_certified":False,"market_power_certified":False}
