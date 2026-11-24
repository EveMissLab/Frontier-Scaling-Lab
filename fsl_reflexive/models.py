"""Conditional dependency ablation, ambiguity and handoff economics. Apache-2.0."""
from .common import (require, exact, choice, ident, integer, boolean, sha, index_rows,
                     bounded_list, pack, ratio)
from fractions import Fraction

FIELDS=["dependency","ambiguity","economics"]


def idset(xs,allowed,where):
    require(isinstance(xs,list) and all(isinstance(x,str) and x in allowed for x in xs)
            and len(set(xs))==len(xs),f"{where}: invalid or duplicate nodes")
    return set(xs)


def closure(seed,rules,blocked=()):
    """Finite nonconsumptive conjunctive/alternative closure."""
    blocked=set(blocked)
    reached=set(seed)-blocked
    while True:
        new={r["conclusion"] for r in rules if r["conclusion"] not in blocked
             and set(r["premises"])<=reached}
        if new<=reached:return reached
        reached|=new


def dependency(p):
    if p is None:return None
    exact(p,["assumed","nodes","rules","targets","handoff_assets","cuts"],"dependency graph")
    boolean(p["assumed"],"fixed nonconsumptive assumptions")
    ns=index_rows(p["nodes"],["node_id","kind","initial_available"],"node_id","node")
    require(0<len(ns)<=512,"node count 1..512")
    for n in ns.values():
        choice(n["kind"],{"common_resource","live_author","tool","derived_asset","research_function"},"node kind")
        boolean(n["initial_available"],"initial availability")
        require(n["kind"]!="research_function" or not n["initial_available"],"function cannot be precredited as available")
    rules=index_rows(p["rules"],["rule_id","premises","conclusion","permission"],"rule_id","rule")
    require(len(rules)<=4096,"rule limit")
    for r in rules.values():
        idset(r["premises"],ns,"joint prerequisites")
        choice(r["conclusion"],ns,"conclusion")
        require(ns[r["conclusion"]]["kind"] in {"derived_asset","research_function"},
                "cannot regenerate exogenous author, common resource, or tool by a rule")
        choice(r["permission"],{"allowed","unknown","blocked"},"rule permission")
    targets=index_rows(p["targets"],["node_id","weight"],"node_id","target")
    require(bool(targets) and set(targets)<=set(ns),"fixed target frame")
    for t in targets.values():
        require(ns[t["node_id"]]["kind"]=="research_function","target must be a research function")
        integer(t["weight"],"target weight",minimum=1)
    handoff=idset(p["handoff_assets"],ns,"handoff assets")
    require(all(ns[x]["kind"]=="derived_asset" for x in handoff),"only transferable derived assets may be handed off")
    cuts=index_rows(p["cuts"],["cut_id","unavailable_nodes"],"cut_id","cut")
    require(len(cuts)<=128,"cut limit")
    for c in cuts.values():
        idset(c["unavailable_nodes"],ns,"cut nodes")
    if not p["assumed"]:return {"conditional_result":None}
    full={k for k,n in ns.items() if n["initial_available"]}
    authors={k for k,n in ns.items() if n["kind"]=="live_author"}
    certain=[r for r in rules.values() if r["permission"]=="allowed"]
    possible=[r for r in rules.values() if r["permission"]!="blocked"]
    baseline=closure(full,certain)
    require(set(targets)<=baseline,"all frozen targets must be feasible in certain full baseline")
    require(handoff<=baseline,"handoff must already be available in certain full baseline")
    total=sum(t["weight"] for t in targets.values())
    def row(label,removed,extra):
        # Unknown permissions create a possible, not certain, path.
        seed=(full|extra)-removed
        lo=closure(seed,certain,removed)
        hi=closure(seed,possible,removed)
        lost_lo=sorted(set(targets)-hi)
        lost_hi=sorted(set(targets)-lo)
        a=sum(targets[t]["weight"] for t in lost_lo)
        b=sum(targets[t]["weight"] for t in lost_hi)
        return {"cut_id":label,"removed":sorted(removed),"certain_reachable_targets":sorted(set(targets)&lo),
                "possible_reachable_targets":sorted(set(targets)&hi),
                "dependency_gap_weight_lower":a,"dependency_gap_weight_upper":b,
                "dependency_gap_fraction_lower":pack(ratio(a,total)),
                "dependency_gap_fraction_upper":pack(ratio(b,total))}
    require(bool(authors),"author-cut requires an explicit live-author resource")
    before=row("author-cut",authors,set())
    after=row("author-cut-with-handoff",authors,handoff)
    require(after["dependency_gap_weight_lower"]<=before["dependency_gap_weight_lower"]
            and after["dependency_gap_weight_upper"]<=before["dependency_gap_weight_upper"],"handoff monotonicity")
    extra=[]
    for cid,c in sorted(cuts.items()):
        removed=set(c["unavailable_nodes"])
        extra.append({"cut_id":cid,"without_handoff":row(cid,removed,set()),
                      "with_handoff_and_author_cut":row(cid,removed|authors,handoff)})
    return {"conditional_result":{"fixed_target_count":len(targets),"fixed_target_weight":total,
             "baseline_reachable_targets":sorted(targets),"author_cut":before,
             "author_cut_with_handoff":after,"additional_cuts":extra,
             "not_actual_dependency_or_time_certification":True}}


def ambiguity(p):
    if p is None:return None
    exact(p,["assumed","mutually_disjoint_acceptable_answers","world_ids","observation_classes_before","observation_classes_after"],"ambiguity")
    boolean(p["assumed"],"fixed possible worlds")
    boolean(p["mutually_disjoint_acceptable_answers"],"disjoint nonempty acceptable sets")
    worlds=p["world_ids"]
    bounded_list(worlds,"worlds",1,256)
    for x in worlds:ident(x,"world")
    require(len(set(worlds))==len(worlds),"duplicate world")
    universe=set(worlds)
    def partition(cs):
        bounded_list(cs,"observation classes",1,len(worlds))
        parts=[];seen=set()
        for c in cs:
            part=idset(c,universe,"equivalence class")
            require(bool(part) and not seen&part,"empty/overlapping class")
            seen|=part;parts.append(part)
        require(seen==universe,"partition must cover fixed worlds")
        return parts
    before=partition(p["observation_classes_before"])
    after=partition(p["observation_classes_after"])
    require(all(any(a<=b for b in before) for a in after),"new observations must refine old partition")
    if not (p["assumed"] and p["mutually_disjoint_acceptable_answers"]):
        return {"conditional_result":None}
    def info(parts):
        m=max(map(len,parts))
        return {"largest_indistinguishable_class":m,
                "conditional_minimax_success_ceiling":pack(Fraction(1,m))}
    return {"conditional_result":{"before":info(before),"after":info(after),
            "requires_nonempty_disjoint_answers_and_no_extra_observation":True,
            "not_actual_researcher_intent_accuracy":True}}


def economics(p):
    if p is None:return None
    exact(p,["assumed","same_quality_and_legal_feasibility","full_cost_attested","baseline_unit_cost_minor",
             "successor_unit_cost_minor","handoff_cost_minor","qualified_output_count"],"handoff cost")
    for k in ("assumed","same_quality_and_legal_feasibility","full_cost_attested"):boolean(p[k],k)
    for k in ("baseline_unit_cost_minor","successor_unit_cost_minor","handoff_cost_minor","qualified_output_count"):
        integer(p[k],k,nullable=True,minimum=1 if k=="qualified_output_count" else 0)
    a,b,k,n=(p[x] for x in ("baseline_unit_cost_minor","successor_unit_cost_minor",
                            "handoff_cost_minor","qualified_output_count"))
    if not all(p[x] for x in ("assumed","same_quality_and_legal_feasibility","full_cost_attested")) or None in (a,b,k):
        return {"conditional_result":None}
    diff=a-b
    first=k//diff+1 if diff>0 else None
    return {"conditional_result":{"strict_cost_advantage_possible":diff>0,
            "first_integer_qualified_count_with_strict_advantage":first,
            "break_even_count":pack(Fraction(k,diff)) if diff>0 else None,
            "baseline_total_minor":None if n is None else a*n,
            "successor_total_minor":None if n is None else k+b*n,
            "successor_strictly_cheaper":None if n is None else k+b*n<a*n,
            "not_personal_or_market_value":True}}


def models(data):
    exact(data,FIELDS,"conditional ablation models")
    return {"dependency":dependency(data["dependency"]),"ambiguity":ambiguity(data["ambiguity"]),
            "economics":economics(data["economics"]),"actual_author_replacement_certified":False}
