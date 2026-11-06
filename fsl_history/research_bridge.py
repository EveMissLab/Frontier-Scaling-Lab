"""FSL v0.9 read-only local AMRAL/FELRA research receipt ingestion.

This bridge is purposefully designed to run next to the user's private
checked-out research workspace. It neither connects to GitHub directly,
executes research code, imports proprietary math text, nor uploads files.

All published summaries are reduced to counts and HMAC-pseudonymized IDs.
FELRA PPV 'verified' is NOT inferred from status.json or the presence of
receipt files; a verifier must be independently executed and reviewed.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re

from fsl_economics.timeaxis import _instant, TemporalError


class BridgeError(ValueError):
    pass


SHA=re.compile(r"[0-9a-f]{64}\Z")
ID=re.compile(r"[A-Za-z0-9_.:-]{1,110}\Z")
GIT_SHA=re.compile(r"[0-9a-f]{40}\Z")
MATERIALS={
    "task_contract","amral_research_report","amral_result",
    "amral_counterexample","felra_ppv_receipts","felra_ppv_status",
    "felra_ppv_ledger","felra_ppv_human_report",
    "independent_replay_report","other_evidence",
}
PROVIDERS={"openai","anthropic","google","xai","deepseek","other","unknown"}
MAX_SINGLE_BYTES=24*1024*1024
MAX_ENTRIES=64


def _require_sha(x,field):
    if not isinstance(x,str) or SHA.fullmatch(x) is None:
        raise BridgeError(field+" needs lowercase SHA256")
    return x


def _id(x,field):
    if not isinstance(x,str) or ID.fullmatch(x) is None:
        raise BridgeError(field+" needs a stable nonsecret ID")
    return x


def _local_file(root, rel):
    if not isinstance(rel,str) or not rel or "\\" in rel:
        raise BridgeError("files must be POSIX-style relative paths inside explicit root")
    p=Path(rel)
    if p.is_absolute() or ".." in p.parts or p.parts in ((),(".",)):
        raise BridgeError("absolute/path-traversal entry forbidden")
    candidate=root
    for part in p.parts:
        candidate=candidate/part
        if candidate.is_symlink():
            raise BridgeError("symlink inside selected evidence root is forbidden")
    f=candidate.resolve(strict=True)
    if not f.is_relative_to(root) or not f.is_file():
        raise BridgeError("file escapes selected evidence root or is not a regular file")
    if f.stat().st_size>MAX_SINGLE_BYTES:
        raise BridgeError("individual evidence file exceeds allowed byte cap")
    return f


def inspect_private_epoch(data, *, root, checked_at=None):
    """Return an **in-memory private result**. Do not publish this object."""
    if not isinstance(data,dict) or data.get("schema")!="fsl/private-math-epoch/0.9":
        raise BridgeError("unknown private AMRAL/FELRA input schema")
    needed=("epoch_id","source_commit_sha","research_line","source_branch",
            "model_provider","model_revision","started_at","finished_at",
            "captured_at","runtime_manifest_sha256","task_contract_sha256",
            "evidence_class","materials")
    if any(k not in data for k in needed):
        raise BridgeError("private epoch needs immutable source, time and artifact fields")
    _id(data["epoch_id"],"epoch_id")
    _id(data["research_line"],"research_line")
    if data["model_provider"] not in PROVIDERS:
        raise BridgeError("model provider must be an explicit category")
    if not isinstance(data["model_revision"],str) or not data["model_revision"].strip():
        raise BridgeError("model revision needs identity")
    if not isinstance(data["source_branch"],str) or not data["source_branch"].strip():
        raise BridgeError("source branch must be recorded privately")
    if not isinstance(data["source_commit_sha"],str) or GIT_SHA.fullmatch(data["source_commit_sha"]) is None:
        raise BridgeError("private repository source revision requires full Git SHA")
    for k in ("runtime_manifest_sha256","task_contract_sha256"):
        _require_sha(data[k],k)
    if data["evidence_class"] not in ("synthetic","observational"):
        raise BridgeError("evidence class must be identified")
    start=_instant(data["started_at"],"started_at")
    end=_instant(data["finished_at"],"finished_at") if data["finished_at"] else None
    captured=_instant(data["captured_at"],"captured_at")
    if end is not None and end<start:
        raise BridgeError("research cannot finish before it starts")
    if start>captured or (end is not None and end>captured):
        raise BridgeError("future research start/finish relative to capture")
    if (checked_at is not None and data["evidence_class"]=="observational"
            and captured>_instant(checked_at,"checked_at")):
        raise BridgeError("real evidence cannot be collected after actual review time")
    folder=Path(root).resolve(strict=True)
    if not folder.is_dir():
        raise BridgeError("private evidence root must exist")
    items=data["materials"]
    if not isinstance(items,list) or not 1<=len(items)<=MAX_ENTRIES:
        raise BridgeError("bounded nonempty list of source files required")
    seen=set(); counts=Counter(); receipts=[]
    for item in items:
        if not isinstance(item,dict) or set(item)!={"logical_id","role","relative_path","sha256"}:
            raise BridgeError("artifact manifest must have exactly four fields")
        logical=_id(item["logical_id"],"logical_id")
        if logical in seen:raise BridgeError("duplicate artifact ID")
        seen.add(logical)
        role=item["role"]
        if role not in MATERIALS:
            raise BridgeError("unsupported FELRA/AMRAL evidence role")
        expected=_require_sha(item["sha256"],"artifact_sha256")
        file=_local_file(folder,item["relative_path"])
        actual=hashlib.sha256()
        size=0
        with file.open("rb") as f:
            while block:=f.read(1024*1024):
                size+=len(block)
                if size>MAX_SINGLE_BYTES:
                    raise BridgeError("file grew beyond maximum")
                actual.update(block)
        if not hmac.compare_digest(actual.hexdigest(),expected):
            raise BridgeError("evidence SHA mismatch (details suppressed to protect private path)")
        counts[role]+=1
        receipts.append({"logical_id":logical,"role":role,
                         "byte_size":size,"sha256":actual.hexdigest()})
    duration=(end-start).total_seconds()/3600 if end is not None else None
    return {
        "schema":"fsl/private-epoch-readonly-audit/0.9",
        "epoch_id":data["epoch_id"],
        "research_line":data["research_line"],
        "source_commit_sha":data["source_commit_sha"],
        "source_branch":data["source_branch"],
        "model_provider":data["model_provider"],
        "model_revision":data["model_revision"],
        "evidence_class":data["evidence_class"],
        "runtime_manifest_sha256":data["runtime_manifest_sha256"],
        "task_contract_sha256":data["task_contract_sha256"],
        "started_at_utc":start.isoformat(),
        "finished_at_utc":end.isoformat() if end else None,
        "captured_at_utc":captured.isoformat(),
        "elapsed_hours_claimed":duration,
        "material_counts":dict(sorted(counts.items())),
        "material_receipts":receipts,
        "all_materials_match_local_bytes":True,
        "felra_ppv_required_files_present":all(
            counts.get(x,0)>0 for x in (
                "felra_ppv_receipts","felra_ppv_status","felra_ppv_ledger")),
        "felra_independent_verification_executed":False,
        "mathematical_theorem_proved_by_bridge":False,
        "G1_multi_day_autonomy_independently_verified":False,
        "proof_limit":"File existence/hash is not FELRA ppv-verify execution, solver replay or proof correctness.",
    }


def public_redacted_summary(private_report, *, export_key):
    """Privacy-preserving output: no repo, branch, file, model revision or raw SHA.

    The HMAC secret is supplied externally; never checked into GitHub.
    """
    if not isinstance(export_key,str) or len(export_key.encode("utf-8"))<32:
        raise BridgeError("public export requires separate 32+ byte HMAC key")
    if not isinstance(private_report,dict) or private_report.get("schema")!=(
            "fsl/private-epoch-readonly-audit/0.9"):
        raise BridgeError("private audit report required")
    def pseudo(value):
        return hmac.new(export_key.encode("utf-8"),str(value).encode("utf-8"),
                        hashlib.sha256).hexdigest()[:20]
    return {
        "schema":"fsl/redacted-math-epoch/0.9",
        "pseudonymous_epoch":pseudo(private_report["epoch_id"]),
        "pseudonymous_source_revision":pseudo(private_report["source_commit_sha"]),
        "provider_cohort":private_report["model_provider"],
        "evidence_class":private_report["evidence_class"],
        "captured_at_utc":private_report["captured_at_utc"],
        "elapsed_hours_claimed":private_report["elapsed_hours_claimed"],
        "materials_by_type":private_report["material_counts"],
        "local_source_byte_integrity_passed":
            private_report["all_materials_match_local_bytes"],
        "felra_ppv_receipt_files_present":
            private_report["felra_ppv_required_files_present"],
        "felra_independently_reexecuted":False,
        "mathematical_claim_independently_verified":False,
        "G1_24_48h_independently_verified":False,
        "underlying_research_content_public":False,
        "research_claim_status":"unverified_source_receipt_only",
        "limitations":[
            "Research output content, private Git branches and paths are not exported.",
            "Elapsed time is self-reported, not a trusted continuous Agent runtime attestation.",
            "Run FELRA ppv-verify independently and inspect results before certifying math status.",
            "HMAC pseudonymization reduces direct exposure but cannot guarantee anonymity.",
            "No historical AI token usage or economic bill may be inferred from research files.",
        ],
    }
