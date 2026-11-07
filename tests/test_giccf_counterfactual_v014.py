"""Offline regression tests: no fabricated years, no history rewriting.

All fixture events are SYNTHETIC and imply no actual model capabilities.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from fsl_civilization.counterfactual import (
    CounterfactualError, audit, load_protocol, utc_timestamp,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "giccf_counterfactual_synthetic_v0.14.json"


class TestGICCFCounterfactualV014(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_protocol()
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_protocol_explicitly_separates_two_counterfactual_worlds(self):
        worlds = self.protocol["scenario_kinds"]
        self.assertEqual(set(worlds), {"never_ai_trajectory", "no_ai_after_anchor"})
        self.assertTrue(self.protocol["data_principles"]["no_automatic_future_year"])

    def test_asof_prior_to_revision_preserves_original(self):
        r = audit(self.fixture, as_of="2026-11-07T08:00:00Z")
        self.assertEqual(r["visible_definition_events"], 1)
        self.assertEqual(r["visible_assessment_events"], 1)
        self.assertEqual(r["active_assertions"][0]["assessment_id"], "synthetic-counterfactual-a1")
        self.assertIsNone(r["active_assertions"][0]["future_year_range"])

    def test_later_assessment_supersedes_but_does_not_delete_history(self):
        r = audit(self.fixture, as_of="2026-11-07T18:00:00Z")
        self.assertEqual(r["all_definition_events"], 2)
        self.assertEqual(r["all_assessment_events"], 2)
        self.assertEqual(r["visible_assessment_events"], 2)
        self.assertEqual(r["current_assessments_after_revision"], 1)
        self.assertEqual(r["active_assertions"][0]["assessment_id"], "synthetic-counterfactual-a2")
        self.assertIsNone(r["certified_counterfactual_year"])
        self.assertIsNone(r["universal_superhuman_score"])
        self.assertFalse(r["external_certification"])

    def test_date_only_cutoff_is_explicit_end_of_day_utc(self):
        r = audit(self.fixture, as_of="2026-11-07")
        self.assertEqual(r["visible_definition_events"], 2)
        self.assertEqual(r["current_assessments_after_revision"], 1)

    def test_noncatalog_indicator_rejected(self):
        broken = copy.deepcopy(self.fixture)
        broken["assessment_events"][0]["comparison_contract"]["linked_indicator_ids"] = ["NOT-99"]
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_same_definition_cannot_be_silently_rewritten(self):
        broken = copy.deepcopy(self.fixture)
        broken["definition_events"][1]["version"] = 8
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_cannot_erase_recorded_predecessor(self):
        broken = copy.deepcopy(self.fixture)
        broken["definition_events"].pop(0)
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_never_ai_world_rejects_legacy_ai_knowledge_as_unmarked_baseline(self):
        broken = copy.deepcopy(self.fixture)
        broken["assessment_events"][0]["scenario"]["knowledge_policy"] = "ai_legacy_explicitly_acknowledged"
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_synthetic_cannot_claim_ai_lead(self):
        broken = copy.deepcopy(self.fixture)
        broken["assessment_events"][0]["lead_label"] = "plausible_contemporary_lead"
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_no_human_failure_data_does_not_prove_impossibility(self):
        broken = copy.deepcopy(self.fixture)
        broken["assessment_events"][0]["no_ai_human_current"]["status"] = "no_documented_success"
        r = audit(broken)
        self.assertEqual(r["lead_label_counts"], {"unassessed": 1})

    def test_future_year_must_have_explicit_model_and_bounds(self):
        broken = copy.deepcopy(self.fixture)
        broken["assessment_events"][0]["no_ai_human_future"]["conditional_year_range"] = 2040
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_historical_dependencies_unresolved_reject_year_claim(self):
        broken = copy.deepcopy(self.fixture)
        broken["assessment_events"][0]["no_ai_human_future"]["conditional_year_range"] = {
            "earliest_year": 2030, "latest_year": 2050,
            "method_id": "toy-conditional", "assumptions": ["not observed"]
        }
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_scenario_conditional_range_is_never_certified_date(self):
        amended = copy.deepcopy(self.fixture)
        a = amended["assessment_events"][1]
        a["scenario"]["kind"] = "no_ai_after_anchor"
        a["scenario"]["knowledge_policy"] = "ai_legacy_explicitly_acknowledged"
        a["no_ai_human_future"]["status"] = "possible_conditional"
        a["no_ai_human_future"]["conditional_year_range"] = {
            "earliest_year": 2030, "latest_year": 2050,
            "method_id": "toy-scenario", "assumptions": [
                "No new AI after the anchor", "Future non-AI instruments may improve"
            ]
        }
        r = audit(amended)
        self.assertIsNone(r["certified_counterfactual_year"])
        self.assertEqual(r["active_assertions"][0]["future_year_range"]["earliest_year"], 2030)

    def test_cannot_backdate_new_definition(self):
        broken = copy.deepcopy(self.fixture)
        broken["definition_events"][1]["recorded_at"] = "2026-11-06T23:00:00Z"
        with self.assertRaises(CounterfactualError):
            audit(broken)

    def test_no_timezone_naive_asof(self):
        with self.assertRaises(CounterfactualError):
            utc_timestamp("2026-11-07T03:00:00")


if __name__ == "__main__":
    unittest.main()
