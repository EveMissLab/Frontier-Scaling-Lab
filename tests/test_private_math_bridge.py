"""Private-source integration test: only synthetic evidence, never user research.

Matches FELRA PPV file TYPES documented in docs/PPV.md, but does NOT execute
FELRA, Lean, the AMRAL run, or certify a mathematical result.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import hashlib
from pathlib import Path
import tempfile
import unittest

from fsl_history.research_bridge import (
    BridgeError, inspect_private_epoch, public_redacted_summary
)

DATA={
    "report":"AMRAL_SYNTHETIC_RESEARCH_ARGUMENT_DO_NOT_USE",
    "receipts":'{"not_real_proof": true}',
    "status":'{"claim_status": "synthetic_fake_verified"}',
    "ledger":"SYNTHETIC_APPEND_ONLY_LEDGER",
}


class PrivateMathBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        paths={
            "report":"amral/synthetic_report.md",
            "receipts":"felra-run/ppv/receipts.json",
            "status":"felra-run/ppv/status.json",
            "ledger":"felra-run/ppv/ledger.jsonl",
        }
        roles={
            "report":"amral_research_report",
            "receipts":"felra_ppv_receipts",
            "status":"felra_ppv_status",
            "ledger":"felra_ppv_ledger",
        }
        mats=[]
        for label,rel in paths.items():
            target=self.root/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(DATA[label],encoding="utf-8")
            mats.append({
                "logical_id":"synthetic_"+label,
                "role":roles[label],
                "relative_path":rel,
                "sha256":hashlib.sha256(DATA[label].encode("utf-8")).hexdigest()
            })
        self.base={
            "schema":"fsl/private-math-epoch/0.9",
            "epoch_id":"SYNTHETIC-21H-EPOCH",
            "research_line":"synthetic-math",
            "source_branch":"private/fictional-research-branch",
            "source_commit_sha":"1"*40,
            "model_provider":"anthropic",
            "model_revision":"FICTIONAL-MODEL-REVISION",
            "started_at":"2026-11-05T08:00:00+08:00",
            "finished_at":"2026-11-06T05:00:00+08:00",
            "captured_at":"2026-11-07T06:00:00+08:00",
            "runtime_manifest_sha256":"a"*64,
            "task_contract_sha256":"b"*64,
            "evidence_class":"synthetic",
            "materials":mats,
        }

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self,data=None,checked=None):
        return inspect_private_epoch(data or self.base,root=self.root,
              checked_at=checked or "2026-11-07T08:00:00+08:00")

    def test_actual_bytes_match_but_fake_verified_label_not_trusted(self):
        result=self.inspect()
        self.assertTrue(result["all_materials_match_local_bytes"])
        self.assertTrue(result["felra_ppv_required_files_present"])
        self.assertEqual(result["elapsed_hours_claimed"],21.0)
        self.assertFalse(result["felra_independent_verification_executed"])
        self.assertFalse(result["mathematical_theorem_proved_by_bridge"])
        self.assertFalse(result["G1_multi_day_autonomy_independently_verified"])

    def test_redacted_summary_hides_private_file_names_and_source_identity(self):
        result=self.inspect()
        public=public_redacted_summary(result,export_key="C"*40)
        raw=str(public)
        self.assertEqual(public["provider_cohort"],"anthropic")
        self.assertIn("felra_ppv_status",public["materials_by_type"])
        self.assertNotIn("private/fictional-research-branch",raw)
        self.assertNotIn("FICTIONAL-MODEL-REVISION",raw)
        self.assertNotIn("1"*40,raw)
        self.assertNotIn("synthetic_report.md",raw)
        self.assertNotIn("SYNTHETIC_APPEND_ONLY_LEDGER",raw)
        self.assertFalse(public["mathematical_claim_independently_verified"])
        self.assertEqual(public["research_claim_status"],"unverified_source_receipt_only")

    def test_key_needed_for_any_public_export(self):
        with self.assertRaises(BridgeError):
            public_redacted_summary(self.inspect(),export_key="too-short")
        self.assertNotEqual(
            public_redacted_summary(self.inspect(),export_key="C"*40)
                ["pseudonymous_epoch"],
            public_redacted_summary(self.inspect(),export_key="D"*40)
                ["pseudonymous_epoch"])

    def test_file_tampering_blocks_even_a_status_json(self):
        (self.root/"felra-run/ppv/status.json").write_text(
            '{"claim_status":"EVEN_MORE_FAKE"}',encoding="utf-8")
        with self.assertRaises(BridgeError):
            self.inspect()

    def test_directories_and_symlinks_cannot_escape_private_root(self):
        data=deepcopy(self.base)
        data["materials"][0]["relative_path"]="../secrets.txt"
        with self.assertRaises(BridgeError):
            self.inspect(data)
        link=self.root/"sneaky-link"
        link.symlink_to(self.root/"amral")
        data=deepcopy(self.base)
        data["materials"][0]["relative_path"]="sneaky-link/synthetic_report.md"
        with self.assertRaises(BridgeError):
            self.inspect(data)

    def test_no_missing_artifact_or_duplicate_logical_id(self):
        data=deepcopy(self.base)
        data["materials"].pop(0)
        data["materials"][0]["logical_id"]=data["materials"][1]["logical_id"]
        with self.assertRaises(BridgeError):
            self.inspect(data)
        data=deepcopy(self.base)
        data["materials"].append(deepcopy(data["materials"][0]))
        with self.assertRaises(BridgeError):
            self.inspect(data)

    def test_synthetic_is_not_promoted_by_elapsed_time(self):
        data=deepcopy(self.base)
        data["finished_at"]="2026-11-07T05:30:00+08:00"
        data["captured_at"]="2026-11-07T06:00:00+08:00"
        result=self.inspect(data)
        self.assertGreater(result["elapsed_hours_claimed"],24)
        self.assertFalse(result["G1_multi_day_autonomy_independently_verified"])

    def test_source_capture_after_review_or_reversed_epoch_is_rejected(self):
        data=deepcopy(self.base)
        data["evidence_class"]="observational"
        with self.assertRaises(BridgeError):
            self.inspect(data,checked="2026-11-07T05:59:00+08:00")
        data=deepcopy(self.base)
        data["started_at"]="2026-11-07T11:00:00+08:00"
        with self.assertRaises(BridgeError):
            self.inspect(data)

    def test_invalid_source_revision_or_wrong_evidence_role_rejected(self):
        data=deepcopy(self.base)
        data["source_commit_sha"]="short"
        with self.assertRaises(BridgeError):
            self.inspect(data)
        data=deepcopy(self.base)
        data["materials"][0]["role"]="THEOREM_PROVEN"
        with self.assertRaises(BridgeError):
            self.inspect(data)

    def test_opaque_status_without_full_ppv_materials_is_not_ppv_ready(self):
        data=deepcopy(self.base)
        data["materials"]=[m for m in data["materials"]
                           if m["role"]!="felra_ppv_ledger"]
        result=self.inspect(data)
        self.assertFalse(result["felra_ppv_required_files_present"])
        self.assertFalse(result["felra_independent_verification_executed"])


if __name__=="__main__":
    unittest.main()
