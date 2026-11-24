import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from fsl_substitution.audit import ASSOError, ROOT, audit, load_catalog, load_json

FIXTURE = ROOT / "tests/fixtures/asso_synthetic_v0.21.json"
EARLY = "2026-11-24T10:30:00Z"
LATE = "2026-11-24T12:30:00Z"


def fraction(n, d):
    return {"numerator": n, "denominator": d}


class ASSOTests(unittest.TestCase):
    def setUp(self):
        self.data = load_json(FIXTURE)

    def run_audit(self, at=LATE, mode="strict_known_at_time"):
        return audit(self.data, as_of=at, mode=mode)

    def rows(self, result=None):
        result = result or self.run_audit()
        return {r["contract_id"]: r for r in result["synthetic_scenario"]["contract_rows"]}

    def test_catalog_unchanged_parent_axes_and_missing(self):
        c = load_catalog()
        self.assertEqual(len(c["axes"]), 12)
        self.assertTrue(all(a["value"] is None for a in c["axes"]))
        old = load_json(ROOT / "data/giccf_capability_catalog_v0.13.json")
        self.assertEqual(len(old["capability_axes"]), 28)
        self.assertEqual(len(old["civilization_domains"]), 38)

    def test_source_manifest_exact_bytes(self):
        base = ROOT / "docs/astt"
        m = load_json(base / "source_manifest.json")
        self.assertEqual(len(m["files"]), 14)
        for entry in m["files"]:
            b = (base / entry["path"]).read_bytes()
            self.assertEqual(len(b), entry["bytes"])
            self.assertEqual(hashlib.sha256(b).hexdigest(), entry["sha256"])
            self.assertEqual(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(), entry["git_blob_sha"])
            self.assertFalse(b.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", b)
            b.decode("utf-8", errors="strict")

    def test_synthetic_not_empirical(self):
        r = self.run_audit()
        self.assertIsNone(r["recorded_observational_assertions"])
        self.assertFalse(r["independent_empirical_certification"])
        self.assertIsNone(r["global_occupation_replacement_rate"])
        self.assertIsNone(r["universal_intelligence_score"])

    def test_inversion_and_separate_outcomes(self):
        r = self.run_audit()
        p = r["synthetic_scenario"]["priority_inversion_pairs"][0]
        self.assertEqual(p["inverted_pairs"], 1)
        self.assertEqual(p["comparable_strict_pairs"], 1)
        m = self.rows(r)["math-example"]["metrics"]
        self.assertEqual(m["SUB-01"]["valid_acceptance_per_attempt"], fraction(7,10))
        self.assertEqual(m["SUB-08"]["transferred_per_prior_human_task_unit"], fraction(3,5))
        self.assertEqual(m["SUB-10"]["fte_compression"], fraction(0,1))
        self.assertEqual(m["SUB-10"]["paid_minutes_compression"], fraction(1,5))
        self.assertEqual(m["SUB-09"]["human_ai_productivity_uplift"], fraction(1,2))

    def test_missing_not_zero_bounds(self):
        r = self.run_audit()
        row = self.rows(r)["unmeasured-example"]
        self.assertIsNone(row["metrics"]["SUB-01"]["valid_acceptance_per_attempt"])
        self.assertEqual(row["metrics"]["SUB-01"]["technical_qualification"], "unknown")
        dom = r["synthetic_scenario"]["domain_frame_summaries"][row["domain_id"]]["technical"]
        self.assertEqual(dom["known_share"], fraction(1,1))
        self.assertEqual(dom["lower_bound"], fraction(2,5))
        self.assertEqual(dom["upper_bound"], fraction(1,1))

    def test_asof_correction_and_retrospective(self):
        before = self.run_audit(EARLY)
        middle = self.run_audit("2026-11-24T11:30:00Z")
        retro = self.run_audit("2026-11-24T11:30:00Z", "retrospective_reconstruction")
        self.assertEqual(before["visible_event_count"], 6)
        self.assertEqual(middle["visible_event_count"], 6)
        self.assertEqual(retro["visible_event_count"], 7)
        self.assertEqual(self.rows(middle)["math-example"]["metrics"]["SUB-05"]["net_benefit_minor"], 7000)
        self.assertEqual(self.rows(retro)["math-example"]["metrics"]["SUB-05"]["net_benefit_minor"], 6000)
        self.assertEqual(self.run_audit()["current_event_count"], 6)

    def test_before_registration(self):
        r = self.run_audit("2026-11-16")
        self.assertEqual(r["visible_contract_count"], 0)
        self.assertEqual(r["visible_event_count"], 0)

    def test_no_synthetic_promotion(self):
        self.data["data_class"] = "observational"
        with self.assertRaises(ASSOError):
            self.run_audit()

    def test_no_observational_claim_without_source(self):
        self.data["data_class"] = "observational"
        for e in self.data["events"]:
            e["evidence_tier"] = "provider_claim"
        with self.assertRaises(ASSOError):
            self.run_audit()

    def test_provider_claim_is_not_trial_measurement(self):
        self.data["data_class"] = "observational"
        for e in self.data["events"]:
            e["evidence_tier"] = "provider_claim"
            e["source_url"] = "https://example.invalid/fictional-test-only"
        r = self.run_audit()
        self.assertIsNone(r["synthetic_scenario"])
        self.assertFalse(r["independent_empirical_certification"])
        rows = r["recorded_observational_assertions"]["contract_rows"]
        self.assertTrue(all(x["metrics"]["SUB-01"]["valid_acceptance_per_attempt"] is None for x in rows))

    def test_observational_repeatable_assertion_requires_artifact(self):
        self.data["data_class"] = "observational"
        for e in self.data["events"]:
            e["evidence_tier"] = "repeatable_test"
            e["source_url"] = "https://example.invalid/fictional-test-only"
        with self.assertRaises(ASSOError):
            self.run_audit()

    def test_failed_physical_gate_does_not_erase_technical(self):
        self.data["events"][1]["data"]["safety"] = "failed"
        r = self.rows()["food-example"]["metrics"]
        self.assertEqual(r["SUB-01"]["technical_qualification"], "passed")
        self.assertEqual(r["SUB-05"]["operational_readiness"], "failed")
        self.assertEqual(r["SUB-12"]["deployment_gate"], "failed")
        self.assertEqual(self.run_audit()["synthetic_scenario"]["priority_inversion_pairs"][0]["comparable_strict_pairs"], 0)

    def test_missing_physical_receipt(self):
        self.data["events"][1]["data"]["physical_receipt_sha256"] = None
        r = self.rows()["food-example"]["metrics"]
        self.assertEqual(r["SUB-05"]["operational_readiness"], "unknown")

    def test_estimates_not_actual(self):
        self.data["events"][3]["data"]["cost_basis"] = "estimate"
        m = self.rows()["food-example"]["metrics"]["SUB-05"]
        self.assertEqual(m["actual_economic_qualification"], "unknown")
        self.assertEqual(m["estimated_economic_qualification"], "passed")

    def test_incomplete_cost_not_net(self):
        self.data["events"][3]["data"]["full_cost_attested"] = False
        self.assertIsNone(self.rows()["food-example"]["metrics"]["SUB-05"]["net_benefit_minor"])

    def test_noncomparable_group(self):
        self.data["contracts"][1]["comparison_group"] = "different"
        self.assertTrue(all(p["comparable_strict_pairs"] == 0 for p in
                            self.run_audit()["synthetic_scenario"]["priority_inversion_pairs"]))

    def test_zero_attempts_and_zero_denominators(self):
        d = self.data["events"][0]["data"]
        for k in ("attempts","delivered","accepted","top_quality","raw_error_trials","accepted_error_trials","human_core_minutes"):
            d[k] = 0
        m = self.rows()["math-example"]["metrics"]
        self.assertIsNone(m["SUB-01"]["valid_acceptance_per_attempt"])
        self.assertEqual(m["SUB-01"]["technical_qualification"], "unknown")

    def test_invalid_counts(self):
        for field, value in (("accepted",11),("top_quality",8),("attempts",True),("raw_error_trials",-1)):
            with self.subTest(field=field):
                original = self.data["events"][0]["data"][field]
                self.data["events"][0]["data"][field] = value
                with self.assertRaises(ASSOError):
                    self.run_audit()
                self.data["events"][0]["data"][field] = original

    def test_invalid_transfer_and_layoffs(self):
        for field,value in (("transferred_prior_task_units",101),("involuntary_exits",2)):
            with self.subTest(field=field):
                original = self.data["events"][4]["data"][field]
                self.data["events"][4]["data"][field] = value
                with self.assertRaises(ASSOError):
                    self.run_audit()
                self.data["events"][4]["data"][field] = original

    def test_correction_fork_and_duplicate_id_rejected(self):
        for field,value in (("supersedes_event_id","food-cost"),("event_id","math-cost")):
            with self.subTest(field=field):
                original = self.data["events"][-1][field]
                self.data["events"][-1][field] = value
                with self.assertRaises(ASSOError):
                    self.run_audit()
                self.data["events"][-1][field] = original

    def test_future_and_late_registration_rejected(self):
        self.data["registered_at"] = "2026-11-24T10:00:00Z"
        with self.assertRaises(ASSOError):
            self.run_audit()

    def test_clock_error(self):
        self.data["events"][0]["fsl_recorded_at"] = "2026-11-24T01:00:00Z"
        with self.assertRaises(ASSOError):
            self.run_audit()

    def test_broken_contract_and_currency(self):
        for field,value in (("weight",0),("domain_id","D99"),("environment","magic")):
            with self.subTest(field=field):
                original = self.data["contracts"][0][field]
                self.data["contracts"][0][field] = value
                with self.assertRaises(ASSOError):
                    self.run_audit()
                self.data["contracts"][0][field] = original
        self.data["currency"] = "TWD/USD"
        with self.assertRaises(ASSOError):
            self.run_audit()

    def test_cli_roundtrip(self):
        run = subprocess.run([sys.executable, "-m", "fsl_substitution.cli", "audit",
                              "--file", str(FIXTURE), "--as-of", LATE],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(run.stdout), self.run_audit())
