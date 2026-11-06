"""Synthetic only: matched-budget success-vector regression tests. Apache-2.0."""
import tempfile
import sqlite3
import unittest

from fsl_timecourse.controlled import (
    TrialError, compare, connect, insert_protocol, insert_trial, vector
)


def protocol(axis="coding",pid="p-coding"):
    return {
        "protocol_id":pid,"axis":axis,"benchmark_key":"synthetic/task-suite",
        "benchmark_version":"1.0.0","task_set_sha256":"a"*64,
        "scoring":"binary_task_success","max_tokens_per_task":2000,
        "model_prompt_policy":"fixed_preamble_v1",
        "tool_setup":"agent_vs_base_predeclared",
        "source_url":"https://example.org/synthetic-protocol",
        "recorded_on":"2026-11-06",
    }


def trial(tid,pid,success,*,mode="base",model="synthetic/model-v1",
          d="2026-11-07",data_class="synthetic"):
    return {
        "trial_id":tid,"protocol_id":pid,"model_key":model,
        "model_version":"1.0.0","run_mode":mode,
        "evaluated_on":d,"published_on":d,"recorded_on":d,
        "data_class":data_class,
        "verification":"synthetic" if data_class=="synthetic" else "reported",
        "success_count":success,"task_count":100,
        "source_url":"https://example.org/synthetic-trials",
    }


class ControlledTests(unittest.TestCase):
    def setUp(self):
        self.db=connect(":memory:")
        insert_protocol(self.db,protocol())
        self.db.execute("PRAGMA foreign_keys=ON")

    def tearDown(self):
        self.db.close()

    def test_task_success_ratio_is_not_general_cognition(self):
        insert_trial(self.db,trial("base","p-coding",20))
        insert_trial(self.db,trial("new","p-coding",40,model="synthetic/model-v2"))
        result=compare(self.db,baseline_id="base",target_id="new",as_of="2026-11-07")
        self.assertEqual(result["comparison_kind"],"model_or_version_change")
        self.assertAlmostEqual(result["task_success_rate_ratio_descriptive"],2)
        self.assertAlmostEqual(result["task_success_percentage_point_change"],20)
        self.assertIsNone(result["capability_multiplier"])
        self.assertFalse(result["cognitive_2_to_3x_claim_licensed"])

    def test_agent_effect_is_separate_from_base_weights(self):
        insert_trial(self.db,trial("base","p-coding",25))
        insert_trial(self.db,trial("agent","p-coding",60,mode="agent"))
        result=compare(self.db,baseline_id="base",target_id="agent",as_of="2026-11-07")
        self.assertEqual(result["comparison_kind"],"agent_system_change")
        insert_trial(self.db,trial("wrong-agent","p-coding",55,mode="agent",
                                   model="synthetic/model-v2"))
        with self.assertRaises(TrialError):
            compare(self.db,baseline_id="base",target_id="wrong-agent",
                    as_of="2026-11-07")

    def test_future_data_unavailable_for_earlier_forecast(self):
        insert_trial(self.db,trial("base","p-coding",25))
        insert_trial(self.db,trial("new","p-coding",40,model="synthetic/model-v2"))
        with self.assertRaises(TrialError):
            compare(self.db,baseline_id="base",target_id="new",as_of="2026-11-06")

    def test_protocol_units_and_task_panel_must_match(self):
        bad=protocol("math","p-math")
        bad["max_tokens_per_task"]=0
        with self.assertRaises(TrialError):
            insert_protocol(self.db,bad)
        bad["max_tokens_per_task"]=2000
        bad["task_set_sha256"]="nonsha"
        with self.assertRaises(TrialError):
            insert_protocol(self.db,bad)
        insert_protocol(self.db,protocol("math","p-math"))
        insert_trial(self.db,trial("a","p-coding",25))
        insert_trial(self.db,trial("b","p-math",40,model="synthetic/model-v2"))
        with self.assertRaises(TrialError):
            compare(self.db,baseline_id="a",target_id="b",as_of="2026-11-07")

    def test_task_panels_must_have_equal_count(self):
        insert_trial(self.db,trial("a","p-coding",25))
        other=trial("b","p-coding",45,model="synthetic/model-v2")
        other["task_count"]=101
        insert_trial(self.db,other)
        with self.assertRaises(TrialError):
            compare(self.db,baseline_id="a",target_id="b",as_of="2026-11-07")

    def test_protocols_and_trials_are_immutable(self):
        insert_trial(self.db,trial("a","p-coding",25))
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM controlled_trials WHERE trial_id='a'")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE controlled_protocols SET axis='math'")
        with self.assertRaises(sqlite3.IntegrityError):
            insert_trial(self.db,trial("a","p-coding",25))

    def test_no_mixed_synthetic_real_pairs(self):
        insert_trial(self.db,trial("a","p-coding",25))
        insert_trial(self.db,trial("b","p-coding",40,model="synthetic/model-v2",
                                   data_class="observational"))
        with self.assertRaises(TrialError):
            compare(self.db,baseline_id="a",target_id="b",as_of="2026-11-07")

    def test_vector_keeps_task_dimensions_separate(self):
        insert_protocol(self.db,protocol("math","p-math"))
        for pid,axis in (("p-coding","coding"),("p-math","math")):
            insert_trial(self.db,trial(axis+"-base",pid,20))
            insert_trial(self.db,trial(axis+"-future",pid,40,
                                       model="synthetic/model-v2"))
        comps=[
            {"baseline_id":"coding-base","target_id":"coding-future"},
            {"baseline_id":"math-base","target_id":"math-future"},
        ]
        res=vector(self.db,comparisons=comps,as_of="2026-11-07")
        self.assertEqual(res["dimensions"],2)
        self.assertIsNone(res["global_intelligence_score"])
        self.assertEqual(res["identification"],"synthetic_demonstration_only")
        with self.assertRaises(TrialError):
            vector(self.db,comparisons=comps+[comps[0]],as_of="2026-11-07")


if __name__=="__main__":
    unittest.main()
