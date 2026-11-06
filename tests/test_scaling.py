import copy
import json
import tempfile
import unittest
from pathlib import Path

from frontier_scaling import (
    ResearchError, append_evidence, asof_events, backtest, estimate,
    overlay_evidence, read_evidence, span
)

CASES = json.loads((Path(__file__).resolve().parent.parent /
                    "data" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]


class ScalingTests(unittest.TestCase):
    def test_reference_bounds_positive(self):
        result = estimate(CASES[0])
        self.assertFalse(result["capacity_is_observed"])
        for pair in result["bounds"].values():
            self.assertGreater(pair[0], 0)
            self.assertLessEqual(pair[0], pair[1])
        self.assertEqual(result["capability_hypothesis"]["identification"],
                         "UNMEASURED_NOT_DERIVED_FROM_PARAMETERS")

    def test_planned_site_gated(self):
        with self.assertRaises(ResearchError):
            estimate(CASES[1])
        result = estimate(CASES[1], include_unbuilt=True)
        self.assertEqual(result["site_stage"], "planned")

    def test_fleet_not_automatically_single_run(self):
        result = estimate(CASES[1], include_unbuilt=True)["bounds"]
        self.assertEqual(result["fleet_gpus"][1], 160000)
        self.assertAlmostEqual(result["connected_run_gpus"][1], 24000)
        case = copy.deepcopy(CASES[1])
        case["run"]["cross_site_fabric"] = True
        pooled = estimate(case, include_unbuilt=True)["bounds"]
        self.assertAlmostEqual(pooled["connected_run_gpus"][1], 96000)

    def test_power_conversion(self):
        case = copy.deepcopy(CASES[0])
        case["site"].pop("gpu_count")
        case["site"].update(power_mw=100, pue=1.25,
                            it_system_share=0.7, system_w_per_gpu=2000)
        self.assertAlmostEqual(estimate(case)["bounds"]["gpus_per_site"][0], 28000)

    def test_duration_doubles_flops(self):
        case = copy.deepcopy(CASES[0])
        case["run"]["days"] = [90, 90]
        before = estimate(case)["bounds"]["single_run_flops"]
        case["run"]["days"] = [180, 180]
        after = estimate(case)["bounds"]["single_run_flops"]
        for x, y in zip(before, after):
            self.assertAlmostEqual(y / x, 2)

    def test_tokens_reduce_inverted_parameter_count(self):
        case = copy.deepcopy(CASES[0])
        case["run"]["tokens"] = 2e13
        before = estimate(case)["bounds"]["active_parameters"]
        case["run"]["tokens"] = 4e13
        after = estimate(case)["bounds"]["active_parameters"]
        self.assertAlmostEqual(before[0] / after[0], 2)

    def test_reject_bad_inputs(self):
        for value in (True, float("nan"), [-1, 2], [2, 1]):
            with self.assertRaises(ResearchError):
                span(value, "bad")
        case = copy.deepcopy(CASES[0])
        case["run"]["mfu"] = 1.2
        with self.assertRaises(ResearchError):
            estimate(case)

    def test_evidence_asof_and_retraction(self):
        event = dict(id="e1", scenario_id=CASES[0]["id"],
                     recorded_at="2026-11-07T12:00:00+00:00",
                     field="run.mfu", value=[0.3, 0.5],
                     source_kind="assumption", state="asserted")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            append_evidence(path, event)
            prefix = path.read_bytes()
            self.assertEqual(asof_events(read_evidence(path), "2026-11-06"), [])
            with self.assertRaises(ResearchError):
                append_evidence(path, event)
            retract = dict(event, id="e2", recorded_at="2026-11-08T12:00:00+00:00",
                           value=None, state="retracted")
            append_evidence(path, retract)
            self.assertTrue(path.read_bytes().startswith(prefix))
            old, _ = overlay_evidence(CASES[0], read_evidence(path), "2026-11-07")
            new, _ = overlay_evidence(CASES[0], read_evidence(path), "2026-11-08")
            self.assertEqual(old["run"]["mfu"], [0.3, 0.5])
            self.assertEqual(new["run"]["mfu"], CASES[0]["run"]["mfu"])

    def test_source_required(self):
        event = dict(id="bad", scenario_id="x", recorded_at="2026-11-06",
                     field="site.gpu_count", value=100,
                     source_kind="manufacturer", state="asserted")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ResearchError):
                append_evidence(Path(directory) / "e.jsonl", event)

    def test_leakage_guard(self):
        forecast = {"scenario_id": "synthetic", "as_of": "2026-11-06",
                    "bounds": {"active_parameters": [1e9, 10e9]}}
        actual = {"scenario_id": "synthetic", "published_at": "2027-01-02",
                  "metric": "active_parameters", "value": 5e9,
                  "source_url": "https://example.org/disclosure"}
        self.assertEqual(backtest(forecast, [actual])["interval_coverage"], 1)
        actual["published_at"] = "2026-11-02"
        with self.assertRaises(ResearchError):
            backtest(forecast, [actual])


if __name__ == "__main__":
    unittest.main()
