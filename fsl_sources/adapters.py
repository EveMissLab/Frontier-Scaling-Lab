"""Documented public API adapters; no indiscriminate crawling.

HF Hub API, HF benchmark leaderboard API, and HF dataset viewer (official
Arena leaderboard public dataset). Only normalized aggregate metadata is stored;
individual user comments, votes and personal identifiers are never downloaded.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request

from .catalog import CatalogError, finite_value, iso_day, source_url

HF_HUB = "https://huggingface.co"
HF_DATASETS = "https://datasets-server.huggingface.co"
ARENA_DATASET = "lmarena-ai/leaderboard-dataset"
ARENA_PAGE = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset"
HF_BENCHMARK_DOC = "https://huggingface.co/docs/hub/leaderboard-data-guide"
USER_AGENT = "Frontier-Scaling-Lab/0.3 (+https://github.com/EveMissLab/Frontier-Scaling-Lab)"
MAX_RESPONSE_BYTES = 3 * 1024 * 1024


def encode_repo_id(repo_id):
    if not isinstance(repo_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_id):
        raise CatalogError("expected trusted namespace/name Hugging Face ID")
    return urllib.parse.quote(repo_id, safe="/")


def json_api_get(url, *, timeout=20, max_bytes=MAX_RESPONSE_BYTES):
    """Bounded official API fetch with rate-limit errors and no credentials.

    Only the two declared Hugging Face hosts are allowed; do not follow third-
    party redirects. An optional HTTP bearer token is deliberately NOT used.
    """
    source_url(url)
    parts = urllib.parse.urlsplit(url)
    if parts.hostname not in ("huggingface.co", "datasets-server.huggingface.co"):
        raise CatalogError("only official Hugging Face API hosts are allowed")
    if parts.port is not None or parts.username or parts.password:
        raise CatalogError("nonstandard ports and credentials are forbidden")
    req = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": USER_AGENT})
    # A custom redirect handler restricts redirect targets to the same allowlist.
    class AllowedRedirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            target = urllib.parse.urlsplit(newurl)
            if target.scheme != "https" or target.hostname not in (
                "huggingface.co", "datasets-server.huggingface.co"):
                raise CatalogError("redirect to untrusted host blocked")
            return super().redirect_request(request, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(AllowedRedirects())
    try:
        with opener.open(req, timeout=timeout) as response:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise CatalogError("API response exceeds configured byte limit")
            if response.status != 200:
                raise CatalogError(f"unexpected HTTP status {response.status}")
    except urllib.error.HTTPError as exc:
        raise CatalogError(
            f"API HTTP {exc.code}. Respect provider limits and retry manually later."
        ) from exc
    except urllib.error.URLError as exc:
        raise CatalogError(f"API connection failed: {exc.reason}") from exc
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogError("API did not return UTF-8 JSON") from exc


def hf_model_request(model_id):
    return HF_HUB + "/api/models/" + encode_repo_id(model_id)


def hf_benchmark_request(dataset_id):
    return HF_HUB + "/api/datasets/" + encode_repo_id(dataset_id) + "/leaderboard"


def arena_splits_request():
    return HF_DATASETS + "/splits?" + urllib.parse.urlencode(
        {"dataset": ARENA_DATASET})


def arena_rows_request(config, split, *, offset=0, limit=100):
    if not isinstance(config, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", config):
        raise CatalogError("invalid arena configuration")
    if split not in ("latest", "full"):
        raise CatalogError("arena split must be latest or full")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise CatalogError("offset must be a nonnegative integer")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise CatalogError("Arena API page must contain 1..100 rows")
    params = urllib.parse.urlencode({
        "dataset": ARENA_DATASET, "config": config,
        "split": split, "offset": offset, "length": limit})
    return HF_DATASETS + "/rows?" + params


def _utc_date(value):
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return iso_day(value[:10])
    except CatalogError:
        return None


def _metric(model_id, measure, value, unit, channel, methodology, category,
            *, published=None, count=None, low=None, high=None, flags=None):
    score = finite_value(value, measure)
    return {
        "external_model_id": model_id, "measure": measure, "value": score,
        "unit": unit, "channel": channel, "methodology": methodology,
        "category": category, "published_on": published,
        "sample_size": count, "ci_low": low, "ci_high": high,
        "provenance_flags": flags or [],
    }


def parse_hf_model(data, *, model_id, retrieved_on):
    if not isinstance(data, dict):
        raise CatalogError("model API must return an object")
    stable_id = data.get("id")
    if stable_id and stable_id != model_id:
        raise CatalogError("API model ID mismatch")
    last_modified = _utc_date(data.get("lastModified"))
    if last_modified and last_modified > retrieved_on:
        raise CatalogError("model lastModified is after retrieval date")
    model_key = "hf:" + model_id
    sha = data.get("sha")
    card = data.get("cardData") or {}
    source_license_name = (card.get("license") if isinstance(card, dict) else None)
    if not isinstance(source_license_name, str) or not source_license_name:
        source_license_name = "unknown"
    output = []
    # Safetensors metadata counts *serialized* weights in a repository, which
    # can include adapters, quantized variants, and tied/un-tied parameters.
    # It is NOT necessarily architectural parameter count or per-token active N.
    sf = data.get("safetensors")
    sf_total = sf.get("total") if isinstance(sf, dict) else None
    if sf_total is not None:
        total = finite_value(sf_total, "safetensors.total")
        if total > 0:
            output.append(_metric(
                model_key, "serialized_safetensors_elements", total, "elements",
                "metadata", "hf-hub-api-safetensors-total", "weights",
                published=last_modified or retrieved_on,
                flags=["repo_weight_element_count_not_verified_model_parameters",
                       "not_active_parameters", "quantization_or_adapter_caveat"]))
    for field in ("downloads", "likes"):
        raw = data.get(field)
        if raw is not None:
            val = finite_value(raw, field)
            if val >= 0:
                output.append(_metric(
                    model_key, "hub_" + field, val, "count", "metadata",
                    "hf-hub-api-" + field, "hub_usage",
                    published=retrieved_on,
                    flags=["popularity_not_model_quality", "provider_metric_definition"]))
    return {
        "source_type": "hf_model", "resource_id": model_id,
        "url": HF_HUB + "/" + encode_repo_id(model_id),
        "license_name": source_license_name,
        "attribution": "Hugging Face Hub / source model publisher",
        "published_on": last_modified, "retrieved_on": retrieved_on,
        "raw_document": data, "observations": output,
        "note": "repo SHA " + str(sha or "not reported") + "; metadata is not a benchmark",
    }


def parse_arena_page(data, *, config, split, offset, retrieved_on):
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise CatalogError("Arena dataset viewer JSON must have rows")
    results = []
    for entry in data["rows"]:
        row = entry.get("row") if isinstance(entry, dict) else None
        if not isinstance(row, dict):
            continue
        name = row.get("model_name")
        if not isinstance(name, str) or not name.strip():
            continue
        category = row.get("category") or "overall"
        if not isinstance(category, str):
            raise CatalogError("invalid arena category")
        published = _utc_date(row.get("leaderboard_publish_date"))
        if published is None:
            raise CatalogError("Arena published date is essential for temporal inference")
        if published > retrieved_on:
            raise CatalogError("Arena publish date is later than retrieval")
        # Agent is IPS scoring, distinct from text-style Bradley-Terry rating.
        is_agent_score = isinstance(row.get("score"), (int, float)) and not isinstance(row.get("score"), bool)
        label = "ips_score" if is_agent_score else "arena_rating"
        unit = "ips_score" if is_agent_score else "arena_rating"
        field = "score" if is_agent_score else "rating"
        if field not in row:
            continue
        val = finite_value(row[field], field)
        lower_field, upper_field = (
            ("score_ci_lower", "score_ci_upper") if is_agent_score
            else ("rating_lower", "rating_upper"))
        lower, upper = row.get(lower_field), row.get(upper_field)
        if lower is not None:
            lower = finite_value(lower, lower_field)
        if upper is not None:
            upper = finite_value(upper, upper_field)
        num = row.get("observation_count" if is_agent_score else "vote_count")
        if isinstance(num, float) and num.is_integer():
            num = int(num)
        if isinstance(num, bool) or not isinstance(num, int) or num < 0:
            num = None
        flags = ["human_comparison_preference_not_general_cognition",
                 "leaderboard_methodology_can_change_over_time"]
        if is_agent_score:
            flags.append("agent_ips_not_bradley_terry")
        results.append(_metric(
            "arena:" + name, label, val, unit, "preference",
            "arena-dataset:" + config + ":" + label,
            category, published=published, count=num, low=lower, high=upper,
            flags=flags))
    return {
        "source_type": "arena",
        "resource_id": ARENA_DATASET + ":" + config + ":" + split + ":" + str(offset),
        "url": ARENA_PAGE,
        "license_name": "CC-BY-4.0 (as declared in dataset card)",
        "attribution": "Arena (arena.ai), leaderboard-dataset, via Hugging Face",
        "published_on": None, "retrieved_on": retrieved_on,
        "raw_document": data, "observations": results,
        "note": "Subset " + config + ", split " + split +
                "; methodology and leaderboard category must not be collapsed",
    }


def parse_hf_benchmark(data, *, dataset_id, retrieved_on, max_rows=100):
    """Official benchmark leaderboard API returns array of entries.

    A leaderboard score may be submitted by the developer and not independently
    reproduced: preserve the verified field as a provenance warning.
    """
    if not isinstance(data, list):
        raise CatalogError("HF benchmark leaderboard API is expected to return a list")
    if len(data) > max_rows:
        raise CatalogError("benchmark exceeds requested row cap")
    records = []
    for row_index, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("modelId")
        value = entry.get("value")
        if not isinstance(model_id, str) or not model_id or isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        flags = ["hf_benchmark_entry_not_necessarily_reproduced",
                 "evaluation_agent_and_scaffold_may_differ"]
        flags.append("entry_marked_verified" if entry.get("verified") is True
                     else "entry_not_marked_verified")
        # A model may have several leaderboard submissions with different
        # agents/scaffolds. Never overwrite or dedupe them as one model score.
        # Row index is included to disambiguate repeated filenames even when
        # the upstream leaderboard contains several identical submission IDs.
        label = json.dumps({
            "file": entry.get("filename"), "pull_request": entry.get("pullRequest"),
            "row_index": row_index, "model_id": model_id,
        }, sort_keys=True, ensure_ascii=False)
        submission_id = hashlib.sha256(label.encode("utf-8")).hexdigest()[:20]
        methodology = ("hf-official-benchmark:" + dataset_id +
                       ":submission:" + submission_id)
        flags.append("submission_specific_not_a_universal_model_score")
        records.append(_metric(
            "hf:" + model_id, "submitted_benchmark_value", value,
            "benchmark_defined_units", "benchmark",
            methodology,
            dataset_id, published=retrieved_on, flags=flags))
        nparam = entry.get("num_parameters")
        if isinstance(nparam, (int, float)) and not isinstance(nparam, bool) and nparam > 0:
            records.append(_metric(
                "hf:" + model_id, "leaderboard_reported_parameters", nparam,
                "parameters_reported", "metadata",
                methodology + ":parameter-report",
                dataset_id, published=retrieved_on,
                flags=["not_architecturally_verified", "not_active_parameters"]))
    return {
        "source_type": "hf_benchmark", "resource_id": dataset_id,
        "url": HF_HUB + "/datasets/" + encode_repo_id(dataset_id),
        "license_name": "unknown; consult individual dataset and submission terms",
        "attribution": "Hugging Face official benchmark leaderboard contributors",
        "published_on": retrieved_on, "retrieved_on": retrieved_on,
        "raw_document": data, "observations": records,
        "note": "Scores may be submitted by third parties; retain agent/scaffold confounders",
    }


def _wilson(positive, n, z=1.96):
    p = positive / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    bound = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/denom
    return max(0.0, centre-bound), min(1.0, centre+bound)


def parse_community_rollup(data, *, retrieved_on):
    """Only reviewed, anonymous counts. NO raw comments, user IDs or excerpts."""
    if not isinstance(data, dict):
        raise CatalogError("a feedback rollup must be a JSON object")
    allowed = {
        "external_model_id", "category", "counts", "sampling_method",
        "collected_on", "source_url", "source_license", "attribution",
        "sample_window_id",
    }
    if set(data) - allowed:
        raise CatalogError("unexpected fields; do not ingest raw comments or identities")
    needed = allowed - set(data)
    if needed:
        raise CatalogError("missing required rollup fields")
    if data["sampling_method"] not in (
        "opt_in_survey", "curated_public_sample", "structured_user_study"):
        raise CatalogError("unknown sampling method")
    source_url(data["source_url"])
    day = iso_day(data["collected_on"], "collected_on")
    if day > retrieved_on:
        raise CatalogError("feedback date is in the future")
    counts = data["counts"]
    if not isinstance(counts, dict) or set(counts) != {
        "positive", "neutral", "negative"}:
        raise CatalogError("counts must contain positive, neutral and negative")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0
           for v in counts.values()):
        raise CatalogError("all counts must be nonnegative integers")
    n = sum(counts.values())
    if n == 0:
        raise CatalogError("zero-size sample")
    if not all(isinstance(data[k], str) and data[k].strip()
               for k in ("external_model_id", "category", "source_license",
                         "attribution", "sample_window_id")):
        raise CatalogError("missing model, category, license or attribution")
    low, high = _wilson(counts["positive"], n)
    method = "community:" + data["sampling_method"] + ":" + data["sample_window_id"]
    observations = [_metric(
        "community:" + data["external_model_id"],
        "positive_response_fraction", counts["positive"] / n, "fraction",
        "community", method, data["category"], published=day,
        count=n, low=low, high=high, flags=[
            "subjective_self_selected_or_nonrepresentative",
            "wilson_interval_sampling_assumptions_not_guaranteed",
            "not_training_feedback_for_parameter_model",
            "not_a_global_cognition_measure",
            "no_individual_comments_stored",
        ])]
    return {
        "source_type": "community_rollup",
        "resource_id": data["source_url"] + "#" + data["sample_window_id"],
        "url": data["source_url"], "license_name": data["source_license"],
        "attribution": data["attribution"], "published_on": day,
        "retrieved_on": retrieved_on, "raw_document": data,
        "observations": observations,
        "note": "Aggregates only; " + data["sampling_method"] + "; n=" + str(n),
    }
