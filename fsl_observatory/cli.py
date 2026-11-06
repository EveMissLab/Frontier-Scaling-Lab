"""v0.7 mission observer CLI; read-only intake and append-only SQLite storage.

GitHub API requests are GET only. GITHUB_TOKEN, if provided, is never printed
or persisted. The CLI does not run a background AI Agent or certify outcomes.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .registry import (
    ObservatoryError, add_receipt, add_session, connect, link_receipt, utc_now,
)
from .providers import github_commit, github_workflow, github_artifact, local_file
from .audit import audit


def emit(item,output=None):
    data=json.dumps(item,ensure_ascii=False,indent=2,sort_keys=True,
                    allow_nan=False)+"\n"
    if output is None:
        print(data,end="")
    else:
        path=Path(output)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(data,encoding="utf-8")


def main(argv=None):
    p=argparse.ArgumentParser(description="FSL v0.7: inspectable Agent/mission evidence intake")
    p.add_argument("--db",default="data/fsl_observatory.sqlite")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("init")

    session=sub.add_parser("session",help="start independent observation session")
    session.add_argument("--id",required=True)
    session.add_argument("--project",required=True)
    session.add_argument("--purpose",default="read_only_observation")
    session.add_argument("--mission-run",default=None)

    commit=sub.add_parser("github-commit")
    commit.add_argument("--session",required=True)
    commit.add_argument("--repo",required=True)
    commit.add_argument("--sha",required=True)

    workflow=sub.add_parser("github-workflow")
    workflow.add_argument("--session",required=True)
    workflow.add_argument("--repo",required=True)
    workflow.add_argument("--run-id",type=int,required=True)

    artifact=sub.add_parser("github-artifact")
    artifact.add_argument("--session",required=True)
    artifact.add_argument("--repo",required=True)
    artifact.add_argument("--artifact-id",type=int,required=True)

    file=sub.add_parser("local-file")
    file.add_argument("--session",required=True)
    file.add_argument("--root",required=True)
    file.add_argument("--path",required=True,help="root-relative path only")

    link=sub.add_parser("link")
    link.add_argument("--receipt",required=True)
    link.add_argument("--event",required=True)
    link.add_argument("--role",required=True,choices=[
        "supports_progress","supports_checkpoint","supports_deliverable",
        "supports_ci","supports_recovery"])

    panel=sub.add_parser("audit")
    panel.add_argument("--session",required=True)
    panel.add_argument("--as-of")
    panel.add_argument("--output")

    pilot=sub.add_parser("pilot",help="bounded live source pilot; no autonomy claim")
    pilot.add_argument("--session",required=True)
    pilot.add_argument("--repo",required=True)
    pilot.add_argument("--sha",required=True)
    pilot.add_argument("--run-id",type=int,required=True)
    pilot.add_argument("--root",required=True)
    pilot.add_argument("--file",default="README.md")
    pilot.add_argument("--output")

    args=p.parse_args(argv)
    token=os.environ.get("GITHUB_TOKEN")
    try:
        with connect(args.db) as db:
            if args.command=="init":
                result={"status":"initialized","schema":"fsl/observer/v0.7",
                        "database":args.db}
            elif args.command=="session":
                result={"session_id":add_session(
                    db,session_id=args.id,project_ref=args.project,
                    purpose=args.purpose,mission_run_id=args.mission_run,
                    created_at=utc_now())}
            elif args.command=="github-commit":
                receipt=github_commit(args.repo,args.sha,token=token)
                result={"receipt_id":add_receipt(
                    db,session_id=args.session,receipt=receipt),
                    "source_kind":receipt["kind"],"proof_scope":receipt["metadata"]["proof_scope"]}
            elif args.command=="github-workflow":
                receipt=github_workflow(args.repo,args.run_id,token=token)
                result={"receipt_id":add_receipt(
                    db,session_id=args.session,receipt=receipt),
                    "status":receipt["state"],
                    "conclusion":receipt["metadata"]["conclusion"]}
            elif args.command=="github-artifact":
                receipt=github_artifact(args.repo,args.artifact_id,token=token)
                result={"receipt_id":add_receipt(
                    db,session_id=args.session,receipt=receipt),
                    "scope":"artifact_metadata_only"}
            elif args.command=="local-file":
                receipt=local_file(args.root,args.path)
                result={"receipt_id":add_receipt(
                    db,session_id=args.session,receipt=receipt),
                    "file_sha256":receipt["content_sha256"],
                    "scope":"local_file_bytes_at_collection_only"}
            elif args.command=="link":
                result={"link_id":link_receipt(
                    db,receipt_id=args.receipt,event_id=args.event,
                    role=args.role,recorded_at=utc_now())}
            elif args.command=="audit":
                result=audit(db,args.session,as_of=args.as_of or utc_now())
            elif args.command=="pilot":
                add_session(db,session_id=args.session,project_ref=args.repo,
                            created_at=utc_now(),
                            purpose="first_party_source_metadata_pilot_no_agent_claim")
                receipts=[
                    github_commit(args.repo,args.sha,token=token),
                    github_workflow(args.repo,args.run_id,token=token),
                    local_file(args.root,args.file),
                ]
                if receipts[1]["metadata"]["head_sha"]!=args.sha:
                    raise ObservatoryError("pilot CI head_sha must match selected repository commit")
                ids=[add_receipt(db,session_id=args.session,receipt=x)
                     for x in receipts]
                result=audit(db,args.session,as_of=utc_now())
                result["receipt_ids"]=ids
                result["pilot_description"]="GitHub and file provenance only; no autonomous mission measured"
            else:
                raise ObservatoryError("unhandled command")
        emit(result,getattr(args,"output",None))
    except (ObservatoryError,ValueError,TypeError,KeyError,OSError) as exc:
        p.exit(2,f"observer error: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
