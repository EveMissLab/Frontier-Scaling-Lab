"""No-network cost accounting and access-limit guards.

All 48-hour mission activity, usage, provider bills and credits are fictional.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import json
from pathlib import Path
import sqlite3
import unittest

from fsl_affordability.ledger import CostError, analyze, connect, save


SOURCE=(Path(__file__).resolve().parent/"fixtures"/
        "affordability_synthetic_48h.json")
EXAMPLE=json.loads(SOURCE.read_text(encoding="utf-8"))


class AffordabilityTests(unittest.TestCase):
    def test_subscription_not_divided_into_fictitious_tokens(self):
        result=analyze(copy.deepcopy(EXAMPLE))
        self.assertEqual(result["billing_mode"],"hybrid")
        self.assertEqual(result["monthly_subscription_outlay_usd"],"200")
        self.assertEqual(result["paid_variable_usd"]["total"],"16")
        self.assertEqual(result["total_monthly_cash_outlay_plus_variable_usd"],"216")
        self.assertEqual(result["allocated_subscription_usd_not_cash_payment"],"20.00")
        self.assertEqual(result["allocated_experiment_cost_usd"],"36.00")
        self.assertEqual(result["included_credits_used_usd_equivalent_not_cash"],"5")
        self.assertEqual(result["remaining_plan_allowance"],"unknown_not_inferred_from_price")
        self.assertIsNone(result["cost_per_independently_verified_result_usd"])

    def test_wall_clock_is_not_active_intelligent_work(self):
        result=analyze(copy.deepcopy(EXAMPLE))
        self.assertEqual(result["wall_hours"],48)
        self.assertEqual(result["observed_active_hours"],8)
        self.assertEqual(result["quota_interruptions"],1)
        self.assertFalse(result["can_sustain_48h_verified"])
        self.assertFalse(result["mission_completed_and_independently_verified"])

    def test_overlapping_activity_not_double_counted(self):
        case=copy.deepcopy(EXAMPLE)
        case["activity_windows"].append({
            "start":"2026-11-07T03:00:00Z","end":"2026-11-07T04:30:00Z",
            "source_url":"https://example.org/synthetic-overlap"})
        result=analyze(case)
        self.assertEqual(result["observed_active_hours"],8.5)

    def test_api_cost_is_rates_times_tokens_not_subscription_allowance(self):
        case=copy.deepcopy(EXAMPLE)
        case["access"].update({
            "run_id":"synthetic-api", "billing_mode":"api",
            "plan_id":"API pay-as-you-go","monthly_subscription_usd":"0"})
        case["charges"]=[
            {"id":"api-tokens","type":"api_tokens",
             "at":"2026-11-07T02:00:00Z",
             "source_url":"https://example.org/synthetic-API-bill",
             "pricing_source_url":"https://developers.openai.com/api/docs/pricing",
             "uncached_input_tokens":8000000,
             "cached_input_tokens":2000000,
             "output_tokens":1000000,
             "usd_per_million":{
                "uncached_input":"2.00","cached_input":"0.10","output":"10.00"}}
        ]
        value=analyze(case)
        self.assertEqual(value["monthly_subscription_outlay_usd"],"0")
        from decimal import Decimal
        self.assertEqual(Decimal(value["paid_variable_usd"]["api_tokens"]),Decimal("26.20"))
        self.assertEqual(Decimal(value["total_monthly_cash_outlay_plus_variable_usd"]),Decimal("26.20"))
        self.assertFalse(value["can_sustain_24h_verified"])

    def test_no_subscriptions_claim_api_token_bill_on_included_route(self):
        case=copy.deepcopy(EXAMPLE)
        case["access"]["billing_mode"]="subscription"
        case["charges"].append({
            "id":"api", "type":"api_tokens","at":"2026-11-07T01:00:00Z",
            "source_url":"https://example.org/bill",
            "pricing_source_url":"https://developers.openai.com/api/docs/pricing",
            "uncached_input_tokens":10,"cached_input_tokens":0,
            "output_tokens":0,
            "usd_per_million":{"uncached_input":"2","cached_input":"0.1","output":"10"}})
        with self.assertRaises(CostError):
            analyze(case)

    def test_unknown_usage_allowance_cannot_be_derived_from_price(self):
        case=copy.deepcopy(EXAMPLE)
        case["access"]["run_id"]="free-tier"
        case["access"]["plan_id"]="Free"
        case["access"]["monthly_subscription_usd"]="0"
        case["charges"]=[]
        value=analyze(case)
        self.assertEqual(value["monthly_subscription_outlay_usd"],"0")
        self.assertEqual(value["remaining_plan_allowance"],"unknown_not_inferred_from_price")
        self.assertFalse(value["can_sustain_48h_verified"])

    def test_invalid_activity_and_future_charges_rejected(self):
        case=copy.deepcopy(EXAMPLE)
        case["activity_windows"][0]["end"]="2026-11-11T00:00:00Z"
        with self.assertRaises(CostError):
            analyze(case)
        case=copy.deepcopy(EXAMPLE)
        case["charges"][0]["at"]="2026-11-10T00:00:00Z"
        with self.assertRaises(CostError):
            analyze(case)

    def test_negative_credits_and_duplicate_charge_rejected(self):
        case=copy.deepcopy(EXAMPLE)
        case["charges"][0]["usd"]="-1.0"
        with self.assertRaises(CostError):
            analyze(case)
        case=copy.deepcopy(EXAMPLE)
        case["charges"].append(copy.deepcopy(case["charges"][0]))
        with self.assertRaises(CostError):
            analyze(case)

    def test_reject_missing_pricing_source_and_wrong_route(self):
        case=copy.deepcopy(EXAMPLE)
        case["access"]["plan_source_url"]=""
        with self.assertRaises(CostError):
            analyze(case)
        case=copy.deepcopy(EXAMPLE)
        case["access"]["billing_mode"]="local"
        with self.assertRaises(CostError):
            analyze(case)

    def test_immutable_persisted_cost_scenarios(self):
        with connect(":memory:") as db:
            report=save(db,copy.deepcopy(EXAMPLE))
            self.assertEqual(report["wall_hours"],48)
            with self.assertRaises(sqlite3.IntegrityError):
                save(db,copy.deepcopy(EXAMPLE))
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE affordability_runs SET plan_id='other'")


if __name__=="__main__":
    unittest.main()
