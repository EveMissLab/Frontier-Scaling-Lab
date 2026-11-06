"""Offline G2 preregistration, held-out adaptation and real-outcome guard tests.

All mission dates, reviewers and actions in this file are synthetic and do NOT
demonstrate a long-running autonomous Agent.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import unittest

from fsl_functional.store import add_event, add_run, add_spec
from fsl_interventions.ledger import (
    InterventionError, add_protocol, bind_choice, connect, evaluate,
    oracle_commitment, preregister, reveal,
)


FIXTURE=json.loads((Path(__file__).resolve().parent/"fixtures"/
                    "g2_intervention_synthetic.json").read_text(encoding="utf-8"))
CUTOFF="2026-01-18T00:00:00Z"


def replay(db, fixture=FIXTURE, *, do_bind=True, do_reveal=True):
    add_spec(db,fixture["spec"])
    add_run(db,fixture["run"])
    add_protocol(db,fixture["protocol"])
    for case in fixture["preregistered_cases"]:
        oracle=fixture["synthetic_oracles"][case["case_id"]]
        commitment=oracle_commitment(case["case_id"],oracle["expected_action"],
                                      oracle["expected_goal_sha256"],oracle["oracle_nonce"])
        preregister(db,dict(case,sealed_oracle_sha256=commitment))
    for event in fixture["mission_events"]:
        add_event(db,event)
    if do_bind:
        for b in fixture["bindings"]:
            bind_choice(db,b)
    if do_reveal:
        for item in fixture["reveals"]:
            reveal(db,item)


class InterventionTests(unittest.TestCase):
    def setUp(self):
        self.db=connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_four_case_synthetic_protocol_does_not_certify_ability(self):
        replay(self.db)
        result=evaluate(self.db,FIXTURE["protocol"]["protocol_id"],CUTOFF)
        self.assertEqual(result["total_cases_preregistered"],4)
        self.assertTrue(result["four_case_recorded_outcomes_satisfied"])
        self.assertFalse(result["G2_recorded_conditions_satisfied"])
        self.assertFalse(result["G2_externally_verified"])
        self.assertFalse(result["adaptive_model_weights_updated"])
        self.assertTrue(result["g1_prerequisite"]["recorded_conditions_satisfied"])
        self.assertFalse(result["g1_prerequisite"]["independently_verified"])
        for cls,row in result["four_scenario_case_coverage"].items():
            self.assertEqual(row["tested"],1,cls)
            self.assertEqual(row["recorded_pass"],1,cls)
        self.assertTrue(all(c["recorded_outcome_gate"] for c in result["case_records"]))

    def test_sealed_answer_does_not_leak_in_predecision_audit(self):
        replay(self.db,do_bind=False,do_reveal=False)
        old=evaluate(self.db,FIXTURE["protocol"]["protocol_id"],
                     "2026-01-04T00:00:00Z")
        self.assertEqual(old["total_cases_preregistered"],4)
        self.assertIsNone(old["case_records"][0]["revealed_case_type"])
        self.assertTrue(old["case_records"][0]["expected_action_hidden_until_reveal"])
        self.assertIsNone(old["case_records"][0]["choice_matches_precommitted_oracle"])
        self.assertFalse(old["four_case_recorded_outcomes_satisfied"])

    def test_oracle_reveal_requires_correct_salt_and_final_judgement(self):
        replay(self.db,do_reveal=False)
        wrong=dict(FIXTURE["reveals"][0],oracle_nonce="f"*32)
        with self.assertRaises(InterventionError):
            reveal(self.db,wrong)
        wrong=dict(FIXTURE["reveals"][0],adjudicated_at="2026-01-04T01:00:00Z")
        with self.assertRaises(InterventionError):
            reveal(self.db,wrong)
        self.assertTrue(reveal(self.db,FIXTURE["reveals"][0])
                        ["choice_matches_prior_oracle"])

    def test_cannot_preregister_after_perturbation_was_logged(self):
        add_spec(self.db,FIXTURE["spec"])
        add_run(self.db,FIXTURE["run"])
        add_protocol(self.db,FIXTURE["protocol"])
        for event in FIXTURE["mission_events"]:
            if event["event_id"]=="pert-goal":
                add_event(self.db,event)
                break
        case=FIXTURE["preregistered_cases"][0]
        secret=FIXTURE["synthetic_oracles"][case["case_id"]]
        commitment=oracle_commitment(case["case_id"],secret["expected_action"],
                    secret["expected_goal_sha256"],secret["oracle_nonce"])
        with self.assertRaises(InterventionError):
            preregister(self.db,dict(case,sealed_oracle_sha256=commitment))

    def test_wrong_perturbation_event_cannot_be_bound(self):
        replay(self.db,do_bind=False,do_reveal=False)
        bad=dict(FIXTURE["bindings"][0],decision_event_id="decision-case-maintain")
        with self.assertRaises(InterventionError):
            bind_choice(self.db,bad)

    def test_unrecorded_decision_cannot_be_bound_before_timestamp(self):
        replay(self.db,do_bind=False,do_reveal=False)
        early=dict(FIXTURE["bindings"][0],bound_at="2026-01-03T09:01:00Z")
        with self.assertRaises(InterventionError):
            bind_choice(self.db,early)

    def test_outcome_deadline_cannot_be_changed_after_decision(self):
        fixture=copy.deepcopy(FIXTURE)
        for case in fixture["preregistered_cases"]:
            case["outcome_due_at"]="2026-01-20T00:00:00Z"
        replay(self.db,fixture,do_reveal=False)
        with self.assertRaises(InterventionError):
            reveal(self.db,fixture["reveals"][0])

    def test_correct_decision_but_after_deadline_does_not_count(self):
        fixture=copy.deepcopy(FIXTURE)
        fixture["preregistered_cases"][0]["outcome_due_at"]="2026-01-03T08:30:00Z"
        # The delayed choice is still logged for retrospective failure.
        # The other cases retain their normal dates and oracle commitments.
        replay(self.db,fixture)
        result=evaluate(self.db,fixture["protocol"]["protocol_id"],CUTOFF)
        case=next(x for x in result["case_records"] if x["case_id"]=="case-replan")
        self.assertFalse(case["decision_before_preregistered_deadline"])
        self.assertFalse(case["recorded_outcome_gate"])

    def test_wrong_action_remains_failure_even_if_goal_accepted(self):
        fixture=copy.deepcopy(FIXTURE)
        wrong=next(e for e in fixture["mission_events"]
                   if e["event_id"]=="decision-case-replan")
        wrong["payload"]["choice"]="maintain"
        grade=next(e for e in fixture["mission_events"]
                   if e["event_id"]=="judge-case-replan")
        grade["payload"]["correct"]=False
        replay(self.db,fixture)
        result=evaluate(self.db,fixture["protocol"]["protocol_id"],CUTOFF)
        failed=next(x for x in result["case_records"] if x["case_id"]=="case-replan")
        self.assertFalse(failed["choice_matches_precommitted_oracle"])
        self.assertFalse(failed["recorded_outcome_gate"])
        self.assertTrue(failed["accepted_final_user_goal_matched"])
        self.assertFalse(result["four_case_recorded_outcomes_satisfied"])

    def test_final_acceptance_of_wrong_goal_never_counts(self):
        fixture=copy.deepcopy(FIXTURE)
        final=next(e for e in fixture["mission_events"]
                   if e["event_id"]=="accepted-final-goal")
        final["payload"]["goal_sha256"]="a"*64
        replay(self.db,fixture)
        result=evaluate(self.db,fixture["protocol"]["protocol_id"],CUTOFF)
        self.assertFalse(result["four_case_recorded_outcomes_satisfied"])
        self.assertTrue(all(not c["accepted_final_user_goal_matched"]
                            for c in result["case_records"]))

    def test_no_declarations_based_on_premature_acceptance(self):
        replay(self.db,do_bind=True,do_reveal=False)
        result=evaluate(self.db,FIXTURE["protocol"]["protocol_id"],
                        "2026-01-10T00:00:00Z")
        self.assertFalse(result["four_case_recorded_outcomes_satisfied"])
        self.assertTrue(all(not c["oracle_revealed"] for c in result["case_records"]))

    def test_fake_reviewer_correctness_cannot_overrule_hidden_answer(self):
        fixture=copy.deepcopy(FIXTURE)
        judgement=next(e for e in fixture["mission_events"]
                       if e["event_id"]=="judge-case-maintain")
        judgement["payload"]["correct"]=False
        with self.assertRaises(InterventionError):
            replay(self.db,fixture)

    def test_cannot_reveal_action_inconsistent_with_hidden_case_type(self):
        replay(self.db,do_reveal=False)
        item=dict(FIXTURE["reveals"][0],declared_case_type="irrelevant_noise")
        with self.assertRaises(InterventionError):
            reveal(self.db,item)

    def test_non_reversible_append_only_reviews_and_binding(self):
        replay(self.db)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM g2_adjudications")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE g2_precommitted_cases SET sealed_oracle_sha256='x'")
        with self.assertRaises(sqlite3.IntegrityError):
            reveal(self.db,FIXTURE["reveals"][0])

    def test_oracle_salt_validation(self):
        with self.assertRaises(InterventionError):
            oracle_commitment("case", "replan", "b"*64, "abc")
        with self.assertRaises(InterventionError):
            oracle_commitment("case", "random_action", "b"*64, "1"*32)

    def test_public_event_history_is_a_result_not_policy_for_the_agent(self):
        replay(self.db)
        result=evaluate(self.db,FIXTURE["protocol"]["protocol_id"],CUTOFF)
        self.assertIsNone(result.get("agent_training_instruction"))
        self.assertFalse(result["G2_externally_verified"])
        self.assertEqual(result["assessment_status"],"synthetic_demonstration_only")


if __name__=="__main__":
    unittest.main()
