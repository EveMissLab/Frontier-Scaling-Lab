"""Agent-origin event bridge: replay, role segregation and privacy tests.

All artifacts and model behaviors in this file are synthetic.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from fsl_functional.store import add_event, add_run, add_spec
from fsl_interventions.agent_bridge import ingest, load_jsonl
from fsl_interventions.ledger import (
    InterventionError, add_protocol, connect, oracle_commitment, preregister
)


FIXTURE=json.loads((Path(__file__).parent/"fixtures"/
                    "g2_intervention_synthetic.json").read_text(encoding="utf-8"))


class AgentIntakeTests(unittest.TestCase):
    def setUp(self):
        self.db=connect(":memory:")
        add_spec(self.db,FIXTURE["spec"])
        add_run(self.db,FIXTURE["run"])
        add_protocol(self.db,FIXTURE["protocol"])
        case=FIXTURE["preregistered_cases"][0]
        secret=FIXTURE["synthetic_oracles"][case["case_id"]]
        preregister(self.db,dict(
            case,sealed_oracle_sha256=oracle_commitment(
                case["case_id"],secret["expected_action"],
                secret["expected_goal_sha256"],secret["oracle_nonce"],secret["case_type"])))
        for name in ("user-intent","pert-goal"):
            add_event(self.db,next(x for x in FIXTURE["mission_events"]
                                   if x["event_id"]==name))

    def tearDown(self):
        self.db.close()

    def decision(self):
        return copy.deepcopy(next(x for x in FIXTURE["mission_events"]
                                  if x["event_id"]=="decision-case-replan"))

    def ingest(self,events,when="2026-01-03T09:20:00Z"):
        return ingest(self.db,run_id=FIXTURE["run"]["run_id"],events=events,
                      collector_at=when,protocol_id=FIXTURE["protocol"]["protocol_id"])

    def test_real_agent_hook_binds_only_blind_precommitted_change(self):
        result=self.ingest([self.decision()])
        self.assertEqual(result["events_created"],["decision-case-replan"])
        self.assertEqual(result["blinded_cases_bound"],["case-replan"])
        self.assertFalse(result["user_or_evaluator_verdicts_written"])
        self.assertFalse(result["oracle_answers_visible_to_agent"])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM g2_adjudications").fetchone()[0],0)

    def test_replay_is_idempotent_and_never_replaces_a_choice(self):
        first=self.ingest([self.decision()])
        same=self.ingest([self.decision()])
        self.assertEqual(first["blinded_cases_bound"],["case-replan"])
        self.assertEqual(same["events_created"],[])
        self.assertEqual(same["idempotent_replays"],["decision-case-replan"])
        self.assertEqual(same["blinded_cases_bound"],[])
        edited=self.decision()
        edited["payload"]["choice"]="maintain"
        with self.assertRaises(InterventionError):
            self.ingest([edited])

    def test_user_and_reviewer_impersonation_is_forbidden(self):
        user=copy.deepcopy(next(x for x in FIXTURE["mission_events"]
                                if x["event_id"]=="pert-goal"))
        reviewer=copy.deepcopy(next(x for x in FIXTURE["mission_events"]
                                    if x["event_id"]=="judge-case-replan"))
        for item in (user,reviewer):
            with self.assertRaises(InterventionError):
                self.ingest([item])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM g2_bound_decisions").fetchone()[0],0)

    def test_private_payload_fields_cannot_be_stored(self):
        item=self.decision()
        item["payload"]["oracle_nonce"]="SECRET_NOT_TO_SHARE"
        with self.assertRaises(InterventionError):
            self.ingest([item])
        item=self.decision()
        item["payload"]["raw_user_prompt"]="sensitive personal user detail"
        with self.assertRaises(InterventionError):
            self.ingest([item])

    def test_no_future_or_cross_mission_events(self):
        with self.assertRaises(InterventionError):
            self.ingest([self.decision()],when="2026-01-03T08:00:00Z")
        invalid=self.decision()
        invalid["run_id"]="unrelated-project"
        with self.assertRaises(InterventionError):
            self.ingest([invalid])

    def test_no_decision_without_independent_perturbation(self):
        # A preregistration must exist AND the real user/environment event
        # must already have been recorded before the AI's choice is bound.
        self.db.execute("PRAGMA foreign_keys=ON")
        case=FIXTURE["preregistered_cases"][1]
        secret=FIXTURE["synthetic_oracles"][case["case_id"]]
        preregister(self.db,dict(
            case,sealed_oracle_sha256=oracle_commitment(
                case["case_id"],secret["expected_action"],
                secret["expected_goal_sha256"],secret["oracle_nonce"],secret["case_type"])))
        decision=copy.deepcopy(next(x for x in FIXTURE["mission_events"]
                                    if x["event_id"]=="decision-case-maintain"))
        with self.assertRaises(InterventionError):
            self.ingest([decision],when="2026-01-05T09:20:00Z")
        self.assertIsNone(self.db.execute(
            "SELECT event_id FROM functional_events WHERE event_id=?",
            ("decision-case-maintain",)).fetchone())

    def test_validated_batch_rejects_evaluator_line_before_any_write(self):
        progress=self.decision()
        other=copy.deepcopy(progress)
        other["event_id"]="independent-not-allowed"
        other["actor"]="evaluator"
        with self.assertRaises(InterventionError):
            self.ingest([progress,other])
        self.assertIsNone(self.db.execute(
            "SELECT event_id FROM functional_events WHERE event_id=?",
            ("decision-case-replan",)).fetchone())

    def test_jsonl_works_with_bounded_bytes_and_rejects_bad_lines(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"agent-events.jsonl"
            path.write_text(json.dumps(self.decision())+"\n",encoding="utf-8")
            self.assertEqual(len(load_jsonl(path)),1)
            self.assertEqual(self.ingest(load_jsonl(path))["blinded_cases_bound"],
                             ["case-replan"])
            with self.assertRaises(InterventionError):
                load_jsonl(path,max_bytes=5)
            path.write_text("{bad json\n",encoding="utf-8")
            with self.assertRaises(InterventionError):
                load_jsonl(path)


if __name__=="__main__":
    unittest.main()
