"""Bounded external refresh tests use injected JSON; never call the network.

SPDX-License-Identifier: Apache-2.0
"""
import unittest

from fsl_sources.catalog import connect
from scripts.public_evidence_refresh import refresh


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_small_complete_refresh(self):
        def fake_fetch(url):
            if "/api/models/" in url:
                return {
                    "id": "Qwen/Qwen3-0.6B", "likes": 1,
                    "downloads": 2, "safetensors": {"total": 100},
                    "lastModified": "2026-11-04T00:00:00Z",
                    "cardData": {"license": "apache-2.0"},
                }
            if "config=text" in url:
                return {"rows": [{"row_idx": 0, "row": {
                    "model_name": "SYNTHETIC", "rating": 1400,
                    "rating_lower": 1390, "rating_upper": 1410,
                    "vote_count": 100, "category": "overall",
                    "leaderboard_publish_date": "2026-11-04",
                }}]}
            if "config=agent" in url:
                return {"rows": [{"row_idx": 0, "row": {
                    "model_name": "SYNTHETIC", "score": 0.1,
                    "score_ci_lower": 0.05, "score_ci_upper": 0.15,
                    "observation_count": 100, "category": "overall",
                    "leaderboard_publish_date": "2026-11-04",
                }}]}
            if "/leaderboard" in url:
                return [{"modelId": "synthetic/example", "value": 80.0,
                         "verified": False, "num_parameters": 1000}]
            raise AssertionError("unexpected network URL")

        report = refresh(self.db, "2026-11-06", fetch=fake_fetch)
        self.assertEqual(report["stored"], 4)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM public_snapshots").fetchone()[0], 4)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM feedback").fetchone()[0], 0)

    def test_http_failure_is_visible_not_an_empty_observation(self):
        def failed(_):
            raise ConnectionError("SYNTHETIC upstream outage")

        result = refresh(self.db, "2026-11-06", fetch=failed)
        self.assertEqual(result["stored"], 0)
        self.assertEqual(result["failed"], 4)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM public_observations").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
