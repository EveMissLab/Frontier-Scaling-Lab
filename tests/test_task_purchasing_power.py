"""Within-period functional task costs and historical counterfactual safety.

All outcomes, dollar amounts, and provider/model names are synthetic fixtures,
NOT actual 2026 AI performance.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from fsl_economics.comparison import EconomicsError, compare_cohorts
from fsl_economics.historical import historical_scenarios

FIXTURES=Path(__file__).resolve().parent/"fixtures"
CURRENT=json.loads((FIXTURES/"task_purchasing_power_synthetic.json").read_text("utf-8"))
HISTORY=json.loads((FIXTURES/"historical_task_cost_synthetic.json").read_text("utf-8"))


class CrossEraEconomicsTests(unittest.TestCase):
    def test_frontier_and_other_at_same_time_have_distinct_result_and_cost(self):
        res=compare_cohorts(deepcopy(CURRENT))
        self.assertEqual(res["study_design"],"cross_model_matched_runtime")
        self.assertEqual(res["evidence_class"],"synthetic")
        self.assertFalse(res["has_independently_certified_result"])
        self.assertEqual(len(res["cohorts"]),3)
        a,b,c=res["cohorts"]
        self.assertEqual(a["model_class"],"frontier_at_time")
        self.assertEqual(c["model_class"],"other_at_time")
        self.assertEqual(a["reported_accepted"],2)
        self.assertEqual(c["reported_accepted"],1)
        self.assertEqual(Decimal(a["total_cycle_cash_obligation_usd"]),Decimal("215"))
        self.assertEqual(Decimal(a["allocated_experiment_spend_usd"]),Decimal("35"))
        self.assertEqual(Decimal(a["reported_cost_per_accepted_usd"]),Decimal("17.5"))
        self.assertEqual(Decimal(b["reported_cost_per_accepted_usd"]),Decimal("12"))
        self.assertEqual(Decimal(c["reported_cost_per_accepted_usd"]),Decimal("12"))
        self.assertEqual(res["lowest_reported_allocated_cost_cohort"],
                         "synthetic-frontier-api")

    def test_high_subscription_cost_is_not_per_trial_api_rate(self):
        report=compare_cohorts(deepcopy(CURRENT))
        sub=report["cohorts"][0]
        self.assertEqual(Decimal(sub["subscription_monthly_cash_usd"]),Decimal("200"))
        self.assertEqual(Decimal(sub["variable_cash_usd"]),Decimal("15"))
        self.assertNotEqual(Decimal(sub["total_cycle_cash_obligation_usd"]),
                            Decimal(sub["allocated_experiment_spend_usd"]))
        self.assertIn("monthly access obligation",sub["notes"][2])

    def test_no_invented_success_on_missing_or_censored_outcomes(self):
        panel=deepcopy(CURRENT)
        panel["cohorts"][0]["trials"][1]["outcome"]="censored"
        a=compare_cohorts(panel)["cohorts"][0]
        self.assertEqual(a["unresolved_censored"],1)
        self.assertIsNone(a["reported_cost_per_accepted_usd"])
        panel=deepcopy(CURRENT)
        for t in panel["cohorts"][2]["trials"]:
            t["outcome"]="failed_reported"
            t["outcome_sha256"]=None
        c=compare_cohorts(panel)["cohorts"][2]
        self.assertEqual(c["reported_accepted"],0)
        self.assertIsNone(c["reported_accepted_results_per_100_allocated_usd"])

    def test_zero_dollar_success_is_not_infinite_purchasing_power(self):
        panel=deepcopy(CURRENT)
        c=panel["cohorts"][2]
        for t in c["trials"]:
            t["variable_cash_usd"]="0"
        out=compare_cohorts(panel)["cohorts"][2]
        self.assertEqual(out["reported_cost_per_accepted_usd"],"0.000000")
        self.assertIsNone(out["reported_accepted_results_per_100_allocated_usd"])

    def test_same_model_access_requires_same_frozen_model_and_runtime(self):
        panel=deepcopy(CURRENT)
        panel["design"]="same_model_access"
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)
        for c in panel["cohorts"]:
            c["model_id"]="FICTIONAL-SAME-MODEL"
            c["model_revision"]="fixture-fixed-1"
        result=compare_cohorts(panel)
        self.assertEqual(result["scope"],"matched_model_and_runtime_access_comparison")

    def test_cross_model_must_fix_agent_runtime(self):
        panel=deepcopy(CURRENT)
        panel["cohorts"][2]["runtime_sha256"]="1"*64
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)
        panel["design"]="natural_product_path"
        result=compare_cohorts(panel)
        self.assertIn("confounded",result["scope"])

    def test_explicit_source_and_year_month_required(self):
        panel=deepcopy(CURRENT)
        panel["cohorts"][0]["pricing_source_url"]="http://insecure.example"
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)
        panel=deepcopy(CURRENT)
        panel["evaluation_month"]="2026-13"
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)
        panel=deepcopy(CURRENT)
        panel["cohorts"][0]["price_snapshot_on"]="2027-01-01"
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)

    def test_attempt_cost_cannot_be_negative_or_duplicate(self):
        panel=deepcopy(CURRENT)
        panel["cohorts"][0]["trials"][0]["variable_cash_usd"]="-0.01"
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)
        panel=deepcopy(CURRENT)
        panel["cohorts"][0]["trials"][1]["trial_id"]="A1"
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)

    def test_reported_acceptance_needs_artifact_digest(self):
        panel=deepcopy(CURRENT)
        panel["cohorts"][0]["trials"][0]["outcome_sha256"]=None
        with self.assertRaises(EconomicsError):
            compare_cohorts(panel)

    def test_historical_unavailable_is_not_just_high_price(self):
        out=historical_scenarios(deepcopy(HISTORY))
        scenarios={x["scenario_id"]:x for x in out["scenarios"]}
        self.assertEqual(scenarios["2023-impossible"]["status"],
                         "not_feasible_in_original_historical_environment")
        self.assertIsNone(scenarios["2023-impossible"]
                          ["conditional_expected_cost_per_accepted_outcome_usd"])
        self.assertFalse(out["historical_cash_price_not_modern_substitution"] is False)

    def test_unknown_old_model_probability_stays_null(self):
        s=historical_scenarios(deepcopy(HISTORY))["scenarios"][1]
        self.assertEqual(s["status"],"historical_cost_unidentifiable")
        self.assertIsNone(s["hypothetical_success_probability_interval"]["low"])
        self.assertIsNone(s["conditional_expected_cost_per_accepted_outcome_usd"])
        self.assertTrue(s["missing_evidence"])

    def test_conditional_historical_result_is_not_empirical(self):
        s=historical_scenarios(deepcopy(HISTORY))["scenarios"][2]
        self.assertEqual(s["status"],"conditional_counterfactual_range_not_observed")
        self.assertEqual(Decimal(s["conditional_expected_cost_per_accepted_outcome_usd"]
                                 ["lower_usd"]).quantize(Decimal("0.0001")),
                         Decimal("11.4286"))
        self.assertEqual(Decimal(s["conditional_expected_cost_per_accepted_outcome_usd"]
                                 ["upper_usd"]),Decimal("120"))
        self.assertFalse(s["actual_trial_was_replayed"])
        self.assertFalse(s["independently_verified_completion"])

    def test_present_replay_is_not_original_historical_cost(self):
        s=historical_scenarios(deepcopy(HISTORY))["scenarios"][3]
        self.assertEqual(s["status"],"modern_replay_requires_real_trials")
        self.assertEqual(s["price_basis"],"present_day_replay")
        self.assertIsNone(s["conditional_expected_cost_per_accepted_outcome_usd"])

    def test_wrong_price_date_or_model_before_release_rejected(self):
        data=deepcopy(HISTORY)
        data["scenarios"][2]["price_reference_on"]="2026-05-01"
        with self.assertRaises(EconomicsError):
            historical_scenarios(data)
        data=deepcopy(HISTORY)
        data["scenarios"][2]["model_release_on"]="2026-05-01"
        with self.assertRaises(EconomicsError):
            historical_scenarios(data)

    def test_historical_probability_range_and_zero_denominator_safe(self):
        data=deepcopy(HISTORY)
        data["scenarios"][2]["trial_success_probability"]={"low":"0","high":"0.4"}
        result=historical_scenarios(data)["scenarios"][2]
        self.assertIsNone(result["conditional_expected_cost_per_accepted_outcome_usd"]
                          ["upper_usd"])
        self.assertTrue(result["conditional_expected_cost_per_accepted_outcome_usd"]
                        ["upper_not_finitely_bounded"])
        data=deepcopy(HISTORY)
        data["scenarios"][2]["trial_success_probability"]={"low":"0.5","high":"0.3"}
        with self.assertRaises(EconomicsError):
            historical_scenarios(data)

    def test_historical_observations_require_real_trials_in_original_month(self):
        data=deepcopy(HISTORY)
        data["scenarios"][2]["study_mode"]="contemporaneous_historical_observation"
        with self.assertRaises(EconomicsError):
            historical_scenarios(data)

    def test_invalid_model_availability_input_rejected(self):
        data=deepcopy(HISTORY)
        data["scenarios"][2]["model_accessible_then"]="yes"
        with self.assertRaises(EconomicsError):
            historical_scenarios(data)
        data=deepcopy(HISTORY)
        data["scenarios"][2]["required_tools_accessible_then"]=1
        with self.assertRaises(EconomicsError):
            historical_scenarios(data)


if __name__=="__main__":
    unittest.main()
