"""FSL-PMQ v0.20 physical manufacturing quality and source discipline tests.

All manufacturing examples are synthetic; none certify a factory or part.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from fsl_manufacturing.audit import (
    ManufacturingStudyError, audit, load_catalog, load_sources
)

ROOT=Path(__file__).resolve().parent.parent
FIXTURE=ROOT/"tests"/"fixtures"/"manufacturing_quality_synthetic_v0.20.json"


class ManufacturingQualityV020Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(FIXTURE.read_text(encoding="utf-8"))

    def altered(self,index,**overrides):
        copydata=copy.deepcopy(self.data)
        copydata["events"][index].update(overrides)
        return copydata

    def test_catalog_has_sixteen_axes_and_eighty_metrics(self):
        catalog,ids=load_catalog()
        self.assertEqual(len(catalog["axes"]),16)
        self.assertEqual(len(ids),80)
        self.assertEqual(len(set(ids)),80)

    def test_human_comparison_is_human_plus_nonai_tools(self):
        c,_=load_catalog()
        self.assertIn("H_PLUS_CURRENT_NON_AI_TOOLS",c["comparison_baselines"])
        self.assertIn("bare human only",c["human_comparison_note"])

    def test_source_registry_has_published_scope_but_no_factory_certificate(self):
        sources=load_sources()
        self.assertEqual(len(sources["sources"]),9)
        self.assertEqual(len(sources["source_bound_claims"]),6)
        self.assertTrue(sources["no_real_factory_benchmark_performed"])
        self.assertTrue(all(s["independent_physical_product_certification"] is False
                            for s in sources["source_bound_claims"]))

    def test_standards_cannot_be_turned_into_product_certification(self):
        sources=load_sources()
        x=next(i for i in sources["sources"] if i["id"]=="iso-22514-7-2026-09")
        self.assertEqual(x["published_on"],"2026-09")
        self.assertEqual(x["publication_precision"],"month")

    def test_synthetic_fixtures_do_not_claim_product_quality(self):
        r=audit(self.data)
        self.assertEqual(r["archived_observations"],5)
        self.assertEqual(r["active_after_revisions"],4)
        self.assertFalse(r["AI_manufacturing_quality_superiority_certified"])
        self.assertFalse(r["new_physical_quality_frontier_certified"])
        self.assertFalse(r["SAS_systemic_singularity_certified"])
        self.assertFalse(r["SAS_civilizational_positive_sum_certified"])

    def test_prior_asof_keeps_original_toy_record(self):
        r=audit(self.data,as_of="2026-11-08T03:30:00+08:00")
        self.assertEqual(r["visible_observations"],4)
        ids={x["event_id"] for x in r["active_records"]}
        self.assertIn("toy_output_001",ids)
        self.assertNotIn("toy_output_002",ids)

    def test_later_record_does_not_erase_history(self):
        r=audit(self.data,as_of="2026-11-08")
        self.assertEqual(r["visible_observations"],5)
        ids={x["event_id"] for x in r["active_records"]}
        self.assertIn("toy_output_002",ids)
        self.assertNotIn("toy_output_001",ids)

    def test_model_inspection_only_cannot_certify_better_goods(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(0,claim_label="quality_improvement_candidate"))

    def test_more_parts_does_not_automatically_establish_quality(self):
        r=audit(self.data)
        x=next(e for e in r["active_records"] if e["event_id"]=="toy_output_002")
        self.assertEqual(x["claim_label"],"unassessed")

    def test_design_only_does_not_establish_physical_material_property(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(2,claim_label="beyond_contemporary_quality_frontier_candidate"))

    def test_synthetic_cannot_forge_independent_replication(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(1,evidence_tier="independent_physical_replication"))

    def test_observational_claim_needs_source_url(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(1,evidence_class="observational",evidence_tier="vendor_claim"))

    def test_observational_physical_test_needs_receipt(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(1,evidence_class="observational",
                               evidence_tier="reproducible_physical_test",
                               source_url="https://example.org/synthetic-test"))

    def test_uncalibrated_real_data_cannot_claim_superior(self):
        d=self.altered(1,evidence_class="observational",
                       evidence_tier="independent_physical_replication",
                       source_url="https://example.org/fictional-only",
                       receipt_sha256="a"*64,
                       claim_label="quality_improvement_candidate",
                       safety_status="passed")
        with self.assertRaises(ManufacturingStudyError):
            audit(d)

    def test_new_property_cannot_be_unmeasured(self):
        d=self.altered(2,evidence_class="observational",
                       evidence_tier="independent_physical_replication",
                       source_url="https://example.org/fictional-only",
                       receipt_sha256="b"*64,
                       claim_label="beyond_contemporary_quality_frontier_candidate",
                       safety_status="passed")
        with self.assertRaises(ManufacturingStudyError):
            audit(d)

    def test_wrong_metric_id_rejected(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(1,metric_id="PMQ-FAKE-99"))

    def test_wrong_timezone_rejected(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(2,recorded_at="2026-11-08T02:04:00"))

    def test_revision_cannot_change_product(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(4,product_id="different_product_r1"))

    def test_defects_and_life_not_commutable(self):
        c,ids=load_catalog()
        self.assertIn("PMQ-DEF-01",ids)
        self.assertIn("PMQ-DUR-01",ids)
        self.assertNotEqual("PMQ-DEF-01","PMQ-DUR-01")

    def test_measurements_need_unit(self):
        d=self.altered(1)
        d["events"][1]["measurement"]["unit"]=None
        with self.assertRaises(ManufacturingStudyError):
            audit(d)

    def test_future_no_AI_year_cannot_be_fabricated(self):
        with self.assertRaises(ManufacturingStudyError):
            audit(self.altered(2,future_no_ai_year=2040))

    def test_unknown_future_year_remains_explicitly_null(self):
        r=audit(self.data)
        self.assertIsNone(r["future_no_AI_human_year"])

    def test_negative_result_withheld_not_allowed_in_append_only_correction(self):
        d=self.altered(4)
        d["events"][4]["revision_of"]="unknown_event"
        with self.assertRaises(ManufacturingStudyError):
            audit(d)

    def test_count_only_claim_never_certifies_SAS(self):
        r=audit(self.data)
        self.assertIsNone(r["universal_aggregate_quality_score"])
        self.assertFalse(r["SAS_systemic_singularity_certified"])


if __name__=="__main__":
    unittest.main()
