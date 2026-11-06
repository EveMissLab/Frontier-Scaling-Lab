"""Offline import and provenance tests: no external HTTP calls.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import json
import sqlite3
import unittest

from fsl_sources.adapters import (
    arena_rows_request, encode_repo_id, hf_benchmark_request, hf_model_request,
    parse_arena_page, parse_community_rollup, parse_hf_benchmark, parse_hf_model,
)
from fsl_sources.catalog import (
    CatalogError, add_alias, connect, list_observations, save_snapshot, trend,
)


def model_api():
    return {
        "id": "demo/example", "sha": "0123456789abcdef",
        "downloads": 14, "likes": 3, "lastModified": "2026-11-03T11:00:00Z",
        "safetensors": {"total": 1000000000},
        "cardData": {"license": "apache-2.0"},
    }


def arena_text(date="2026-11-04", rating=1423.0, category="overall"):
    return {
        "rows": [{
            "row_idx": 0,
            "row": {
                "model_name": "SYNTHETIC-CHAT-001", "organization": "example",
                "rating": rating, "rating_lower": rating-5, "rating_upper": rating+5,
                "vote_count": 510, "category": category,
                "leaderboard_publish_date": date,
            },
        }],
    }


def arena_agent():
    return {
        "rows": [{
            "row_idx": 0,
            "row": {
                "model_name": "SYNTHETIC-AGENT-001",
                "score": 0.15, "score_ci_lower": 0.13, "score_ci_upper": 0.17,
                "observation_count": 2400, "category": "overall",
                "leaderboard_publish_date": "2026-11-04",
            },
        }],
    }


def feedback():
    return {
        "external_model_id": "demo/chat-v1",
        "category": "coding_reliability",
        "counts": {"positive": 6, "neutral": 3, "negative": 1},
        "sampling_method": "curated_public_sample",
        "collected_on": "2026-11-04",
        "source_url": "https://example.org/aggregate-study",
        "source_license": "research-aggregate-only",
        "attribution": "SYNTHETIC research example",
        "sample_window_id": "synthetic-window-001",
    }


class SourcesTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_hf_model_extracts_metadata_without_declaring_true_parameters(self):
        item = parse_hf_model(model_api(), model_id="demo/example",
                              retrieved_on="2026-11-06")
        self.assertEqual(item["license_name"], "apache-2.0")
        names = {r["measure"] for r in item["observations"]}
        self.assertEqual(names, {"serialized_safetensors_elements", "hub_downloads", "hub_likes"})
        weight = next(r for r in item["observations"]
                      if r["measure"] == "serialized_safetensors_elements")
        self.assertIn("not_active_parameters", weight["provenance_flags"])
        self.assertEqual(weight["unit"], "elements")

    def test_hf_api_identity_mismatch_fails(self):
        with self.assertRaises(CatalogError):
            parse_hf_model(model_api(), model_id="someone/else",
                           retrieved_on="2026-11-06")

    def test_arena_ratings_and_agent_ips_remain_separate(self):
        t = parse_arena_page(arena_text(), config="text", split="latest",
                             offset=0, retrieved_on="2026-11-06")
        a = parse_arena_page(arena_agent(), config="agent", split="latest",
                             offset=0, retrieved_on="2026-11-06")
        self.assertEqual(t["observations"][0]["measure"], "arena_rating")
        self.assertEqual(t["observations"][0]["sample_size"], 510)
        self.assertEqual(a["observations"][0]["measure"], "ips_score")
        self.assertEqual(a["observations"][0]["sample_size"], 2400)
        self.assertNotEqual(t["observations"][0]["methodology"],
                            a["observations"][0]["methodology"])
        self.assertEqual(t["license_name"], "CC-BY-4.0 (as declared in dataset card)")

    def test_arena_future_publication_not_backdateable(self):
        with self.assertRaises(CatalogError):
            parse_arena_page(arena_text(date="2030-01-01"),
                             config="text", split="latest", offset=0,
                             retrieved_on="2026-11-06")

    def test_official_hf_benchmark_submitted_not_certified(self):
        raw = [{"modelId": "demo/example", "value": 76.5, "verified": False,
                "rank": 1, "num_parameters": 1000000000}]
        prepared = parse_hf_benchmark(
            raw, dataset_id="SWE-bench/SWE-bench_Verified",
            retrieved_on="2026-11-06")
        self.assertEqual(len(prepared["observations"]), 2)
        metric = prepared["observations"][0]
        self.assertEqual(metric["measure"], "submitted_benchmark_value")
        self.assertIn("entry_not_marked_verified", metric["provenance_flags"])

    def test_subjective_aggregate_wilson_and_strict_no_raw_comments(self):
        item = parse_community_rollup(feedback(), retrieved_on="2026-11-06")
        metric = item["observations"][0]
        self.assertEqual(metric["sample_size"], 10)
        self.assertAlmostEqual(metric["value"], 0.6)
        self.assertLess(metric["ci_low"], 0.6)
        self.assertGreater(metric["ci_high"], 0.6)
        self.assertIn("not_training_feedback_for_parameter_model",
                      metric["provenance_flags"])
        invalid = feedback()
        invalid["raw_comments"] = ["private personal story"]
        with self.assertRaises(CatalogError):
            parse_community_rollup(invalid, retrieved_on="2026-11-06")
        invalid = feedback()
        invalid["counts"]["negative"] = -1
        with self.assertRaises(CatalogError):
            parse_community_rollup(invalid, retrieved_on="2026-11-06")

    def test_can_save_source_and_replay(self):
        prepared = parse_hf_model(model_api(), model_id="demo/example",
                                  retrieved_on="2026-11-06")
        first = save_snapshot(self.db, **prepared)
        second = save_snapshot(self.db, **prepared)
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM public_snapshots").fetchone()[0], 1)
        self.assertEqual(len(list_observations(self.db, model_id="hf:demo/example")), 3)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM public_snapshots WHERE snapshot_id=?",
                            (first["snapshot_id"],))

    def test_subjective_not_mixed_with_benchmark_or_training_feedback(self):
        prepared = parse_community_rollup(feedback(), retrieved_on="2026-11-06")
        save_snapshot(self.db, **prepared)
        self.assertEqual(len(list_observations(self.db, channel="community")), 1)
        self.assertEqual(len(list_observations(self.db, channel="benchmark")), 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0], 0)

    def test_trend_requires_same_methodology_and_dates(self):
        for day, value in (("2026-11-01", 1400), ("2026-11-02", 1410),
                           ("2026-11-03", 1430)):
            prepared = parse_arena_page(arena_text(date=day, rating=value),
                                        config="text", split="full", offset=0,
                                        retrieved_on="2026-11-06")
            save_snapshot(self.db, **prepared)
        summary = trend(self.db, model_id="arena:SYNTHETIC-CHAT-001",
                        measure="arena_rating", category="overall",
                        methodology="arena-dataset:text:arena_rating",
                        channel="preference")
        self.assertEqual(summary["n_distinct_dates"], 3)
        self.assertEqual(summary["status"], "descriptive_only")
        another = trend(self.db, model_id="arena:SYNTHETIC-CHAT-001",
                        measure="ips_score", category="overall",
                        methodology="arena-dataset:agent:ips_score",
                        channel="preference")
        self.assertEqual(another["n_distinct_dates"], 0)
        self.assertEqual(another["status"], "insufficient_for_trend")

    def test_cross_platform_matching_is_manual(self):
        first = add_alias(self.db, source_type="arena",
                          external_model_id="SYNTHETIC-CHAT-001",
                          canonical_model_key="example:chat:v1",
                          source="https://example.org/model-card",
                          recorded_on="2026-11-06")
        self.assertTrue(first)
        with self.assertRaises(sqlite3.IntegrityError):
            add_alias(self.db, source_type="arena",
                      external_model_id="SYNTHETIC-CHAT-001",
                      canonical_model_key="different:maybe",
                      source="https://example.org/model-card",
                      recorded_on="2026-11-06")

    def test_url_and_bounded_requests(self):
        self.assertTrue(hf_model_request("Qwen/Qwen3-0.6B").startswith("https://huggingface.co/"))
        self.assertIn("leaderboard", hf_benchmark_request("SWE-bench/SWE-bench_Verified"))
        self.assertIn("length=100", arena_rows_request("text", "latest", limit=100))
        for bad in ("bad/../../repo", "single", "a/b/c"):
            with self.assertRaises(CatalogError):
                encode_repo_id(bad)
        with self.assertRaises(CatalogError):
            arena_rows_request("text", "latest", limit=101)
        with self.assertRaises(CatalogError):
            arena_rows_request("agent", "unknown", limit=10)

    def test_reject_bad_future_dates_and_license(self):
        prepared = parse_hf_model(model_api(), model_id="demo/example",
                                  retrieved_on="2026-11-06")
        revised = copy.deepcopy(prepared)
        revised["published_on"] = "2030-01-01"
        with self.assertRaises(CatalogError):
            save_snapshot(self.db, **revised)
        revised = copy.deepcopy(prepared)
        revised["license_name"] = ""
        with self.assertRaises(CatalogError):
            save_snapshot(self.db, **revised)

    def test_all_provenance_retained(self):
        prepared = parse_arena_page(arena_text(), config="text", split="latest",
                                    offset=0, retrieved_on="2026-11-06")
        saved = save_snapshot(self.db, **prepared)
        row = self.db.execute("""SELECT source_license, attribution, content_sha256
             FROM public_snapshots WHERE snapshot_id=?""", (saved["snapshot_id"],)).fetchone()
        self.assertEqual(row["source_license"], prepared["license_name"])
        self.assertIn("Arena", row["attribution"])
        self.assertEqual(len(row["content_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
