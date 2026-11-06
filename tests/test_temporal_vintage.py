"""UTC vs Taipei, publication vs observation, and dated historical-price tests.

Official 2024 release and 2026 source-capture dates are separately grounded;
all multi-day Agent examples are synthetic, never real capability claims.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from fsl_economics.timeaxis import (
    TemporalError, audit_asof, validate_catalog, validate_mission_clock
)

ROOT=Path(__file__).resolve().parent.parent
SOURCES=json.loads((ROOT/"data"/
    "verified_release_and_price_vintage_2026-11-07.json").read_text(encoding="utf-8"))
MISSION=json.loads((ROOT/"tests"/"fixtures"/
    "mission_clock_synthetic_2026-11-07.json").read_text(encoding="utf-8"))


class TemporalResearchTests(unittest.TestCase):
    def test_original_publication_and_2026_collection_remain_separate(self):
        rows=validate_catalog(SOURCES)
        self.assertEqual(len(rows),5)
        example=next(x for x in rows if x["kind"]=="model_release")
        self.assertEqual(example["event_effective_on"],"2024-05-13")
        self.assertEqual(example["first_captured_on"],"2026-11-07")
        self.assertEqual(example["source_grade"],"provider_primary")

    def test_2024_strict_cutoff_cannot_use_information_first_collected_2026(self):
        result=audit_asof(SOURCES,as_of="2024-05-13",
                          mode="strict_known_at_time")
        self.assertTrue(all(not row["included_for_requested_mode"]
                            for row in result["rows"]))
        self.assertFalse(result["rows"][0]["admissible_to_previously_issued_forecast"])
        self.assertEqual(result["rows"][0]["asof_status"],
                         "published_then_but_captured_by_fsl_later")
        self.assertTrue(result["historical_forecast_reconstruction_permitted"])

    def test_2024_retrospective_release_date_is_not_an_issued_forecast(self):
        result=audit_asof(SOURCES,as_of="2024-05-13",
                          mode="retrospective_reconstruction")
        known=[x for x in result["rows"] if x["included_for_requested_mode"]]
        self.assertEqual(len(known),2)
        self.assertTrue(all(not x["admissible_to_previously_issued_forecast"]
                            for x in known))
        self.assertFalse(result["historical_forecast_reconstruction_permitted"])

    def test_sonnet_historical_quote_on_exact_release_day(self):
        result=audit_asof(SOURCES,as_of="2024-06-21",
                          mode="retrospective_reconstruction")
        record=next(x for x in result["rows"] if x["kind"]=="price_quote")
        self.assertEqual(record["asof_status"],
                         "published_then_but_captured_by_fsl_later")
        self.assertTrue(record["retrospective_historical_publication_supported"])
        self.assertTrue(record["day_precision_ambiguous_within_same_day"])

    def test_do_not_carry_2024_launch_price_as_2026_market_price(self):
        result=audit_asof(SOURCES,as_of="2026-11-07",
                          mode="strict_known_at_time")
        record=next(x for x in result["rows"] if x["kind"]=="price_quote")
        self.assertEqual(record["asof_status"],
                         "historical_point_price_not_verified_for_later_date")
        self.assertFalse(record["included_for_requested_mode"])
        self.assertTrue(any(x["kind"]=="model_shutdown" and
                            x["included_for_requested_mode"]
                            for x in result["rows"]))

    def test_source_publication_and_capture_cannot_be_backdated(self):
        source=deepcopy(SOURCES)
        source["assertions"][0]["first_captured_on"]="2024-01-01"
        with self.assertRaises(TemporalError):
            validate_catalog(source)
        source=deepcopy(SOURCES)
        source["catalog_checked_on"]="2024-01-01"
        with self.assertRaises(TemporalError):
            validate_catalog(source)

    def test_source_deadline_and_unknown_precision(self):
        source=deepcopy(SOURCES)
        source["assertions"][0]["published_on"]="2024-05-13T00:00:00Z"
        with self.assertRaises(TemporalError):
            validate_catalog(source)
        source=deepcopy(SOURCES)
        source["assertions"][0]["effective_until"]="2020-01-01"
        with self.assertRaises(TemporalError):
            validate_catalog(source)
        with self.assertRaises(TemporalError):
            audit_asof(SOURCES,as_of="2026-11-07T12:00:00Z")

    def test_mission_timezone_converts_to_utc_without_changing_raw_source(self):
        report=validate_mission_clock(MISSION)
        self.assertEqual(report["elapsed_execution_hours"],47.5)
        self.assertEqual(report["original_timestamps"]["execution_started_at"],
                         "2026-11-04T00:00:00+08:00")
        self.assertEqual(report["utc_timestamps"]["execution_started_at"],
                         "2026-11-03T16:00:00+00:00")
        self.assertTrue(report["price_vintage_backfilled_from_after_run_start"])
        self.assertFalse(report["price_vintage_admissible_at_run_start"])
        self.assertFalse(report["48h_continuous_autonomy_certified"])
        self.assertFalse(report["final_functional_work_independently_verified"])

    def test_missing_finish_is_censored_not_zero_duration(self):
        mission=deepcopy(MISSION)
        mission["execution_finished_at"]=None
        mission["accepted_at"]=None
        report=validate_mission_clock(mission)
        self.assertIsNone(report["elapsed_execution_hours"])
        self.assertIsNone(report["goal_to_outcome_hours"])
        self.assertFalse(report["24h_continuous_autonomy_certified"])

    def test_cannot_accept_before_finish_or_log_future_finish(self):
        mission=deepcopy(MISSION)
        mission["accepted_at"]="2026-11-04T18:00:00+08:00"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission)
        mission=deepcopy(MISSION)
        mission["execution_finished_at"]="2026-11-08T00:00:00+08:00"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission)

    def test_mission_cannot_precede_model_release_or_pricing(self):
        mission=deepcopy(MISSION)
        mission["model_first_available_on"]="2026-11-06"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission)
        mission=deepcopy(MISSION)
        mission["pricing_effective_on"]="2026-11-06"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission)

    def test_price_evidence_cannot_appear_in_the_future(self):
        mission=deepcopy(MISSION)
        mission["price_first_captured_on"]="2026-11-09"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission)

    def test_obs_future_collector_cutoff_rejected(self):
        mission=deepcopy(MISSION)
        mission["evidence_class"]="observational"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission,checked_at="2026-11-06T00:00:00Z")
        result=validate_mission_clock(
            mission,checked_at="2026-11-08T00:00:00Z")
        self.assertFalse(result["48h_continuous_autonomy_certified"])

    def test_timezone_naive_mission_cannot_fake_duration(self):
        mission=deepcopy(MISSION)
        mission["execution_started_at"]="2026-11-04T00:00:00"
        with self.assertRaises(TemporalError):
            validate_mission_clock(mission)

    def test_day_precision_is_never_silently_converted_to_midnight_utc(self):
        result=audit_asof(SOURCES,as_of="2026-11-07")
        self.assertEqual(result["date_precision"],
                         "calendar_day_not_invented_utc_midnight")
        self.assertEqual(result["catalog_reviewed_on_Asia_Taipei"],"2026-11-07")


if __name__=="__main__":
    unittest.main()
