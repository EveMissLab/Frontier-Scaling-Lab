"""FSL v0.9 canonical dated provider claims, NEVER task success scores.

Separates announced release, point-in-time API price, agent tooling and
retirement. It does not extrapolate the historical price to all future dates
or infer public access solely because a model was once announced.

Every assertion is linked to a primary source and a FSL first-capture date.
Past publications newly read by FSL in 2026 are retrospective evidence, NOT
observations FSL actually possessed in 2024 or 2025.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from urllib.parse import urlsplit

SCHEMA="fsl/historical-release-catalog/v0.9"
DATE=re.compile(r"\d{4}-\d{2}-\d{2}\Z")
ID=re.compile(r"[A-Za-z0-9_.:-]{1,110}\Z")
PROVIDERS=("openai","anthropic","google","xai","deepseek")
CATEGORIES={
    "model_announcement", "model_update", "agent_tool_release",
    "model_retirement", "plan_policy", "api_price_quote",
}
CHANNELS={"chat","api","coding_agent","research_tool","private_preview",
          "enterprise","open_weights","other"}
AVAILABILITY={"launched","rollout","preview","limited_preview",
              "planned_not_yet_available","retired","unknown"}
IDENTIFIER_KINDS={"named_family","dated_snapshot","api_alias","tool",
                  "product_route"}
BASIS={"point_quote","explicit_bounded_interval"}


class CatalogError(ValueError): pass


def day(x,field):
    if not isinstance(x,str) or DATE.fullmatch(x) is None:
        raise CatalogError(field+" needs exactly YYYY-MM-DD")
    try:
        v=date.fromisoformat(x)
    except ValueError as exc:raise CatalogError(field+" is invalid date") from exc
    if v.isoformat()!=x:raise CatalogError(field+" is not canonical")
    return x


def ident(x,field):
    if not isinstance(x,str) or ID.fullmatch(x) is None:
        raise CatalogError(field+" needs stable ASCII identifier")
    return x


def text(x,field,cap=400):
    if not isinstance(x,str) or not x.strip() or len(x)>cap:
        raise CatalogError(field+" needs concise nonempty source-grounded prose")
    return x


def uri(x,field):
    if not isinstance(x,str):
        raise CatalogError(field+" needs HTTPS")
    p=urlsplit(x)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise CatalogError(field+" needs HTTPS without credentials")
    return x


def amount(x,field):
    if isinstance(x,bool) or not isinstance(x,(str,int,float,Decimal)):
        raise CatalogError(field+" invalid decimal")
    try: d=Decimal(str(x))
    except InvalidOperation as exc:raise CatalogError(field+" invalid decimal") from exc
    if not d.is_finite() or d<0:raise CatalogError(field+" must be nonnegative finite")
    return d


def fingerprint(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,
                    separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()


def validate(data):
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA:
        raise CatalogError("wrong historical catalog schema")
    cutoff=day(data.get("catalog_reviewed_on"),"catalog_reviewed_on")
    if data.get("catalog_review_timezone")!="Asia/Taipei":
        raise CatalogError("must specify source capture calendar Asia/Taipei")
    sources=data.get("sources"); events=data.get("events")
    if not isinstance(sources,list) or not sources or not isinstance(events,list) or not events:
        raise CatalogError("sources/events must be nonempty lists")
    src={}
    for s in sources:
        required=("source_id","publisher","url","published_on","first_captured_on",
                  "document_kind","date_basis")
        if not isinstance(s,dict) or any(k not in s for k in required):
            raise CatalogError("source missing time/provenance")
        sid=ident(s["source_id"],"source_id")
        if sid in src:raise CatalogError("duplicate source")
        if s["publisher"] not in PROVIDERS:raise CatalogError("non-provider primary source")
        uri(s["url"],"source URL")
        published=day(s["published_on"],"source published_on")
        captured=day(s["first_captured_on"],"source first_captured_on")
        if published>captured or captured>cutoff:
            raise CatalogError("source publication/capture not in temporal order")
        if s["document_kind"] not in ("dated_announcement","dated_change_log","dated_release_notes"):
            raise CatalogError("source must be dated provider primary material")
        if s["date_basis"] not in ("article_date","dated_subsection"):
            raise CatalogError("explicit publication date basis needed")
        src[sid]=s
    seen=set()
    for e in events:
        required=("event_id","source_id","provider","model_key",
                  "identifier_kind","kind","occurred_on","availability_at_event",
                  "channels","claim","proof_limit")
        if not isinstance(e,dict) or any(k not in e for k in required):
            raise CatalogError("event lacks model identity or source date")
        eid=ident(e["event_id"],"event_id")
        if eid in seen:raise CatalogError("duplicate event")
        seen.add(eid)
        s=src.get(e["source_id"])
        if s is None:raise CatalogError("unknown source")
        if e["provider"]!=s["publisher"]:
            raise CatalogError("provider and source publisher mismatch")
        ident(e["model_key"],"model_key")
        if e["identifier_kind"] not in IDENTIFIER_KINDS:
            raise CatalogError("version identifier precision required")
        if e["kind"] not in CATEGORIES:
            raise CatalogError("unsupported historical event")
        happened=day(e["occurred_on"],"event occurred_on")
        if happened>cutoff:raise CatalogError("catalog cannot claim future-observed events")
        # Past retrospective claims are fine even if the original source
        # published a later correction, but do not imply FSL knew it then.
        if e["availability_at_event"] not in AVAILABILITY:
            raise CatalogError("availability cannot be assumed")
        ch=e["channels"]
        if not isinstance(ch,list) or len(set(ch))!=len(ch) or not ch or not set(ch)<=CHANNELS:
            raise CatalogError("invalid model/tool access channel")
        text(e["claim"],"claim",350);text(e["proof_limit"],"proof_limit",350)
        if e["kind"]=="model_retirement" and e["availability_at_event"]!="retired":
            raise CatalogError("retired model must be labeled retired")
        if e["kind"]=="api_price_quote":
            price=e.get("price")
            if not isinstance(price,dict):
                raise CatalogError("price event needs a typed monetary price quote")
            keys={"currency","unit","uncached_input","cached_input","output",
                  "billing_product","validity"}
            if set(price)!=keys:raise CatalogError("price schema missing scope")
            if price["currency"]!="USD" or price["unit"]!="per_million_tokens":
                raise CatalogError("unsupported price units")
            if price["billing_product"]!="api":
                raise CatalogError("price cannot be presented as subscription cost")
            if price["validity"]!="point_quote":
                raise CatalogError("price quote may only be used on its event date")
            amount(price["uncached_input"],"uncached_input")
            amount(price["output"],"output")
            if price["cached_input"] is not None:
                amount(price["cached_input"],"cached_input")
        elif e.get("price") is not None:
            raise CatalogError("non-price event must not silently carry API price")
    return {
        "schema":SCHEMA,"source_count":len(sources),"event_count":len(events),
        "providers":sorted({e["provider"] for e in events}),
        "years":sorted({e["occurred_on"][:4] for e in events}),
        "original_catalog_sha256":fingerprint(data),
        "reviewed_on":cutoff,
    }


def timeline(data, *, as_of, mode="retrospective"):
    validate(data)
    cutoff=day(as_of,"as_of")
    if mode not in ("retrospective","strict_known_at_time"):
        raise CatalogError("unknown source-vintage mode")
    ss={s["source_id"]:s for s in data["sources"]}
    entries=[]
    for e in data["events"]:
        s=ss[e["source_id"]]
        happened=e["occurred_on"]<=cutoff
        published=s["published_on"]<=cutoff
        observed=s["first_captured_on"]<=cutoff
        eligible=happened and published and (observed or mode=="retrospective")
        if not happened:state="not_yet_event"
        elif not published:state="not_published_at_cutoff"
        elif not observed:state="historically_published_reconstructed_later"
        else:state="known_to_FSL_at_cutoff"
        entries.append({
            "event_id":e["event_id"],"provider":e["provider"],
            "model_key":e["model_key"],"identifier_kind":e["identifier_kind"],
            "kind":e["kind"],"occurred_on":e["occurred_on"],
            "source_published_on":s["published_on"],
            "source_first_captured_on":s["first_captured_on"],
            "source_date_basis":s["date_basis"],
            "source_url":s["url"],"availability_at_event":e["availability_at_event"],
            "channels":e["channels"],"claim":e["claim"],
            "proof_limit":e["proof_limit"],
            "price_quote_valid_only_on":(
                e["occurred_on"] if e["kind"]=="api_price_quote" else None),
            "price":e.get("price"),
            "time_status":state,"included":bool(eligible),
            "admissible_to_original_forecast":bool(eligible and observed),
            "functional_G1_to_G4_measured":False,
        })
    entries.sort(key=lambda e:(e["occurred_on"],e["provider"],e["event_id"]))
    return {
        "schema":"fsl/historical-timeline/0.9","as_of":cutoff,
        "mode":mode,"date_precision":"calendar_day",
        "catalog_reviewed_on_Asia_Taipei":data["catalog_reviewed_on"],
        "events":entries,
        "included_count":sum(e["included"] for e in entries),
        "independently_verified_autonomous_completion_count":0,
        "warning":"Announced release is not proof of continuous availability, historical user entitlement, autonomous task completion or original-forecast knowledge.",
    }


def period_matrix(data, *, month_ends):
    """Historical MARKET INTRODUCTION coverage, not actual API reachability."""
    validate(data)
    if not isinstance(month_ends,list) or not month_ends:
        raise CatalogError("provide explicit period_end dates")
    if len(set(month_ends))!=len(month_ends):
        raise CatalogError("duplicate period")
    reports=[]
    for cutoff in month_ends:
        out=timeline(data,as_of=cutoff,mode="retrospective")
        available=[e for e in out["events"] if e["included"]]
        group=[]
        for provider in PROVIDERS:
            prov=[e for e in available if e["provider"]==provider]
            introductions=[e for e in prov if e["kind"] in
                           ("model_announcement","model_update")]
            items=[]
            for e in introductions:
                items.append({
                    "model_key":e["model_key"],
                    "event_id":e["event_id"],
                    "introduced_on":e["occurred_on"],
                    "channel_at_introduction":e["channels"],
                    "historical_source_url":e["source_url"],
                    "now_or_at_period_end_available":None,
                })
            price_points=[e for e in prov if e["kind"]=="api_price_quote"
                          and e["occurred_on"]==cutoff]
            group.append({
                "provider":provider,
                "releases_announced_by_cutoff":len(introductions),
                "dated_introductions":items,
                "price_quotes_published_on_cutoff_day_only":price_points,
                "actual_subscription_quota_at_cutoff":None,
                "actual_24h_agent_completions":None,
                "actual_48h_agent_completions":None,
                "historical_price_valid_through_cutoff":None,
            })
        reports.append({"period_end":cutoff,
                        "provider_rows":group,
                        "historical_coverage_is_retrospective":True})
    return {
        "schema":"fsl/period-access-matrix/0.9",
        "periods":reports,"providers":list(PROVIDERS),
        "source_vintage":"first captured on 2026-11-07, not contemporaneous observation",
        "no_task_completion_scores_inferred":True,
        "warnings":[
            "An introduced model may have since been retired, renamed or silently changed.",
            "A dated price is valid as a POINT quote; it cannot be carried forward without more sources.",
            "No API entitlement or 24-48h task success rate is inferable from announcement dates.",
        ]
    }
