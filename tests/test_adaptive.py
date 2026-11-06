"""Offline regression tests for the adaptive temporal ensemble.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import unittest

from fsl_adaptive.engine import forecast, posterior, forecast_variant
from fsl_adaptive.registry import (
    DataError, add_evidence, connect, insert_feedback, insert_forecast, snapshot
)

CONFIG = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "adaptive_scenarios.json")
    .read_text(encoding="utf-8")
)


class AdaptiveTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        # Test-only synthetic fixtures exercising the observational code path;
        # these example.org sources are not admissible scientific evidence.
        self.test_observed_config = copy.deepcopy(CONFIG)
        self.test_observed_config["data_classification"] = "observational"
        self.test_observed_config["baseline"]["source_url"] = "https://example.org/test-baseline"
        for cohort in self.test_observed_config["cohorts"]:
            if cohort["stage"] == "operational":
                cohort["source_url"] = "https://example.org/test-deployment"

    def tearDown(self):
        self.db.close()

    def prediction(self, *, year=2030, asof="2026-11-06",
                   allow_planned=True, target_class="synthetic", target_key="demo"):
        config = self.test_observed_config if target_class == "observational" else CONFIG
        return forecast(self.db, config, as_of=asof, target_year=year,
                        allow_planned=allow_planned,
                        target_key=target_key, target_class=target_class)

    def event(self, eid="e1", day="2026-11-07", value=12000, kind="assumption"):
        return {
            "event_id": eid, "entity_id": "demo-planned-2027", "entity_kind": "site",
            "field": "site.gpus", "value": value, "unit": "GPU",
            "state": "asserted", "source_kind": kind,
            "published_on": day, "recorded_on": day,
        }

    def test_competing_hypotheses_are_independent_of_cognition(self):
        result = self.prediction()
        self.assertEqual(result["cognition"]["inferred_from_model_size"], False)
        self.assertFalse(result["cognition"]["measured"])
        self.assertEqual(result["cognition"]["user_proposed_capability_range"], [2, 3])
        self.assertEqual(len(result["hypotheses"]), 3)
        self.assertEqual(result["ensemble"]["online_update"]["n_disclosed_outcomes"], 0)
        self.assertEqual(result["ensemble"]["online_update"]["state"], "uncalibrated")

    def test_planned_hardware_gated_and_not_pooled(self):
        past = self.prediction(allow_planned=False)
        future = self.prediction(allow_planned=True)
        self.assertTrue(any(h["selected_site_conditional"] for h in future["hypotheses"]))
        self.assertTrue(all(not h["selected_site_conditional"] for h in past["hypotheses"]))
        self.assertGreater(
            future["ensemble"]["weighted_parameter_multiplier"],
            past["ensemble"]["weighted_parameter_multiplier"])
        # A future campus is not automatically a pool of all GPU sites.
        self.assertTrue(all("selected_site_id" in h for h in future["hypotheses"]))

    def test_matured_investment_and_release_lag(self):
        old = self.prediction(year=2026, allow_planned=True)
        newer = self.prediction(year=2030, allow_planned=True)
        for result in (old, newer):
            self.assertTrue(all(h["parameter_multiplier"] <= h["assumed_parameter_ceiling"]
                                for h in result["hypotheses"]))
        self.assertGreater(newer["ensemble"]["weighted_parameter_multiplier"],
                           old["ensemble"]["weighted_parameter_multiplier"])
        for h in newer["hypotheses"]:
            self.assertLess(h["available_hardware_year_after_release_lag"], 2030)

    def test_asof_prevents_revised_information_leak(self):
        baseline = self.prediction(year=2029)
        add_evidence(self.db, self.event(value=1))
        old = self.prediction(year=2029, asof="2026-11-06")
        revised = self.prediction(year=2029, asof="2026-11-08")
        self.assertEqual(old["ensemble"], baseline["ensemble"])
        self.assertNotEqual(revised["input_sha256"], baseline["input_sha256"])
        self.assertTrue(revised["changed_fields"])

    def test_future_effective_stage_does_not_become_operational_early(self):
        event = {
            "event_id": "future-stage", "entity_id": "demo-planned-2027",
            "entity_kind": "site", "field": "site.stage", "value": "operational",
            "state": "asserted", "source_kind": "assumption",
            "published_on": "2026-11-06", "recorded_on": "2026-11-06",
            "effective_on": "2029-01-01",
        }
        add_evidence(self.db, event)
        early, _ = snapshot(self.db, "2026-11-06")
        later, _ = snapshot(self.db, "2029-01-02")
        self.assertNotIn(("demo-planned-2027", "site.stage"), early)
        self.assertEqual(later[("demo-planned-2027", "site.stage")]["value"], "operational")

    def test_explicit_site_units_are_required(self):
        event = self.event()
        event["unit"] = "racks"
        with self.assertRaises(DataError):
            add_evidence(self.db, event)

    def test_retraction_restores_original_config_not_old_fact(self):
        add_evidence(self.db, self.event(value=1))
        add_evidence(self.db, {
            **self.event(eid="e2", day="2026-11-08", value=None),
            "state": "retracted", "supersedes_id": "e1",
        })
        facts, proof = snapshot(self.db, "2026-11-09")
        self.assertNotIn(("demo-planned-2027", "site.gpus"), facts)
        self.assertEqual(len(proof["event_ids"]), 2)
        restored = self.prediction(year=2029, asof="2026-11-09")
        baseline = self.prediction(year=2029, asof="2026-11-06")
        self.assertEqual(restored["ensemble"], baseline["ensemble"])

    def test_wrong_source_and_duplicate_rejected(self):
        with self.assertRaises(DataError):
            add_evidence(self.db, self.event(kind="manufacturer"))
        add_evidence(self.db, self.event())
        with self.assertRaises(sqlite3.IntegrityError):
            add_evidence(self.db, self.event())
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE evidence_events SET note='changed' WHERE event_id='e1'")

    def test_no_observational_forecast_from_synthetic_config(self):
        with self.assertRaises(DataError):
            forecast(self.db, CONFIG, as_of="2026-11-06", target_year=2030,
                     target_key="demo", target_class="observational",
                     allow_planned=True)

    def test_synthetic_forecast_cannot_be_used_for_scoring(self):
        f = self.prediction()
        fid = insert_forecast(self.db, f)
        entry = {
            "feedback_id": "result-1", "forecast_id": fid,
            "observed_multiplier": 4.0, "published_on": "2030-01-01",
            "recorded_on": "2030-01-02",
            "model_source_url": "https://example.org/new-model",
            "baseline_source_url": "https://example.org/base-model",
        }
        with self.assertRaises(DataError):
            insert_feedback(self.db, entry)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0], 0)

    def test_immutable_forecast_and_prequential_learning(self):
        f = self.prediction(year=2028, target_class="observational", target_key="series-x")
        fid = insert_forecast(self.db, f)
        self.assertEqual(insert_forecast(self.db, f), fid)  # idempotent
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM forecasts WHERE forecast_id=?", (fid,))
        near = next(h["parameter_multiplier"] for h in f["hypotheses"]
                    if h["id"] == "sustained_expansion")
        feedback = {
            "feedback_id": "real-public-1", "forecast_id": fid,
            "observed_multiplier": near, "published_on": "2029-03-01",
            "recorded_on": "2029-03-05",
            "model_source_url": "https://example.org/new-model",
            "baseline_source_url": "https://example.org/base-model",
        }
        with self.assertRaises(DataError):
            insert_feedback(self.db, {**feedback, "published_on": "2026-11-01"})
        insert_feedback(self.db, feedback)
        prior = posterior(self.db, "2029-03-02", CONFIG["calibration_group"],
                          [h["id"] for h in CONFIG["hypotheses"]])
        after = posterior(self.db, "2029-03-06", CONFIG["calibration_group"],
                          [h["id"] for h in CONFIG["hypotheses"]])
        self.assertEqual(prior["n_disclosed_outcomes"], 0)
        self.assertEqual(after["n_disclosed_outcomes"], 1)
        self.assertGreater(after["weights"]["sustained_expansion"],
                           prior["weights"]["sustained_expansion"])

    def test_drift_requires_multiple_bad_observations(self):
        for index in (1, 2):
            result = self.prediction(
                year=2028 + index, target_class="observational",
                target_key=f"series-{index}")
            fid = insert_forecast(self.db, result)
            insert_feedback(self.db, {
                "feedback_id": f"outcome-{index}", "forecast_id": fid,
                "observed_multiplier": 100000.0,
                "published_on": f"203{index}-03-01",
                "recorded_on": f"203{index}-03-05",
                "model_source_url": "https://example.org/model",
                "baseline_source_url": "https://example.org/base",
            })
        fitted = posterior(self.db, "2032-05-01", CONFIG["calibration_group"],
                           [h["id"] for h in CONFIG["hypotheses"]])
        self.assertEqual(fitted["n_disclosed_outcomes"], 2)
        self.assertTrue(fitted["drift_alert"])


if __name__ == "__main__":
    unittest.main()
