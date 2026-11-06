"""Historical market facts must not be promoted into task-completion results.

This dataset contains dated, primary-source provider *announcement claims*
and a few point-in-time price quotations, not agent outcome experiments.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from fsl_history.catalog import CatalogError, validate, timeline, period_matrix

DATA=json.loads((Path(__file__).resolve().parent.parent/"data"/
        "official_ai_history_2024_2026_v0.9.json").read_text("utf-8"))


class HistoricalCatalogTests(unittest.TestCase):
    def test_minimum_real_primary_source_coverage_2024_2025_2026(self):
        result=validate(DATA)
        self.assertEqual(result["schema"],"fsl/historical-release-catalog/v0.9")
        self.assertGreaterEqual(result["source_count"],30)
        self.assertGreaterEqual(result["event_count"],40)
        self.assertEqual(result["providers"],
                         ["anthropic","deepseek","google","openai","xai"])
        self.assertEqual(result["years"],["2024","2025","2026"])
        self.assertEqual(result["reviewed_on"],"2026-11-07")

    def test_strict_2024_does_not_use_sources_first_seen_by_fsl_in_2026(self):
        out=timeline(DATA,as_of="2024-12-31",mode="strict_known_at_time")
        self.assertEqual(out["included_count"],0)
        self.assertFalse(any(x["admissible_to_original_forecast"]
                             for x in out["events"]))

    def test_retrospective_2024_recovers_publications_without_forecast_claim(self):
        out=timeline(DATA,as_of="2024-12-31",mode="retrospective")
        events=[x for x in out["events"] if x["included"]]
        self.assertGreaterEqual(len(events),6)
        self.assertEqual({x["provider"] for x in events},
                         {"openai","anthropic","google","xai","deepseek"})
        self.assertTrue(all(x["time_status"]==
                            "historically_published_reconstructed_later" for x in events))
        self.assertTrue(all(not x["admissible_to_original_forecast"] for x in events))

    def test_provider_launch_pricing_is_point_in_time_not_2026_rate(self):
        e=timeline(DATA,as_of="2026-11-07")["events"]
        sonnet=next(x for x in e if
                    x["event_id"]=="2024-anthropic-sonnet35-api-rate")
        self.assertEqual(sonnet["price_quote_valid_only_on"],"2024-06-21")
        self.assertEqual(Decimal(sonnet["price"]["uncached_input"]),Decimal("3"))
        self.assertEqual(Decimal(sonnet["price"]["output"]),Decimal("15"))
        self.assertIsNone(sonnet["price"]["cached_input"])

    def test_alias_and_dated_snapshot_identity_not_interchangeable(self):
        events=timeline(DATA,as_of="2026-11-07")["events"]
        v3=next(x for x in events if x["event_id"]=="2024-deepseek-v3")
        self.assertEqual(v3["identifier_kind"],"api_alias")
        shutdown=next(x for x in events if
                      x["event_id"]=="2026-openai-gpt4o-2024-snapshot-shutdown")
        self.assertEqual(shutdown["identifier_kind"],"dated_snapshot")
        self.assertEqual(shutdown["kind"],"model_retirement")
        self.assertEqual(shutdown["occurred_on"],"2026-10-23")
        self.assertNotEqual(shutdown["model_key"],"gpt-4o")

    def test_2026_11_retrospective_market_matrix_not_task_rankings(self):
        result=period_matrix(DATA,month_ends=[
            "2024-12-31","2025-12-31","2026-11-07"])
        self.assertEqual(len(result["periods"]),3)
        for period in result["periods"]:
            self.assertEqual(len(period["provider_rows"]),5)
            for r in period["provider_rows"]:
                self.assertIsNone(r["actual_48h_agent_completions"])
                self.assertIsNone(r["actual_subscription_quota_at_cutoff"])
                self.assertIsNone(r["historical_price_valid_through_cutoff"])
                candidate=r["latest_dated_announcement_candidate"]
                if candidate is not None:
                    self.assertIsNone(candidate["frontier_model_classification"])
                    self.assertIsNone(candidate["currently_accessible"])
                    self.assertIsNone(candidate["cost_per_accepted_task_usd"])
                self.assertTrue(all(
                    item["now_or_at_period_end_available"] is None
                    for item in r["dated_introductions"]))
        self.assertTrue(result["no_task_completion_scores_inferred"])

    def test_dated_announcements_after_cutoff_not_visible(self):
        r=timeline(DATA,as_of="2024-05-13",mode="retrospective")
        self.assertFalse(next(x for x in r["events"] if
                      x["event_id"]=="2024-anthropic-sonnet35")["included"])
        self.assertTrue(next(x for x in r["events"] if
                      x["event_id"]=="2024-openai-gpt4o")["included"])

    def test_2026_point_prices_have_actual_source_and_no_extension(self):
        e=timeline(DATA,as_of="2026-11-07")["events"]
        terra=next(x for x in e if
                   x["event_id"]=="2026-openai-terra61-price")
        self.assertEqual(Decimal(terra["price"]["cached_input"]),Decimal("0.05"))
        self.assertEqual(terra["price_quote_valid_only_on"],"2026-10-26")
        self.assertFalse(terra["functional_G1_to_G4_measured"])

    def test_source_provider_mismatch_and_duplicate_source_rejected(self):
        bad=deepcopy(DATA)
        bad["events"][0]["provider"]="anthropic"
        with self.assertRaises(CatalogError):validate(bad)
        bad=deepcopy(DATA)
        bad["sources"].append(deepcopy(bad["sources"][0]))
        with self.assertRaises(CatalogError):validate(bad)

    def test_price_events_need_complete_unit_and_no_negative_rates(self):
        bad=deepcopy(DATA)
        e=next(x for x in bad["events"] if x["kind"]=="api_price_quote")
        e["price"]["currency"]="NTD"
        with self.assertRaises(CatalogError):validate(bad)
        bad=deepcopy(DATA)
        e=next(x for x in bad["events"] if x["kind"]=="api_price_quote")
        e["price"]["uncached_input"]="-5"
        with self.assertRaises(CatalogError):validate(bad)
        bad=deepcopy(DATA)
        e=next(x for x in bad["events"] if x["kind"]=="api_price_quote")
        e["price"]["validity"]="unbounded"
        with self.assertRaises(CatalogError):validate(bad)

    def test_price_cannot_be_smuggled_into_model_release(self):
        bad=deepcopy(DATA)
        rate=next(x["price"] for x in bad["events"] if x["kind"]=="api_price_quote")
        row=next(x for x in bad["events"] if x["kind"]=="model_announcement")
        row["price"]=rate
        with self.assertRaises(CatalogError):validate(bad)

    def test_2027_dates_or_2024_fake_collection_rejected(self):
        bad=deepcopy(DATA)
        bad["events"][0]["occurred_on"]="2027-11-07"
        with self.assertRaises(CatalogError):validate(bad)
        bad=deepcopy(DATA)
        bad["sources"][0]["first_captured_on"]="2024-01-01"
        with self.assertRaises(CatalogError):validate(bad)

    def test_malformed_calendar_timezone_not_normalized_silently(self):
        bad=deepcopy(DATA)
        bad["sources"][0]["published_on"]="2024-02-15T00:00:00Z"
        with self.assertRaises(CatalogError):validate(bad)
        bad=deepcopy(DATA)
        bad["catalog_review_timezone"]="UTC"
        with self.assertRaises(CatalogError):validate(bad)

    def test_model_release_does_not_prove_24h_agent_or_aaa_game(self):
        out=timeline(DATA,as_of="2026-11-07")
        self.assertEqual(out["independently_verified_autonomous_completion_count"],0)
        self.assertTrue(all(not x["functional_G1_to_G4_measured"]
                            for x in out["events"]))

    def test_unknown_future_source_modes_rejected(self):
        with self.assertRaises(CatalogError):
            timeline(DATA,as_of="2026-11-07",mode="invented_truth")
        with self.assertRaises(CatalogError):
            period_matrix(DATA,month_ends=["2024-12-31","2024-12-31"])


if __name__=="__main__":
    unittest.main()
