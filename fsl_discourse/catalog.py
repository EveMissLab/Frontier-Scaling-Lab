"""AI interview claims as time-bounded PUBLIC STATEMENTS, not private beliefs.

A source records the original *publisher* and external interviewee in their
role AT THE TIME. A claim records an attributable, locatable paraphrase.
An analytical dimension is a candidate observation, not a true mental state.

No wholesale transcripts, model-inferred private intention, invented precise
interview time, or score of "AGI credibility" is stored.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlsplit
import hashlib
import json
import re


class DiscourseError(ValueError):
    pass


SCHEMA="fsl/discourse-sources-and-claims/0.10"
DAY=re.compile(r"\d{4}-\d{2}-\d{2}\Z")
UID=re.compile(r"[a-z0-9][a-z0-9._-]{1,115}\Z")
LOC=re.compile(r"(?:[0-9]{2}:)?[0-9]{2}:[0-9]{2}\Z")
DIMENSIONS={
    "self_description","definition","forecast","intent_direction",
    "research_strategy","governance","safety","economic_diffusion",
    "verification_criterion","reversibility","uncertainty","public_influence",
}
MODALITIES={
    "asserted","hypothesized","explicitly_uncertain","conditional",
    "personal_preference","organizational_intention_claim",
}
AUTHORITY={
    "individual_public_statement","spokesperson_attributed_company",
    "official_company_position",
}
TRANSCRIPT_ORIGIN={
    "publisher_transcript","original_interviewer_qa","episode_page_only",
}
REVERSIBILITY={
    "not_assessed","question_raised","candidate_reversible",
    "candidate_irreversible","mixed_or_path_dependent",
}
SOURCE_CONFIDENCE={"original_publisher","original_interviewer_qa"}
RELATIONSHIP_CLASS={"speaker_at_time","guest_organization_at_time"}


def _date(v,name):
    if not isinstance(v,str) or DAY.fullmatch(v) is None:
        raise DiscourseError(name+" must be YYYY-MM-DD")
    try:d=date.fromisoformat(v)
    except ValueError as ex:raise DiscourseError(name+" invalid calendar date") from ex
    if d.isoformat()!=v:raise DiscourseError(name+" noncanonical date")
    return v


def _id(v,name):
    if not isinstance(v,str) or UID.fullmatch(v) is None:
        raise DiscourseError(name+" needs stable lowercase/ASCII identifier")
    return v


def _url(v,name):
    if not isinstance(v,str):
        raise DiscourseError(name+" needs HTTPS URL")
    p=urlsplit(v)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        raise DiscourseError(name+" needs HTTPS no credentials")
    return v


def _plain(v,name,max_len=600):
    if not isinstance(v,str) or not v.strip() or len(v)>max_len:
        raise DiscourseError(name+" requires nonblank bounded short prose")
    return v


def hash_canonical(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,ensure_ascii=False,separators=(",",":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def validate(catalog):
    if not isinstance(catalog,dict) or catalog.get("schema")!=SCHEMA:
        raise DiscourseError("unknown interview history schema")
    if catalog.get("capture_calendar_timezone")!="Asia/Taipei":
        raise DiscourseError("capture timezone must be Asia/Taipei")
    captured_day=_date(catalog.get("catalog_reviewed_on"),"catalog_reviewed_on")
    speakers=catalog.get("speakers"); sources=catalog.get("sources")
    claims=catalog.get("claims")
    if not all(isinstance(x,list) for x in (speakers,sources,claims)):
        raise DiscourseError("speakers, sources, claims must be arrays")
    if not speakers or not sources or not claims:
        raise DiscourseError("nonempty speaker, interview and claim corpus needed")
    identities={}
    for s in speakers:
        fields=("speaker_id","display_name")
        if not isinstance(s,dict) or any(x not in s for x in fields):
            raise DiscourseError("speaker identity fields missing")
        sid=_id(s["speaker_id"],"speaker_id")
        _plain(s["display_name"],"display_name",150)
        if sid in identities:raise DiscourseError("duplicate speaker")
        identities[sid]=s
    seen={}
    for s in sources:
        req=("source_id","title","publisher","published_on",
             "first_captured_on","interview_recorded_on",
             "speaker_id","organization_at_time","role_at_time",
             "affiliation_relation","format","url","transcript_url",
             "transcript_origin","source_confidence","publication_date_basis")
        if not isinstance(s,dict) or any(k not in s for k in req):
            raise DiscourseError("interview needs publication/capture/speaker metadata")
        uid=_id(s["source_id"],"source_id")
        if uid in seen:raise DiscourseError("duplicate interview source ID")
        if s["speaker_id"] not in identities:
            raise DiscourseError("speaker unknown")
        for key in ("title","publisher","organization_at_time","role_at_time"):
            _plain(s[key],key,220)
        if s["affiliation_relation"] not in RELATIONSHIP_CLASS:
            raise DiscourseError("speaker affiliation semantics required")
        if s["format"] not in ("podcast_interview","interview_QA"):
            raise DiscourseError("interview format must be explicit")
        if s["transcript_origin"] not in TRANSCRIPT_ORIGIN or s["source_confidence"] not in SOURCE_CONFIDENCE:
            raise DiscourseError("original source type required")
        if s["transcript_origin"]=="episode_page_only":
            if s["transcript_url"] is not None:
                raise DiscourseError("episode-only source may not claim a transcript")
        elif s["transcript_url"] is None:
            raise DiscourseError("quote localization requires primary transcript/original Q&A")
        _url(s["url"],"source url")
        if s["transcript_url"] is not None:
            _url(s["transcript_url"],"transcript URL")
        published=_date(s["published_on"],"published_on")
        first=_date(s["first_captured_on"],"first_captured_on")
        if published>first or first>captured_day:
            raise DiscourseError("interview cannot be observed before publication")
        if s["interview_recorded_on"] is not None:
            recorded=_date(s["interview_recorded_on"],"interview_recorded_on")
            if recorded>published:
                raise DiscourseError("recorded interview time cannot postdate publication")
        if s["publication_date_basis"] not in ("publisher_page","platform_episode_metadata"):
            raise DiscourseError("publication day evidence basis missing")
        seen[uid]=s
    claim_ids=set()
    for c in claims:
        req=("claim_id","source_id","speaker_id","source_locator",
             "record_status","original_language","paraphrase_zh_tw",
             "claim_scope","modality","dimensions",
             "reversibility_assessment","stance_link_hypothesis",
             "annotation_status","analytic_limits")
        if not isinstance(c,dict) or any(k not in c for k in req):
            raise DiscourseError("claim missing citation or inference/authority flags")
        cid=_id(c["claim_id"],"claim_id")
        if cid in claim_ids:raise DiscourseError("duplicate claim ID")
        claim_ids.add(cid)
        src=seen.get(c["source_id"])
        if src is None or src["speaker_id"]!=c["speaker_id"]:
            raise DiscourseError("claim requires matching source + real speaker")
        loc=c["source_locator"]
        if not isinstance(loc,dict) or set(loc)!={"timecode","section"}:
            raise DiscourseError("claim locator must specify timecode/section")
        if loc["timecode"] is not None and (
            not isinstance(loc["timecode"],str) or LOC.fullmatch(loc["timecode"]) is None):
            raise DiscourseError("timecode must match source video timestamp")
        if loc["section"] is not None:_plain(loc["section"],"section",160)
        if loc["timecode"] is None and loc["section"] is None:
            raise DiscourseError("interview claim must be locatable")
        if c["record_status"] not in ("paraphrased_original_QA","paraphrased_publisher_transcript"):
            raise DiscourseError("claim must not be presented as reproduced quote")
        if c["original_language"] not in ("en","zh-CN","zh-TW"):
            raise DiscourseError("origin language needed")
        _plain(c["paraphrase_zh_tw"],"paraphrase_zh_tw",500)
        if c["claim_scope"] not in AUTHORITY or c["modality"] not in MODALITIES:
            raise DiscourseError("no ungrounded company attribution / modality")
        if c["claim_scope"]=="official_company_position":
            raise DiscourseError("interviewee speech alone is not a binding company position")
        dims=c["dimensions"]
        if (not isinstance(dims,list) or not dims or len(dims)!=len(set(dims))
                or not set(dims)<=DIMENSIONS):
            raise DiscourseError("supported non-exclusive research dimensions required")
        if c["reversibility_assessment"] not in REVERSIBILITY:
            raise DiscourseError("reversibility must allow explicit unknown")
        if c["annotation_status"]!="analyst_provisional_not_fact":
            raise DiscourseError("do not present a researcher interpretation as speaker fact")
        if c["stance_link_hypothesis"] is not None:
            _plain(c["stance_link_hypothesis"],"hypothesis",220)
        _plain(c["analytic_limits"],"analytic_limits",240)
        if c.get("verbatim_quote") is not None:
            raise DiscourseError("do not copy verbatim interview transcript into public catalog")
    return {
        "schema":"fsl/discourse-catalog-validated/0.10",
        "speaker_count":len(identities),
        "interview_count":len(seen),
        "claim_count":len(claims),
        "publisher_count":len({s["publisher"] for s in sources}),
        "organization_count":len({s["organization_at_time"] for s in sources}),
        "first_FSL_capture_Asia_Taipei":captured_day,
        "canonical_catalog_sha256":hash_canonical(catalog),
        "internal_beliefs_inferred":False,
        "any_proven_causal_claim":False,
    }


def asof_view(catalog,*,as_of,mode="retrospective"):
    validate(catalog)
    _date(as_of,"as_of")
    if mode not in ("strict_known_at_time","retrospective"):
        raise DiscourseError("unsupported chronology mode")
    sources={s["source_id"]:s for s in catalog["sources"]}
    rows=[]
    for c in catalog["claims"]:
        source=sources[c["source_id"]]
        pub=source["published_on"]<=as_of
        observed=source["first_captured_on"]<=as_of
        included=pub and (observed or mode=="retrospective")
        status=("not_yet_published" if not pub else
                "historically_published_captured_later" if not observed else
                "already_captured_by_FSL")
        rows.append({
            "claim_id":c["claim_id"],"speaker_id":c["speaker_id"],
            "source_id":c["source_id"],
            "organization_at_time":source["organization_at_time"],
            "publisher":source["publisher"],"source_url":source["url"],
            "published_on":source["published_on"],
            "first_captured_on":source["first_captured_on"],
            "paraphrase_zh_tw":c["paraphrase_zh_tw"],
            "dimensions":c["dimensions"],
            "modality":c["modality"],
            "reversibility_assessment":c["reversibility_assessment"],
            "source_locator":c["source_locator"],
            "asof_status":status,
            "included":bool(included),
            "original_forecast_knowledge":bool(pub and observed),
            "observed_company_action":False,
            "speaker_internal_belief_known":False,
            "predictive_accuracy_adjudicated":False,
        })
    rows.sort(key=lambda r:(r["published_on"],r["source_id"],r["claim_id"]))
    return {
        "schema":"fsl/discourse-asof/0.10",
        "as_of":as_of,"mode":mode,
        "date_precision":"publication_day; actual recording time may be unknown",
        "rows":rows,"included_claims":sum(r["included"] for r in rows),
        "report_is_observational_not_theory_closure":True,
        "warning":"Public statements are source-grounded, not proof of private intention, company policy, or causal effects on future AI.",
    }
