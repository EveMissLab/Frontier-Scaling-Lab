"""RRAO v0.25: synthetic, adversarial and exact conditional checks."""
import copy
import hashlib
import itertools
import json
import subprocess
import sys
import unittest
from fractions import Fraction

from fsl_reflexive.audit import ROOT, RRAOError, audit, load_catalog, load_json
from fsl_reflexive.models import closure, economics, ambiguity
from fsl_reflexive.continuity import entry_digest

FIXTURE=ROOT/"tests/fixtures/rrao_synthetic_v0.25.json"
EARLY="2026-11-25T10:30:00Z"
MID="2026-11-25T11:30:00Z"
LATE="2026-11-25T12:30:00Z"


def frac(n,d=1):
    f=Fraction(n,d)
    return {"numerator":f.numerator,"denominator":f.denominator}


class RRAOTests(unittest.TestCase):
    def setUp(self):
        self.p=load_json(FIXTURE)

    def run_audit(self,at=EARLY,mode="strict_known_at_time"):
        return audit(self.p,as_of=at,mode=mode)

    def frame(self,fid,at=EARLY,mode="strict_known_at_time"):
        r=self.run_audit(at,mode)
        rows=(r["synthetic_scenario"] or r["recorded_observational_assertions"])["frames"]
        return next(x["conditional_result"] for x in rows if x["frame"]["frame_id"]==fid)

    def design(self,fid):
        return next(x["design"] for x in self.p["frames"] if x["frame_id"]==fid)

    def event(self,eid):
        return next(e for e in self.p["events"] if e["event_id"]==eid)

    def trial(self,case,arm,eid="trials-1"):
        return next(t for t in self.event(eid)["data"]["trials"] if t["case_id"]==case and t["arm_id"]==arm)

    def row(self,case,arm,at=EARLY,mode="strict_known_at_time"):
        return next(r for r in self.frame("trials",at,mode)["trial_rows"] if r["case_id"]==case and r["arm_id"]==arm)

    def model(self,key):
        return self.frame("models")[key]["conditional_result"]

    def observational(self,fid,tier="repeatable_test"):
        # Fictional observations used solely as negative controls.
        self.p["data_class"]="observational"
        self.p["frames"]=[f for f in self.p["frames"] if f["frame_id"]==fid]
        self.p["frames"][0]["analysis_basis"]="recorded_accounting"
        self.p["events"]=[e for e in self.p["events"] if e["frame_id"]==fid]
        for e in self.p["events"]:
            e["evidence_tier"]=tier
            e["source_url"]="https://example.invalid/fixture-only"
            e["artifact_sha256"]="a"*64
            if tier=="independent_repeated":
                e["assessor_ref"]="fictional-test-assessor"
            for k in ("cycles","probes"):
                for x in e["data"].get(k,[]):x["transfer_class"]="recorded_actual"

    def test_catalog_original_rta_ids_and_source(self):
        c=load_catalog()
        self.assertEqual([a["id"] for a in c["axes"]],[f"RTA-{i:02d}" for i in range(1,13)])
        self.assertTrue(all(a["value"] is None for a in c["axes"]))
        for s in c["source_papers"]:
            b=(ROOT/s["path"]).read_bytes()
            self.assertEqual(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(),s["git_blob_sha"])

    def test_synthetic_no_empirical_certification(self):
        r=self.run_audit()
        self.assertIsNone(r["recorded_observational_assertions"])
        for k in ("independent_empirical_certification","actual_author_replacement_certified",
                  "institutional_autonomy_certified","independent_research_autonomy_certified",
                  "historical_authorship_certified","systemic_singularity_certified","civilizational_singularity_certified"):
            self.assertFalse(r[k])
        self.assertIsNone(r["global_author_replacement_rate"])

    def test_missing_frame_and_missing_trial(self):
        self.assertIsNone(self.frame("unmeasured"))
        self.assertEqual(self.row("generate","C-handoff")["author_independent"],"unknown")
        self.assertEqual(len(self.frame("trials")["trial_rows"]),35)

    def test_known_replay_not_independent_reconstruction(self):
        self.assertEqual(self.row("replay","B-public")["author_independent"],"passed")
        self.assertEqual(self.row("reconstruct","B-public")["gates"]["original_solver_isolation"],"failed")
        self.assertEqual(self.row("reconstruct","B-public")["artifact_qualification"],"failed")
        self.assertEqual(self.row("reconstruct","C-handoff")["author_independent"],"passed")

    def test_baseline_and_non_author_human_are_distinct(self):
        r=self.row("replay","A-original")
        self.assertEqual(r["artifact_qualification"],"passed")
        self.assertEqual(r["author_independent"],"failed")
        r=self.row("replay","D-independent")
        self.assertEqual(r["author_independent"],"passed")
        self.assertEqual(r["human_core_independent"],"failed")

    def test_autonomous_goal_selection_not_preregistered_answer(self):
        r=self.row("generate","B-public")
        self.assertEqual(r["artifact_qualification"],"passed")
        self.assertEqual(r["author_independent"],"failed")
        self.assertEqual(r["autonomous_generation"],"failed")
        r=self.row("generate","E-autonomous")
        self.assertEqual(r["autonomous_generation"],"passed")

    def test_new_goal_from_independent_human_not_AI_autonomy(self):
        r=self.row("generate","D-independent")
        self.assertEqual(r["author_independent"],"passed")
        self.assertEqual(r["autonomous_generation"],"failed")

    def test_heldout_leakage_unknown_and_confirmed(self):
        r=self.row("application","B-public")
        self.assertEqual(r["artifact_qualification"],"unknown")
        self.trial("application","B-public")["leakage"]="confirmed"
        self.assertEqual(self.row("application","B-public")["artifact_qualification"],"failed")

    def test_negative_result_is_legitimate_but_false_defect_fails(self):
        self.assertEqual(self.row("refute","C-handoff")["artifact_qualification"],"passed")
        self.assertEqual(self.row("refute","B-public")["artifact_qualification"],"failed")
        self.trial("refute","C-handoff")["checks"]["negative_results_logged"]="unknown"
        self.assertEqual(self.row("refute","C-handoff")["artifact_qualification"],"unknown")

    def test_rights_governance_not_compensated(self):
        self.trial("replay","E-autonomous")["checks"]["authorization"]="failed"
        self.assertEqual(self.row("replay","E-autonomous")["artifact_qualification"],"failed")
        self.assertEqual(self.row("institution","C-handoff")["artifact_qualification"],"unknown")

    def test_scope_compliance_and_actual_author_contact(self):
        d=self.trial("replay","B-public")
        d["human"]["author_contacts"]=1
        self.assertEqual(self.row("replay","B-public")["artifact_qualification"],"passed")
        self.assertEqual(self.row("replay","B-public")["author_independent"],"failed")
        d["input_scope_compliance"]="failed"
        self.assertEqual(self.row("replay","B-public")["artifact_qualification"],"failed")

    def test_unknown_intervention_is_not_zero(self):
        self.trial("replay","B-public")["human"]["author_core_steps"]=None
        self.assertEqual(self.row("replay","B-public")["author_independent"],"unknown")

    def test_equal_budget_and_incomplete_cost(self):
        self.trial("replay","B-public")["resources"]["compute_units"]=101
        self.assertEqual(self.row("replay","B-public")["artifact_qualification"],"failed")
        self.trial("carrier","B-public")["full_cost_attested"]=False
        self.assertEqual(self.row("carrier","B-public")["gates"]["budget"],"unknown")
        self.design("trials")["arms"][0]["budget"]["cost_minor"]=999
        with self.assertRaises(RRAOError):self.run_audit()

    def test_blinding_and_review_disagreement(self):
        d=self.trial("replay","B-public")
        d["review_blinding"]="unblinded"
        self.assertEqual(self.row("replay","B-public")["artifact_qualification"],"failed")
        d["review_blinding"]="blinded";d["reviewer_disagreement"]=True
        self.assertEqual(self.row("replay","B-public")["artifact_qualification"],"unknown")
        d["adjudication_sha256"]="f"*64
        self.assertEqual(self.row("replay","B-public")["artifact_qualification"],"passed")

    def test_novelty_receipt_required(self):
        self.trial("generate","E-autonomous")["novelty_receipt_sha256"]=None
        with self.assertRaises(RRAOError):self.run_audit()

    def test_no_posthoc_missing_required_gates_or_holdout(self):
        c=next(c for c in self.design("trials")["cases"] if c["case_id"]=="application")
        c["holdout_commitment_sha256"]=None
        with self.assertRaises(RRAOError):self.run_audit()
        c["holdout_commitment_sha256"]="a"*64;c["required_checks"].remove("attribution")
        with self.assertRaises(RRAOError):self.run_audit()

    def test_required_quality_cannot_be_not_applicable(self):
        self.trial("replay","B-public")["checks"]["source_fidelity"]="not_applicable"
        with self.assertRaises(RRAOError):self.run_audit()

    def test_frozen_strata_cost_and_candidate_coverage(self):
        t=self.frame("trials")
        r=next(x for x in t["strata"] if x["target_type"]=="author" and x["level"]=="autonomous_generation")
        self.assertEqual(r["baseline_qualified_cases_author_free"]["lower_bound"],frac(1))
        self.assertEqual(r["all_registered_cases_human_core_free"]["lower_bound"],frac(1))
        s=next(x for x in t["arm_strata"] if x["arm_id"]=="B-public" and x["target_type"]=="method")
        self.assertEqual(s["complete_frame_cost_minor"],100)
        self.assertIsNone(s["cost_per_qualified_artifact_minor"])

    def test_author_cut_handoff_and_common_outage(self):
        r=self.model("dependency")
        self.assertEqual(r["fixed_target_weight"],6)
        self.assertEqual(r["author_cut"]["dependency_gap_weight_upper"],6)
        self.assertEqual(r["author_cut_with_handoff"]["dependency_gap_weight_upper"],3)
        v=next(x for x in r["additional_cuts"] if x["cut_id"]=="verifier-outage")
        self.assertEqual(v["with_handoff_and_author_cut"]["dependency_gap_weight_lower"],3)
        self.assertEqual(v["with_handoff_and_author_cut"]["dependency_gap_weight_upper"],6)
        v=next(x for x in r["additional_cuts"] if x["cut_id"]=="common-outage")
        self.assertEqual(v["with_handoff_and_author_cut"]["dependency_gap_weight_lower"],6)

    def test_cut_cannot_regenerate_author(self):
        p=self.event("models-1")["data"]["dependency"]
        p["rules"].append({"rule_id":"regenerate-author","premises":[],"conclusion":"author-live","permission":"allowed"})
        with self.assertRaises(RRAOError):self.run_audit()

    def test_frozen_target_and_handoff_must_be_certain(self):
        p=self.event("models-1")["data"]["dependency"]
        p["rules"][0]["permission"]="unknown"
        with self.assertRaises(RRAOError):self.run_audit()

    def test_ambiguity_refinement_bound(self):
        r=self.model("ambiguity")
        self.assertEqual(r["before"]["conditional_minimax_success_ceiling"],frac(1,4))
        self.assertEqual(r["after"]["conditional_minimax_success_ceiling"],frac(1,2))

    def test_ambiguity_nonpartition_or_assumption_false(self):
        p=self.event("models-1")["data"]["ambiguity"]
        p["mutually_disjoint_acceptable_answers"]=False
        self.assertIsNone(self.model("ambiguity"))
        p["observation_classes_after"]=[["w1","w2"],["w2","w3","w4"]]
        with self.assertRaises(RRAOError):self.run_audit()

    def test_strict_break_even(self):
        r=self.model("economics")
        self.assertEqual(r["break_even_count"],frac(5))
        self.assertEqual(r["first_integer_qualified_count_with_strict_advantage"],6)
        self.assertFalse(r["successor_strictly_cheaper"])
        self.event("models-1")["data"]["economics"]["qualified_output_count"]=6
        self.assertTrue(self.model("economics")["successor_strictly_cheaper"])

    def test_cost_never_substitutes_for_quality_or_rights(self):
        p=self.event("models-1")["data"]["economics"]
        p["same_quality_and_legal_feasibility"]=False
        self.assertIsNone(self.model("economics"))
        p["same_quality_and_legal_feasibility"]=True
        p["successor_unit_cost_minor"]=110
        self.assertIsNone(self.model("economics")["first_integer_qualified_count_with_strict_advantage"])

    def test_continuity_synthetic_success_not_empirical(self):
        r=self.frame("trajectory")
        self.assertEqual(r["minimum_horizon_state"],"passed")
        self.assertEqual(r["conditional_human_core_free_research_series"],"passed")
        self.assertEqual(r["accepted_agent_generated_goal_state"],"passed")
        self.assertFalse(r["actual_recorded_series_candidate"])
        self.assertFalse(r["independent_autonomy_certified"])

    def test_continuity_hash_mismatch_or_author_direction(self):
        cs=self.event("trajectory-1")["data"]["cycles"]
        cs[1]["input_sha256"]="f"*64
        self.assertEqual(self.frame("trajectory")["conditional_human_core_free_research_series"],"failed")
        cs[1]["input_sha256"]=cs[0]["output_sha256"]
        cs[1]["author_new_direction_steps"]=1
        self.assertEqual(self.frame("trajectory")["conditional_human_core_free_research_series"],"failed")

    def test_continuity_duration_negative_result_and_missing_trace(self):
        cs=self.event("trajectory-1")["data"]["cycles"]
        self.design("trajectory")["minimum_span_days"]=30
        self.assertEqual(self.frame("trajectory")["minimum_horizon_state"],"failed")
        self.design("trajectory")["minimum_span_days"]=14
        cs[2]["negative_result_receipt_sha256"]=None
        self.assertEqual(self.frame("trajectory")["conditional_human_core_free_research_series"],"unknown")

    def test_continuity_midseries_initial_intent_not_free(self):
        cs=self.event("trajectory-1")["data"]["cycles"]
        cs[1]["initial_intent_steps"]=1
        self.assertEqual(self.frame("trajectory")["conditional_human_core_free_research_series"],"failed")
        cs[1]["goal_source"]="registered_initial"
        with self.assertRaises(RRAOError):self.run_audit()

    def test_continuity_actual_claim_requires_recorded_basis(self):
        self.observational("trajectory")
        self.assertTrue(self.frame("trajectory")["actual_recorded_series_candidate"])
        self.p["frames"][0]["analysis_basis"]="conditional_scenario"
        self.assertFalse(self.frame("trajectory")["actual_recorded_series_candidate"])

    def test_history_checkpoint_and_same_artifact(self):
        r=self.frame("history")
        self.assertTrue(r["checkpoint_prefix_intact"])
        self.assertEqual(r["entry_count"],2)
        self.assertEqual(r["same_artifact_distinct_contributors"],1)
        late=self.frame("history",LATE)
        self.assertEqual(late["entry_count"],3)
        self.assertEqual(late["corrected_entry_ids"],["e1"])
        self.assertFalse(late["historical_truth_or_legal_authorship_certified"])

    def test_history_mutation_and_rehashed_prefix_rejected(self):
        entries=self.event("history-2")["data"]["entries"]
        entries[1]["contributor_ref"]="rewritten"
        with self.assertRaises(RRAOError):self.run_audit()
        # Even an internally consistent new suffix cannot overwrite the earlier snapshot.
        entries[1]["entry_sha256"]=entry_digest(entries[1])
        entries[2]["previous_sha256"]=entries[1]["entry_sha256"]
        entries[2]["entry_sha256"]=entry_digest(entries[2])
        with self.assertRaises(RRAOError):self.run_audit()

    def test_history_frozen_checkpoint_rejects_rehash(self):
        for eid in ("history-1","history-2"):
            es=self.event(eid)["data"]["entries"]
            es[0]["contributor_ref"]="changed"
            head="0"*64
            for e in es:
                e["previous_sha256"]=head;e["entry_sha256"]=entry_digest(e);head=e["entry_sha256"]
        with self.assertRaises(RRAOError):self.run_audit()

    def test_governance_missing_probe_and_no_live_action(self):
        r=self.frame("governance")
        self.assertEqual(r["required_probe_state"],"unknown")
        self.assertFalse(r["live_action_performed"])
        self.assertFalse(r["actual_recorded_probes_candidate"])
        self.event("governance-1")["data"]["probes"][0]["actual_side_effects"]=True
        with self.assertRaises(RRAOError):self.run_audit()

    def test_governance_denial_failure_not_compensated(self):
        self.event("governance-1")["data"]["probes"][0]["state"]="failed"
        self.assertEqual(self.frame("governance")["required_probe_state"],"failed")

    def test_strict_and_retrospective_correction(self):
        self.assertEqual(self.run_audit()["visible_event_count"],5)
        self.assertEqual(self.run_audit(MID)["visible_event_count"],5)
        self.assertEqual(self.run_audit(MID,"retrospective_reconstruction")["visible_event_count"],7)
        self.assertEqual(self.row("application","B-public",MID)["artifact_qualification"],"unknown")
        self.assertEqual(self.row("application","B-public",MID,"retrospective_reconstruction")["artifact_qualification"],"passed")
        self.assertEqual(self.run_audit(LATE)["active_event_count"],5)

    def test_no_synthetic_promotion_or_actual_basis(self):
        self.p["data_class"]="observational"
        with self.assertRaises(RRAOError):self.run_audit()
        self.p["data_class"]="synthetic";self.p["frames"][0]["analysis_basis"]="recorded_accounting"
        with self.assertRaises(RRAOError):self.run_audit()

    def test_provider_claim_not_measured(self):
        self.observational("trials","provider_claim")
        self.assertIsNone(self.frame("trials"))

    def test_observational_independent_claim_needs_receipt(self):
        self.observational("trials","independent_repeated")
        self.event("trials-1")["assessor_ref"]=None
        with self.assertRaises(RRAOError):self.run_audit()
        self.event("trials-1")["assessor_ref"]="fictional"
        self.event("trials-1")["artifact_sha256"]=None
        with self.assertRaises(RRAOError):self.run_audit()

    def test_cross_frame_revision_and_future_vintage(self):
        self.event("history-2")["supersedes_event_id"]="trials-1"
        with self.assertRaises(RRAOError):self.run_audit()
        self.event("history-2")["supersedes_event_id"]="history-1"
        self.event("trials-1")["source_published_at"]="2026-11-24T23:00:00Z"
        with self.assertRaises(RRAOError):self.run_audit()

    def test_before_registration_and_cli(self):
        self.assertEqual(self.run_audit("2026-10-31")["synthetic_scenario"]["frames"],[])
        r=subprocess.run([sys.executable,"-m","fsl_reflexive.cli","audit","--file",str(FIXTURE),"--as-of",EARLY],
                         cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(r.stdout),self.run_audit())


class ExactChecks(unittest.TestCase):
    def test_closure_against_all_closed_supersets(self):
        nodes=set("abc")
        subsets=[set(x for i,x in enumerate(sorted(nodes)) if mask>>i&1) for mask in range(8)]
        rules=[{"premises":["a"],"conclusion":"b"},{"premises":["b"],"conclusion":"c"},
               {"premises":["a","c"],"conclusion":"b"},{"premises":["c"],"conclusion":"a"}]
        for mask in range(16):
            rs=[r for i,r in enumerate(rules) if mask>>i&1]
            for seed in subsets:
                for blocked in subsets:
                    allowed=nodes-blocked
                    candidates=[s for s in subsets if seed-blocked<=s<=allowed
                                and all(r["conclusion"] in blocked or not set(r["premises"])<=s
                                        or r["conclusion"] in s for r in rs)]
                    self.assertEqual(closure(seed,rs,blocked),set.intersection(*candidates))

    def test_economics_strict_threshold_vs_exhaustive(self):
        for a,b,k in itertools.product(range(6),range(6),range(10)):
            p={"assumed":True,"same_quality_and_legal_feasibility":True,"full_cost_attested":True,
               "baseline_unit_cost_minor":a,"successor_unit_cost_minor":b,"handoff_cost_minor":k,
               "qualified_output_count":1}
            r=economics(p)["conditional_result"]
            want=next((n for n in range(1,12) if k+n*b<n*a),None)
            self.assertEqual(r["first_integer_qualified_count_with_strict_advantage"],want)

    def test_ambiguity_upper_against_all_discrete_policies(self):
        for m in range(2,6):
            worlds=[str(i) for i in range(m)]
            p={"assumed":True,"mutually_disjoint_acceptable_answers":True,"world_ids":worlds,
               "observation_classes_before":[worlds],"observation_classes_after":[[w] for w in worlds]}
            r=ambiguity(p)["conditional_result"]
            # Exhaust all probability masses in units 1/m over m distinct answers.
            best=max(min(Fraction(v,m) for v in weights)
                     for weights in itertools.product(range(m+1),repeat=m) if sum(weights)==m)
            self.assertEqual(r["before"]["conditional_minimax_success_ceiling"],frac(best))
