"""Offline source-observatory tests; entirely fictitious metadata and mission."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from fsl_functional.store import add_event, add_run, add_spec
from fsl_observatory.audit import audit
from fsl_observatory.registry import (
    ObservatoryError, add_receipt, add_session, connect, link_receipt)
from fsl_observatory.providers import (
    fetch_json, github_artifact, github_commit, github_workflow, local_file, sha, slug)

REPO="EveMissLab/Frontier-Scaling-Lab"
COMMIT="1"*40
TREE="2"*40
NOW="2026-11-07T15:30:00Z"
SOURCE="https://example.org/SYNTHETIC-NOT-REAL/"


def gh_commit(url,token=None):
    return {"sha":COMMIT,"html_url":f"https://github.com/{REPO}/commit/{COMMIT}",
            "commit":{"tree":{"sha":TREE},
                      "committer":{"date":"2026-11-06T19:00:00Z"}},"parents":[]}


def gh_run(url,token=None):
    return {"id":12345,"head_sha":COMMIT,
            "html_url":f"https://github.com/{REPO}/actions/runs/12345",
            "repository":{"full_name":REPO},
            "created_at":"2026-11-07T12:00:00Z","updated_at":"2026-11-07T12:10:00Z",
            "status":"completed","conclusion":"success","run_attempt":1,"name":"TEST"}


def gh_artifact(url,token=None):
    return {"id":6789,"size_in_bytes":2048,
            "created_at":"2026-11-07T12:12:00Z",
            "name":"SYNTHETIC","expired":False,"workflow_run":{"id":12345}}


def mission_event(eid,kind,payload,occurred="2026-11-07T11:00:00Z"):
    return {"event_id":eid,"run_id":"r1","kind":kind,"actor":"ai",
            "occurred_at":occurred,"recorded_at":"2026-11-07T13:30:00Z",
            "source_url":SOURCE+eid,"payload":payload}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.db=connect(":memory:")
        add_spec(self.db,{
            "spec_id":"s1","track":"digital","kind":"general_digital",
            "title":"SYNTHETIC ONLY","reference_url":SOURCE+"reference",
            "reference_date":"2026-11-01","created_at":"2026-11-07T00:00:00Z",
            "min_duration_days":2,"max_user_rounds":3,
            "required_criteria":["end_to_end_functionality","integrated_delivery",
                                 "independent_user_acceptance"],
            "evidence_class":"synthetic"})
        add_run(self.db,{"run_id":"r1","spec_id":"s1","system_key":"SYNTHETIC",
                         "system_revision":"0","initiated_at":"2026-11-07T00:00:00Z",
                         "evidence_class":"synthetic"})
        add_session(self.db,session_id="s",project_ref=REPO,
                    created_at="2026-11-07T09:00:00Z",mission_run_id="r1")

    def tearDown(self):
        self.db.close()

    def test_metadata_not_certification(self):
        receipts=[
            github_commit(REPO,COMMIT,now=NOW,fetch=gh_commit),
            github_workflow(REPO,12345,now=NOW,fetch=gh_run),
            github_artifact(REPO,6789,now=NOW,fetch=gh_artifact)]
        for x in receipts:
            add_receipt(self.db,session_id="s",receipt=x)
        result=audit(self.db,"s",as_of="2026-11-07T16:00:00Z")
        self.assertEqual(result["receipt_count"],3)
        self.assertEqual(result["distinct_provider_recorded_dates"],1)
        self.assertEqual(receipts[0]["time_trust"],"author_controlled")
        self.assertEqual(receipts[1]["time_trust"],"provider_recorded")
        self.assertFalse(result["certification"]["G1_G4_or_E1_certified"])
        self.assertFalse(result["functional_claim_assessment"]["externally_certified_result"])

    def test_reject_mismatched_commit_repo_and_run(self):
        bad=gh_commit(None);bad["sha"]="9"*40
        with self.assertRaises(ObservatoryError):
            github_commit(REPO,COMMIT,now=NOW,fetch=lambda *a,**k:bad)
        bad=gh_run(None);bad["repository"]["full_name"]="Other/Repo"
        with self.assertRaises(ObservatoryError):
            github_workflow(REPO,12345,now=NOW,fetch=lambda *a,**k:bad)
        bad=gh_run(None);bad["conclusion"]="success";bad["status"]="in_progress"
        with self.assertRaises(ObservatoryError):
            github_workflow(REPO,12345,now=NOW,fetch=lambda *a,**k:bad)

    def test_url_host_and_repo_validation(self):
        for name in ("../test","owner/../../other","owner/repo/extra"):
            with self.assertRaises(ObservatoryError):
                slug(name)
        with self.assertRaises(ObservatoryError):
            sha("invalid")
        with self.assertRaises(ObservatoryError):
            fetch_json("https://evil.example/repos/a/b/commits/x")

    def test_token_never_stored(self):
        rec=github_workflow(REPO,12345,now=NOW,token="PRIVATE_TOKEN",
                            fetch=lambda url,token=None:gh_run(url))
        rid=add_receipt(self.db,session_id="s",receipt=rec)
        stored=str(dict(self.db.execute(
            "SELECT * FROM observer_receipts WHERE receipt_id=?",(rid,)).fetchone()))
        self.assertNotIn("PRIVATE_TOKEN",stored)

    def test_local_file_digest_matches_attached_deliverable(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"build.txt").write_bytes(b"FAKE BUILD")
            rec=local_file(td,"build.txt",now=NOW)
            file_sha=hashlib.sha256(b"FAKE BUILD").hexdigest()
            self.assertEqual(rec["content_sha256"],file_sha)
            add_event(self.db,mission_event("build","deliverable",
                      {"artifact_sha256":file_sha,"artifact_type":"file"}))
            rid=add_receipt(self.db,session_id="s",receipt=rec)
            link_receipt(self.db,receipt_id=rid,event_id="build",
                         role="supports_deliverable",
                         recorded_at="2026-11-07T16:00:00Z")
            self.assertEqual(audit(self.db,"s",as_of="2026-11-07T15:50:00Z")
                             ["mission_links"]["total"],0)
            later=audit(self.db,"s",as_of="2026-11-07T16:10:00Z")
            self.assertEqual(later["mission_links"]["covered_unique_events"],1)
            self.assertFalse(later["certification"]["real_finished_product_quality_verified"])

    def test_hash_mismatch_and_future_link_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"build.txt").write_bytes(b"actual bytes")
            rid=add_receipt(self.db,session_id="s",
                            receipt=local_file(td,"build.txt",now=NOW))
            add_event(self.db,mission_event("build","deliverable",
                      {"artifact_sha256":"a"*64,"artifact_type":"file"}))
            with self.assertRaises(ObservatoryError):
                link_receipt(self.db,receipt_id=rid,event_id="build",
                             role="supports_deliverable",
                             recorded_at="2026-11-07T16:00:00Z")
            with self.assertRaises(ObservatoryError):
                link_receipt(self.db,receipt_id=rid,event_id="build",
                             role="supports_deliverable",
                             recorded_at="2026-11-07T12:00:00Z")

    def test_workflow_ci_support_only_after_success(self):
        bad=gh_run(None);bad["status"]="in_progress";bad["conclusion"]=None
        rec=github_workflow(REPO,12345,now=NOW,fetch=lambda *a,**k:bad)
        rid=add_receipt(self.db,session_id="s",receipt=rec)
        add_event(self.db,mission_event("progress","progress",
                                        {"evidence_sha256":"b"*64}))
        with self.assertRaises(ObservatoryError):
            link_receipt(self.db,receipt_id=rid,event_id="progress",
                         role="supports_ci",recorded_at="2026-11-07T16:00:00Z")

    def test_successful_ci_must_match_exact_claimed_revision(self):
        rec=github_workflow(REPO,12345,now=NOW,fetch=gh_run)
        rid=add_receipt(self.db,session_id="s",receipt=rec)
        add_event(self.db,mission_event(
            "progress","progress",
            {"evidence_sha256":"b"*64,"github_head_sha":"0"*40}))
        with self.assertRaises(ObservatoryError):
            link_receipt(self.db,receipt_id=rid,event_id="progress",
                         role="supports_ci",recorded_at="2026-11-07T16:00:00Z")
        add_event(self.db,mission_event(
            "matching","progress",
            {"evidence_sha256":"b"*64,"github_head_sha":COMMIT}))
        link_receipt(self.db,receipt_id=rid,event_id="matching",
                     role="supports_ci",recorded_at="2026-11-07T16:00:00Z")
        result=audit(self.db,"s",as_of="2026-11-07T17:00:00Z")
        self.assertEqual(result["mission_links"]["covered_unique_events"],1)

    def test_progress_file_hash_must_match_actual_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"checkpoint.bin").write_bytes(b"correct checkpoint")
            rec=local_file(td,"checkpoint.bin",now=NOW)
            rid=add_receipt(self.db,session_id="s",receipt=rec)
            add_event(self.db,mission_event(
                "progress","progress",{"evidence_sha256":"a"*64}))
            with self.assertRaises(ObservatoryError):
                link_receipt(self.db,receipt_id=rid,event_id="progress",
                             role="supports_progress",
                             recorded_at="2026-11-07T16:00:00Z")
            add_event(self.db,mission_event(
                "correct-progress","progress",
                {"evidence_sha256":rec["content_sha256"]}))
            link_receipt(self.db,receipt_id=rid,event_id="correct-progress",
                         role="supports_progress",recorded_at="2026-11-07T16:00:00Z")

    def test_no_path_escape_or_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"file.txt").write_text("hello",encoding="utf-8")
            self.assertEqual(local_file(td,"file.txt",now=NOW)
                             ["metadata"]["size_in_bytes"],5)
            with self.assertRaises(ObservatoryError):
                local_file(td,"../anything",now=NOW)
            (root/"symlink.txt").symlink_to(root/"file.txt")
            with self.assertRaises(ObservatoryError):
                local_file(td,"symlink.txt",now=NOW)

    def test_append_only_idempotent_and_cutoff(self):
        rec=github_commit(REPO,COMMIT,now=NOW,fetch=gh_commit)
        rid=add_receipt(self.db,session_id="s",receipt=rec)
        self.assertEqual(rid,add_receipt(self.db,session_id="s",receipt=rec))
        self.assertEqual(audit(self.db,"s",as_of="2026-11-07T15:00:00Z")
                         ["receipt_count"],0)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM observer_receipts")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE observer_sessions SET purpose='certified'")

    def test_pilot_session_unlinked_to_mission(self):
        add_session(self.db,session_id="pilot",project_ref=REPO,
                    created_at="2026-11-07T09:00:00Z")
        rid=add_receipt(self.db,session_id="pilot",
                        receipt=github_commit(REPO,COMMIT,now=NOW,fetch=gh_commit))
        add_event(self.db,mission_event("progress","progress",
                                        {"evidence_sha256":"a"*64}))
        with self.assertRaises(ObservatoryError):
            link_receipt(self.db,receipt_id=rid,event_id="progress",
                         role="supports_progress",recorded_at="2026-11-07T16:00:00Z")
        self.assertIsNone(audit(self.db,"pilot",as_of="2026-11-07T16:00:00Z")
                          ["functional_claim_assessment"])

    def test_corrections_hide_old_attached_mission_claim(self):
        rid=add_receipt(self.db,session_id="s",
                        receipt=github_commit(REPO,COMMIT,now=NOW,fetch=gh_commit))
        add_event(self.db,mission_event("progress","progress",
                                        {"evidence_sha256":"b"*64}))
        link_receipt(self.db,receipt_id=rid,event_id="progress",
                     role="supports_progress",recorded_at="2026-11-07T16:00:00Z")
        correction=mission_event("correct","correction",
                                 {"supersedes_event_id":"progress"},
                                 occurred="2026-11-07T17:00:00Z")
        correction["recorded_at"]="2026-11-07T18:00:00Z"
        add_event(self.db,correction)
        self.assertEqual(audit(self.db,"s",as_of="2026-11-07T16:30:00Z")
                         ["mission_links"]["total"],1)
        self.assertEqual(audit(self.db,"s",as_of="2026-11-07T19:00:00Z")
                         ["mission_links"]["total"],0)


if __name__=="__main__":
    unittest.main()
