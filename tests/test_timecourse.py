"""Methodology breakpoints, temporal provenance and filtered history tests.

All samples are synthetic, no network calls or real-user records.
SPDX-License-Identifier: Apache-2.0
"""
import unittest

from fsl_sources.catalog import CatalogError, connect, save_snapshot
from fsl_sources.adapters import parse_arena_page
from fsl_timecourse.arena_history import filter_url, import_history
from fsl_timecourse.analysis import arena_regime, analyze_series, study_readiness


MODEL = "gpt-4o-2024-05-13"
METHODOLOGY = "arena-dataset:text_style_control:arena_rating"


def synthetic_row(day, rating=1400, model=MODEL, count=500, category="overall"):
    return {"row_idx": 0, "row": {
        "model_name": model, "organization": "SYNTHETIC",
        "rating": rating, "rating_lower": rating-8,
        "rating_upper": rating+8, "vote_count": count,
        "category": category, "leaderboard_publish_date": day,
    }}


def ingest(db, points, *, retrieved="2026-11-06", config="text_style_control",
           category="overall"):
    payload = {"rows": [
        synthetic_row(day, rating, count=count, category=category)
        for day, rating, count in points
    ]}
    prepared = parse_arena_page(
        payload, config=config, split="full", offset=0, retrieved_on=retrieved)
    return save_snapshot(db, **prepared)


def series(db, *, mode="strict_asof", as_of="2026-11-06", min_samples=100,
           config="text_style_control"):
    return analyze_series(
        db, model_id="arena:"+MODEL, channel="preference",
        measure="arena_rating", category="overall",
        methodology="arena-dataset:"+config+":arena_rating",
        as_of=as_of, mode=mode, min_samples=min_samples)


class TimecourseTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_methodology_breaks_are_explicit(self):
        self.assertNotEqual(
            arena_regime(METHODOLOGY, "2025-07-22"),
            arena_regime(METHODOLOGY, "2025-07-23"))
        self.assertNotEqual(
            arena_regime("arena-dataset:text:arena_rating", "2024-01-08"),
            arena_regime("arena-dataset:text:arena_rating", "2024-01-09"))
        self.assertNotEqual(
            arena_regime("arena-dataset:agent_bash_recovery_steps:ips_score", "2026-10-11"),
            arena_regime("arena-dataset:agent_bash_recovery_steps:ips_score", "2026-10-12"))

    def test_retrospective_is_not_past_known_at_time(self):
        ingest(self.db, [
            ("2025-08-01", 1400, 500),
            ("2025-09-01", 1410, 600),
            ("2025-10-01", 1420, 700)])
        strict = series(self.db, mode="strict_asof", as_of="2025-10-05")
        past = series(self.db, mode="retrospective", as_of="2025-10-05")
        self.assertEqual(strict["unique_published_dates"], 0)
        self.assertEqual(past["unique_published_dates"], 3)
        self.assertEqual(past["historical_forecast_admissibility"], "NOT_prequential")
        self.assertEqual(past["segments"][0]["status"], "descriptive_temporal_series")
        self.assertEqual(past["segments"][0]["level_difference"]["level_change"], 20)
        self.assertIsNone(past["capability_multiplier"])

    def test_regime_separation_prevents_spurious_growth(self):
        ingest(self.db, [
            ("2025-06-01", 1400, 500),
            ("2025-07-01", 1410, 500),
            ("2025-08-01", 1430, 500),
            ("2025-09-01", 1435, 500),
            ("2025-10-01", 1440, 500)])
        result = series(self.db)
        self.assertEqual(len(result["segments"]), 2)
        self.assertEqual(result["segments"][0]["n_dates"], 2)
        self.assertEqual(result["segments"][0]["status"], "insufficient_longitudinal_evidence")
        self.assertEqual(result["segments"][1]["n_dates"], 3)
        self.assertEqual(result["segments"][1]["level_difference"]["level_change"], 10)
        self.assertTrue(all(seg["level_difference"] is None or
                            "capability" in seg["level_difference"]["note"]
                            for seg in result["segments"]))

    def test_fixed_count_rating_revision_and_large_count_drop(self):
        ingest(self.db, [
            ("2025-08-01", 1400, 500),
            ("2025-09-01", 1410, 500),
            ("2025-10-01", 1420, 400),
            ("2025-11-01", 1418, 400)])
        segment = series(self.db)["segments"][0]
        audit = segment["sample_basis_audit"]
        self.assertEqual(audit["same_reported_count_but_score_changed"], 2)
        self.assertEqual(audit["material_sample_count_drops"], 1)
        self.assertEqual(segment["status"], "descriptive_with_sample_basis_warning")

    def test_low_samples_excluded_not_silent_zero(self):
        ingest(self.db, [
            ("2025-08-01", 1400, 3),
            ("2025-09-01", 1410, 500),
            ("2025-10-01", 1420, 500)])
        result = series(self.db)
        self.assertEqual(len(result["excluded_low_samples"]), 1)
        self.assertEqual(result["segments"][0]["n_dates"], 2)

    def test_same_day_conflicting_records_are_flagged(self):
        ingest(self.db, [("2025-10-01", 1410, 500)])
        ingest(self.db, [("2025-10-01", 1499, 500)])
        result = series(self.db)
        self.assertEqual(result["unique_published_dates"], 0)
        self.assertEqual(len(result["same_day_conflicts"]), 1)
        self.assertEqual(result["segments"], [])

    def test_more_recent_revision_selected_at_newer_cutoff(self):
        ingest(self.db, [("2025-10-01", 1400, 500)], retrieved="2026-10-30")
        ingest(self.db, [("2025-10-01", 1420, 500)], retrieved="2026-11-06")
        earlier = series(self.db, as_of="2026-10-31")
        later = series(self.db, as_of="2026-11-06")
        self.assertEqual(earlier["segments"][0]["last_value"], 1400)
        self.assertEqual(later["segments"][0]["last_value"], 1420)

    def test_theil_sen_is_a_level_slope_not_cognitive_multiplier(self):
        ingest(self.db, [
            ("2025-08-01", 1400, 500),
            ("2025-09-01", 1410, 500),
            ("2025-10-01", 1420, 500),
            ("2025-11-01", 1430, 500)])
        result = series(self.db)
        seg = result["segments"][0]
        self.assertGreater(seg["theil_sen_level_change_per_90d"], 0)
        self.assertIsNone(result["compute_parameter_conversion"])

    def test_readiness_does_not_invent_parameter_or_capability_series(self):
        ingest(self.db, [("2025-08-01", 1400, 500)])
        result = study_readiness(self.db, as_of="2026-11-06")
        self.assertEqual(result["source_observations"]["preference"], 1)
        self.assertEqual(result["longitudinal_candidate_strata_with_3_dates"], 0)
        self.assertFalse(result["can_identify_2_to_3x_cognition"])
        self.assertFalse(result["can_identify_5_to_10x_parameters"])

    def test_filtered_history_uses_exact_model_and_respects_limits(self):
        urls=[]
        def fake_fetch(url):
            urls.append(url)
            return {
                "rows": [
                    synthetic_row("2025-08-01", 1400),
                    synthetic_row("2025-09-01", 1410),
                    synthetic_row("2025-10-01", 1420),
                ],
                "num_rows_total": 3, "partial": False,
            }
        result = import_history(
            self.db, config="text_style_control", model=MODEL,
            retrieved_on="2026-11-06", fetch=fake_fetch)
        self.assertEqual(result["rows_seen"], 3)
        self.assertEqual(result["truncated_by_page_cap"], False)
        self.assertEqual(result["historical_status"], "retrospective_only")
        self.assertIn("where=", urls[0])
        self.assertEqual(len(series(self.db)["segments"][0]["points"]), 3)

    def test_filtered_history_rejects_mismatched_or_partial_provider_data(self):
        def wrong(_):
            return {"rows":[synthetic_row("2025-08-01", model="WRONG")],
                    "num_rows_total":1, "partial":False}
        with self.assertRaises(CatalogError):
            import_history(self.db, config="text", model=MODEL, fetch=wrong)
        def partial(_):
            return {"rows":[], "num_rows_total":100, "partial":True}
        with self.assertRaises(CatalogError):
            import_history(self.db, config="text", model=MODEL, fetch=partial)

    def test_filter_http500_falls_back_to_exact_name_search(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if "/filter?" in url:
                raise CatalogError("API HTTP 500. Respect provider limits and retry manually later.")
            return {
                "rows": [
                    synthetic_row("2025-08-01", 1410, model=MODEL),
                    synthetic_row("2025-09-01", 1700, model="OTHER"),
                ],
                "num_rows_total": 2, "partial": False,
            }
        result = import_history(
            self.db, config="text_style_control", model=MODEL,
            retrieved_on="2026-11-06", fetch=fetch)
        self.assertEqual(result["request_method"], "search_exact_postfilter_nonexhaustive")
        self.assertEqual(result["rows_seen"], 1)
        self.assertFalse(result["is_exhaustive"])
        self.assertEqual(len(calls), 2)
        obs = series(self.db)
        self.assertEqual(obs["unique_published_dates"], 1)

    def test_filter_fallback_does_not_ignore_http429(self):
        calls = []
        def fetch(url):
            calls.append(url)
            raise CatalogError("API HTTP 429. Respect provider limits.")
        with self.assertRaises(CatalogError):
            import_history(self.db, config="text", model=MODEL,
                           retrieved_on="2026-11-06", fetch=fetch)
        self.assertEqual(len(calls), 1)

    def test_sql_literals_escaped_and_limit_validated(self):
        u = filter_url(config="text", model="O'Hara (High)")
        self.assertIn("O%27%27Hara", u)
        self.assertIn("leaderboard_publish_date", u)
        with self.assertRaises(CatalogError):
            filter_url(config="text", model="a\nb")
        with self.assertRaises(CatalogError):
            filter_url(config="text", model="good", length=101)
        with self.assertRaises(CatalogError):
            import_history(self.db, config="text", model=MODEL, max_pages=100)


if __name__=="__main__":
    unittest.main()
