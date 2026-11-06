"""Limited read-only GitHub REST and local artifact provenance adapters.

Git commit metadata comes from the provider, but author/committer dates can be
chosen by a committer and are NOT trusted wall-clock proof of agent continuity.
GitHub workflow created_at is a provider-recorded timestamp, not proof that
an agent performed useful autonomous work. No code execution or write APIs.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import urllib.error
import urllib.parse
import urllib.request

from .registry import ObservatoryError, utc_now
from fsl_functional.store import moment

MAX_RESPONSE = 2 * 1024 * 1024
MAX_LOCAL_FILE = 100 * 1024 * 1024
UA = "Frontier-Scaling-Lab-Observer/0.7 (+https://github.com/EveMissLab/Frontier-Scaling-Lab)"


def slug(repo):
    if not isinstance(repo,str) or not re.fullmatch(
        r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}",repo):
        raise ObservatoryError("GitHub repo must be exact owner/name")
    if any(part in ("..",".") for part in repo.split("/")):
        raise ObservatoryError("invalid GitHub repo path")
    return repo


def sha(oid):
    if not isinstance(oid,str) or re.fullmatch(
        r"(?:[a-f0-9]{40}|[a-f0-9]{64})",oid) is None:
        raise ObservatoryError("Git SHA must be 40 or 64 lowercase hex characters")
    return oid


def number(v,name):
    if isinstance(v,bool) or not isinstance(v,int) or v <= 0:
        raise ObservatoryError(f"{name} must be a positive integer")
    return v


def _url(repo,path):
    slug(repo)
    return "https://api.github.com/repos/"+repo+path


def fetch_json(url, token=None, timeout=15):
    """Only official GitHub read API. The provided token is never logged/stored.

    Network errors are reported, never silently converted to 'zero progress'.
    """
    p=urllib.parse.urlsplit(url)
    if (p.scheme!="https" or p.hostname!="api.github.com" or
        p.username or p.password or p.port is not None or
        not p.path.startswith("/repos/")):
        raise ObservatoryError("only allowlisted GitHub API GET endpoints accepted")
    if not isinstance(timeout,(int,float)) or timeout <= 0 or timeout > 120:
        raise ObservatoryError("invalid timeout")
    headers={"Accept":"application/vnd.github+json","User-Agent":UA,
             "X-GitHub-Api-Version":"2022-11-28"}
    if token:
        headers["Authorization"]="Bearer "+token
    request=urllib.request.Request(url,headers=headers,method="GET")

    class NoExternalRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new=urllib.parse.urlsplit(newurl)
            if new.scheme!="https" or new.hostname!="api.github.com":
                raise ObservatoryError("redirect outside api.github.com blocked")
            return super().redirect_request(req,fp,code,msg,headers,newurl)

    try:
        with urllib.request.build_opener(NoExternalRedirect()).open(
                request,timeout=timeout) as response:
            contents=response.read(MAX_RESPONSE+1)
            if len(contents)>MAX_RESPONSE:
                raise ObservatoryError("GitHub API response exceeds byte cap")
    except urllib.error.HTTPError as exc:
        raise ObservatoryError(f"GitHub REST HTTP {exc.code}; check access/rate limits") from exc
    except urllib.error.URLError as exc:
        raise ObservatoryError(f"GitHub REST connection error ({type(exc.reason).__name__})") from exc
    try:
        decoded=json.loads(contents.decode("utf-8"))
    except (UnicodeError,ValueError) as exc:
        raise ObservatoryError("GitHub API returned invalid UTF-8 JSON") from exc
    if not isinstance(decoded,dict):
        raise ObservatoryError("GitHub API object expected")
    return decoded


def _now(now):
    return moment(now or utc_now()).isoformat()


def github_commit(repo,commit_sha,*,now=None,fetch=fetch_json,token=None):
    repo=slug(repo)
    commit_sha=sha(commit_sha)
    endpoint=_url(repo,"/commits/"+commit_sha)
    data=fetch(endpoint,token=token)
    if data.get("sha") != commit_sha:
        raise ObservatoryError("commit SHA does not match requested object")
    link=data.get("html_url")
    if link != f"https://github.com/{repo}/commit/{commit_sha}":
        raise ObservatoryError("commit URL/repository mismatch")
    node=data.get("commit")
    if not isinstance(node,dict):
        raise ObservatoryError("commit metadata absent")
    tree=node.get("tree",{})
    tree_sha=tree.get("sha") if isinstance(tree,dict) else None
    sha(tree_sha)
    stamped=node.get("committer",{})
    committed_at=stamped.get("date") if isinstance(stamped,dict) else None
    # Commit committer/author date is controlled by the committer.
    if committed_at is not None:
        moment(committed_at)
    # Do not mark metadata from an official API as physical task verification.
    return {
        "kind":"github_commit","subject":repo,
        "source_ref":link,"observed_at":_now(now),
        "provider_at":None,"time_trust":"author_controlled",
        "state":"github_commit_metadata_confirmed",
        "content_sha256":hashlib.sha256(
            json.dumps(data,sort_keys=True,ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "metadata":{
            "commit_sha":commit_sha,"tree_sha":tree_sha,
            "committer_reported_time_untrusted":committed_at,
            "parents":[x["sha"] for x in data.get("parents",[]) if
                       isinstance(x,dict) and isinstance(x.get("sha"),str)],
            "source_response_hash_not_file_bytes":True,
            "proof_scope":"existence_of_commit_only",
        },
    }


def github_workflow(repo,run_id,*,now=None,fetch=fetch_json,token=None):
    repo=slug(repo)
    run_id=number(run_id,"run_id")
    endpoint=_url(repo,f"/actions/runs/{run_id}")
    data=fetch(endpoint,token=token)
    if data.get("id") != run_id:
        raise ObservatoryError("workflow run ID mismatch")
    if data.get("html_url") != f"https://github.com/{repo}/actions/runs/{run_id}":
        raise ObservatoryError("workflow URL/repository mismatch")
    nested=data.get("repository",{})
    if isinstance(nested,dict) and nested.get("full_name") not in (None,repo):
        raise ObservatoryError("workflow run belongs to another repository")
    created=moment(data.get("created_at"))
    observed=_now(now)
    if created>moment(observed):
        raise ObservatoryError("workflow creation time is later than observation")
    status=data.get("status")
    conclusion=data.get("conclusion")
    if status not in ("queued","in_progress","completed",
                      "requested","waiting","pending"):
        raise ObservatoryError("unrecognized workflow status")
    if status!="completed" and conclusion is not None:
        raise ObservatoryError("unfinished workflow cannot have final conclusion")
    head_sha=sha(data.get("head_sha"))
    return {
        "kind":"github_workflow","subject":repo,
        "source_ref":data["html_url"],"observed_at":observed,
        "provider_at":created.isoformat(),"time_trust":"provider_recorded",
        "state": "workflow_"+status,
        "content_sha256":hashlib.sha256(
            json.dumps(data,sort_keys=True,ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "metadata":{
            "run_id":run_id,"head_sha":head_sha,
            "workflow_name":str(data.get("name") or "")[:300],
            "status":status,"conclusion":conclusion,
            "run_attempt":data.get("run_attempt"),
            "provider_updated_at":data.get("updated_at"),
            "source_response_hash_not_artifact_bytes":True,
            "proof_scope":"workflow_execution_metadata_only",
        },
    }


def github_artifact(repo,artifact_id,*,now=None,fetch=fetch_json,token=None):
    repo=slug(repo)
    artifact_id=number(artifact_id,"artifact_id")
    endpoint=_url(repo,f"/actions/artifacts/{artifact_id}")
    data=fetch(endpoint,token=token)
    if data.get("id") != artifact_id:
        raise ObservatoryError("artifact ID mismatch")
    if isinstance(data.get("workflow_run"),dict):
        run_id=data["workflow_run"].get("id")
        if run_id is not None:
            number(run_id,"workflow_run.id")
    else:
        run_id=None
    recorded_at=data.get("created_at")
    stamp=moment(recorded_at)
    observed=_now(now)
    if stamp>moment(observed):
        raise ObservatoryError("artifact publication timestamp is later than collection")
    size=data.get("size_in_bytes")
    if isinstance(size,bool) or not isinstance(size,int) or size<0:
        raise ObservatoryError("invalid artifact byte size")
    return {
        "kind":"github_artifact","subject":repo,
        "source_ref":endpoint,
        "observed_at":observed,
        "provider_at":stamp.isoformat(),"time_trust":"provider_recorded",
        "state":"artifact_expired" if data.get("expired") else "artifact_metadata_visible",
        "content_sha256":None,
        "metadata":{
            "artifact_id":artifact_id,"run_id":run_id,
            "artifact_name":str(data.get("name") or "")[:300],
            "size_in_bytes":size,"expired":bool(data.get("expired")),
            "provider_digest_unverified":data.get("digest"),
            "proof_scope":"metadata_only_no_downloaded_byte_verification",
        },
    }


def local_file(root,relative_path,*,now=None):
    """Hash bounded local bytes WITHOUT executing or uploading them."""
    base=Path(root).resolve(strict=True)
    if not base.is_dir():
        raise ObservatoryError("root must be an existing directory")
    if not isinstance(relative_path,str) or not relative_path:
        raise ObservatoryError("relative_path required")
    rel=Path(relative_path)
    if rel.is_absolute() or ".." in rel.parts or str(rel) in (".",""):
        raise ObservatoryError("only file paths inside the explicit workspace are allowed")
    path=base
    for part in rel.parts:
        path=path/part
        if path.is_symlink():
            raise ObservatoryError("symlinks forbidden inside observed workspace")
    target=path.resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ObservatoryError("path escapes root or is not a regular file")
    stat_info=target.stat()
    if stat_info.st_size>MAX_LOCAL_FILE:
        raise ObservatoryError("file is too large for the read-only observer")
    sha256=hashlib.sha256()
    size=0
    with target.open("rb") as file:
        while block:=file.read(1024*1024):
            size+=len(block)
            if size>MAX_LOCAL_FILE:
                raise ObservatoryError("file grew beyond the configured cap")
            sha256.update(block)
    return {
        "kind":"local_file","subject":"local_workspace",
        "source_ref":"workspace:"+rel.as_posix(),
        "observed_at":_now(now),
        "provider_at":None,"time_trust":"collector_clock",
        "state":"local_bytes_hashed",
        "content_sha256":sha256.hexdigest(),
        "metadata":{
            "relative_path":rel.as_posix(),
            "size_in_bytes":size,
            "proof_scope":"file_bytes_exist_at_observation_not_execution_or_quality",
        },
    }
