"""FSL v0.17 systemic AI singularity source-bridge validation tests.

All data in this suite are synthetic. No real industrial regeneration,
AGI/ASI, energy loop or societal benefit is certified.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from fsl_singularity.protocol import (
    SingularityStudyError, audit, load_protocol
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "systemic_singularity_synthetic_v0.17.json"


class SystemicSingularityV017Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.protocol = load_protocol()

    def change(self, i, **fields):
        doc = copy.deepcopy(self.data)
        doc["events"][i].update(fields)
        return doc

    def test_original_sas_definition_and_ewdt_are_separate(self):
        p = self.protocol
        self.assertEqual([x["document_id"] for x in p["definition_priority"][:2]],
                         ["SAS-01", "EWDT-19"])
        self.assertEqual([x["id"] for x in p["boundary_gates"]],
                         ["Sigma_sys", "Sigma_civ"])

    def test_source_vector_and_five_multidimensional_state_components(self):
        p = self.protocol
        self.assertEqual("".join(x["code"] for x in p["system_vector"]), "ICEHMLRN")
        self.assertEqual([x["id"] for x in p["system_state_dimensions"]],
                         ["R_sys", "alpha_AI", "kappa_closure",
                          "epsilon_H", "P_persist"])

    def test_synthetic_evidence_never_promoted(self):
        r = audit(self.data)
        self.assertEqual(r["archived_events"], 7)
        self.assertEqual(r["current_assertions_after_correction"], 6)
        self.assertFalse(r["systemic_singularity_certified"])
        self.assertFalse(r["civilizational_singularity_certified"])
        self.assertTrue(r["multi_cycle_evidence_not_established"])
        self.assertEqual(r["candidate_independently_sourced_system_components"], [])

    def test_asof_before_revision_preserves_original_observation(self):
        r = audit(self.data, as_of="2026-11-07T20:00:00+08:00")
        self.assertEqual(r["visible_events"], 3)
        self.assertEqual(r["current_assertions_after_correction"], 3)
        self.assertFalse(r["systemic_singularity_certified"])

    def test_asof_after_revision_retains_historical_event_count(self):
        r = audit(self.data, as_of="2026-11-08")
        self.assertEqual(r["visible_events"], 7)
        self.assertEqual(r["current_assertions_after_correction"], 6)

    def test_synthetic_claim_cannot_claim_independent_receipt(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(0, source_class="independent_measurement"))

    def test_real_independent_measurement_needs_https_and_digest(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(0, evidence_class="observational",
                              source_class="independent_measurement"))

    def test_cannot_infer_causal_ai_attribution_without_controls(self):
        rec = self.change(1, evidence_class="observational",
                          source_class="independent_measurement",
                          source_url="https://example.org/synthetic-not-evidence",
                          receipt_sha256="a" * 64,
                          assessment_state="candidate_positive",
                          observed_value=0.2, observed_unit="share")
        with self.assertRaises(SingularityStudyError):
            audit(rec)

    def test_unknown_value_cannot_look_numeric(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(1, observed_value=0.6, observed_unit="ratio"))

    def test_civil_impact_must_have_separate_gate(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(5, domain="E"))

    def test_network_metric_must_be_in_network_substrate(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(2, domain="GLOBAL"))

    def test_system_component_not_reduced_to_one_local_domain(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(0, domain="E"))

    def test_duplicate_append_only_record_rejected(self):
        rec = copy.deepcopy(self.data)
        rec["events"].append(copy.deepcopy(rec["events"][0]))
        with self.assertRaises(SingularityStudyError):
            audit(rec)

    def test_correction_must_preserve_subject_and_cycle(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(6, cycle_id="other-cycle"))

    def test_future_capture_does_not_appear_in_historical_replay(self):
        rec = self.change(1, recorded_at="2026-11-09T10:00:00+08:00")
        r = audit(rec, as_of="2026-11-07T20:00:00+08:00")
        self.assertEqual(r["visible_events"], 2)

    def test_cannot_backdate_source_relative_to_event(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.change(1, source_published_at="2026-11-07T09:00:00+08:00"))

    def test_cutoff_requires_timezone_for_iso_timestamp(self):
        with self.assertRaises(SingularityStudyError):
            audit(self.data, as_of="2026-11-08T08:00:00")

    def test_observational_provider_statement_never_independent(self):
        rec = self.change(0, evidence_class="observational",
                          source_class="provider_claim",
                          source_url="https://example.org/not-real-source")
        r = audit(rec)
        self.assertFalse(r["systemic_singularity_certified"])
        self.assertEqual(r["candidate_independently_sourced_system_components"], [])


if __name__ == "__main__":
    unittest.main()
