"""Conditional, finite epoch topology models (ASTT-07). Apache-2.0."""
from collections import defaultdict, deque
from heapq import heappop, heappush
from itertools import combinations

from .common import (require, exact, choice, ident, integer, nonempty, sha,
                     index_rows, ratio, pack, le)

LAYERS = ["K", "R", "T", "P", "I", "A", "S", "G"]
FIELDS = "nodes transitions facts rules resources plans activities joint_coverage".split()
STATES = {"allowed", "unknown", "blocked"}
FACT_STATES = {"present", "unknown", "absent"}


def ids(xs, universe, where):
    require(isinstance(xs, list) and all(isinstance(x, str) and x in universe for x in xs)
            and len(set(xs)) == len(xs), f"{where}: invalid or duplicate IDs")


def reach(start, edges):
    adj = defaultdict(list)
    for e in edges:
        adj[e["source"]].append(e["target"])
    seen, q = {start}, deque([start])
    while q:
        for v in adj[q.popleft()]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    return sorted(seen)


def distances(start, edges, optimistic=False):
    # Unknown cost means no finite known-cost path through that edge.
    # The optimistic graph uses zero for an unknown nonnegative edge cost.
    adj = defaultdict(list)
    for e in edges:
        c = e["cost"]
        if c is not None or optimistic:
            adj[e["source"]].append((e["target"], 0 if c is None else c))
    ds, pq = {start: 0}, [(0, start)]
    while pq:
        d, u = heappop(pq)
        if d != ds[u]:
            continue
        for v, c in adj[u]:
            nd = d + c
            if v not in ds or nd < ds[v]:
                ds[v] = nd
                heappush(pq, (nd, v))
    return ds


def closure(initial, rules):
    current = set(initial)
    while True:
        added = {r["conclusion"] for r in rules if set(r["premises"]) <= current}
        if added <= current:
            return sorted(current)
        current |= added


def critical_path(activities):
    """Fixed DAG, unlimited parallel execution. Zero duration is valid."""
    finish, todo = {}, set(activities)
    while todo:
        ready = sorted(k for k in todo if set(activities[k]["predecessors"]) <= set(finish))
        require(bool(ready), "activity cycle: critical path requires a DAG")
        for k in ready:
            a = activities[k]
            prev = [finish[p] for p in a["predecessors"]]
            finish[k] = (None if a["duration"] is None or None in prev
                         else a["duration"] + max(prev, default=0))
        todo.difference_update(ready)
    return {"finish_by_activity": finish,
            "unlimited_parallel_makespan": None if not finish or None in finish.values() else max(finish.values())}


def resource_test(resources, plans):
    detail = {}
    for pid, p in sorted(plans.items()):
        failure, unknown = [], []
        for rid, cap in sorted(resources.items()):
            n = p["requirements"][rid]
            if cap["capacity"] is None or n is None:
                unknown.append(rid)
            elif n > cap["capacity"]:
                failure.append(rid)
        detail[pid] = {"status": "infeasible" if failure else "unknown" if unknown else "feasible",
                       "overloaded": failure, "unknown": unknown}
    totals, overloaded, unknown = {}, [], []
    for rid, cap in sorted(resources.items()):
        ns = [p["requirements"][rid] for p in plans.values()]
        known_sum = sum(n for n in ns if n is not None)
        totals[rid] = None if None in ns else known_sum
        if cap["capacity"] is not None and known_sum > cap["capacity"]:
            overloaded.append(rid)
        elif cap["capacity"] is None or None in ns:
            unknown.append(rid)
    return {"model": "fixed simultaneous exclusive additive requirements only",
            "individual": detail, "joint_requirements": totals,
            "joint_status": "infeasible" if overloaded else "unknown" if unknown else "feasible",
            "overloaded": overloaded, "unknown": unknown}


def coverage(c):
    if c is None:
        return None
    exact(c, ["population", "left_count", "right_count", "joint_count"], "joint coverage")
    n, a, b, h = [c[k] for k in ("population", "left_count", "right_count", "joint_count")]
    integer(n, "population", minimum=1)
    for k, v in c.items():
        if k != "population":
            integer(v, k, nullable=True)
            le(v, n, k)
    le(h, a, "joint left")
    le(h, b, "joint right")
    lo, hi = (0 if None in (a,b) else max(0,a+b-n)), min([n]+[v for v in (a,b) if v is not None])
    if h is not None:
        require(lo <= h <= hi, "joint count contradicts marginals")
    return {"common_population": n, "marginal_left": a, "marginal_right": b,
            "observed_joint": h, "identified_lower": pack(ratio(h if h is not None else lo,n)),
            "identified_upper": pack(ratio(h if h is not None else hi,n)),
            "marginal_only_lower": lo, "marginal_only_upper": hi}


def topology(data, frame):
    exact(data, FIELDS, "topology")
    nodes = index_rows(data["nodes"], ["node_id","domain_id","layers"], "node_id", "node")
    require(0 < len(nodes) <= 256, "topology node limit 1..256")
    for n in nodes.values():
        choice(n["domain_id"], frame["domain_ids"], "node domain")
        exact(n["layers"], LAYERS, "eight layers")
        for k, v in n["layers"].items():
            nonempty(v, k, nullable=True)
    edges = index_rows(data["transitions"],
        ["edge_id","source","target","permission","cost","operation_sha256"], "edge_id", "edge")
    require(len(edges) <= 4096, "edge limit")
    for e in edges.values():
        choice(e["source"], nodes, "edge source")
        choice(e["target"], nodes, "edge target")
        choice(e["permission"], STATES, "edge permission")
        integer(e["cost"], "nonnegative additive cost", nullable=True)
        sha(e["operation_sha256"], "operation contract")
    facts = index_rows(data["facts"], ["fact_id","initial"], "fact_id", "fact")
    for f in facts.values():
        choice(f["initial"], FACT_STATES, "fact state")
    rules = index_rows(data["rules"], ["rule_id","premises","conclusion","permission"], "rule_id", "rule")
    for r in rules.values():
        ids(r["premises"], facts, "AND premises")
        choice(r["conclusion"], facts, "rule conclusion")
        choice(r["permission"], STATES, "rule permission")
    resources = index_rows(data["resources"], ["resource_id","capacity"], "resource_id", "resource")
    for r in resources.values():
        integer(r["capacity"], "resource capacity", nullable=True)
    plans = index_rows(data["plans"], ["plan_id","requirements"], "plan_id", "plan")
    for p in plans.values():
        exact(p["requirements"], resources, "resource requirements (explicit zero or null)")
        for v in p["requirements"].values():
            integer(v, "resource need", nullable=True)
    acts = index_rows(data["activities"], ["activity_id","predecessors","duration"], "activity_id", "activity")
    for a in acts.values():
        ids(a["predecessors"], acts, "predecessors")
        integer(a["duration"], "duration", nullable=True)
    certain = [e for e in edges.values() if e["permission"]=="allowed"]
    possible = [e for e in edges.values() if e["permission"]!="blocked"]
    paths = []
    for u in sorted(nodes):
        rlo, rhi = reach(u,certain), reach(u,possible)
        dlo, dhi = distances(u,possible,True), distances(u,certain)
        paths.append({"source": u, "certain_reachable_in_model": rlo,
                      "possible_reachable_in_model": rhi,
                      "distances": {v: {"optimistic_lower": dlo.get(v),
                                       "known_cost_upper": dhi.get(v),
                                       "state": ("certain" if v in rlo else "unknown" if v in rhi else "excluded_in_model")}
                                    for v in sorted(nodes)}})
    low = closure([f["fact_id"] for f in facts.values() if f["initial"]=="present"],
                  [r for r in rules.values() if r["permission"]=="allowed"])
    high = closure([f["fact_id"] for f in facts.values() if f["initial"]!="absent"],
                   [r for r in rules.values() if r["permission"]!="blocked"])
    return {"nodes": [nodes[k] for k in sorted(nodes)], "candidate_graph": paths,
            "conditional_minimum_open_neighborhoods": {p["source"]:p["certain_reachable_in_model"] for p in paths},
            "monotone_nonconsumptive_closure": {"certain": low, "possible": high},
            "shared_resource_model": resource_test(resources,plans),
            "critical_path_model": critical_path(acts),
            "same_frame_joint_coverage": coverage(data["joint_coverage"]),
            "universal_epoch_rank": None, "deployment_probability": None,
            "conditional_only": True}
