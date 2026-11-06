"""Synthetic task-horizon protocol regression tests: not real model scores."""
import copy
import math
import unittest
from fsl_timecourse.horizon import HorizonError, horizon_estimate, compare_matched


def make_model(*, cutoff=55, model="fixture-model-v1", scaffold="no-tools"):
    tasks=[]
    for i in range(24):
        minutes=8*1.31**i
        probability=1/(1+math.exp(1.4*math.log(minutes/cutoff)))
        tasks.append({"task_id":f"t{i:02d}","human_expert_minutes":minutes,
                      "attempts":12,"successes":round(12*probability)})
    return {"schema":"fsl/horizon-input/0.5","protocol":{
        "task_set_sha256":"a"*64,"benchmark_version":"fixture-1.0",
        "domain":"coding-reliability","model_key":model,
        "model_revision":"revision-fixture-1","scaffold_key":scaffold,
        "tool_policy_sha256":"b"*64,"prompt_sha256":"c"*64,
        "budget":{"max_total_tokens_per_task":10000,
                  "max_wall_seconds_per_task":600,"max_usd_per_task":3.0},
        "source_url":"https://example.org/synthetic-not-real-source",
        "published_on":"2026-11-07","recorded_on":"2026-11-07",
        "evaluation_mode":"synthetic"},"tasks":tasks}


class HorizonTests(unittest.TestCase):
    def test_reliability_horizons_80_is_shorter_than_50(self):
        result=horizon_estimate(make_model(),bootstrap=100)
        h50=result["horizon"]["0.5"]["human_expert_minutes"]
        h80=result["horizon"]["0.8"]["human_expert_minutes"]
        self.assertIsNotNone(h50)
        self.assertIsNotNone(h80)
        self.assertGreater(h50,h80)
        self.assertEqual(result["n_tasks"],24)
        self.assertEqual(result["evaluation_mode"],"synthetic")

    def test_matched_model_version_comparison_not_general_intelligence(self):
        base=make_model(cutoff=35)
        next_version=make_model(cutoff=88,model="fixture-model-v2")
        result=compare_matched(base,next_version,bootstrap=30)
        self.assertEqual(result["attribution"],"model_revision_difference")
        self.assertIsNone(result["general_intelligence_multiplier"])
        self.assertGreater(result["reliability_horizon_ratios"]["0.5"]["task_horizon_ratio"],1)

    def test_fixed_model_scaffold_ablation_is_separate(self):
        base=make_model(cutoff=35)
        agent=make_model(cutoff=85,scaffold="agent-v1")
        result=compare_matched(base,agent,bootstrap=0)
        self.assertEqual(result["attribution"],"scaffold_or_agent_difference")

    def test_budget_and_task_anchor_changes_refused(self):
        base=make_model()
        b=make_model(model="fixture-model-v2")
        b["protocol"]["budget"]["max_total_tokens_per_task"]=50000
        with self.assertRaises(HorizonError):
            compare_matched(base,b)
        b=make_model(model="fixture-model-v2")
        b["tasks"][0]["human_expert_minutes"]=5
        with self.assertRaises(HorizonError):
            compare_matched(base,b)

    def test_quality_gates(self):
        base=make_model()
        mutations=(
            lambda d:d.update(tasks=d["tasks"][:11]),
            lambda d:d["tasks"][0].update(attempts=1),
            lambda d:d["tasks"][0].update(human_expert_minutes=-1),
            lambda d:d["protocol"].update(source_url="http://untrusted.example"),
        )
        for change in mutations:
            d=copy.deepcopy(base)
            change(d)
            with self.assertRaises(HorizonError):
                horizon_estimate(d,bootstrap=0)

    def test_all_failure_unidentifiable(self):
        d=make_model()
        for row in d["tasks"]:
            row["successes"]=0
        with self.assertRaises(HorizonError):
            horizon_estimate(d)

    def test_bootstrap_deterministic_under_fixed_seed(self):
        a=horizon_estimate(make_model(),bootstrap=100,seed=7)
        b=horizon_estimate(make_model(),bootstrap=100,seed=7)
        self.assertEqual(a,b)


if __name__=="__main__":
    unittest.main()
