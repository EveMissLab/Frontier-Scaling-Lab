import hashlib
import json
import subprocess
import sys
import unittest

from fsl_epistemic.audit import KIFError, ROOT, audit, load_catalog, load_json

FIXTURE=ROOT/"tests/fixtures/kif_synthetic_v0.22.json"
EARLY="2026-11-24T10:30:00Z"
MID="2026-11-24T11:30:00Z"
LATE="2026-11-24T12:30:00Z"


def frac(n,d):
    return {"numerator":n,"denominator":d}


class KIFTests(unittest.TestCase):
    def setUp(self):
        self.p=load_json(FIXTURE)

    def run_audit(self,at=EARLY,mode="strict_known_at_time"):
        return audit(self.p,as_of=at,mode=mode)

    def syn(self,at=EARLY,mode="strict_known_at_time"):
        return self.run_audit(at,mode)["synthetic_scenario"]

    def row(self,case,arm,at=EARLY,mode="strict_known_at_time"):
        return next(r for r in self.syn(at,mode)["trial_rows"] if r["case_id"]==case and r["arm_id"]==arm)

    def event(self,eid):
        return next(e for e in self.p["events"] if e["event_id"]==eid)

    def flow(self):
        return self.event("flow-1")["data"]

    def population(self):
        return self.event("pop-1")["data"]

    def observational(self,tier="repeatable_test"):
        # Deliberate fictional records for structural negative controls only.
        self.p["data_class"]="observational"
        for e in self.p["events"]:
            e["evidence_tier"]=tier
            e["source_url"]="https://example.invalid/fixture-only"
            e["artifact_sha256"]="a"*64
            if tier=="independent_repeated":
                e["assessor_ref"]="synthetic-test-assessor-ref"

    def test_catalog_unmeasured_and_original_oil_ids(self):
        c=load_catalog()
        self.assertEqual(len(c["axes"]),14)
        self.assertEqual([a["id"] for a in c["axes"][:6]],["O1","O2","O3","O4","O5","O6"])
        self.assertTrue(all(a["value"] is None for a in c["axes"]))
        for s in c["source_papers"]:
            b=(ROOT/s["path"]).read_bytes()
            self.assertEqual(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(),s["git_blob_sha"])

    def test_synthetic_is_not_empirical(self):
        r=self.run_audit()
        self.assertIsNone(r["recorded_observational_assertions"])
        for k in ("independent_empirical_certification","causal_effect_certified","global_novelty_certified","neural_mechanism_certified"):
            self.assertFalse(r[k])
        self.assertIsNone(r["universal_intelligence_score"])
        self.assertIsNone(r["human_replacement_rate"])

    def test_formal_validity_not_contextual_application(self):
        r=self.row("application","ai")
        self.assertEqual(r["recorded_quality_checks"]["formal_validity"],"passed")
        self.assertEqual(r["admissible_quality_checks"]["formal_validity"],"passed")
        self.assertEqual(r["recorded_quality_checks"]["O5"],"failed")
        self.assertEqual(r["qualified_answer"],"failed")

    def test_appropriate_abstention_is_not_answer(self):
        r=self.row("abstain","human")
        self.assertEqual(r["qualified_abstain_or_escalate"],"passed")
        self.assertEqual(r["qualified_answer"],"not_applicable")
        self.assertEqual(self.row("abstain","ai")["qualified_abstain_or_escalate"],"failed")
        self.assertEqual(self.row("escalate","ai")["qualified_abstain_or_escalate"],"passed")

    def test_missing_trial_and_leakage(self):
        self.assertEqual(self.row("theory","hybrid")["qualified_answer"],"unknown")
        r=self.row("theory","ai")
        self.assertEqual(r["holdout_integrity_state"],"unknown")
        self.assertEqual(r["qualified_answer"],"unknown")
        self.assertEqual(r["recorded_quality_checks"]["scoped_originality"],"passed")
        self.assertEqual(r["admissible_quality_checks"]["scoped_originality"],"unknown")
        self.event("theory-ai")["data"]["leakage"]="confirmed"
        self.assertEqual(self.row("theory","ai")["qualified_answer"],"failed")

    def test_seen_leakage_not_ignored(self):
        self.event("interpretation-ai")["data"]["leakage"]="confirmed"
        self.assertEqual(self.row("interpretation","ai")["qualified_answer"],"failed")

    def test_matched_cost_and_incomplete_frame(self):
        a=self.syn()["arm_summaries"]
        self.assertEqual(a["human"]["complete_answer_frame_cost_minor"],5600)
        self.assertEqual(a["human"]["cost_per_qualified_answer_minor"],frac(2800,3))
        self.assertIsNone(a["ai"]["cost_per_qualified_answer_minor"])
        self.assertIsNone(a["hybrid"]["cost_per_qualified_answer_minor"])

    def test_quality_dimensions_not_joint_marginal(self):
        r=self.syn()["arm_summaries"]["ai"]
        self.assertEqual(r["answer_quality"]["frame_n"],7)
        self.assertEqual(r["answer_quality"]["passed"],4)
        self.assertEqual(r["answer_quality"]["unknown"],1)
        self.assertEqual(r["answer_quality"]["lower_bound"],frac(4,7))
        self.assertEqual(r["answer_quality"]["upper_bound"],frac(5,7))
        self.assertEqual(r["quality_coordinates"]["formal_validity"]["passed"],2)
        self.assertEqual(r["quality_coordinates"]["O4"]["failed"],1)

    def test_pair_unknown_not_failure(self):
        pairs=self.syn()["paired_outcomes"]
        p=next(x for x in pairs if x["arm_a"]=="ai" and x["arm_b"]=="human" and x["outcome"]=="qualified_answer")
        self.assertEqual(p["only_a_pass"],1)
        self.assertEqual(p["only_b_pass"],2)
        self.assertEqual(p["unknown_pairs"],1)
        self.assertEqual(p["both_pass"],3)
        self.assertEqual(p["not_applicable"],2)

    def test_replay_revision_and_cutoff(self):
        self.assertEqual(self.run_audit(EARLY)["visible_event_count"],28)
        self.assertEqual(self.run_audit(MID)["visible_event_count"],28)
        self.assertEqual(self.run_audit(MID,"retrospective_reconstruction")["visible_event_count"],29)
        self.assertEqual(self.row("application","ai",MID)["qualified_answer"],"failed")
        self.assertEqual(self.row("application","ai",MID,"retrospective_reconstruction")["qualified_answer"],"passed")
        self.assertEqual(self.run_audit(LATE)["active_event_count"],28)

    def test_before_registration_no_frame(self):
        r=self.syn("2026-11-16")
        self.assertEqual(r["trial_rows"],[])
        self.assertEqual(r["knowledge_flow_frames"],[])
        self.assertEqual(r["population_frames"],[])

    def test_budget_equal_caps_and_excess(self):
        self.event("proof-ai")["data"]["resources"]["compute_units"]=101
        self.assertEqual(self.row("proof","ai")["budget_state"],"failed")
        self.assertEqual(self.row("proof","ai")["qualified_answer"],"failed")
        self.p["arms"][0]["budget"]["cost_minor"]=9999
        with self.assertRaises(KIFError):
            self.run_audit()
        self.p["comparison_mode"]="actual_cost"
        self.run_audit()

    def test_incomplete_cost_is_not_budget_pass(self):
        self.event("proof-human")["data"]["full_cost_attested"]=False
        self.assertEqual(self.row("proof","human")["budget_state"],"unknown")
        self.assertIsNone(self.syn()["arm_summaries"]["human"]["cost_per_qualified_answer_minor"])

    def test_review_blinding_and_disagreement(self):
        d=self.event("proof-ai")["data"]
        d["review_blinding"]="unblinded"
        self.assertEqual(self.row("proof","ai")["qualified_answer"],"failed")
        d["review_blinding"]="blinded"
        d["reviewer_disagreement"]=True
        self.assertEqual(self.row("proof","ai")["qualified_answer"],"unknown")
        d["adjudication_sha256"]="f"*64
        self.assertEqual(self.row("proof","ai")["qualified_answer"],"passed")

    def test_missing_formal_receipt_rejected(self):
        self.event("proof-ai")["data"]["formal_receipt_sha256"]=None
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_missing_originality_receipt_rejected(self):
        self.event("theory-ai")["data"]["originality_receipt_sha256"]=None
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_required_checks_and_high_risk(self):
        self.p["cases"][1]["required_checks"].remove("safety")
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_optional_safety_failure_blocks(self):
        self.event("proof-ai")["data"]["checks"]["safety"]="failed"
        self.assertEqual(self.row("proof","ai")["qualified_answer"],"failed")

    def test_no_not_applicable_for_required(self):
        self.event("proof-ai")["data"]["checks"]["O1"]="not_applicable"
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_scope_and_holdout_commitment(self):
        self.p["cases"][0]["heldout_commitment_sha256"]=None
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_no_delivery_not_qualified(self):
        d=self.event("proof-ai")["data"]
        d["disposition"]="no_delivery"
        d["output_sha256"]=None
        d["checks"]={k:("failed" if k in self.p["cases"][0]["required_checks"] else "not_applicable") for k in d["checks"]}
        self.assertEqual(self.row("proof","ai")["qualified_answer"],"failed")

    def test_flow_queue_bottleneck_and_dedup(self):
        r=self.syn()["knowledge_flow_frames"][0]
        self.assertEqual(r["valid_per_raw"],frac(4,5))
        self.assertEqual(r["observed_backlog_change"],85)
        self.assertEqual(r["conditional_ideal_closing"],105)
        self.assertEqual(r["conditional_serial_capacity"],35)
        self.assertEqual(r["conditional_bottleneck_stages"],["I"])

    def test_flow_invalid_conservation(self):
        self.flow()["closing_backlog"]=106
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_flow_invalid_stage_or_demand(self):
        for k,v in (("deduplicated_valid",161),("new_demand_units",141),("terminal_outputs",36)):
            with self.subTest(k=k):
                old=self.flow()[k]
                self.flow()[k]=v
                with self.assertRaises(KIFError):
                    self.run_audit()
                self.flow()[k]=old

    def test_partial_serial_bound(self):
        self.flow()["stage_capacities"]["B"]=None
        self.flow()["terminal_outputs"]=36
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_flow_no_model_no_inferred_bottleneck(self):
        f=self.p["flow_frames"][0]
        f["queue_model"]="accounting_only"
        f["serial_model"]="not_assumed"
        r=self.syn()["knowledge_flow_frames"][0]
        self.assertIsNone(r["conditional_serial_capacity"])
        self.assertIsNone(r["conditional_ideal_closing"])
        self.assertEqual(r["observed_backlog_change"],85)

    def test_population_selection_decomposition(self):
        p=self.syn()["population_frames"][0]
        self.assertEqual(p["confirmed_retained_baseline_mean_difference"],frac(10,1))
        d=p["complete_case_population_decomposition"]
        self.assertEqual(d["baseline_mean"],frac(40,1))
        self.assertEqual(d["followup_mean"],frac(130,3))
        self.assertEqual(d["mean_change"],frac(10,3))
        self.assertEqual(d["exit_selection"],frac(20,3))
        self.assertEqual(d["entry_selection"],frac(-20,3))
        self.assertEqual(d["retained_individual_change"],frac(10,3))
        self.assertFalse(p["motivation_inferred_from_exit"])

    def test_population_lost_followup_bounds(self):
        d=self.population()
        d["exited_n"]=20
        d["lost_n"]=20
        d["exit_baseline_sum"]=500
        d["lost_baseline_sum"]=500
        r=self.syn()["population_frames"][0]
        self.assertEqual(r["retention_lower"],frac(3,5))
        self.assertEqual(r["retention_upper"],frac(4,5))
        self.assertIsNone(r["complete_case_population_decomposition"])

    def test_population_invalid_count_and_score_mass(self):
        for k,v in (("retained_n",61),("baseline_sum",3999),("entrant_sum",3001),("role_transition_n",61)):
            with self.subTest(k=k):
                old=self.population()[k]
                self.population()[k]=v
                with self.assertRaises(KIFError):
                    self.run_audit()
                self.population()[k]=old

    def test_population_small_cell_and_inference_suppression(self):
        self.observational()
        d=self.population()
        d["role_transition_n"]=3
        with self.assertRaises(KIFError):
            self.run_audit()
        d["role_transition_n"]=None
        d["retained_n"]=None
        d["exited_n"]=95
        d["retained_baseline_sum"]=None
        d["retained_followup_sum"]=None
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_population_no_personal_fields(self):
        self.population()["individual_name"]="not permitted"
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_no_synthetic_promotion(self):
        self.p["data_class"]="observational"
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_provider_claims_do_not_score(self):
        self.observational("provider_claim")
        r=self.run_audit()
        self.assertIsNone(r["synthetic_scenario"])
        a=r["recorded_observational_assertions"]
        self.assertTrue(all(x["required_quality_state"]=="unknown" for x in a["trial_rows"]))
        self.assertIsNone(a["knowledge_flow_frames"][0]["observed_backlog_change"])
        self.assertIsNone(a["population_frames"][0]["complete_case_population_decomposition"])

    def test_observational_requires_receipt_and_assessor(self):
        self.observational("independent_repeated")
        self.event("proof-ai")["assessor_ref"]=None
        with self.assertRaises(KIFError):
            self.run_audit()
        self.event("proof-ai")["assessor_ref"]="test-only"
        self.event("proof-ai")["artifact_sha256"]=None
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_no_correction_fork_or_cross_arm(self):
        self.event("application-ai-revision")["supersedes_event_id"]="application-human"
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_no_future_vintage(self):
        self.event("proof-ai")["source_published_at"]="2026-11-24T07:00:00Z"
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_late_registration(self):
        self.p["registered_at"]="2026-11-18T00:00:00Z"
        with self.assertRaises(KIFError):
            self.run_audit()

    def test_cli_roundtrip(self):
        r=subprocess.run([sys.executable,"-m","fsl_epistemic.cli","audit","--file",str(FIXTURE),"--as-of",EARLY],
                         cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(r.stdout),self.run_audit())
