"""Create an AMRAL/FELRA epoch manifest locally, never upload research files.

The builder hashes explicitly selected files and records provided runner/model
metadata in a PRIVATE UTF-8 JSON. The final research bridge checks all hashes.
If the destination exists the builder refuses to overwrite it.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from .research_bridge import (
    BridgeError, _id, _local_file, MATERIALS, PROVIDERS, MAX_SINGLE_BYTES
)
from .research_bridge import inspect_private_epoch


def main(argv=None):
    p=argparse.ArgumentParser(
        description="FSL v0.9: build a PRIVATE AMRAL/FELRA evidence manifest")
    p.add_argument("--root",required=True)
    p.add_argument("--output",required=True,
                   help="must be PRIVATE location, file created only if absent")
    p.add_argument("--epoch-id",required=True)
    p.add_argument("--research-line",required=True)
    p.add_argument("--source-branch",required=True)
    p.add_argument("--source-commit-sha",required=True)
    p.add_argument("--model-provider",required=True,choices=sorted(PROVIDERS))
    p.add_argument("--model-revision",required=True)
    p.add_argument("--started-at",required=True,
                   help="timezone-aware ISO start (do not invent start)")
    p.add_argument("--finished-at",default=None)
    p.add_argument("--runtime-manifest-sha256",required=True)
    p.add_argument("--task-contract-sha256",required=True)
    p.add_argument("--evidence-class",choices=["synthetic","observational"],
                   default="observational")
    p.add_argument("--material",action="append",required=True,
                   help="ROLE=relative/file/path, repeat; role from PPV/AMRAL whitelist")
    args=p.parse_args(argv)
    try:
        root=Path(args.root).resolve(strict=True)
        if not root.is_dir():
            raise BridgeError("evidence root must exist")
        materials=[]
        for i,raw in enumerate(args.material):
            if "=" not in raw:
                raise BridgeError("material needs ROLE=relative_path")
            role,rel=raw.split("=",1)
            if role not in MATERIALS:
                raise BridgeError("unknown evidence material role")
            file=_local_file(root,rel)
            digest=hashlib.sha256()
            size=0
            with file.open("rb") as f:
                while block:=f.read(1024*1024):
                    size+=len(block)
                    if size>MAX_SINGLE_BYTES:
                        raise BridgeError("artifact exceeded bounded intake")
                    digest.update(block)
            materials.append({
                "logical_id":"material_"+str(i+1),
                "role":role,"relative_path":rel,
                "sha256":digest.hexdigest(),
            })
        now=datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest={
            "schema":"fsl/private-math-epoch/0.9",
            "epoch_id":args.epoch_id,
            "research_line":args.research_line,
            "source_branch":args.source_branch,
            "source_commit_sha":args.source_commit_sha,
            "model_provider":args.model_provider,
            "model_revision":args.model_revision,
            "started_at":args.started_at,
            "finished_at":args.finished_at,
            "captured_at":now,
            "runtime_manifest_sha256":args.runtime_manifest_sha256,
            "task_contract_sha256":args.task_contract_sha256,
            "evidence_class":args.evidence_class,
            "materials":materials,
        }
        # Validate the entire complete document prior to saving.
        report=inspect_private_epoch(manifest,root=root,checked_at=now)
        target=Path(args.output)
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(manifest,ensure_ascii=False,indent=2,
                       sort_keys=True,allow_nan=False)+"\n"
        # Private, create-only mode; never overwrite and never echo paths.
        mode=os.O_CREAT|os.O_WRONLY|os.O_EXCL
        with os.fdopen(os.open(target,mode,0o600),"w",encoding="utf-8") as f:
            f.write(raw)
        print(json.dumps({
            "schema":"fsl/private-epoch-manifest-written/0.9",
            "materials_hashed":len(materials),
            "bytes_correct":report["all_materials_match_local_bytes"],
            "destination_is_user_controlled_private_path":True,
            "private_paths_or_lookups_printed":False,
            "mathematical_theorem_verified":False,
            "G1_real_continuous_execution_verified":False,
        },ensure_ascii=False))
    except (BridgeError,OSError,KeyError,ValueError,TypeError) as exc:
        p.exit(2,"private manifest error: "+str(type(exc).__name__)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
