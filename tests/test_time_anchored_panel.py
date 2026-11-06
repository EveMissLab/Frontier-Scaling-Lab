"""Time-anchored cross-provider economics cannot erase execution chronology.

All model prices, accepted results and run clocks in this fixture are
fictitious. Source release records are separately date-only real metadata.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from fsl_economics.temporal_panel import compare_time_anchored
from fsl_economics.timeaxis import TemporalError

F=Path(__file__).resolve().parent/"fixtures"/"time_anchored_task_panel_synthetic.json"
FIXTURE=json.loads(F.read_text(encoding="utf-8"))


def get_clock(case,ci=0,ti=0):
    target=case["panel"]["cohorts"][ci]
    trial=target["trials"][ti]
    return next(x["clock"] for x in case["mission_clocks"] if
                x["cohort_id"]==target["cohort_id"] and
                x["trial_id"]==trial["trial_id"])


class TimeAnchoredEconomicsTests(unittest.TestCase):
    def test_all_attempts_have_time_and_month_assignment(self):
        r=compare_time_anchored(deepcopy(FIXTURE))
        self.assertTrue(r["all_attempts_have_valid_timestamps"])
        self.assertEqual(len(r["observed_trial_clocks"]),3)
        self.assertEqual(sum(len(x["trial_timestamps"])
                         for x in r["observed_trial_clocks"]),9)
        self.assertFalse(r["can_assert_24_48h_autonomy"])
        self.assertFalse(r["independently_verified_task_success"])
        self.assertEqual(r["cutoff_at_utc"],"2026-10-31T15:59:00+00:00")

    def test_cutoff_must_precede_nothing_that_is_used(self):
        data=deepcopy(FIXTURE)
        data["cutoff_at"]="2026-10-07T08:00:00+08:00"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_no_missing_or_extra_trial_clocks(self):
        data=deepcopy(FIXTURE)
        data["mission_clocks"].pop()
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)
        data=deepcopy(FIXTURE)
        data["mission_clocks"].append(deepcopy(data["mission_clocks"][0]))
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_reject_model_version_and_runtime_drift(self):
        data=deepcopy(FIXTURE)
        get_clock(data)["model_revision"]="MODIFIED"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)
        data=deepcopy(FIXTURE)
        get_clock(data)["runtime_manifest_sha256"]="8"*64
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_work_reported_in_earlier_month_is_not_october_outcome(self):
        data=deepcopy(FIXTURE)
        get_clock(data)["accepted_at"]="2026-11-01T00:00:00+08:00"
        get_clock(data)["captured_at"]="2026-11-01T01:00:00+08:00"
        data["cutoff_at"]="2026-11-02T00:00:00+08:00"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_acceptance_requires_final_timestamp_and_accepted_outcome(self):
        data=deepcopy(FIXTURE)
        get_clock(data)["accepted_at"]=None
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)
        data=deepcopy(FIXTURE)
        data["panel"]["cohorts"][0]["trials"][0]["outcome"]="failed_reported"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_source_price_newer_than_run_cannot_be_priced_historically(self):
        data=deepcopy(FIXTURE)
        get_clock(data)["pricing_effective_on"]="2026-11-01"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)
        data=deepcopy(FIXTURE)
        data["panel"]["cohorts"][0]["price_snapshot_on"]="2026-10-08"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_time_precision_and_timezone_are_required(self):
        data=deepcopy(FIXTURE)
        get_clock(data)["execution_started_at"]="2026-10-06T09:00:00"
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_censored_observation_requires_last_progress_not_fake_finish(self):
        data=deepcopy(FIXTURE)
        trial=data["panel"]["cohorts"][0]["trials"][1]
        trial["outcome"]="censored"
        clock=get_clock(data,0,1)
        clock["execution_finished_at"]=None
        clock["accepted_at"]=None
        result=compare_time_anchored(data)
        self.assertEqual(result["observed_trial_clocks"][0]
                         ["trial_timestamps"][1]["outcome"],"censored")
        clock["last_progress_at"]=None
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)

    def test_retrospective_price_is_flagged_not_rewritten(self):
        data=deepcopy(FIXTURE)
        clock=get_clock(data)
        clock["price_first_captured_on"]="2026-10-07"
        report=compare_time_anchored(data)
        record=report["observed_trial_clocks"][0]["trial_timestamps"][0]
        self.assertTrue(record["observed_time"]["price_quote_is_retrospective_only"])
        self.assertEqual(report["observed_trial_clocks"][0]["n_backfilled_prices"],1)
        self.assertFalse(report["can_assert_historical_forecast_accuracy"])

    def test_previously_frozen_task_hash_is_required(self):
        data=deepcopy(FIXTURE)
        get_clock(data)["task_contract_sha256"]="0"*64
        with self.assertRaises(TemporalError):
            compare_time_anchored(data)


if __name__=="__main__":
    unittest.main()
