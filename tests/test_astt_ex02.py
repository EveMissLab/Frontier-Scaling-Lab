"""Verify EX02 canonical source and run its exact embedded finite-model replay."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ASTT=ROOT/"docs/astt"
MANIFEST=ASTT/"source_manifest_EX02.json"


class ASTTEX02Tests(unittest.TestCase):
    def setUp(self):
        self.m=json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.path=ASTT/self.m["file"]["path"]
        self.b=self.path.read_bytes()
        self.s=self.b.decode("utf-8",errors="strict")

    def test_canonical_source_and_hash(self):
        self.assertFalse(self.b.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r",self.b)
        self.assertTrue(self.b.endswith(b"\n"))
        self.assertEqual(len(self.b),self.m["file"]["bytes"])
        self.assertEqual(hashlib.sha256(self.b).hexdigest(),self.m["file"]["sha256"])
        self.assertEqual(hashlib.sha1(f"blob {len(self.b)}\0".encode()+self.b).hexdigest(),
                         self.m["file"]["git_blob_sha"])
        self.assertIn('paper: "EX02"',self.s)
        self.assertIn("保留的未決問題（不是終局結論）",self.s)

    def test_math_delimiters_and_abstract_scope(self):
        self.assertNotRegex(self.s,r"\\[()\[\]]")
        self.assertNotRegex(self.s,r"(?i)\b(?:Anthropic|Claude)\b|某\s*A|UP\s*主")
        # All math delimiters outside the fenced Python block must match by width.
        body=self.s.split("\n"+chr(96)*3+"python\n")[0]
        state=None
        for match in re.finditer(r"(?<!\\)\$\$|(?<!\\)\$",body):
            token=match.group()
            if state is None:state=token
            else:
                self.assertEqual(state,token)
                state=None
        self.assertIsNone(state)

    def test_original_manifest_unchanged(self):
        b=(ASTT/"source_manifest.json").read_bytes()
        self.assertEqual(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest(),
                         "3ec4dc9cf2416753cf7ae3a1e85f4771e4b752b0")
        self.assertEqual(len(json.loads(b)["files"]),14)

    def test_embedded_replay(self):
        fences=re.findall(r"(?m)^"+chr(96)*3+r"python\n([\s\S]*?)^"+chr(96)*3+r"$",self.s)
        self.assertEqual(len(fences),1)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"replay.py"
            p.write_bytes(fences[0].encode("utf-8"))
            result=subprocess.run([sys.executable,str(p)],capture_output=True,text=True,
                                  check=True,timeout=30)
        replay=json.loads(result.stdout)
        print("ASTT-EX02 replay receipt: "+json.dumps(replay,sort_keys=True))
        expected=self.m["replay"]
        self.assertEqual(replay["scope"],expected["expected_scope"])
        self.assertEqual(replay["groups"],expected["expected_group_counts"])
        self.assertEqual(replay["configurations"],expected["expected_configurations"])
        self.assertFalse(replay["empirical_certification"])
        self.assertIsNone(replay["terminal_verdict"])
