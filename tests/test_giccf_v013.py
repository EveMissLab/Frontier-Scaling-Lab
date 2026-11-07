"""FSL GICCF taxonomy and as-of audit regression checks.

All trial data are synthetic. No test certifies a real product.

SPDX-License-Identifier: Apache-2.0
"""
import copy
import json
from pathlib import Path
import unittest

from fsl_civilization.registry import (GICCFError, audit_observations,
                                       catalog_sha256, load_catalog,
                                       validate_catalog)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "giccf_observations_synthetic_v0.13.json"


class TestGICCFV013(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_catalog_complete_and_unique(self):
        meta = validate_catalog(self.catalog)
        self.assertEqual(meta["axis_count"], 28)
        self.assertEqual(meta["indicator_count"], 224)
        self.assertEqual(meta["domain_count"], 38)
        self.assertEqual(meta["example_task_family_count"], 114)
        self.assertEqual(len(catalog_sha256()), 64)

    def test_fixture_unmeasured_and_never_certified(self):
        report = audit_observations(self.fixture, catalog=self.catalog)
        self.assertEqual(report["total_archive_records"], 4)
        self.assertEqual(report["visible_at_cutoff"], 4)
        self.assertEqual(len(report["sparse_results"]), 4)
        self.assertFalse(report["independent_capability_certification"])
        self.assertIsNone(report["global_intelligence_score"])
        self.assertTrue(all(not r["external_certified"]
                            and not r["independent_review_candidate"]
                            and r["synthetic_records"] == 1
                            for r in report["sparse_results"]))

    def test_asof_no_future_capture(self):
        report = audit_observations(self.fixture, catalog=self.catalog, as_of="2026-11-06")
        self.assertEqual(report["visible_at_cutoff"], 1)
        self.assertEqual(report["active_after_visible_supersessions"], 1)

    def test_provider_claim_cannot_pretend_test(self):
        broken = copy.deepcopy(self.fixture)
        broken["observations"][0]["evidence_tier"] = "provider_claim"
        with self.assertRaises(GICCFError):
            audit_observations(broken, catalog=self.catalog)

    def test_synthetic_cannot_promote_independent(self):
        broken = copy.deepcopy(self.fixture)
        broken["observations"][0]["evidence_tier"] = "independent_repeated"
        with self.assertRaises(GICCFError):
            audit_observations(broken, catalog=self.catalog)

    def test_bad_temporal_provenance_fails(self):
        broken = copy.deepcopy(self.fixture)
        broken["observations"][0]["fsl_recorded_at"] = "2026-11-01T00:00:00Z"
        with self.assertRaises(GICCFError):
            audit_observations(broken, catalog=self.catalog)

    def test_unknown_indicator_rejected(self):
        broken = copy.deepcopy(self.fixture)
        broken["observations"][0]["indicator_id"] = "FAK-99"
        with self.assertRaises(GICCFError):
            audit_observations(broken, catalog=self.catalog)

    def test_duplicate_event_rejected(self):
        broken = copy.deepcopy(self.fixture)
        broken["observations"].append(copy.deepcopy(broken["observations"][0]))
        with self.assertRaises(GICCFError):
            audit_observations(broken, catalog=self.catalog)

    def test_consecutive_overrides_preserve_prior_asof(self):
        amended = copy.deepcopy(self.fixture)
        original = amended["observations"][0]
        revise = copy.deepcopy(original)
        revise.update({
            "observation_id": "synthetic-memory-002",
            "outcome": "failed",
            "event_occurred_at": "2026-11-07T07:00:00Z",
            "source_published_at": "2026-11-07T07:20:00Z",
            "fsl_recorded_at": "2026-11-07T10:00:00Z",
            "supersedes_observation_id": original["observation_id"]
        })
        amended["observations"].append(revise)
        before = audit_observations(amended, catalog=self.catalog, as_of="2026-11-06")
        after = audit_observations(amended, catalog=self.catalog, as_of="2026-11-07")
        self.assertEqual(before["visible_at_cutoff"], 1)
        self.assertEqual(after["total_archive_records"], 5)
        self.assertEqual(after["active_after_visible_supersessions"], 4)
        item = next(x for x in after["sparse_results"] if x["indicator_id"] == "MEM-01")
        self.assertEqual(item["passed"], 0)
        self.assertEqual(item["failed"], 1)

    def test_catalog_duplicate_indicator_fails(self):
        bad = copy.deepcopy(self.catalog)
        bad["capability_axes"][1]["indicators"][0]["id"] = bad["capability_axes"][0]["indicators"][0]["id"]
        with self.assertRaises(GICCFError):
            validate_catalog(bad)


if __name__ == "__main__":
    unittest.main()
