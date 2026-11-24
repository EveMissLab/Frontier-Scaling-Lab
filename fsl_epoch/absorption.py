"""Civilizational absorption: accounting and conditional matching (ASTT-09).
No allocation decisions about real persons are made. Apache-2.0.
"""
from collections import defaultdict, deque
from .common import (require, exact, choice, ident, integer, sha, index_rows, pack,
                     ratio, le, timestamp)

FIELDS = ["queue","matching","standardized_budget","followup"]


def count(v, name, data_class, minimum, nullable=True):
    integer(v,name,nullable=nullable)
    if data_class=="observational" and v is not None:
        require(v==0 or v>=minimum,"small public cell must be suppressed")


def check_partition(total, parts, data_class, minimum, where):
    if total is None:
        return
    known=sum(x for x in parts if x is not None)
    require(known<=total,f"{where}: partition exceeds population")
    if None not in parts:
        require(known==total,f"{where}: partition conservation")
    elif data_class=="observational" and parts.count(None)==1:
        require(total-known==0 or total-known>=minimum,f"{where}: inferable small complement")


def queue(q,dc,mincell):
    if q is None:
        return None
    exact(q,["group_ids","period_duration_days","model","periods"],"queue")
    gs=q["group_ids"]
    require(isinstance(gs,list) and 0<len(gs)<=64,"groups 1..64")
    for g in gs:
        ident(g,"aggregate group id")
    require(len(set(gs))==len(gs),"duplicate groups")
    integer(q["period_duration_days"],"period duration",minimum=1)
    choice(q["model"],{"accounting_only","work_conserving_partitioned"},"queue model")
    ps=q["periods"]
    require(isinstance(ps,list) and 0<len(ps)<=120,"periods 1..120")
    rows=[]
    previous={}
    pool=None
    pool_active=q["model"]=="work_conserving_partitioned"
    exposure=0
    peak=0
    all_known=True
    for i,p in enumerate(ps):
        exact(p,["period_index","groups"],"period")
        require(type(p["period_index"]) is int and p["period_index"]==i+1,"ordered period index")
        exact(p["groups"],gs,"fixed group frame")
        total_open,total_arr,total_cap,total_close=0,0,0,0
        complete=True
        for g in gs:
            d=p["groups"][g]
            exact(d,["opening","arrivals","relapses","absorbed","other_exits","capacity","closing"],"group period")
            for k,v in d.items():
                count(v,k,dc,mincell)
            o,a,r,s,e,c,z=(d[k] for k in ("opening","arrivals","relapses","absorbed","other_exits","capacity","closing"))
            if g in previous and previous[g] is not None and o is not None:
                require(previous[g]==o,"queue discontinuity between periods")
            previous[g]=z
            if q["model"]=="work_conserving_partitioned":
                require(r in (None,0) and e in (None,0),"ideal pooling model excludes relapse and other exits")
            le(s,c,"absorbed exceeds qualified capacity")
            if None not in (o,a,r):
                available=o+a+r
                check_partition(available,[s,e,z],dc,mincell,"queue")
                if q["model"]=="work_conserving_partitioned" and r==e==0 and c is not None:
                    if s is not None:
                        require(s==min(available,c),"work-conserving absorption contradiction")
                    if z is not None:
                        require(z==max(0,available-c),"work-conserving closing contradiction")
            if None in (o,a,r,s,e,c,z):
                complete=False
            else:
                total_open+=o;total_arr+=a;total_cap+=c;total_close+=z
        known_close=[p["groups"][g]["closing"] for g in gs]
        closing=None if None in known_close else sum(known_close)
        if closing is None:
            all_known=False
        else:
            exposure+=closing*q["period_duration_days"]
            peak=max(peak,closing)
        if pool_active and complete:
            if pool is None:
                pool=total_open
            # Disjoint populations and immediate costless pooling are assumptions, not recommendations.
            pool=max(0,pool+total_arr-total_cap)
            require(total_close>=pool,"partitioned queue violates pooled lower bound")
        else:
            pool_active=False
            pool=None
        idle=[None if None in (d["capacity"],d["absorbed"]) else d["capacity"]-d["absorbed"]
              for d in p["groups"].values()]
        rows.append({"period_index":i+1,"groups":p["groups"],"closing_total":closing,
                     "idle_capacity_total":None if None in idle else sum(idle),
                     "conditional_ideal_pooled_closing":pool,
                     "conditional_fragmentation_gap":None if pool is None or closing is None else closing-pool})
    return {"model":q["model"],"period_duration_days":q["period_duration_days"],"periods":rows,
            "peak_closing_backlog":peak if all_known else None,
            "cumulative_discrete_event_days":exposure if all_known else None,
            "known_period_exposure_lower":exposure,
            "final_backlog":rows[-1]["closing_total"],
            "not_exact_individual_waiting_time":True}


def maximum_flow(groups,slots,edges):
    """Integer capacities, anonymous homogeneous groups; Edmonds-Karp."""
    source=("source","")
    sink=("sink","")
    adj=defaultdict(set)
    residual={}
    def add(u,v,c):
        adj[u].add(v);adj[v].add(u)
        residual[u,v]=c
        residual[v,u]=0
    for g,n in groups.items():
        add(source,("g",g),n)
    for s,n in slots.items():
        add(("s",s),sink,n)
    total=sum(groups.values())
    for g,s in edges:
        add(("g",g),("s",s),total)
    value=0
    while True:
        parents={source:None}
        todo=deque([source])
        while todo and sink not in parents:
            u=todo.popleft()
            for v in sorted(adj[u]):
                if v not in parents and residual[u,v]>0:
                    parents[v]=u
                    todo.append(v)
        if sink not in parents:
            break
        amount=total
        v=sink
        while parents[v] is not None:
            u=parents[v]
            amount=min(amount,residual[u,v]);v=u
        v=sink
        while parents[v] is not None:
            u=parents[v]
            residual[u,v]-=amount
            residual[v,u]+=amount
            v=u
        value+=amount
    return value


def matching(m,dc,mincell):
    if m is None:
        return None
    exact(m,["groups","slots","compatibilities","homogeneous_group_contract_sha256"],"matching")
    sha(m["homogeneous_group_contract_sha256"],"group compatibility contract")
    groups=index_rows(m["groups"],["group_id","count"],"group_id","matching group")
    slots=index_rows(m["slots"],["slot_id","count"],"slot_id","slot group")
    require(0<len(groups)<=64 and len(slots)<=64,"grouped matching size limit")
    for x in [*groups.values(),*slots.values()]:
        count(x["count"],"matching count",dc,mincell)
    require(isinstance(m["compatibilities"],list),"compatibilities array")
    declared={}
    for e in m["compatibilities"]:
        exact(e,["group_id","slot_id","compatibility"],"compatibility edge")
        choice(e["group_id"],groups,"group")
        choice(e["slot_id"],slots,"slot")
        choice(e["compatibility"],{"allowed","unknown","blocked"},"compatibility")
        k=(e["group_id"],e["slot_id"])
        require(k not in declared,"duplicate compatibility")
        declared[k]=e["compatibility"]
    # Undeclared cross-product edges remain unknown, never silently blocked.
    lower=[k for k,v in declared.items() if v=="allowed"]
    upper=[(g,s) for g in groups for s in slots if declared.get((g,s),"unknown")!="blocked"]
    g={k:x["count"] for k,x in groups.items()}
    s={k:x["count"] for k,x in slots.items()}
    if None in g.values() or None in s.values():
        n=lo=hi=None
    else:
        n=sum(g.values())
        lo=maximum_flow(g,s,lower)
        hi=maximum_flow(g,s,upper)
    return {"population":n,"total_slots":None if None in s.values() else sum(s.values()),
            "certain_edge_count":len(lower),"possible_edge_count":len(upper),
            "conditional_matched_lower":lo,"conditional_matched_upper":hi,
            "conditional_unmatched_lower":None if hi is None else n-hi,
            "conditional_unmatched_upper":None if lo is None else n-lo,
            "not_actual_hiring_or_individual_ranking":True}


def budget(b):
    if b is None:
        return None
    exact(b,["budget_contract_sha256","initial_cash_minor","periods"],"standardized budget")
    sha(b["budget_contract_sha256"],"standardized budget contract")
    initial=b["initial_cash_minor"]
    integer(initial,"initial cash",nullable=True)
    ps=b["periods"]
    require(isinstance(ps,list) and 0<len(ps)<=120,"budget periods 1..120")
    cash=initial
    deficit=None if initial is None else 0
    signed=0
    positive=0
    income_complete=True
    path=[]
    for p in ps:
        exact(p,["received_inflow_minor","due_outflow_minor","comparison_income_minor","actual_income_minor"],"budget period")
        for k,v in p.items():
            integer(v,k,nullable=True)
        inc,out,ref,actual=(p[k] for k in ("received_inflow_minor","due_outflow_minor","comparison_income_minor","actual_income_minor"))
        if None in (cash,inc,out):
            cash=None;deficit=None
        else:
            cash+=inc-out
            deficit=max(deficit,-cash,0)
        path.append(cash)
        if None in (ref,actual):
            income_complete=False
        else:
            signed+=ref-actual
            positive+=max(ref-actual,0)
    return {"period_end_cash_without_bridge_minor":path,
            "minimum_upfront_bridge_minor":deficit,
            "net_comparison_income_shortfall_minor":signed if income_complete else None,
            "positive_period_income_shortfall_minor":positive if income_complete else None,
            "scope":"one specified standardized budget, end-of-period cash only; not per-household inference",
            "comparison_income_is_causal_counterfactual":False}


def followup(f,dc,mincell):
    if f is None:
        return None
    exact(f,["cohort_n","first_horizon_days","sustained_followup_days","first","sustained"],"followup")
    n=f["cohort_n"]
    count(n,"cohort",dc,mincell,nullable=False)
    require(n>0,"positive fixed cohort")
    for k in ("first_horizon_days","sustained_followup_days"):
        integer(f[k],k,minimum=1)
    result={}
    for key in ("first","sustained"):
        d=f[key]
        exact(d,["success","failure","unknown"],key)
        for v in d.values():
            count(v,key,dc,mincell)
        a,b,u=(d[k] for k in ("success","failure","unknown"))
        check_partition(n,[a,b,u],dc,mincell,key)
        lo=0 if a is None else a
        hi=n-(0 if b is None else b)
        # Unknown is a missing-outcome count, not a failure. Suppressed counts also remain unknown.
        if a is not None and u is not None:
            hi=min(hi,a+u)
        result[key]={"counts":d,"lower_bound":pack(ratio(lo,n)),"upper_bound":pack(ratio(hi,n))}
    a=f["first"];s=f["sustained"]
    le(s["success"],a["success"],"sustained success requires confirmed first success")
    le(a["failure"],s["failure"],"first failure must also fail sustained endpoint")
    # Tighten the upper sustained endpoint with the first endpoint upper bound.
    upper=result["sustained"]["upper_bound"];first_upper=result["first"]["upper_bound"]
    if upper["numerator"]*first_upper["denominator"]>first_upper["numerator"]*upper["denominator"]:
        result["sustained"]["upper_bound"]=first_upper
    low=result["sustained"]["lower_bound"];high=result["sustained"]["upper_bound"]
    require(low["numerator"]*high["denominator"]<=high["numerator"]*low["denominator"],
            "inconsistent first and sustained outcome bounds")
    return {"cohort_n":n,"first_horizon_days":f["first_horizon_days"],
            "sustained_followup_days":f["sustained_followup_days"],**result,
            "bounds_are_not_confidence_intervals":True}


def absorption(data,frame,data_class):
    exact(data,FIELDS,"absorption")
    mincell=frame["min_public_cell"]
    return {"queue":queue(data["queue"],data_class,mincell),
            "matching":matching(data["matching"],data_class,mincell),
            "standardized_budget":budget(data["standardized_budget"]),
            "followup":followup(data["followup"],data_class,mincell),
            "causal_AI_displacement_certified":False,"civilizational_absorption_score":None}
