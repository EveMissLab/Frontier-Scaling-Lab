"""FSL v0.15: Validate chronology, attributed speaker, and non-certified forecasts.

Only validates public archival metadata, not external prediction truth.
SPDX-License-Identifier: Apache-2.0
"""
from datetime import date
import json
from pathlib import Path
import unittest

DATA = (Path(__file__).resolve().parent.parent /
        "data" / "ai_network_orbit_narrative_candidates_2026-11-08_v0.15.json")


class DatedAgenticOrbitResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATA.read_text(encoding="utf-8"))
        cls.sources = {x["id"]: x for x in cls.payload["sources"]}
        cls.claims = {x["id"]: x for x in cls.payload["statements"]}

    def test_unique_dated_sources_and_provenance(self):
        p = self.payload
        self.assertEqual(p["schema"], "fsl/dated-agentic-network-orbit-hypotheses/0.15")
        self.assertEqual(p["timezone"], "Asia/Taipei")
        self.assertEqual(len(self.sources), len(p["sources"]))
        for s in p["sources"]:
            self.assertTrue(s["url"].startswith("https://"))
            self.assertEqual(s["first_captured_on"], "2026-11-08")
            if s["published_on"] is not None:
                self.assertLessEqual(date.fromisoformat(s["published_on"]),
                                     date.fromisoformat(s["first_captured_on"]))
            if s["event_on"] is not None:
                self.assertLessEqual(date.fromisoformat(s["event_on"]),
                                     date.fromisoformat(s["first_captured_on"]))

    def test_every_speaker_claim_references_dated_evidence(self):
        self.assertEqual(len(self.claims), len(self.payload["statements"]))
        for c in self.claims.values():
            self.assertIn(c["source_id"], self.sources)
            self.assertIn(c["speaker"], {"Elon Musk", "Matthew Prince"})
            self.assertTrue(c["proposition_zh"].strip())
            self.assertLessEqual(date.fromisoformat(c["uttered_on"]),
                                 date.fromisoformat(self.payload["review_date"]))
            self.assertNotIn(c["verification_status"], {"verified_forecast", "forecast_success"})

    def test_thousand_fold_originally_attributed_to_cloudflare(self):
        s1, s3 = self.claims["s01"], self.claims["s03"]
        self.assertEqual(s1["speaker"], "Elon Musk")
        self.assertEqual(s1["first_party_forecast_origin"], "cloudflare-20260806-prince")
        self.assertEqual(s3["speaker"], "Matthew Prince")
        self.assertEqual(s1["metric"]["value"], 1000)
        self.assertEqual(s3["metric"]["value"], 1000)
        self.assertEqual(s3["kind"], "conditional_forecast")

    def test_starlink_multiplies_hardware_not_agentic_traffic(self):
        self.assertEqual(self.claims["s04"]["metric"]["quantity"],
                         "starlink_total_system_bandwidth_multiplier")
        self.assertEqual(self.claims["s04"]["metric"]["value"], 100)
        self.assertEqual(self.claims["s05"]["metric"]["quantity"],
                         "starlink_v4_vs_v3_capability_multiplier")
        self.assertEqual(self.claims["s05"]["metric"]["value"], 10)

    def test_no_transcript_or_satellite_commercial_certification(self):
        self.assertEqual(len(self.payload["research_hypotheses"]), 3)
        self.assertTrue(all(h["status"] == "unadjudicated" and
                            h["numerical_threshold"] is None
                            for h in self.payload["research_hypotheses"]))
        self.assertTrue(all(self.payload["guards"].values()))
        space = next(e for e in self.payload["counter_evidence"] if e["id"] == "e01")
        self.assertEqual(space["establishes"], "provider_reported_small_scale_test")
        self.assertNotEqual(space["establishes"],
                            "large_operational_orbital_data_center_or_economic_cost_advantage")


if __name__ == "__main__":
    unittest.main()
