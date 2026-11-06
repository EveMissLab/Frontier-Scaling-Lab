"""FSL v0.11 temporal narrative replay conformance, source-bound and no mind-reading.

The cases include real original interview source references but all analytical
hypotheses are unverified 2026 research interpretations.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from fsl_discourse.replay import ReplayError,validate_cases,replay_case,replay_all

ROOT=Path(__file__).resolve().parent.parent
def load(name):
    return json.loads((ROOT/"data"/name).read_text(encoding="utf-8"))

DISCOURSE=load("agi_asi_public_interviews_seed_2026-11-07.json")
MARKET=load("official_ai_history_2024_2026_v0.9.json")
CASES=load("longitudinal_narrative_cases_v0.11.json")


def run(case_id,date="2026-11-07",mode="retrospective"):
    return replay_case(DISCOURSE,MARKET,CASES,case_id=case_id,
                       as_of=date,mode=mode)


class NarrativeReplayTests(unittest.TestCase):
    def test_three_sourced_cases_open_to_multiple_hypotheses(self):
        r=validate_cases(CASES,discourse=DISCOURSE,market=MARKET)
        self.assertEqual(r["case_count"],3)
        self.assertEqual(r["analyst_authored_on"],"2026-11-07")
        self.assertEqual(r["actual_causal_influences_certified"],0)
        self.assertEqual(r["actual_strategy_reversals_certified"],0)
        self.assertEqual(sum(len(c["candidate_interpretations"])
                             for c in CASES["cases"]),9)
        self.assertEqual(sum(len(c["discriminating_evidence"])
                             for c in CASES["cases"]),7)

    def test_dario_replay_on_2023_08_08_blocks_future_and_2026_analysis(self):
        r=run("dario-2023-2026-scaling-diffusion","2023-08-08")
        self.assertEqual(r["baseline_cutoff"],"2023-08-08")
        self.assertEqual(sum(x["is_visible_at_requested_cutoff"]
                             for x in r["baseline_utterances"]),2)
        self.assertFalse(any(x["is_visible_at_requested_cutoff"]
                              for x in r["later_utterances"]))
        self.assertFalse(any(x["visible_at_asof"]
                              for x in r["later_official_product_events"]))
        self.assertEqual(r["alternative_interpretations"],[])
        self.assertIsNone(r["reversibility_probe"])
        self.assertFalse(r["causal_relation_proved"])

    def test_strict_2023_has_no_retroactively_discovered_fsl_knowledge(self):
        r=run("dario-2023-2026-scaling-diffusion",
              "2023-08-08","strict_known_at_time")
        self.assertFalse(any(x["is_visible_at_requested_cutoff"]
                              for x in r["baseline_utterances"]))
        self.assertEqual(r["documented_observation_count"],0)
        self.assertTrue(all(x["historical_original_forecast_by_FSL"] is False
                            for x in r["baseline_utterances"]))

    def test_dario_2026_compatible_but_not_proven_identical(self):
        r=run("dario-2023-2026-scaling-diffusion")
        self.assertEqual(r["documented_observation_count"],8)
        self.assertEqual(len(r["alternative_interpretations"]),3)
        self.assertEqual(len(r["later_utterances"]),4)
        self.assertFalse(r["narrative_contradiction_proved"])
        self.assertFalse(r["private_belief_change_proved"])
        kinds={h["kind"] for h in r["alternative_interpretations"]}
        self.assertEqual(kinds,{"possible_continuity","possible_reframing",
                                "insufficient_evidence"})

    def test_demis_2030_forecast_not_due_in_2026(self):
        r=run("demis-2025-2030-high-bar-agi")
        self.assertEqual(len(r["dated_forecast_statuses"]),1)
        forecast=r["dated_forecast_statuses"][0]
        self.assertEqual(forecast["target_by"],"2030-12-31")
        self.assertEqual(forecast["speaker_probability"],"0.50")
        self.assertEqual(forecast["status"],"not_due")
        self.assertIsNone(forecast["predictive_success_known"])
        self.assertFalse(r["causal_relation_proved"])

    def test_hypothetical_2031_still_not_automatically_scored(self):
        r=run("demis-2025-2030-high-bar-agi","2031-01-01")
        self.assertEqual(r["dated_forecast_statuses"][0]["status"],
                         "deadline_passed_needs_independent_adjudication")
        self.assertIsNone(r["dated_forecast_statuses"][0]["predictive_success_known"])
        self.assertFalse(r["new_independent_task_outcome_found"])

    def test_demis_gemini_release_does_not_prove_game_or_agi(self):
        r=run("demis-2025-2030-high-bar-agi")
        self.assertEqual(sum(x["visible_at_asof"]
                             for x in r["later_official_product_events"]),2)
        self.assertTrue(all(not x["proves_functional_AGI_ASI"]
                            for x in r["later_official_product_events"]))
        self.assertTrue(r["reversibility_probe"]["alternative_routes"])
        self.assertFalse(r["reversal_or_irreversibility_proved"])

    def test_liang_2024_baseline_without_future_model(self):
        r=run("liang-2024-2026-architecture-openness","2024-07-22")
        self.assertEqual(sum(x["is_visible_at_requested_cutoff"]
                             for x in r["baseline_utterances"]),5)
        self.assertFalse(any(x["visible_at_asof"]
                             for x in r["later_official_product_events"]))
        self.assertEqual(r["alternative_interpretations"],[])

    def test_liang_2025_r1_visible_not_2026_v4(self):
        r=run("liang-2024-2026-architecture-openness","2025-12-31")
        self.assertEqual(sum(x["visible_at_asof"]
                             for x in r["later_official_product_events"]),1)
        self.assertEqual(r["later_official_product_events"][0]["event_id"],
                         "2025-deepseek-r1")
        self.assertFalse(r["actual_company_direction_identified"])
        self.assertFalse(r["reversal_or_irreversibility_proved"])

    def test_liang_2026_source_does_not_establish_irreversibility(self):
        r=run("liang-2024-2026-architecture-openness")
        self.assertEqual(sum(x["visible_at_asof"]
                             for x in r["later_official_product_events"]),2)
        self.assertEqual(r["reversibility_probe"]["decision_authority"],
                         "not_independently_verified")
        self.assertTrue(all(x["feasibility_status"]=="unknown"
                            for x in r["reversibility_probe"]["alternative_routes"]))

    def test_replay_all_conforms_to_2024_2025_2026_cutoffs(self):
        self.assertEqual(len(replay_all(DISCOURSE,MARKET,CASES,
                           as_of="2023-08-08")["cases"]),1)
        self.assertEqual(len(replay_all(DISCOURSE,MARKET,CASES,
                           as_of="2024-12-31")["cases"]),2)
        self.assertEqual(len(replay_all(DISCOURSE,MARKET,CASES,
                           as_of="2025-12-31")["cases"]),3)
        r=replay_all(DISCOURSE,MARKET,CASES,as_of="2026-11-07")
        self.assertEqual(r["identified_causal_effects"],0)
        self.assertEqual(r["actual_reversibility_certificates"],0)
        self.assertEqual(r["AGI_ASI_verified_claims"],0)

    def test_reject_fake_baseline_using_a_future_speaker_statement(self):
        bad=deepcopy(CASES)
        bad["cases"][0]["baseline_claim_ids"].append("dario26-scaled-as-expected")
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)

    def test_reject_swapping_speakers_or_past_events(self):
        bad=deepcopy(CASES)
        bad["cases"][0]["baseline_claim_ids"]=["liang24-agi-target"]
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)
        bad=deepcopy(CASES)
        bad["cases"][1]["external_event_ids"].append("2024-openai-gpt4o")
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)

    def test_competing_hypotheses_cannot_proclaim_winner(self):
        bad=deepcopy(CASES)
        bad["cases"][0]["candidate_interpretations"][0]["inference_status"]="confirmed_true"
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)
        bad=deepcopy(CASES)
        bad["cases"][1]["candidate_interpretations"].pop()
        bad["cases"][1]["candidate_interpretations"].pop()
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)

    def test_no_fake_real_decision_or_return_path(self):
        bad=deepcopy(CASES)
        bad["cases"][2]["reversibility_probe"]["actual_reversal_observed"]=True
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)
        bad=deepcopy(CASES)
        bad["cases"][2]["reversibility_probe"]["alternative_routes"][0]["feasibility_status"]="reversible"
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)

    def test_governance_or_external_result_cannot_be_declared_verified(self):
        bad=deepcopy(CASES)
        bad["cases"][2]["discriminating_evidence"][0]["status"]="certified"
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)

    def test_analyst_authored_2026_cannot_be_a_2023_prediction(self):
        bad=deepcopy(CASES)
        bad["analyst_authored_on"]="2023-08-08"
        with self.assertRaises(ReplayError):
            validate_cases(bad,discourse=DISCOURSE,market=MARKET)

    def test_replay_requires_known_case_and_admissible_date(self):
        with self.assertRaises(ReplayError):
            run("dario-2023-2026-scaling-diffusion","2022-01-01")
        with self.assertRaises(ReplayError):
            run("unregistered-case")
        with self.assertRaises(ReplayError):
            run("dario-2023-2026-scaling-diffusion","2026-13-44")

if __name__=="__main__":
    unittest.main()
