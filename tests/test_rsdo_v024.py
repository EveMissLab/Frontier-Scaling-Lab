"""RSDO v0.24 exact conditional model, evidence and regression tests."""
import hashlib
import itertools
import json
import subprocess
import sys
import unittest
from fractions import Fraction

from fsl_distribution.audit import ROOT, RSDOError, audit, load_catalog, load_json
from fsl_distribution.scarcity import maxflow, equilibrium
from fsl_distribution.income import physical_clearing
from fsl_distribution.institutions import funding, tax_benefits, backup_routes, hysteresis

FIXTURE=ROOT/"tests/fixtures/rsdo_synthetic_v0.24.json"
EARLY="2026-11-25T10:30:00Z"
MID="2026-11-25T11:30:00Z"
LATE="2026-11-25T12:30:00Z"


def frac(n,d=1):
    f=Fraction(n,d)
    return {"numerator":f.numerator,"denominator":f.denominator}


def unpack(x):
    return Fraction(x["numerator"],x["denominator"])


class RSDOTests(unittest.TestCase):
    def setUp(self):
        self.p=load_json(FIXTURE)

    def run_audit(self,at=EARLY,mode="strict_known_at_time"):
        return audit(self.p,as_of=at,mode=mode)

    def frame(self,fid,at=EARLY,mode="strict_known_at_time"):
        r=self.run_audit(at,mode)
        rows=(r["synthetic_scenario"] or r["recorded_observational_assertions"])["frames"]
        return next(x["conditional_result"] for x in rows if x["frame"]["frame_id"]==fid)

    def model(self,fid,key,at=EARLY,mode="strict_known_at_time"):
        return self.frame(fid,at,mode)[key]["conditional_result"]

    def event(self,eid):
        return next(e for e in self.p["events"] if e["event_id"]==eid)

    def scarcity(self):
        return self.event("scarcity-1")["data"]

    def income(self):
        return self.event("income-1")["data"]

    def institutions(self):
        return self.event("institutions-1")["data"]

    def observational(self,fid,tier="repeatable_test"):
        # Fictional assertions used only as negative controls, not real records.
        self.p["data_class"]="observational"
        self.p["frames"]=[f for f in self.p["frames"] if f["frame_id"]==fid]
        self.p["events"]=[e for e in self.p["events"] if e["frame_id"]==fid]
        for e in self.p["events"]:
            e["evidence_tier"]=tier
            e["source_url"]="https://example.invalid/fictional-test"
            e["artifact_sha256"]="a"*64
            if tier=="independent_repeated":
                e["assessor_ref"]="fictional-assessor"

    def test_catalog_ids_sources_and_parent(self):
        c=load_catalog()
        self.assertEqual(len(c["axes"]),36)
        self.assertEqual([a["id"] for a in c["axes"]],
                         [f"{p}-{i:02d}" for p in ("RSL","IPD","CTI") for i in range(1,13)])
        self.assertTrue(all(a["value"] is None for a in c["axes"]))
        for s in c["source_papers"]:
            b=(ROOT/s["path"]).read_bytes()
            self.assertEqual(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(),s["git_blob_sha"])

    def test_synthetic_isolation_no_policy_or_causal_claim(self):
        r=self.run_audit()
        self.assertIsNone(r["recorded_observational_assertions"])
        for k in ("independent_empirical_certification","causal_economic_effect_certified",
                  "policy_certified","legal_entitlement_certified","systemic_singularity_certified",
                  "civilizational_singularity_certified"):
            self.assertFalse(r[k])
        self.assertIsNone(r["universal_welfare_score"])
        self.assertIsNone(r["global_replacement_rate"])

    def test_missing_frame(self):
        self.assertIsNone(self.frame("unmeasured"))
        self.assertEqual(self.run_audit()["synthetic_scenario"]["not_observed_or_not_eligible"],1)

    def test_complement_value_migrates(self):
        r=self.model("scarcity","complement")
        self.assertEqual(r["before_net_surplus_minor"],50)
        self.assertEqual(r["after_net_surplus_minor"],90)
        self.assertEqual(r["target_unit_increment_before_minor"],0)
        self.assertEqual(r["target_unit_increment_after_minor"],30)

    def test_complement_unknown_and_bad_schedule(self):
        p=self.scarcity()["complement"]
        p["net_values_minor"]=[50,None,30]
        self.assertIsNone(self.model("scarcity","complement"))
        p["net_values_minor"]=[50,None,60]
        with self.assertRaises(RSDOError):self.run_audit()

    def test_network_joint_expansion_not_individual(self):
        r=self.model("scarcity","network")
        self.assertEqual(r["max_flow"],3)
        self.assertEqual(r["unit_capacity_increase_gain"],{"left":0,"right":0})
        self.assertEqual(r["joint_expansion_gain"],1)
        self.assertEqual(r["edges_in_every_min_cut_by_unit_gain"],[])

    def test_network_unique_bottleneck_and_null(self):
        p=self.scarcity()["network"]
        p["edges"][1]["capacity"]=5
        r=self.model("scarcity","network")
        self.assertEqual(r["edges_in_every_min_cut_by_unit_gain"],["left"])
        p["edges"][1]["capacity"]=None
        self.assertIsNone(self.model("scarcity","network"))

    def test_network_invalid_endpoint_or_parallel(self):
        p=self.scarcity()["network"]
        p["edges"][0]["target"]="not-a-node"
        with self.assertRaises(RSDOError):self.run_audit()
        p["edges"][0]["target"]="m"
        p["edges"].append({"edge_id":"parallel","source":"s","target":"m","capacity":1})
        with self.assertRaises(RSDOError):self.run_audit()

    def test_competitive_fixed_capacity_all_gain_to_rent(self):
        r=self.model("scarcity","competitive")
        self.assertEqual(r["before"]["quantity"],frac(10))
        self.assertEqual(r["after"]["price_minor"],frac(80))
        self.assertEqual(r["change"]["rent_minor"],frac(300))
        self.assertEqual(r["change"]["consumer_surplus_minor"],frac(0))
        self.assertEqual(r["incremental_rent_share_of_positive_surplus_gain"],frac(1))
        self.assertFalse(r["actual_market_power_identified"])

    def test_competitive_slack_and_no_transaction(self):
        p=self.scarcity()["competitive"]
        p["capacity"]=100
        r=self.model("scarcity","competitive")
        self.assertEqual(r["after"]["rent_minor"],frac(0))
        self.assertGreater(unpack(r["change"]["consumer_surplus_minor"]),0)
        p["ai_before_minor"]=150
        self.assertIsNone(self.model("scarcity","competitive")["before"]["price_minor"])

    def test_competitive_disabled_or_invalid_slope(self):
        p=self.scarcity()["competitive"]
        p["assumed"]=False
        self.assertIsNone(self.model("scarcity","competitive"))
        p["beta_minor"]=0
        with self.assertRaises(RSDOError):self.run_audit()

    def test_outside_option_and_no_trade(self):
        r=self.model("scarcity","outside_option")
        self.assertEqual(r["before"]["conditional_seller_increment_minor"],frac(105,2))
        self.assertEqual(r["after"]["conditional_seller_increment_minor"],frac(45,2))
        self.scarcity()["outside_option"]["buyer_outside_after_minor"]=81
        r=self.model("scarcity","outside_option")["after"]
        self.assertFalse(r["mutually_acceptable"])
        self.assertIsNone(r["acceptable_price_interval_minor"])

    def test_final_rent_ledger_conservation_and_merge(self):
        r=self.model("scarcity","beneficiary_ledger")
        self.assertEqual(r["rent_minor"],frac(100))
        self.assertEqual(r["rent_share_concentration"],frac(1,4))
        self.assertEqual(r["fixed_ledger_merge_increment"],frac(1,8))
        self.assertEqual(r["fixed_ledger_merged_concentration"],frac(3,8))
        self.assertIsNone(r["product_market_HHI"])

    def test_rent_shares_invalid_or_unmeasured(self):
        p=self.scarcity()["beneficiary_ledger"]
        p["interfaces"][0]["final_shares_bps"]["B"]=1
        with self.assertRaises(RSDOError):self.run_audit()
        p["interfaces"][0]["final_shares_bps"]["B"]=None
        self.assertIsNone(self.model("scarcity","beneficiary_ledger"))

    def test_rent_zero_and_no_double_count_attestation(self):
        p=self.scarcity()["beneficiary_ledger"]
        for e in p["interfaces"]:e["realized_rent_minor"]=0
        r=self.model("scarcity","beneficiary_ledger")
        self.assertIsNone(r["rent_share_concentration"])
        p["nonduplicated_realized_rent_attested"]=False
        self.assertIsNone(self.model("scarcity","beneficiary_ledger"))

    def test_finite_window_and_censoring(self):
        r=self.model("scarcity","window")
        one,three,end,unknown=r["scenarios"]
        self.assertEqual(unpack(three["pv_minor"])-unpack(one["pv_minor"]),Fraction(684,5))
        self.assertTrue(end["right_censored_in_window"])
        self.assertIsNone(unknown["pv_minor"])
        self.assertIsNone(unknown["right_censored_in_window"])

    def test_window_order_assumption_checked(self):
        self.scarcity()["window"]["rent_after_minor"][0]=101
        with self.assertRaises(RSDOError):self.run_audit()

    def test_fixed_basket_insufficient_price_offset(self):
        r=self.model("income","fixed_basket")
        self.assertEqual(r["relative_income_decline"],frac(3,10))
        self.assertEqual(r["relative_basket_price_decline"],frac(1,10))
        self.assertEqual(r["affordable_baskets_after"],frac(7,9))
        self.assertFalse(r["purchasing_power_not_declined"])

    def test_basket_zero_baseline_income_not_infinite(self):
        p=self.income()["fixed_basket"]
        p["income_before_minor"]=0
        self.assertIsNone(self.model("income","fixed_basket")["relative_income_decline"])
        p["items"][0]["price_after_minor"]=0
        with self.assertRaises(RSDOError):self.run_audit()

    def test_income_increase_with_expenditure_fall(self):
        r=self.model("income","income_routing")
        self.assertEqual(r["total_income_change_minor"],20)
        self.assertEqual(r["conditional_expenditure_change_minor"],frac(-8))
        self.assertIsNone(r["GDP_change"])

    def test_market_price_quantity_revenue_diverge(self):
        r=self.model("income","market_absorption")
        self.assertEqual(r["before"]["quantity"],frac(3))
        self.assertEqual(r["after"]["quantity"],frac(10))
        self.assertEqual(r["before"]["revenue_minor"],frac(12))
        self.assertEqual(r["after"]["revenue_minor"],frac(10))
        self.assertIsNone(r["profit_minor"])

    def test_demand_capacity_expansion_not_more_output(self):
        p=self.income()["demand_feedback"]
        self.assertEqual(self.model("income","demand_feedback")["unique_fixed_point"],frac(60))
        p["capacity"]=100
        self.assertEqual(self.model("income","demand_feedback")["unique_fixed_point"],frac(60))
        p["feedback_bps"]=10000
        with self.assertRaises(RSDOError):self.run_audit()

    def test_cash_pool_enough_but_rights_exclude(self):
        r=self.model("income","cash_rights")
        self.assertEqual(r["conditional_distributable_pool_minor"],100)
        self.assertEqual(r["total_registered_cash_gap_minor"],50)
        self.assertEqual(r["arbitrary_targeting_minimum_residual_minor"],0)
        self.assertEqual(r["fixed_rights_full_pool_payout"]["A"]["residual_gap_minor"],frac(30))
        self.assertTrue(r["fixed_rights_any_finite_pool_infeasible"])
        self.assertIsNone(r["fixed_rights_minimum_pool_minor"])

    def test_cash_rights_min_pool_and_unattested(self):
        p=self.income()["cash_rights"]
        for g,s in zip(p["groups"],[5000,2500,2500]):g["fixed_cash_share_bps"]=s
        self.assertEqual(self.model("income","cash_rights")["fixed_rights_minimum_pool_minor"],frac(80))
        p["legally_distributable_attested"]=False
        self.assertIsNone(self.model("income","cash_rights")["conditional_distributable_pool_minor"])

    def test_cash_no_unrealized_assets_or_negative_available(self):
        p=self.income()["cash_rights"]
        p["realized_net_receipts_minor"]=-30
        r=self.model("income","cash_rights")
        self.assertEqual(r["conditional_distributable_pool_minor"],0)
        self.assertLess(r["signed_cash_after_obligations_and_reserve_minor"],0)
        p["unrealized_assets_minor"]=100000
        with self.assertRaises(RSDOError):self.run_audit()

    def test_fixed_physical_scale_invariance(self):
        r=self.model("income","physical_clearing")
        self.assertEqual(r["conditional_unit_price_minor"],frac(10))
        self.assertEqual(r["scaled_unit_price_minor"],frac(20))
        self.assertEqual(r["physical_allocations"],r["scaled_physical_allocations"])
        self.assertEqual(r["minimum_budget_transfer_at_fixed_total_minor"],frac(20))

    def test_physical_impossibility_not_money_shortfall(self):
        p=self.income()["physical_clearing"]
        for g in p["groups"]:g["physical_target"]=6
        r=self.model("income","physical_clearing")
        self.assertFalse(r["all_targets_physically_feasible"])
        self.assertIsNone(r["minimum_budget_transfer_at_fixed_total_minor"])
        for g in p["groups"]:g["budget_minor"]=0
        self.assertIsNone(self.model("income","physical_clearing"))

    def test_deadline_bounds_not_approval(self):
        r=self.frame("institutions")["delivery"]
        self.assertEqual(r["timely_protection_lower"],frac(3,5))
        self.assertEqual(r["timely_protection_upper"],frac(7,10))
        self.assertTrue(r["received_not_merely_approved"])

    def test_bad_delivery_partition(self):
        self.institutions()["delivery"]["unknown"]=11
        with self.assertRaises(RSDOError):self.run_audit()

    def test_funding_prefix_and_stress(self):
        r=self.model("institutions","funding")
        s={x["scenario_id"]:x for x in r["scenario_results"]}
        self.assertEqual(s["base"]["minimum_opening_cash_minor"],7)
        self.assertEqual(s["stress"]["minimum_opening_cash_minor"],9)
        self.assertEqual(r["robust_minimum_opening_cash_minor"],9)
        self.assertEqual(r["extra_initial_cash_needed_minor"],2)
        self.assertFalse(r["all_registered_scenarios_pass"])

    def test_funding_unknown_not_optimistic_guarantee(self):
        self.institutions()["funding"]["scenarios"][1]["net_receipts_minor"][1]=None
        r=self.model("institutions","funding")
        self.assertIsNone(r["robust_minimum_opening_cash_minor"])
        self.assertIsNone(r["all_registered_scenarios_pass"])

    def test_tax_cliff_and_joint_continuous(self):
        p=self.institutions()["tax_benefits"]
        r=self.model("institutions","tax_benefits")
        self.assertEqual(r["sampled_net_cash_declines"][0]["net_change_minor"],frac(-17,4))
        self.assertIsNone(r["sufficient_global_nondecreasing_condition"])
        p["programs"].pop()
        r=self.model("institutions","tax_benefits")
        self.assertEqual(r["joint_continuous_lower_slope"],frac(1,4))
        self.assertTrue(r["sufficient_global_nondecreasing_condition"])
        p["programs"].append({"program_id":"second","kind":"continuous","max_benefit_minor":5,
                             "threshold_minor":10,"withdrawal_bps":5000})
        self.assertFalse(self.model("institutions","tax_benefits")["sufficient_global_nondecreasing_condition"])

    def test_service_capacity_matching_not_allocation(self):
        r=self.model("institutions","service_access")
        self.assertEqual(r["eligible_people"],3)
        self.assertEqual(r["qualified_service_units"],3)
        self.assertEqual(r["serviceable_upper"],2)
        self.assertEqual(r["unserved_lower"],1)

    def test_backup_shared_gate_not_independence(self):
        r=self.model("institutions","backup_routes")
        self.assertEqual(r["union_lower"],frac(9,10))
        self.assertEqual(r["union_upper"],frac(9,10))
        self.assertFalse(r["independence_assumed"])

    def test_backup_invalid_joint(self):
        self.institutions()["backup_routes"]["joint_success"]=80
        with self.assertRaises(RSDOError):self.run_audit()

    def test_hysteresis_variation_and_base_floor(self):
        r=self.model("institutions","hysteresis")
        self.assertEqual(r["optional_support_states"],[1,1,1,0,1])
        self.assertEqual(r["switch_count"],3)
        self.assertEqual(r["necessary_variation_for_switches"],4)
        self.assertEqual(r["true_pressure_total_variation"],4)
        self.assertFalse(r["automatic_policy_execution"])
        self.institutions()["hysteresis"]["base_floor_protected"]=False
        self.assertIsNone(self.model("institutions","hysteresis"))

    def test_hysteresis_error_unknown_and_bad_threshold(self):
        p=self.institutions()["hysteresis"]
        p["true_values"][0]=0
        with self.assertRaises(RSDOError):self.run_audit()
        p["true_values"][0]=None
        self.assertIsNone(self.model("institutions","hysteresis")["true_pressure_total_variation"])
        p["high"]=3
        with self.assertRaises(RSDOError):self.run_audit()

    def test_observed_small_group_and_suppressed_complement(self):
        self.observational("institutions")
        self.institutions()["service_access"]=None
        self.assertIsNotNone(self.frame("institutions")["delivery"])
        self.institutions()["delivery"].update({"timely":69,"late":20,"unmet":10,"unknown":None})
        with self.assertRaises(RSDOError):self.run_audit()

    def test_observed_service_small_group(self):
        self.observational("institutions")
        with self.assertRaises(RSDOError):self.run_audit()

    def test_provider_claim_not_measured(self):
        self.observational("scarcity","provider_claim")
        self.assertIsNone(self.frame("scarcity"))

    def test_observational_source_and_assessor_required(self):
        self.observational("scarcity","independent_repeated")
        self.event("scarcity-1")["assessor_ref"]=None
        with self.assertRaises(RSDOError):self.run_audit()
        self.event("scarcity-1")["assessor_ref"]="fictional"
        self.event("scarcity-1")["artifact_sha256"]=None
        with self.assertRaises(RSDOError):self.run_audit()

    def test_no_synthetic_promotion(self):
        self.p["data_class"]="observational"
        with self.assertRaises(RSDOError):self.run_audit()
        self.p["data_class"]="synthetic"
        self.p["frames"][0]["analysis_basis"]="recorded_accounting"
        with self.assertRaises(RSDOError):self.run_audit()

    def test_revision_and_vintage(self):
        self.assertEqual(self.run_audit(EARLY)["visible_event_count"],3)
        self.assertEqual(self.run_audit(MID)["visible_event_count"],3)
        self.assertEqual(self.run_audit(MID,"retrospective_reconstruction")["visible_event_count"],4)
        self.assertEqual(self.model("scarcity","competitive",MID)["change"]["rent_minor"],frac(300))
        self.assertEqual(self.model("scarcity","competitive",MID,"retrospective_reconstruction")["change"]["rent_minor"],frac(200))
        self.assertEqual(self.run_audit(LATE)["active_event_count"],3)

    def test_cross_frame_revision_and_future_source(self):
        self.event("scarcity-2")["supersedes_event_id"]="income-1"
        with self.assertRaises(RSDOError):self.run_audit()
        self.event("scarcity-2")["supersedes_event_id"]="scarcity-1"
        self.event("scarcity-1")["source_published_at"]="2026-11-24T23:00:00Z"
        with self.assertRaises(RSDOError):self.run_audit()

    def test_before_registration_no_frame(self):
        self.assertEqual(self.run_audit("2026-10-31")["synthetic_scenario"]["frames"],[])

    def test_cli_roundtrip(self):
        r=subprocess.run([sys.executable,"-m","fsl_distribution.cli","audit","--file",str(FIXTURE),"--as-of",EARLY],
                         cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(r.stdout),self.run_audit())


class ExactChecks(unittest.TestCase):
    def test_max_flow_against_all_cuts(self):
        nodes=["s","a","t"]
        arcs=[(u,v) for u in nodes for v in nodes if u!=v]
        for capacities in itertools.product(range(3),repeat=6):
            es=[(*e,c) for e,c in zip(arcs,capacities)]
            expected=min(sum(c for u,v,c in es if u in side and v not in side)
                         for side in ({"s"},{"s","a"}))
            value,cut=maxflow(nodes,es,"s","t")
            self.assertEqual(value,expected)
            self.assertEqual(sum(c for u,v,c in es if u in cut and v not in cut),value)

    def test_equilibrium_kkt_and_surplus(self):
        for alpha,beta,cap,ac,oc in itertools.product(range(1,7),range(1,4),range(1,5),range(5),range(4)):
            r=equilibrium(alpha,beta,cap,ac,oc)
            q,price,rent=r["quantity"],r["price_minor"],r["unit_rent_minor"]
            self.assertGreaterEqual(q,0)
            self.assertLessEqual(q,cap)
            self.assertEqual(rent*(cap-q),0)
            if q>0:self.assertEqual(price,ac+oc+rent)
            else:self.assertIsNone(price)
            self.assertEqual(r["modeled_total_surplus_minor"],r["rent_minor"]+r["consumer_surplus_minor"])

    def test_fixed_physical_scale_exhaustive(self):
        for q,b1,b2,e1,e2 in itertools.product(range(1,5),range(4),range(4),range(4),range(4)):
            if b1+b2==0:continue
            p={"assumed":True,"capacity":q,"uniform_budget_scale_bps":25000,"groups":[
               {"group_id":"a","budget_minor":b1,"physical_target":e1},
               {"group_id":"b","budget_minor":b2,"physical_target":e2}]}
            r=physical_clearing(p)["conditional_result"]
            self.assertEqual(r["physical_allocations"],r["scaled_physical_allocations"])
            self.assertEqual(r["all_targets_physically_feasible"],e1+e2<=q)
            self.assertEqual(sum(unpack(x) for x in r["physical_allocations"].values()),q)

    def test_prefix_reserve_vs_integer_feasibility(self):
        for reserve,r1,r2,c1,c2,d1,d2 in itertools.product(range(2),range(3),range(3),range(2),range(2),range(3),range(3)):
            p={"assumed":True,"cash_ledger_sha256":"a"*64,"opening_cash_minor":0,"reserve_minor":reserve,
               "fixed_obligations_minor":[d1,d2],"scenarios":[{"scenario_id":"s","net_receipts_minor":[r1,r2],"priority_due_minor":[c1,c2]}]}
            def valid(start):
                bal=start
                if bal<reserve:return False
                for r,c,d in zip((r1,r2),(c1,c2),(d1,d2)):
                    bal+=r-c-d
                    if bal<reserve:return False
                return True
            want=next(x for x in range(10) if valid(x))
            self.assertEqual(funding(p)["conditional_result"]["robust_minimum_opening_cash_minor"],want)

    def test_backup_bounds_against_all_subsets(self):
        for n in range(1,6):
            for g in range(n+1):
                unions={}
                for a,b in itertools.product(range(1<<g),repeat=2):
                    unions.setdefault((a.bit_count(),b.bit_count()),set()).add((a|b).bit_count())
                for (a,b),actual in unions.items():
                    r=backup_routes({"assumed":True,"cohort_n":n,"route_a":a,"route_b":b,
                                     "shared_gate":g,"joint_success":None},"synthetic",10)["conditional_result"]
                    self.assertEqual(actual,set(range(int(unpack(r["union_lower"])*n),int(unpack(r["union_upper"])*n)+1)))

    def test_joint_taper_bound_by_exact_differences(self):
        for tax,r1,r2 in itertools.product((0,2500,5000,10000),repeat=3):
            p={"assumed":True,"tax_bps":tax,"gross_income_grid_minor":list(range(21)),
               "programs":[{"program_id":"a","kind":"continuous","max_benefit_minor":5,"threshold_minor":3,"withdrawal_bps":r1},
                           {"program_id":"b","kind":"continuous","max_benefit_minor":7,"threshold_minor":5,"withdrawal_bps":r2}]}
            r=tax_benefits(p)["conditional_result"]
            ys=[unpack(x["net_cash_minor"]) for x in r["income_grid"]]
            lower=Fraction(10000-tax-r1-r2,10000)
            self.assertTrue(all(b-a>=lower for a,b in zip(ys,ys[1:])))

    def test_hysteresis_variation_exhaustive(self):
        for x in itertools.product(range(5),repeat=3):
            for errors in itertools.product((-1,0,1),repeat=3):
                z=[a+b for a,b in zip(x,errors)]
                if min(z)<0:continue
                p={"assumed":True,"base_floor_protected":True,"appeal_reference_sha256":"a"*64,
                   "low":0,"high":3,"error_bound":1,"initial_state":0,"measured":z,"true_values":list(x)}
                r=hysteresis(p)["conditional_result"]
                self.assertLessEqual(max(0,r["switch_count"]-1),sum(abs(a-b) for a,b in zip(x,x[1:])))
