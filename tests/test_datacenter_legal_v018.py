"""FSL v0.18 legal and regulatory source-vintage regression suite.

Does not test law enforcement or infer regulation -> AI-buildout causality.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import copy
import unittest
from fsl_legal.registry import LegalStudyError, load_data, validate, replay


class DataCenterLegalV018Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_data()
        cls.case_id = {e["id"]:i for i,e in enumerate(cls.snapshot["legal_events"])}

    def altered(self, event_id, **updates):
        d = copy.deepcopy(self.snapshot)
        d["legal_events"][self.case_id[event_id]].update(updates)
        return d

    def test_catalog_and_sources_do_not_claim_effect(self):
        x = validate(self.snapshot)
        self.assertEqual((x["axes"], x["indicators"], x["sources"], x["events"]),
                         (12, 60, 7, 7))
        self.assertFalse(self.snapshot["forecasts"]["impact_causality_certified"])

    def test_2026_11_07_strict_cannot_see_2026_11_08_FSL_capture(self):
        r = replay(self.snapshot, as_of="2026-11-07")
        self.assertEqual(r["visible_source_events"], 0)

    def test_2026_11_07_retrospective_uses_late_captured_historical_sources(self):
        r = replay(self.snapshot, as_of="2026-11-07",
                   mode="retrospective_reconstruction")
        self.assertEqual(r["visible_source_events"], 7)
        self.assertTrue(all(x["FSL_first_captured_on"] == "2026-11-08"
                            for x in r["legal_states"]))

    def test_2026_11_08_strict_includes_first_captured_sources(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        self.assertEqual(r["visible_source_events"], 7)
        self.assertEqual(r["active_after_corrections"], 7)

    def test_signed_virginia_is_not_automatically_certified_in_force(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        x = next(e for e in r["legal_states"] if e["jurisdiction"] == "US-VA")
        self.assertEqual(x["status_at_source"], "signed")
        self.assertIsNone(x["effective_date_verified"])
        self.assertFalse(x["project_level_enforceability_certified"])

    def test_piqua_ballot_is_unofficial_binding_candidate(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        self.assertEqual(r["local_binding_candidate_pending_certification"], 1)
        x = next(e for e in r["legal_states"] if e["jurisdiction"] == "US-OH-PIQUA")
        self.assertEqual(x["bindingness"], "binding_candidate_pending_certification_and_applicability")
        self.assertIsNone(x["effective_date_verified"])

    def test_bloomington_advisory_does_not_become_law(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        self.assertEqual(r["nonbinding_advisory_votes"], 1)
        with self.assertRaises(LegalStudyError):
            validate(self.altered("us-il-bloomington-advisory-20261103",
                                  instrument="state_legislation"))

    def test_introduced_pennsylvania_bill_is_not_a_moratorium_in_force(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        self.assertEqual(r["introduced_not_enacted_in_source"], 1)
        with self.assertRaises(LegalStudyError):
            validate(self.altered("us-pa-sb1359-proposed-asof-20260915",
                                  effect_on="2026-09-15"))

    def test_EU_in_force_reporting_not_conflated_with_a_ban(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        self.assertEqual(r["in_force_EU_reporting_instrument"], 1)
        eu = next(x for x in r["legal_states"] if x["jurisdiction"] == "EU")
        self.assertEqual(eu["bindingness"], "binding_reporting_scope_limited")

    def test_China_policy_is_not_binding_siting_ban(self):
        cn = next(x for x in self.snapshot["legal_events"] if x["jurisdiction_code"] == "CN")
        self.assertEqual(cn["status"], "policy_plan_published")
        self.assertEqual(cn["bindingness"], "policy_target_not_direct_permit_ban")

    def test_order_to_rtos_not_general_national_ban(self):
        fed = next(x for x in self.snapshot["legal_events"] if x["jurisdiction_code"] == "US-FED")
        self.assertEqual(fed["status"], "agency_order_issued")
        self.assertEqual(fed["bindingness"], "binding_procedural_on_addressees")

    def test_wrong_bindingness_rejected(self):
        with self.assertRaises(LegalStudyError):
            validate(self.altered("us-oh-piqua-ballot-20261103",
                                  bindingness="binding_reporting_scope_limited"))

    def test_future_source_publication_cannot_backfill_earlier_event(self):
        d = copy.deepcopy(self.snapshot)
        s = next(s for s in d["sources"] if s["id"] == "src-piqua-2026")
        s["published_on"] = "2026-11-09"
        with self.assertRaises(LegalStudyError):
            validate(d)

    def test_source_cannot_appear_before_it_is_published(self):
        d = copy.deepcopy(self.snapshot)
        s = d["sources"][0]
        s["first_FSL_captured_on"] = "2026-06-01"
        with self.assertRaises(LegalStudyError):
            validate(d)

    def test_duplicate_event_rejected(self):
        d = copy.deepcopy(self.snapshot)
        d["legal_events"].append(copy.deepcopy(d["legal_events"][0]))
        with self.assertRaises(LegalStudyError):
            validate(d)

    def test_revision_rejects_changed_jurisdiction(self):
        d = copy.deepcopy(self.snapshot)
        original = d["legal_events"][0]
        revised = copy.deepcopy(original)
        revised["id"] = "us-ferc-later-revision-synthetic"
        revised["supersedes_event_id"] = original["id"]
        revised["jurisdiction_code"] = "US-VA"
        d["legal_events"].append(revised)
        with self.assertRaises(LegalStudyError):
            validate(d)

    def test_no_real_law_capacity_impact_is_inferred(self):
        r = replay(self.snapshot, as_of="2026-11-08")
        self.assertIsNone(r["legal_impact_on_AI_compute"])
        self.assertIsNone(r["legal_impact_on_energized_MW"])
        self.assertFalse(r["causal_effect_certified"])
        self.assertIsNone(r["one_number_legal_ranking"])

    def test_invalid_replay_mode_or_date_rejected(self):
        with self.assertRaises(LegalStudyError):
            replay(self.snapshot, as_of="2026-11-08", mode="pretend_predictive")
        with self.assertRaises(LegalStudyError):
            replay(self.snapshot, as_of="2026-11-34")


if __name__ == "__main__":
    unittest.main()
