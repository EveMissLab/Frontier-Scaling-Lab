"""Synthetic, adversarial, and exact finite-model checks for HCAO v0.23."""
import hashlib
import itertools
import json
import subprocess
import sys
import unittest
from fractions import Fraction

from fsl_epoch.audit import ROOT, HCAOError, audit, load_catalog, load_json
from fsl_epoch.absorption import maximum_flow, budget
from fsl_epoch.topology import closure, distances, reach, coverage
from fsl_epoch.coupling import linear, bounded

FIXTURE=ROOT/"tests/fixtures/hcao_synthetic_v0.23.json"
EARLY="2026-11-25T10:30:00Z"
MID="2026-11-25T11:30:00Z"
LATE="2026-11-25T12:30:00Z"


def frac(n,d=1):
    return {"numerator":n,"denominator":d}


class HCAOTests(unittest.TestCase):
    def setUp(self):
        self.p=load_json(FIXTURE)

    def run_audit(self,at=EARLY,mode="strict_known_at_time"):
        return audit(self.p,as_of=at,mode=mode)

    def result(self,fid,at=EARLY,mode="strict_known_at_time"):
        r=self.run_audit(at,mode)
        rows=(r["synthetic_scenario"] or r["recorded_observational_assertions"])["frames"]
        return next(x["conditional_result"] for x in rows if x["frame"]["frame_id"]==fid)

    def event(self,eid):
        return next(x for x in self.p["events"] if x["event_id"]==eid)

    def topology(self):
        return self.event("epoch-1")["data"]

    def coupling(self):
        return self.event("feedback-1")["data"]

    def absorption(self):
        return self.event("transition-1")["data"]

    def observational(self,fid,tier="repeatable_test"):
        # Fictional assertions for validation tests only; never publish as empirical.
        self.p["data_class"]="observational"
        self.p["frames"]=[f for f in self.p["frames"] if f["frame_id"]==fid]
        self.p["events"]=[e for e in self.p["events"] if e["frame_id"]==fid]
        for e in self.p["events"]:
            e["evidence_tier"]=tier
            e["source_url"]="https://example.invalid/fixture-only"
            e["artifact_sha256"]="a"*64
            if tier=="independent_repeated":
                e["assessor_ref"]="test-only-assessor"
            if fid=="feedback":
                for c in e["data"]["cycles"]:
                    c["transfer_class"]="recorded_actual"

    def test_catalog_original_ids_and_sources(self):
        c=load_catalog()
        self.assertEqual(len(c["axes"]),36)
        self.assertEqual(c["layers"],["K","R","T","P","I","A","S","G"])
        self.assertTrue(all(a["value"] is None for a in c["axes"]))
        for s in c["source_papers"]:
            b=(ROOT/s["path"]).read_bytes()
            self.assertEqual(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(),s["git_blob_sha"])

    def test_synthetic_isolation(self):
        r=self.run_audit()
        self.assertIsNone(r["recorded_observational_assertions"])
        self.assertFalse(r["independent_empirical_certification"])
        self.assertFalse(r["systemic_singularity_certified"])
        self.assertFalse(r["civilizational_singularity_certified"])
        self.assertIsNone(r["global_epoch_rank"])
        self.assertIsNone(r["global_replacement_rate"])

    def test_missing_frame_not_zero(self):
        self.assertIsNone(self.result("not-measured"))
        self.assertEqual(self.run_audit()["synthetic_scenario"]["not_observed_or_not_eligible"],1)

    def test_directional_reach_and_cost_bounds(self):
        r=self.result("epoch")
        k=next(x for x in r["candidate_graph"] if x["source"]=="knowledge")
        self.assertEqual(k["certain_reachable_in_model"],["digital","knowledge","validation"])
        self.assertEqual(k["possible_reachable_in_model"],["digital","knowledge","physical","validation"])
        self.assertEqual(k["distances"]["digital"],{"optimistic_lower":5,"known_cost_upper":5,"state":"certain"})
        self.assertEqual(k["distances"]["physical"],{"optimistic_lower":2,"known_cost_upper":None,"state":"unknown"})
        p=next(x for x in r["candidate_graph"] if x["source"]=="physical")
        self.assertEqual(p["distances"]["knowledge"]["state"],"excluded_in_model")

    def test_allowed_edge_unknown_cost_not_unreachable(self):
        e=self.topology()["transitions"][3]
        e["permission"]="allowed"
        r=self.result("epoch")
        k=next(x for x in r["candidate_graph"] if x["source"]=="knowledge")
        self.assertEqual(k["distances"]["physical"]["state"],"certain")
        self.assertIsNone(k["distances"]["physical"]["known_cost_upper"])

    def test_and_closure_unknown_not_present(self):
        r=self.result("epoch")["monotone_nonconsumptive_closure"]
        self.assertEqual(r["certain"],["tech"])
        self.assertEqual(r["possible"],["deploy","permit","tech","use"])
        self.topology()["facts"][1]["initial"]="present"
        self.assertEqual(self.result("epoch")["monotone_nonconsumptive_closure"]["certain"],r["possible"])

    def test_resource_individually_but_not_joint(self):
        r=self.result("epoch")["shared_resource_model"]
        self.assertEqual(r["individual"]["plan-a"]["status"],"feasible")
        self.assertEqual(r["individual"]["plan-b"]["status"],"feasible")
        self.assertEqual(r["joint_status"],"infeasible")
        self.assertEqual(r["joint_requirements"]["shared-power"],7)

    def test_partial_resource_known_lower_overload(self):
        self.topology()["resources"][0]["capacity"]=2
        self.topology()["plans"][1]["requirements"]["shared-power"]=None
        r=self.result("epoch")["shared_resource_model"]
        self.assertIsNone(r["joint_requirements"]["shared-power"])
        self.assertEqual(r["joint_status"],"infeasible")
        self.assertEqual(r["individual"]["plan-b"]["status"],"unknown")

    def test_critical_path_and_unknown_duration(self):
        r=self.result("epoch")["critical_path_model"]
        self.assertEqual(r["unlimited_parallel_makespan"],7)
        self.topology()["activities"][0]["duration"]=None
        self.assertIsNone(self.result("epoch")["critical_path_model"]["unlimited_parallel_makespan"])

    def test_critical_path_rejects_cycle(self):
        self.topology()["activities"][0]["predecessors"]=["c"]
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_frechet_bounds_and_invalid_joint(self):
        r=self.result("epoch")["same_frame_joint_coverage"]
        self.assertEqual(r["identified_lower"],frac(0))
        self.assertEqual(r["identified_upper"],frac(1,2))
        self.topology()["joint_coverage"]["joint_count"]=51
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_invalid_layer_and_negative_cost(self):
        self.topology()["nodes"][0]["layers"]["extra"]="forbidden"
        with self.assertRaises(HCAOError):
            self.run_audit()
        del self.topology()["nodes"][0]["layers"]["extra"]
        self.topology()["transitions"][0]["cost"]=-1
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_pipeline_separate_capacity_duration_and_acceptance(self):
        r=self.result("feedback")["pipeline"]
        self.assertEqual(r["conditional_serial_capacity"],35)
        self.assertEqual(r["conditional_bottlenecks"],["physical-validation"])
        self.assertEqual(r["conditional_serial_speedup"],frac(5,2))
        self.assertEqual(r["joint_acceptance_per_candidate"],frac(2,5))
        self.assertEqual(r["conditional_acceptance_rates"],[frac(4,5),frac(1,2)])
        self.assertFalse(r["independent_stage_success_assumed"])

    def test_pipeline_no_assumption_no_estimate(self):
        p=self.coupling()["pipeline"]
        p["serial_capacity_assumed"]=False
        p["fixed_serial_cycle_assumed"]=False
        r=self.result("feedback")["pipeline"]
        self.assertIsNone(r["conditional_serial_capacity"])
        self.assertIsNone(r["conditional_serial_speedup"])

    def test_invalid_acceptance_chain(self):
        self.coupling()["pipeline"]["acceptance_chain"]=[None,101]
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_feedback_threshold_and_no_rsi(self):
        r=self.result("feedback")
        self.assertEqual(r["linear_feedback_model"]["conditional_regime"],"supercritical")
        self.assertEqual(r["linear_feedback_model"]["exact_threshold_gap"],frac(3,16))
        self.assertFalse(r["strong_RSI_certified"])
        self.assertFalse(r["Sigma_sys_certified"])
        self.assertFalse(r["Sigma_civ_certified"])

    def test_feedback_unknown_and_outside_assumptions(self):
        p=self.coupling()["linear_feedback"]
        p["a_bps"]=None
        self.assertIsNone(self.result("feedback")["linear_feedback_model"]["conditional_regime"])
        p["a_bps"]=7500
        p["fixed_no_external_input_or_delay"]=False
        self.assertIsNone(self.result("feedback")["linear_feedback_model"]["conditional_regime"])
        p["a_bps"]=10000
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_bounded_stock_zero_and_positive_equilibrium(self):
        r=self.result("feedback")["bounded_stock_model"]
        self.assertEqual(r["positive_equilibrium"],frac(100))
        self.assertEqual(r["conditional_path"][1],frac(14))
        self.coupling()["bounded_stock"]["initial"]=0
        r=self.result("feedback")["bounded_stock_model"]
        self.assertEqual(r["limit_from_initial"],frac(0))
        self.assertTrue(all(x==frac(0) for x in r["conditional_path"]))

    def test_bounded_stock_equality_and_unknown(self):
        p=self.coupling()["bounded_stock"]
        p["gamma_bps"]=1000
        p["initial"]=150
        self.assertEqual(self.result("feedback")["bounded_stock_model"]["limit_from_initial"],frac(100))
        p["capacity"]=None
        self.assertIsNone(self.result("feedback")["bounded_stock_model"]["conditional_path"])

    def test_synthetic_cycle_cannot_assert_actual_link(self):
        r=self.result("feedback")["cycle_evidence"]
        self.assertTrue(r["consecutive_links"][0]["artifact_hash_matches"])
        self.assertFalse(r["consecutive_links"][0]["candidate_recorded_link"])
        self.coupling()["cycles"][0]["transfer_class"]="recorded_actual"
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_recorded_cycle_still_not_causal(self):
        self.observational("feedback")
        r=self.result("feedback")["cycle_evidence"]
        self.assertTrue(r["consecutive_links"][0]["candidate_recorded_link"])
        self.assertFalse(r["attribution_certified"])
        self.coupling()["cycles"][1]["input_sha256"]="f"*64
        self.assertFalse(self.result("feedback")["cycle_evidence"]["consecutive_links"][0]["candidate_recorded_link"])

    def test_cycle_time_overlap_rejected(self):
        self.coupling()["cycles"][1]["started_at"]="2026-08-31T00:00:00Z"
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_queue_equal_terminal_different_exposure(self):
        r=self.result("transition")["queue"]
        self.assertEqual(r["final_backlog"],0)
        self.assertEqual(r["cumulative_discrete_event_days"],360)
        self.assertEqual(r["peak_closing_backlog"],8)
        self.assertEqual(r["periods"][0]["conditional_fragmentation_gap"],8)
        self.assertEqual(r["periods"][0]["idle_capacity_total"],8)

    def test_queue_unknown_and_accounting_only(self):
        q=self.absorption()["queue"]
        q["periods"][0]["groups"]["A"]["closing"]=None
        r=self.result("transition")["queue"]
        self.assertIsNone(r["cumulative_discrete_event_days"])
        self.assertIsNone(r["periods"][1]["conditional_ideal_pooled_closing"])
        q["model"]="accounting_only"
        self.assertIsNone(self.result("transition")["queue"]["periods"][0]["conditional_ideal_pooled_closing"])

    def test_queue_discontinuity_and_conservation(self):
        d=self.absorption()["queue"]["periods"][1]["groups"]["A"]
        d["opening"]=9
        with self.assertRaises(HCAOError):
            self.run_audit()
        d["opening"]=8
        d["closing"]=5
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_relapse_ideal_pooling_rejected(self):
        q=self.absorption()["queue"]
        q["periods"][0]["groups"]["A"]["relapses"]=1
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_matching_unknown_not_blocked(self):
        r=self.result("transition")["matching"]
        self.assertEqual(r["population"],3)
        self.assertEqual(r["total_slots"],3)
        self.assertEqual(r["conditional_matched_lower"],2)
        self.assertEqual(r["conditional_matched_upper"],3)
        self.assertEqual(r["conditional_unmatched_upper"],1)
        self.absorption()["matching"]["compatibilities"].append(
            {"group_id":"A","slot_id":"slot-B","compatibility":"blocked"})
        r=self.result("transition")["matching"]
        self.assertEqual(r["conditional_unmatched_lower"],1)

    def test_matching_missing_count_no_imputation(self):
        self.absorption()["matching"]["slots"][0]["count"]=None
        r=self.result("transition")["matching"]
        self.assertIsNone(r["conditional_matched_lower"])
        self.assertIsNone(r["conditional_matched_upper"])

    def test_budget_prefix_gap_and_signed_income(self):
        r=self.result("transition")["standardized_budget"]
        self.assertEqual(r["period_end_cash_without_bridge_minor"],[-20,-40,0])
        self.assertEqual(r["minimum_upfront_bridge_minor"],40)
        self.assertEqual(r["net_comparison_income_shortfall_minor"],0)
        self.assertEqual(r["positive_period_income_shortfall_minor"],40)
        self.absorption()["standardized_budget"]["periods"][1]["received_inflow_minor"]=None
        self.assertIsNone(self.result("transition")["standardized_budget"]["minimum_upfront_bridge_minor"])

    def test_followup_bounds(self):
        r=self.result("transition")["followup"]
        self.assertEqual(r["first"]["lower_bound"],frac(4,5))
        self.assertEqual(r["first"]["upper_bound"],frac(9,10))
        self.assertEqual(r["sustained"]["lower_bound"],frac(3,5))
        self.assertEqual(r["sustained"]["upper_bound"],frac(4,5))

    def test_followup_contradiction(self):
        self.absorption()["followup"]["sustained"]={"success":90,"failure":10,"unknown":0}
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_observed_small_coverage_cell_guard(self):
        self.observational("epoch")
        self.topology()["joint_coverage"]["joint_count"]=1
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_observed_small_aggregate_cell_guard(self):
        self.observational("transition")
        with self.assertRaises(HCAOError):
            self.run_audit()
        self.absorption()["queue"]=None
        self.absorption()["matching"]=None
        self.absorption()["standardized_budget"]=None
        self.assertIsNotNone(self.result("transition")["followup"])

    def test_provider_claim_not_measurement(self):
        self.observational("epoch","provider_claim")
        r=self.run_audit()
        self.assertIsNone(r["synthetic_scenario"])
        self.assertIsNone(r["recorded_observational_assertions"]["frames"][0]["conditional_result"])

    def test_observation_needs_receipt_and_assessor(self):
        self.observational("epoch","independent_repeated")
        self.event("epoch-1")["assessor_ref"]=None
        with self.assertRaises(HCAOError):
            self.run_audit()
        self.event("epoch-1")["assessor_ref"]="fictional"
        self.event("epoch-1")["artifact_sha256"]=None
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_no_synthetic_promotion(self):
        self.p["data_class"]="observational"
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_vintage_correction(self):
        self.assertEqual(self.run_audit()["visible_event_count"],3)
        self.assertEqual(self.run_audit(MID)["visible_event_count"],3)
        self.assertEqual(self.run_audit(MID,"retrospective_reconstruction")["visible_event_count"],4)
        self.assertEqual(self.result("feedback",MID)["linear_feedback_model"]["conditional_regime"],"supercritical")
        self.assertEqual(self.result("feedback",MID,"retrospective_reconstruction")["linear_feedback_model"]["conditional_regime"],"critical")
        self.assertEqual(self.run_audit(LATE)["active_event_count"],3)

    def test_no_cross_frame_correction(self):
        self.event("feedback-2")["supersedes_event_id"]="epoch-1"
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_no_future_source_and_no_preregistration_leak(self):
        r=self.run_audit("2026-08-23")
        self.assertEqual(r["synthetic_scenario"]["frames"],[])
        self.event("epoch-1")["source_published_at"]="2026-11-24T23:00:00Z"
        with self.assertRaises(HCAOError):
            self.run_audit()

    def test_cli_roundtrip(self):
        r=subprocess.run([sys.executable,"-m","fsl_epoch.cli","audit","--file",str(FIXTURE),"--as-of",EARLY],
                         cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(r.stdout),self.run_audit())


class ExactModelChecks(unittest.TestCase):
    def test_grouped_matching_against_exhaustive_unit_assignments(self):
        # 16 two-by-two edge sets x 81 count configurations = 1296 cases.
        names=["A","B"]; slots=["X","Y"]
        all_edges=list(itertools.product(names,slots))
        checked=0
        for gcounts in itertools.product(range(3),repeat=2):
            for scounts in itertools.product(range(3),repeat=2):
                gs=dict(zip(names,gcounts)); ss=dict(zip(slots,scounts))
                people=[g for g in names for _ in range(gs[g])]
                jobs=[s for s in slots for _ in range(ss[s])]
                for mask in range(16):
                    edges={e for i,e in enumerate(all_edges) if mask>>i&1}
                    best=0
                    for k in range(1,min(len(people),len(jobs))+1):
                        if any(all((people[i],jobs[j]) in edges for i,j in zip(ps,js))
                               for ps in itertools.combinations(range(len(people)),k)
                               for js in itertools.permutations(range(len(jobs)),k)):
                            best=k
                    self.assertEqual(maximum_flow(gs,ss,edges),best)
                    checked+=1
        self.assertEqual(checked,1296)

    def test_frechet_all_subset_pairs(self):
        for n in range(1,7):
            observed={}
            for a,b in itertools.product(range(1<<n),repeat=2):
                key=(a.bit_count(),b.bit_count())
                observed.setdefault(key,set()).add((a&b).bit_count())
            for (a,b),hs in observed.items():
                r=coverage({"population":n,"left_count":a,"right_count":b,"joint_count":None})
                self.assertEqual(hs,set(range(r["marginal_only_lower"],r["marginal_only_upper"]+1)))

    def test_directed_shortest_paths_against_floyd_warshall(self):
        nodes=range(3)
        pairs=[(i,j) for i in nodes for j in nodes if i!=j]
        for weights in itertools.product((None,0,2),repeat=6):
            es=[{"source":u,"target":v,"cost":c} for (u,v),c in zip(pairs,weights) if c is not None]
            m=[[0 if i==j else 100 for j in nodes] for i in nodes]
            for e in es:
                m[e["source"]][e["target"]]=e["cost"]
            for k in nodes:
                for i in nodes:
                    for j in nodes:
                        m[i][j]=min(m[i][j],m[i][k]+m[k][j])
            for i in nodes:
                want={j:m[i][j] for j in nodes if m[i][j]<100}
                self.assertEqual(distances(i,es),want)
                self.assertEqual(reach(i,es),sorted(want))

    def test_linear_regime_exact_independent_polynomial_sign(self):
        for a,d in itertools.product((0,2500,5000,7500),repeat=2):
            for b,c in itertools.product((0,2500,5000,7500,10000),repeat=2):
                p={"a_bps":a,"b_bps":b,"c_bps":c,"d_bps":d,
                   "normalization_sha256":"a"*64,"fixed_no_external_input_or_delay":True}
                # characteristic polynomial evaluated at 1, with a+d<2.
                aa,bb,cc,dd=(Fraction(x,10000) for x in (a,b,c,d))
                f=1-(aa+dd)+(aa*dd-bb*cc)
                self.assertEqual(linear(p)["conditional_regime"],
                                 "supercritical" if f<0 else "critical" if f==0 else "subcritical")

    def test_stock_replay_monotone_with_bound(self):
        for initial,delta,gamma,capacity in itertools.product((0,1,3,10),(2500,5000,10000),(0,2500,5000,10000,15000),(1,4)):
            p={"initial":initial,"delta_bps":delta,"gamma_bps":gamma,"capacity":capacity,
               "periods":12,"fixed_no_external_input":True}
            r=bounded(p)
            path=[Fraction(x["numerator"],x["denominator"]) for x in r["conditional_path"]]
            limit=Fraction(r["limit_from_initial"]["numerator"],r["limit_from_initial"]["denominator"])
            self.assertEqual(path[0],initial)
            for x,y in zip(path,path[1:]):
                self.assertGreaterEqual(y,0)
                self.assertLessEqual(abs(y-limit),abs(x-limit))
                self.assertEqual(y,(1-Fraction(delta,10000))*x+min(Fraction(gamma,10000)*x,capacity))

    def test_budget_bridge_against_integer_feasibility(self):
        for initial in range(3):
            for sequence in itertools.product(range(3),repeat=6):
                pairs=list(zip(sequence[::2],sequence[1::2]))
                p={"budget_contract_sha256":"a"*64,"initial_cash_minor":initial,
                   "periods":[{"received_inflow_minor":i,"due_outflow_minor":o,
                               "comparison_income_minor":0,"actual_income_minor":0} for i,o in pairs]}
                def valid(g):
                    balance=initial+g
                    for i,o in pairs:
                        balance+=i-o
                        if balance<0:
                            return False
                    return True
                want=next(g for g in range(7) if valid(g))
                self.assertEqual(budget(p)["minimum_upfront_bridge_minor"],want)
