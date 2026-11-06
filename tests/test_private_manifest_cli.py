"""Local private manifest builder: never uploads or prints AMRAL/FELRA contents.

All research bytes and actor identities in fixtures are synthetic.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from fsl_history.manifest_cli import main


class PrivateManifestBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/"fake_ppv").mkdir()
        (self.root/"fake_ppv"/"receipts.json").write_text(
            '{"not_real":"PRIVATE_SYNTHETIC_CONTENT"}',encoding="utf-8")
        self.path=self.root/"separate_private_manifest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def args(self):
        return [
            "--root",str(self.root),
            "--output",str(self.path),
            "--epoch-id","SYNTHETIC-LOCAL-EPOCH",
            "--research-line","SYNTHETIC-RESEARCH-LINE",
            "--source-branch","private/never-publish-this-branch",
            "--source-commit-sha","f"*40,
            "--model-provider","anthropic",
            "--model-revision","SYNTHETIC-PRIVATE-MODEL",
            "--started-at","2025-01-01T00:00:00+08:00",
            "--runtime-manifest-sha256","a"*64,
            "--task-contract-sha256","b"*64,
            "--evidence-class","synthetic",
            "--material","felra_ppv_receipts=fake_ppv/receipts.json",
        ]

    def test_builder_digests_real_bytes_to_private_manifest(self):
        out=StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(self.args()),0)
        doc=json.loads(self.path.read_text("utf-8"))
        self.assertEqual(doc["schema"],"fsl/private-math-epoch/0.9")
        self.assertEqual(doc["materials"][0]["role"],"felra_ppv_receipts")
        self.assertEqual(len(doc["materials"][0]["sha256"]),64)
        self.assertEqual(doc["evidence_class"],"synthetic")
        stdout=out.getvalue()
        self.assertNotIn("PRIVATE_SYNTHETIC_CONTENT",stdout)
        self.assertNotIn("never-publish-this-branch",stdout)
        self.assertNotIn(str(self.path),stdout)
        self.assertIn('"mathematical_theorem_verified": false',stdout)

    def test_does_not_overwrite_private_manifest(self):
        with redirect_stdout(StringIO()):
            main(self.args())
        original=self.path.read_bytes()
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit):
            main(self.args())
        self.assertEqual(self.path.read_bytes(),original)

    def test_bad_evidence_path_does_not_create_manifest(self):
        args=self.args()
        args[-1]="felra_ppv_receipts=../outside-private.txt"
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit):
            main(args)
        self.assertFalse(self.path.exists())

    def test_public_code_cannot_evaluate_a_fake_18h_run(self):
        with redirect_stdout(StringIO()):
            main(self.args())
        from fsl_history.research_bridge import inspect_private_epoch
        record=inspect_private_epoch(json.loads(self.path.read_text("utf-8")),
                                     root=self.root)
        self.assertIsNone(record["elapsed_hours_claimed"])
        self.assertFalse(record["G1_multi_day_autonomy_independently_verified"])
        self.assertFalse(record["felra_independent_verification_executed"])


if __name__=="__main__":
    unittest.main()
