"""Keep public narratives and independently dated product events as separate axes.

A public claim may temporally precede a model/tool/product release, but the
release alone neither proves the speaker was accurate nor caused the decision.

A same-person later interview can describe *different framing* without
proving a reversal of personal belief, company strategy or actual technology.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from .catalog import (
    validate, _date, _id, _plain, _url, DiscourseError
)


RELATION_KINDS={
    "speaker_later_rearticulation",
    "public_statement_then_independently_dated_product_event",
    "independently_dated_prior_product_context",
}
INTERPRETATIONS={
    "open_comparison", "possible_directional_consistency",
    "possible_tension", "reframing_candidate",
}
NEXT_GATES={
    "not_assessed", "source_retrieval_needed",
    "independent_outcome_needed", "institutional_document_needed",
}
NO_CAUSAL_STATUS="not_established"


def _source_index(catalog):
    return {s["source_id"]:s for s in catalog["sources"]}


def reconcile(public_claims, history, links, *, as_of):
    """Only a dated relation ledger, never a retrospectively improved forecast."""
    validate(public_claims)
    _date(as_of,"as_of")
    if not isinstance(history,dict) or history.get("schema")!=(
            "fsl/historical-release-catalog/v0.9"):
        raise DiscourseError("expected original v0.9 dated product history")
    # Reuse the v0.9 authoritative validation rather than trusting old IDs.
    from fsl_history.catalog import validate as validate_market
    validate_market(history)
    if not isinstance(links,dict) or links.get("schema")!=(
            "fsl/discourse-history-links/0.10"):
        raise DiscourseError("unknown relation ledger")
    recorded=_date(links.get("reviewed_on"),"reviewed_on")
    if recorded>public_claims["catalog_reviewed_on"]:
        raise DiscourseError("link ledger is later than available claim corpus")
    relations=links.get("relations")
    if not isinstance(relations,list):
        raise DiscourseError("relations must be list, including empty")
    claims={c["claim_id"]:c for c in public_claims["claims"]}
    sources=_source_index(public_claims)
    product={e["event_id"]:e for e in history["events"]}
    market_sources={s["source_id"]:s for s in history["sources"]}
    ids=set()
    results=[]
    for l in relations:
        fields=("relation_id","left_claim_id","right_kind","right_id",
                "relation_kind","interpretation","causal_status",
                "reversibility_status","review_gate","source_url",
                "research_note","annotation_status")
        if not isinstance(l,dict) or any(k not in l for k in fields):
            raise DiscourseError("relation lacks provenance/temporal review")
        lid=_id(l["relation_id"],"relation_id")
        if lid in ids:
            raise DiscourseError("duplicate relation ID")
        ids.add(lid)
        left=claims.get(l["left_claim_id"])
        if left is None:raise DiscourseError("relation must reference a known quote claim")
        if l["relation_kind"] not in RELATION_KINDS or l["interpretation"] not in INTERPRETATIONS:
            raise DiscourseError("unsupported relation or interpretation")
        if l["causal_status"]!=NO_CAUSAL_STATUS:
            raise DiscourseError("time adjacency is not verified causation")
        if l["reversibility_status"]!="not_demonstrated":
            raise DiscourseError("cannot assert a strategic reversal on text alone")
        if l["review_gate"] not in NEXT_GATES:
            raise DiscourseError("unknown independent-review status")
        if l["annotation_status"]!="analyst_provisional":
            raise DiscourseError("provisional interpretation must not be factual")
        _plain(l["research_note"],"research_note",240)
        _url(l["source_url"],"source_url")
        event_date=sources[left["source_id"]]["published_on"]
        if l["right_kind"]=="discourse_claim":
            target=claims.get(l["right_id"])
            if target is None:
                raise DiscourseError("unknown subsequent interview claim")
            if l["relation_kind"]!="speaker_later_rearticulation":
                raise DiscourseError("claim-to-claim requires rearticulation relation")
            if target["speaker_id"]!=left["speaker_id"]:
                raise DiscourseError("speaker change cannot be an individual revision")
            right_date=sources[target["source_id"]]["published_on"]
            if right_date<=event_date:
                raise DiscourseError("subsequent self-comparison must occur later")
            if l["source_url"]!=sources[target["source_id"]]["transcript_url"]:
                raise DiscourseError("later interview source URL must be canonical")
            source_capture=sources[target["source_id"]]["first_captured_on"]
        elif l["right_kind"]=="historical_product_event":
            target=product.get(l["right_id"])
            if target is None:
                raise DiscourseError("product event is not in v0.9 source history")
            right_date=target["occurred_on"]
            if l["relation_kind"]=="public_statement_then_independently_dated_product_event" and right_date<event_date:
                raise DiscourseError("future product cannot predate original interview")
            if l["relation_kind"]=="independently_dated_prior_product_context" and right_date>event_date:
                raise DiscourseError("prior product context must not come from future")
            ms=market_sources[target["source_id"]]
            if l["source_url"]!=ms["url"]:
                raise DiscourseError("product anchor must link to its primary source")
            source_capture=ms["first_captured_on"]
        else:
            raise DiscourseError("relation target must be claim or dated product event")
        possible=bool(event_date<=as_of and right_date<=as_of and
                      sources[left["source_id"]]["published_on"]<=as_of)
        originally_known=possible and sources[left["source_id"]]["first_captured_on"]<=as_of and source_capture<=as_of
        results.append({
            "relation_id":lid,
            "left_claim_id":l["left_claim_id"],
            "left_published_on":event_date,
            "right_kind":l["right_kind"],"right_id":l["right_id"],
            "right_occurred_or_published_on":right_date,
            "relation_kind":l["relation_kind"],
            "interpretation_candidate":l["interpretation"],
            "asof_date_eligible_retrospective":possible,
            "admissible_as_original_historical_forecast_knowledge":originally_known,
            "causal_influence_identified":False,
            "actual_reversibility_observed":False,
            "private_intention_inferred":False,
            "factual_contradiction_proved":False,
            "research_note":l["research_note"],
            "next_review_gate":l["review_gate"],
        })
    return {
        "schema":"fsl/discourse-history-reconciliation/0.10",
        "as_of":as_of,"reviewed_on":recorded,
        "relations":results,
        "temporally_eligible_links":sum(x["asof_date_eligible_retrospective"] for x in results),
        "causal_links_verified":0,
        "actual_strategy_reversals_verified":0,
        "warning":"Public utterance may affect technology and technology may affect utterances; neither arrow is identified from ordering alone.",
    }
