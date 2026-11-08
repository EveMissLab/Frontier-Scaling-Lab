"""Regression checks for FSL-NET v0.16.

All examples are SYNTHETIC and must never be interpreted as actual satellite,
cable, provider or autonomous robot results.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from fsl_connectivity.audit import (
    NetworkStudyError, audit, load_catalog
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "connectivity_synthetic_v0.16.json"


class ConnectivityV016Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _modified(self, i, **kwargs):
        payload = copy.deepcopy(self.fixture)
        payload["events"][i].update(kwargs)
        return payload

    def test_catalog_has_14_axes_and_70_unique_measurables(self):
        catalog, ids = load_catalog()
        self.assertEqual(len(catalog["research_axes"]), 14)
        self.assertEqual(len(ids), 70)
        self.assertEqual(len(set(ids)), 70)
        self.assertEqual(len(catalog["principles"]), 11)

    def test_synthetic_fixture_is_not_real_world_certification(self):
        report = audit(self.fixture)
        self.assertEqual(report["archived_event_count"], 5)
        self.assertEqual(report["active_event_count"], 4)
        self.assertEqual(report["indicator_count"], 70)
        self.assertFalse(report["ai_capability_independently_certified"])
        self.assertIsNone(report["aggregated_network_intelligence_score"])
        self.assertTrue(all(x["data_class"] == "synthetic" for x in report["active_cases"]))

    def test_asof_preserves_pre_revision_without_future_data(self):
        report = audit(self.fixture, cutoff="2026-11-08T04:45:00+08:00")
        self.assertEqual(report["events_visible"], 4)
        self.assertEqual(report["active_event_count"], 4)
        ids = {x["event_id"] for x in report["active_cases"]}
        self.assertIn("synthetic-cable-001", ids)
        self.assertNotIn("synthetic-cable-002", ids)

    def test_revision_preserves_history(self):
        report = audit(self.fixture, cutoff="2026-11-08")
        self.assertEqual(report["events_visible"], 5)
        ids = {x["event_id"] for x in report["active_cases"]}
        self.assertIn("synthetic-cable-002", ids)
        self.assertNotIn("synthetic-cable-001", ids)

    def test_api_403_is_not_network_outage(self):
        report = audit(self.fixture)
        self.assertEqual(report["failure_scope_counts"]["physical_up_service_denied"], 1)
        x = next(x for x in report["active_cases"] if x["event_id"] == "synthetic-api403-001")
        self.assertEqual(x["primary_path"], "up")
        self.assertEqual(x["service_access"], "blocked_policy")

    def test_403_disallows_false_link_outage_claim(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(1, primary_path="down"))

    def test_403_cannot_forge_restoration_time(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(1, failover_rto_seconds=1))

    def test_physical_two_links_share_failure_domain(self):
        report = audit(self.fixture)
        x = next(x for x in report["active_cases"] if x["event_id"] == "synthetic-power-001")
        self.assertEqual(x["primary_path"], "down")
        self.assertEqual(x["backup_path"], "down")
        self.assertEqual(x["local_safety"], "safe")
        self.assertEqual(x["path_independence"], "shared_dependency")

    def test_shared_power_cannot_be_independent(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(2, path_independence="verified_distinct_failure_domains"))

    def test_synthetic_cannot_promote_external_receipt(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(0, evidence_kind="independent_field"))

    def test_observation_requires_source_url_and_receipt(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(0, data_class="observational", evidence_kind="field_receipt"))

    def test_no_access_without_any_transport(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(2, service_access="allowed"))

    def test_unknown_metric_rejected(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(0, metric_id="NET-BAD-99"))

    def test_future_source_cannot_precede_incident(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(0, source_published_at="2026-11-07T23:00:00+08:00"))

    def test_duplicate_id_rejected(self):
        payload = copy.deepcopy(self.fixture)
        payload["events"].append(copy.deepcopy(payload["events"][0]))
        with self.assertRaises(NetworkStudyError):
            audit(payload)

    def test_revision_cannot_change_task_contract(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(4, task_contract_id="another-contract"))

    def test_revision_cannot_precede_original(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(4, recorded_at="2026-11-07T01:00:00+08:00"))

    def test_rto_requires_available_backup(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(0, backup_path="down"))

    def test_missing_timezone_rejected(self):
        with self.assertRaises(NetworkStudyError):
            audit(self._modified(0, recorded_at="2026-11-08T01:00:00"))


if __name__ == "__main__":
    unittest.main()
