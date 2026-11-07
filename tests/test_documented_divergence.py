"""Dated real-world AI product reversals vs controls (2019-2026).

The real cited facts are vendor/Reuters documentary reports. None is an
independently recreated GPT-2 weight-release audit, a production rollback
replay, evidence of private AGI beliefs, or proof of structural irreversibility.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import unittest

from fsl_discourse.divergence import DivergenceError,validate,replay

PATH=(Path(__file__).resolve().parent.parent/"data"/
      "ai_documented_divergences_2019_2026_v0.12.json")
DATA=json.loads(PATH.read_text(encoding="utf-8"))


def by_id(panel,case_id):
    return next(x for x in panel["cases"] if x["case_id"]==case_id)


class DocumentaryDivergenceTests(unittest.TestCase):
    def test_source_catalog_8_cases_15_dated_origins(self):
        result=validate(DATA)
        self.assertEqual(result["case_count"],8)
        self.assertEqual(result["source_count"],15)
        self.assertEqual(result["first_FSL_reviewed_on"],"2026-11-07")
        self.assertFalse(result["independent_behavior_or_decision_verifications_completed"])
        self.assertEqual(result["AGI_ASI_attainments_proved"],0)

    def test_same_gpt2_weights_did_move_from_withheld_to_public_staged_release(self):
        r=replay(DATA,as_of="2019-11-05")
        case=by_id(r,"gpt2-staged-withheld-to-open")
        self.assertEqual(case["time_bounded_classification"],
                         "provider_documented_access_change")
        self.assertTrue(case["documented_state_transition_from_sources"])
        self.assertEqual(case["scope_relation"],"same_model_weights")
        self.assertFalse(case["corporate_strategic_reversal_verified"])
        self.assertFalse(case["technical_irreversibility_verified"])

    def test_2019_release_cannot_appear_at_2019_february_cutoff(self):
        case=by_id(replay(DATA,as_of="2019-02-14"),
                   "gpt2-staged-withheld-to-open")
        self.assertEqual(case["time_bounded_classification"],
                         "evidence_not_yet_visible")
        self.assertEqual(sum(x["included_at_cutoff"] for x in case["visible_events"]),1)
        self.assertIsNone(case["visible_events"][1]["state"])

    def test_strict_2019_knows_nothing_fsl_first_collected_in_2026(self):
        case=by_id(replay(DATA,as_of="2019-11-05",
                          mode="strict_known_at_time"),
                   "gpt2-staged-withheld-to-open")
        self.assertFalse(any(e["included_at_cutoff"] for e in case["visible_events"]))
        self.assertFalse(case["documented_state_transition_from_sources"])

    def test_gpt4o_rollback_is_local_and_provider_reported(self):
        r=replay(DATA,as_of="2026-11-07")
        case=by_id(r,"gpt4o-2025-sycophancy-rollback")
        self.assertEqual(case["time_bounded_classification"],
                         "provider_documented_local_model_rollback")
        self.assertTrue(case["documented_state_transition_from_sources"])
        self.assertFalse(case["independent_review_done"])
        self.assertFalse(case["speaker_belief_change_verified"])
        self.assertEqual(case["scope_relation"],"same_serving_snapshot_family")

    def test_intention_vs_realized_behavior_mismatch_not_independently_proved(self):
        case=by_id(replay(DATA,as_of="2026-11-07"),
                   "gpt4o-2025-sycophancy-rollback")
        self.assertTrue(case["provider_reports_intent_outcome_gap"])
        self.assertFalse(case["outcome_gap_independently_verified"])
        before=by_id(replay(DATA,as_of="2025-04-25"),
                     "gpt4o-2025-sycophancy-rollback")
        self.assertFalse(before["provider_reports_intent_outcome_gap"])
        self.assertFalse(before["documented_state_transition_from_sources"])
        actual=DATA["cases"][1]["intended_effect_vs_observed"]
        self.assertEqual(actual["observed_effect_source_id"],
                         "gpt4o-2025-retro-analysis")

    def test_scopeless_postmortem_cannot_prove_belief_mismatch(self):
        bad=deepcopy(DATA)
        bad["cases"][1]["intended_effect_vs_observed"]["same_deployment_unit"]=False
        with self.assertRaises(DivergenceError):
            validate(bad)
        bad=deepcopy(DATA)
        bad["cases"][1]["intended_effect_vs_observed"]["provisional_gap_status"] = "independently_proved"
        with self.assertRaises(DivergenceError):
            validate(bad)

    def test_april_28_event_only_disclosed_by_may_2_postmortem(self):
        case=by_id(replay(DATA,as_of="2025-04-28"),
                   "gpt4o-2025-sycophancy-rollback")
        self.assertEqual(case["time_bounded_classification"],
                         "evidence_not_yet_visible")
        event=case["visible_events"][1]
        self.assertEqual(event["occurred_on"],"2025-04-28")
        self.assertEqual(event["original_published_on"],"2025-05-02")
        self.assertFalse(event["included_at_cutoff"])
        self.assertTrue(event["later_report_can_describe_earlier_event"])

    def test_o4mini_unknown_original_deployment_date_stays_unknown(self):
        case=by_id(replay(DATA,as_of="2025-06-06"),
                   "o4mini-2025-rollback-unknown-start")
        self.assertEqual(case["time_bounded_classification"],
                         "provider_reported_rollback_original_deploy_day_unknown")
        self.assertIsNone(case["visible_events"][0]["occurred_on"])
        self.assertTrue(case["documented_state_transition_from_sources"])
        self.assertFalse(case["independent_review_done"])

    def test_voice_schedule_does_not_gain_fake_fixed_alpha_deadline(self):
        case=by_id(replay(DATA,as_of="2024-06-25"),
                   "gpt4o-voice-2024-schedule-change")
        self.assertEqual(case["time_bounded_classification"],
                         "documented_same_feature_schedule_revision")
        self.assertTrue(case["documented_state_transition_from_sources"])
        self.assertFalse(case["visible_events"][2]["included_at_cutoff"])
        self.assertNotIn("exact_delay_days",case)

    def test_september_voice_availability_is_not_july_same_alpha_cohort(self):
        case=by_id(replay(DATA,as_of="2024-09-24"),
                   "gpt4o-voice-2024-schedule-change")
        self.assertEqual(sum(e["included_at_cutoff"] for e in
                             case["visible_events"]),3)
        self.assertFalse(case["predictive_correctness_verified"])
        self.assertFalse(case["corporate_strategic_reversal_verified"])

    def test_different_gptoss_families_cannot_count_as_old_gpt_rollback(self):
        case=by_id(replay(DATA,as_of="2025-08-05"),
                   "gpt2-to-gptoss-different-families")
        self.assertEqual(case["time_bounded_classification"],
                         "two_distinct_model_families_not_a_rollback")
        self.assertFalse(case["documented_state_transition_from_sources"])
        self.assertEqual(case["scope_relation"],"different_model_family")

    def test_dario_potentially_consistent_does_not_prove_contradiction(self):
        case=by_id(replay(DATA,as_of="2026-11-07"),
                   "dario-2023-2026-possible-continuity")
        self.assertEqual(case["time_bounded_classification"],
                         "public_wording_may_be_compatible")
        self.assertFalse(case["speaker_belief_change_verified"])
        self.assertFalse(case["corporate_strategic_reversal_verified"])

    def test_demis_2030_forecast_not_due(self):
        case=by_id(replay(DATA,as_of="2026-11-07"),
                   "demis-2030-not-yet-due")
        self.assertEqual(case["time_bounded_classification"],
                         "forecast_not_yet_due")
        self.assertFalse(case["predictive_correctness_verified"])
        future=by_id(replay(DATA,as_of="2031-01-01"),
                     "demis-2030-not-yet-due")
        self.assertEqual(future["time_bounded_classification"],
                         "forecast_due_no_independent_adjudication")
        self.assertFalse(future["predictive_correctness_verified"])

    def test_liang_openness_scope_stays_underidentified(self):
        case=by_id(replay(DATA,as_of="2026-11-07"),
                   "liang-open-source-still-underidentified")
        self.assertEqual(case["time_bounded_classification"],
                         "claimed_direction_vs_actual_state_not_yet_resolved")
        self.assertFalse(case["corporate_strategic_reversal_verified"])

    def test_historical_2025_does_not_leak_2026_analyst_interpretation(self):
        case=by_id(replay(DATA,as_of="2025-06-06"),
                   "o4mini-2025-rollback-unknown-start")
        self.assertFalse(case["analyst_interpretation_visible_at_asof"])
        self.assertEqual(case["unanswered_questions"],[])

    def test_validations_block_fabricated_earlier_source_capture(self):
        bad=deepcopy(DATA)
        bad["sources"][0]["first_captured_on"]="2019-01-01"
        with self.assertRaises(DivergenceError):validate(bad)
        bad=deepcopy(DATA)
        bad["sources"][0]["published_on"]="2027-01-01"
        with self.assertRaises(DivergenceError):validate(bad)

    def test_rollback_cannot_be_claimed_from_two_different_families(self):
        bad=deepcopy(DATA)
        case=next(c for c in bad["cases"] if c["case_id"]==
                  "gpt4o-2025-sycophancy-rollback")
        case["scope_relation"]="different_model_family"
        with self.assertRaises(DivergenceError):validate(bad)

    def test_two_different_weights_cannot_be_claimed_to_rollback_each_other(self):
        bad=deepcopy(DATA)
        c=next(c for c in bad["cases"] if c["case_id"]==
               "gpt4o-2025-sycophancy-rollback")
        c["documented_events"][1]["subject_key"]="some-unrelated-model"
        with self.assertRaises(DivergenceError):
            validate(bad)
        bad=deepcopy(DATA)
        c=next(c for c in bad["cases"] if c["case_id"]==
               "gpt2-to-gptoss-different-families")
        c["documented_events"][1]["subject_key"]=c["documented_events"][0]["subject_key"]
        with self.assertRaises(DivergenceError):
            validate(bad)

    def test_access_transition_requires_dated_withheld_and_released_states(self):
        bad=deepcopy(DATA)
        bad["cases"][0]["documented_events"][1]["state"]="public_assertion"
        with self.assertRaises(DivergenceError):validate(bad)

    def test_no_fake_documentary_company_belief_or_asi_agreement(self):
        bad=deepcopy(DATA)
        bad["cases"][0]["fsl_analyst_status"]="proven_director_intent"
        with self.assertRaises(DivergenceError):validate(bad)
        panel=replay(DATA,as_of="2026-11-07")
        self.assertEqual(panel["scientifically_verified_personal_belief_change"],0)
        self.assertEqual(panel["AGI_ASI_or_general_irreversibility_proved"],0)

    def test_missing_original_rollback_date_rejected_if_fabricated(self):
        bad=deepcopy(DATA)
        case=next(c for c in bad["cases"] if c["case_id"]==
                  "o4mini-2025-rollback-unknown-start")
        case["documented_events"][0]["occurred_on"]="2025-06-02"
        with self.assertRaises(DivergenceError):validate(bad)

    def test_roadmap_scope_mismatch_rejected(self):
        bad=deepcopy(DATA)
        case=next(c for c in bad["cases"] if c["case_id"]==
                  "gpt4o-voice-2024-schedule-change")
        case["scope_relation"]="different_model_family"
        with self.assertRaises(DivergenceError):validate(bad)

    def test_primary_self_report_cannot_be_inflated_to_independent_judgment(self):
        r=replay(DATA,as_of="2026-11-07")
        self.assertEqual(r["fully_independently_adjudicated_direction_changes"],0)
        self.assertEqual(r["provider_documented_state_transitions"],4)
        self.assertFalse(any(c["independent_review_done"] for c in r["cases"]))
        self.assertTrue(all(not c["causal_influence_identified"] for c in r["cases"]))

    def test_invalid_undated_price_and_source_day_precision_guard(self):
        bad=deepcopy(DATA)
        bad["sources"][0]["published_on"]="2019-02-14T00:00:00Z"
        with self.assertRaises(DivergenceError):validate(bad)
        bad=deepcopy(DATA)
        bad["cases"][1]["documented_events"][1]["occurred_on"]="2026-12-01"
        with self.assertRaises(DivergenceError):validate(bad)


if __name__=="__main__":
    unittest.main()
