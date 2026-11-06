"""AGI/ASI public interview history: attribution, vintage and no causal claims.

Fixtures are genuine PUBLIC original-interview paraphrases, never a private
mental-state dataset or an AGI attainment measurement.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from fsl_discourse.catalog import DiscourseError,validate,asof_view
from fsl_discourse.relations import reconcile
from fsl_discourse.cli import _trajectory

ROOT=Path(__file__).resolve().parent.parent
CAT=json.loads((ROOT/"data"/"agi_asi_public_interviews_seed_2026-11-07.json")
               .read_text(encoding="utf-8"))
LINK=json.loads((ROOT/"data"/"discourse_to_model_history_links_v0.10.json")
                .read_text(encoding="utf-8"))
MARKET=json.loads((ROOT/"data"/"official_ai_history_2024_2026_v0.9.json")
                  .read_text(encoding="utf-8"))


class DiscourseCorpusTests(unittest.TestCase):
    def test_six_organizations_first_seven_interviews_not_exhaustive(self):
        out=validate(CAT)
        self.assertEqual(out["speaker_count"],6)
        self.assertEqual(out["organization_count"],6)
        self.assertEqual(out["interview_count"],7)
        self.assertEqual(out["claim_count"],23)
        self.assertEqual(out["first_FSL_capture_Asia_Taipei"],"2026-11-07")
        self.assertFalse(out["internal_beliefs_inferred"])
        self.assertFalse(out["any_proven_causal_claim"])
        self.assertEqual(CAT["coverage_status"],"curated_seed_not_all_companies_not_exhaustive")

    def test_2024_strict_historical_forecast_cannot_know_2026_retrieval(self):
        report=asof_view(CAT,as_of="2024-12-31",mode="strict_known_at_time")
        self.assertEqual(report["included_claims"],0)
        self.assertFalse(any(r["original_forecast_knowledge"] for r in report["rows"]))
        self.assertFalse(any(r["included"] for r in report["rows"]))

    def test_retrospective_keeps_actual_publication_and_later_retrieval_dates(self):
        report=asof_view(CAT,as_of="2024-12-31",mode="retrospective")
        self.assertGreaterEqual(report["included_claims"],15)
        self.assertTrue(all(
            x["first_captured_on"]=="2026-11-07" for x in report["rows"]))
        included=[x for x in report["rows"] if x["included"]]
        self.assertTrue(all(not x["original_forecast_knowledge"] for x in included))
        self.assertTrue(all(not x["speaker_internal_belief_known"] for x in included))

    def test_dario_2023_and_2026_public_views_not_private_belief_shift(self):
        s=_trajectory(CAT,"dario-amodei","2026-11-07")
        self.assertEqual(s["source_publication_years"],["2023","2026"])
        self.assertEqual(len(s["claims"]),6)
        self.assertIsNone(s["observed_change_in_private_belief"])
        self.assertIsNone(s["observed_organizational_reversal"])

    def test_claude_2026_cannot_appear_in_2025_asof(self):
        report=asof_view(CAT,as_of="2025-12-31")
        self.assertFalse(any(
            r["included"] for r in report["rows"]
            if r["source_id"]=="dwarkesh-dario-2026"))

    def test_agi_asi_topics_are_source_explicit_not_invented(self):
        self.assertTrue(any("AGI" in c["topics"] for c in CAT["claims"]))
        # This pilot did not select a sourced, explicit ASI statement yet.
        self.assertFalse(any("ASI" in c["topics"] for c in CAT["claims"]))
        bad=deepcopy(CAT)
        bad["claims"][0]["topics"]=["MAGIC_SUPERINTELLIGENCE"]
        with self.assertRaises(DiscourseError):validate(bad)

    def test_explicit_probability_requires_speaker_and_semantic_definition(self):
        has=next(c for c in CAT["claims"] if
                 c["claim_id"]=="demis25-agi-2030")
        self.assertEqual(has["forecast"]["target_by"],"2030-12-31")
        self.assertEqual(has["forecast"]["probability"],"0.50")
        bad=deepcopy(CAT)
        next(c for c in bad["claims"] if
             c["claim_id"]=="demis25-agi-2030")["forecast"]["probability"]="1.5"
        with self.assertRaises(DiscourseError):validate(bad)
        bad=deepcopy(CAT)
        next(c for c in bad["claims"] if
             c["claim_id"]=="demis25-agi-2030")["forecast"]["citation_mode"]="model_assumed"
        with self.assertRaises(DiscourseError):validate(bad)

    def test_missing_original_speaker_role_or_affiliation_rejected(self):
        bad=deepcopy(CAT)
        bad["sources"][0]["speaker_id"]="not-the-original-interviewee"
        with self.assertRaises(DiscourseError):validate(bad)
        bad=deepcopy(CAT)
        bad["sources"][0]["role_at_time"]=""
        with self.assertRaises(DiscourseError):validate(bad)

    def test_no_mind_reading_or_wholesale_transcript_in_schema(self):
        bad=deepcopy(CAT)
        bad["claims"][0]["verbatim_quote"]="We absolutely achieved the AGI."
        with self.assertRaises(DiscourseError):validate(bad)
        bad=deepcopy(CAT)
        bad["claims"][0]["claim_scope"]="official_company_position"
        with self.assertRaises(DiscourseError):validate(bad)
        bad=deepcopy(CAT)
        bad["claims"][0]["annotation_status"]="confirmed_truth"
        with self.assertRaises(DiscourseError):validate(bad)

    def test_missing_timecode_and_section_blocks_unlocated_attribution(self):
        bad=deepcopy(CAT)
        bad["claims"][0]["source_locator"]={"timecode":None,"section":None}
        with self.assertRaises(DiscourseError):validate(bad)
        bad=deepcopy(CAT)
        bad["claims"][0]["source_locator"]["timecode"]="99:banana"
        with self.assertRaises(DiscourseError):validate(bad)

    def test_recorded_interview_time_is_unknown_not_fictional_published_midnight(self):
        self.assertTrue(all(s["interview_recorded_on"] is None
                            for s in CAT["sources"]))
        bad=deepcopy(CAT)
        bad["sources"][0]["interview_recorded_on"]="2025-01-01"
        with self.assertRaises(DiscourseError):validate(bad)

    def test_36kr_original_publisher_date_and_2024_liang_wenfeng(self):
        source=next(s for s in CAT["sources"] if s["source_id"]=="36kr-liang-2024")
        self.assertEqual(source["published_on"],"2024-07-22")
        self.assertEqual(source["transcript_origin"],"original_interviewer_qa")
        self.assertEqual(source["first_captured_on"],"2026-11-07")

    def test_first_reconciliation_seven_time_chains_no_causation(self):
        result=reconcile(CAT,MARKET,LINK,as_of="2026-11-07")
        self.assertEqual(len(result["relations"]),7)
        self.assertEqual(result["temporally_eligible_links"],7)
        self.assertEqual(result["causal_links_verified"],0)
        self.assertEqual(result["actual_strategy_reversals_verified"],0)
        self.assertTrue(all(
            not x["actual_reversibility_observed"] and
            not x["private_intention_inferred"]
            for x in result["relations"]))

    def test_history_with_same_speaker_future_is_not_proof_of_mental_reversal(self):
        result=reconcile(CAT,MARKET,LINK,as_of="2026-11-07")
        pair=next(x for x in result["relations"] if
                  x["relation_id"]=="dario23-mechanism-to-2026")
        self.assertEqual(pair["interpretation_candidate"],"reframing_candidate")
        self.assertFalse(pair["actual_reversibility_observed"])
        self.assertFalse(pair["factual_contradiction_proved"])

    def test_reconciliation_cannot_use_future_product_at_2024_cutoff(self):
        r=reconcile(CAT,MARKET,LINK,as_of="2024-12-31")
        self.assertEqual(r["temporally_eligible_links"],0)

    def test_hypothetical_causal_confirmation_and_reversal_blocked(self):
        bad=deepcopy(LINK)
        bad["relations"][0]["causal_status"]="established"
        with self.assertRaises(DiscourseError):reconcile(CAT,MARKET,bad,as_of="2026-11-07")
        bad=deepcopy(LINK)
        bad["relations"][0]["reversibility_status"]="proven_irreversible"
        with self.assertRaises(DiscourseError):reconcile(CAT,MARKET,bad,as_of="2026-11-07")

    def test_product_link_must_match_cited_v09_primary_source(self):
        bad=deepcopy(LINK)
        bad["relations"][2]["source_url"]="https://example.org/fake-product-page"
        with self.assertRaises(DiscourseError):reconcile(CAT,MARKET,bad,as_of="2026-11-07")

    def test_later_self_rearticulation_cannot_cross_speakers(self):
        bad=deepcopy(LINK)
        bad["relations"][0]["right_id"]="sam24-agi-definition"
        with self.assertRaises(DiscourseError):reconcile(CAT,MARKET,bad,as_of="2026-11-07")


if __name__=="__main__":
    unittest.main()
