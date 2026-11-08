"""FSL v0.19: source-vintage, US-China, Taiwan and frontier-cost scope tests.

No test infers political advice, a model-capability winner, or country-level ROI.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import unittest

from fsl_strategy.registry import StrategyStudyError, load_data, replay, validate


class FrontierGeopoliticsAndCostV019Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo, cls.cost = load_data()

    def altered(self):
        return copy.deepcopy(self.geo), copy.deepcopy(self.cost)

    def test_catalog_has_separate_geopolitics_and_cost_dimensions(self):
        m = validate(self.geo, self.cost)
        self.assertEqual((m["geo_axes"], m["geo_indicators"]), (8, 40))
        self.assertEqual((m["cost_axes"], m["cost_indicators"]), (9, 45))
        self.assertEqual((m["source_count"], m["cases"], m["cost_buckets"],
                          m["strategies"], m["cost_observations"]), (7, 7, 13, 8, 3))

    def test_first_capture_is_2026_11_08_not_prior_known_model(self):
        r = replay(self.geo, self.cost, as_of="2026-11-07")
        self.assertEqual(r["visible_geopolitical_claims"], 0)
        self.assertEqual(r["visible_cost_source_claims"], 0)

    def test_retrospective_is_explicit_and_not_backdated(self):
        r = replay(self.geo, self.cost, as_of="2026-11-07",
                   mode="retrospective_reconstruction")
        self.assertEqual(r["visible_geopolitical_claims"], 7)
        self.assertEqual(r["visible_cost_source_claims"], 3)

    def test_all_records_visible_by_research_date(self):
        r = replay(self.geo, self.cost, as_of="2026-11-08")
        self.assertEqual(r["visible_geopolitical_claims"], 7)
        self.assertEqual(r["visible_cost_source_claims"], 3)
        self.assertIsNone(r["taiwan_country_policy_recommendation"])

    def test_stanford_month_precision_does_not_forge_release_day(self):
        s = next(s for s in self.geo["source_registry"]
                 if s["id"] == "stanford-ai-index-2026")
        self.assertIsNone(s["publication_date"])
        self.assertEqual(s["publication_period"], "2026-04")
        self.assertEqual(s["known_by"], "2026-04-30")
        r = replay(self.geo, self.cost, as_of="2026-04-15",
                   mode="retrospective_reconstruction")
        self.assertNotIn("geo-us-cn-private-ai-investment-2025",
                         r["geopolitical_claim_ids"])

    def test_us_china_2025_private_investment_is_not_total_AI_spending(self):
        r = replay(self.geo, self.cost, as_of="2026-11-08")
        values = r["reported_private_2025_investment"]
        self.assertEqual({x["region"]:x["value"] for x in values},
                         {"US":285.88,"CN":12.41})
        self.assertIsNone(r["full_country_AI_spending_estimate"])
        self.assertIsNone(r["us_china_global_capability_winner"])

    def test_no_overclaim_of_independent_validation(self):
        self.assertTrue(all(x["verified_independent_outcome"] is False
                            for x in self.geo["cases"]))

    def test_bis_export_control_is_conditional_2026_license(self):
        e = next(x for x in self.geo["cases"] if x["metric_name"] == "chip_export_license_case_by_case")
        self.assertEqual(e["source_id"], "us-bis-2026-01-15")
        self.assertIn("逐案", e["interpretation_zh"])

    def test_china_five_year_plan_is_policy_not_capacity_measurement(self):
        e = next(x for x in self.geo["cases"]
                 if x["metric_name"] == "semiconductor_AI_self_reliance_policy")
        self.assertEqual(e["type"], "documented_policy_intent")
        self.assertEqual(e["measured_values"], [])

    def test_taiwan_does_develop_and_train_models(self):
        e = next(x for x in self.geo["cases"] if x["id"] == "geo-taiwan-TAIDE-2602")
        self.assertEqual(e["type"], "documented_model_release")
        self.assertEqual(e["measured_values"][0]["value"], 12)
        self.assertIn("Gemma-3-12B", e["interpretation_zh"])

    def test_national_policy_and_provider_model_not_same_as_global_frontier(self):
        paths = {x["id"]:x for x in self.cost["policy_strategy_options"]}
        self.assertIn("open_weight_specialized_training", paths)
        self.assertIn("full_scratch_global_frontier", paths)
        self.assertIn("sovereign_regional_foundation", paths)
        self.assertNotEqual(paths["full_scratch_global_frontier"]["base_model_route"],
                            paths["open_weight_specialized_training"]["base_model_route"])

    def test_original_small_architecture_is_still_a_research_path(self):
        x = next(x for x in self.cost["policy_strategy_options"]
                 if x["id"] == "original_small_architecture_lab")
        self.assertEqual(x["base_model_route"], "small_original_research")

    def test_cashflow_sovereign_value_and_public_value_not_added_as_one_number(self):
        r = replay(self.geo, self.cost, as_of="2026-11-08")
        self.assertIsNone(r["frontier_model_training_roi_estimate"])
        self.assertFalse(r["sovereign_value_converted_to_company_cashflow"])

    def test_cloud_hardware_and_equipment_accounting_are_distinct(self):
        buckets = {x["id"]:x for x in self.cost["accounting_buckets"]}
        self.assertIn("cloud_rental", buckets)
        self.assertIn("hardware_infrastructure", buckets)
        self.assertIn("avoid_double_count", buckets["cloud_rental"])
        self.assertIn("avoid_double_count", buckets["hardware_infrastructure"])

    def test_epoch_historical_trend_not_real_2027_cost(self):
        x = next(x for x in self.cost["dated_cost_observations"]
                 if x["id"] == "epoch-2024-training-trend")
        self.assertEqual(x["kind"], "historical_cost_model")
        self.assertEqual(x["event_period"], "2016–2024 estimated")
        self.assertEqual(x["value"], 2.4)
        self.assertIn("conditional", x["scope_limit"])

    def test_reuters_forecast_not_one_training_run_bill(self):
        x = next(x for x in self.cost["dated_cost_observations"]
                 if x["id"] == "reuters-2026-cashflow")
        self.assertEqual(x["kind"], "financial_forward_projection")
        self.assertIsNone(x["value"])

    def test_change_stanford_month_to_fake_day_rejected(self):
        geo, econ = self.altered()
        s = next(x for x in geo["source_registry"] if x["id"] == "stanford-ai-index-2026")
        s["publication_date"] = "2026-04-01"
        with self.assertRaises(StrategyStudyError):
            validate(geo, econ)

    def test_source_cannot_be_captured_before_publication(self):
        geo, econ = self.altered()
        s = next(x for x in geo["source_registry"] if x["id"] == "taiwan-taide-2026-02-13")
        s["first_FSL_captured_on"] = "2026-01-01"
        with self.assertRaises(StrategyStudyError):
            validate(geo, econ)

    def test_duplicate_or_unknown_geopolitical_source_rejected(self):
        geo, econ = self.altered()
        geo["cases"][0]["source_id"] = "nonexistent-source"
        with self.assertRaises(StrategyStudyError):
            validate(geo, econ)

    def test_no_unmeasured_private_investment_rescoped_as_all_AI(self):
        geo, econ = self.altered()
        e = next(x for x in geo["cases"] if x["metric_name"] == "private_AI_investment")
        e["type"] = "national_total_AI_expenditure"
        with self.assertRaises(StrategyStudyError):
            validate(geo, econ)

    def test_cost_bucket_repeated_rejected(self):
        geo, econ = self.altered()
        econ["accounting_buckets"].append(copy.deepcopy(econ["accounting_buckets"][0]))
        with self.assertRaises(StrategyStudyError):
            validate(geo, econ)

    def test_epoch_cost_projection_cannot_be_recast_as_2027_spending(self):
        geo, econ = self.altered()
        e = next(x for x in econ["dated_cost_observations"]
                 if x["id"] == "epoch-2024-training-trend")
        e["event_period"] = "actual_2027"
        with self.assertRaises(StrategyStudyError):
            validate(geo, econ)

    def test_invalid_date_and_mode_rejected(self):
        for kwargs in ({"as_of":"2026-11-44"}, {"as_of":"2026-11-08","mode":"prescient"}):
            with self.assertRaises(StrategyStudyError):
                replay(self.geo, self.cost, **kwargs)

    def test_no_actual_country_strategy_asserted_without_source(self):
        vals = {s["actual_country_choice"]
                for s in self.cost["policy_strategy_options"]}
        self.assertTrue(vals <= {
            "not_asserted", "counterfactual_option_only",
            "documented_taiwan_TAIDE_example","documented_TW_semiconductor_strength"
        })


if __name__ == "__main__":
    unittest.main()
