"""KIF v0.22: registered, read-only evidence replay. Apache-2.0."""
from collections import defaultdict
from urllib.parse import urlsplit
import re

from .constants import (CHECKS, MINIMUM, BUDGET, STAGES, TIERS, COMPUTABLE, SCHEMA)
from .common import (ROOT, KIFError, load_json, require, exact, choice, ident, sha,
                     integer, boolean, nonempty, timestamp, index_rows)
from .models import (TRIAL, validate_trial, validate_flow, validate_population,
                     assess_trial, arm_summary, paired, flow_summary, population_summary)

CATALOG_PATH = ROOT/"data/kif_indicator_catalog_v0.22.json"
GICCF_PATH = ROOT/"data/giccf_capability_catalog_v0.13.json"
TOP = "schema_version catalog_version study_id data_class registered_at registration_sha256 window_start window_end comparison_mode currency compute_meter_sha256 arms cases flow_frames population_frames events".split()
ARM = "arm_id actor stack_sha256 tool_policy_sha256 budget".split()
CASE = "case_id domain_id task_kind novelty source_artifact_sha256 contract_sha256 reference_corpus_sha256 heldout_commitment_sha256 expected_disposition risk blind_review_required required_checks".split()
FLOW_FRAME = "frame_id domain_id unit_contract_sha256 queue_model serial_model".split()
POP_FRAME = "frame_id domain_id population_contract_sha256 voluntary_survey_scale_sha256 aggregation_consent_receipt_sha256 score_max min_public_cell".split()
EVENT = "event_id target_id event_occurred_at source_published_at fsl_recorded_at evidence_tier source_url artifact_sha256 assessor_ref supersedes_event_id kind data".split()


def load_catalog(path=CATALOG_PATH):
    c=load_json(path)
    require(c.get("catalog_id")=="KIF" and c.get("version")=="0.22.0","catalog version")
    ids=CHECKS[:6]+[f"KIF-{i:02d}" for i in range(1,9)]
    axes=c.get("axes")
    require(isinstance(axes,list) and [a.get("id") for a in axes]==ids,"catalog axis IDs")
    for a in axes:
        require("value" in a and a["value"] is None and a.get("status")=="not_measured",
                "catalog must be unmeasured")
        for k in ("label_zh","definition","source"):
            nonempty(a.get(k),k)
    require(c.get("task_minimum_checks")==MINIMUM and c.get("quality_checks")==CHECKS
            and c.get("knowledge_flow_stages")==STAGES,"catalog contract mismatch")
    return c


def validate(payload):
    exact(payload,TOP,"study")
    require(payload["schema_version"]==SCHEMA and payload["catalog_version"]=="0.22.0","version")
    ident(payload["study_id"],"study_id")
    choice(payload["data_class"],{"synthetic","observational"},"data_class")
    choice(payload["comparison_mode"],{"equal_budget","actual_cost"},"comparison_mode")
    require(isinstance(payload["currency"],str) and re.fullmatch(r"[A-Z]{3}",payload["currency"]),"currency")
    for k in ("registration_sha256","compute_meter_sha256"):
        sha(payload[k],k)
    reg,start,end=[timestamp(payload[k]) for k in ("registered_at","window_start","window_end")]
    require(reg<=start<end,"registration must precede observation window")
    arms=index_rows(payload["arms"],ARM,"arm_id","arm")
    cases=index_rows(payload["cases"],CASE,"case_id","case")
    flows=index_rows(payload["flow_frames"],FLOW_FRAME,"frame_id","flow frame")
    populations=index_rows(payload["population_frames"],POP_FRAME,"frame_id","population frame")
    require(bool(arms)==bool(cases) and (cases or flows or populations),"empty or incomplete study frame")
    require(not (set(cases)&set(flows) or set(cases)&set(populations) or set(flows)&set(populations)),
            "target ID collision")
    for a in arms.values():
        choice(a["actor"],{"human_non_ai","ai_system","human_ai"},"actor")
        for k in ("stack_sha256","tool_policy_sha256"):
            sha(a[k],k)
        exact(a["budget"],BUDGET,"budget")
        for k,v in a["budget"].items():
            integer(v,k)
        require(a["budget"]["wall_seconds"]>0,"positive wall budget required")
    if arms and payload["comparison_mode"]=="equal_budget":
        first=next(iter(arms.values()))["budget"]
        require(all(a["budget"]==first for a in arms.values()),"equal-budget arms must have identical caps")
    domains={d["id"] for d in load_json(GICCF_PATH)["civilization_domains"]}
    for f in [*cases.values(),*flows.values(),*populations.values()]:
        choice(f["domain_id"],domains,"GICCF domain")
    for c in cases.values():
        choice(c["task_kind"],MINIMUM,"task kind")
        choice(c["novelty"],{"seen","held_out","shifted_domain","novel_real_world"},"novelty")
        choice(c["expected_disposition"],{"answer","abstain","escalate"},"expected disposition")
        choice(c["risk"],{"low","moderate","high","critical"},"risk")
        boolean(c["blind_review_required"],"blind review")
        for k in ("source_artifact_sha256","contract_sha256","reference_corpus_sha256"):
            sha(c[k],k)
        sha(c["heldout_commitment_sha256"],"holdout commitment",nullable=c["novelty"]=="seen")
        rs=c["required_checks"]
        require(isinstance(rs,list) and all(isinstance(x,str) and x in CHECKS for x in rs)
                and len(set(rs))==len(rs) and bool(rs),"required checks")
        if c["expected_disposition"]=="answer":
            require(set(MINIMUM[c["task_kind"]])<=set(rs),"required substantive task checks missing")
        else:
            require({"O3","O6"}<=set(rs),"abstention/escalation requires scope and traceability")
        if c["risk"] in {"high","critical"}:
            require({"safety","authorization"}<=set(rs),"high-risk safety/authorization gates")
    for f in flows.values():
        sha(f["unit_contract_sha256"],"flow unit contract")
        choice(f["queue_model"],{"accounting_only","work_conserving_homogeneous"},"queue model")
        choice(f["serial_model"],{"not_assumed","serial_same_unit"},"serial model")
    for f in populations.values():
        for k in ("population_contract_sha256","voluntary_survey_scale_sha256","aggregation_consent_receipt_sha256"):
            sha(f[k],k)
        integer(f["score_max"],"score maximum",minimum=1)
        integer(f["min_public_cell"],"minimum public cell",minimum=10)
    require(isinstance(payload["events"],list),"events must be array")
    events,latest,by_id=[],{},{}
    for e in payload["events"]:
        exact(e,EVENT,"event")
        ident(e["event_id"],"event_id")
        ident(e["target_id"],"target_id")
        ident(e["supersedes_event_id"],"supersedes",nullable=True)
        eid,target,kind,tier=(e[k] for k in ("event_id","target_id","kind","evidence_tier"))
        require(eid not in by_id,"duplicate event ID")
        choice(kind,{"trial","flow","population"},"event kind")
        choice(tier,TIERS,"tier")
        dc=payload["data_class"]
        require((dc=="synthetic")==(tier=="synthetic_fixture"),"synthetic/observational mixing")
        sha(e["artifact_sha256"],"event artifact",nullable=True)
        nonempty(e["source_url"],"source URL",nullable=True)
        nonempty(e["assessor_ref"],"assessor reference",nullable=True)
        if dc=="synthetic":
            require(e["source_url"] is None and e["assessor_ref"] is None,
                    "synthetic cannot pose as external evidence")
        elif tier!="unobserved":
            try:
                u=urlsplit(e["source_url"] or "")
                require(u.scheme=="https" and bool(u.hostname) and u.username is None and u.password is None,
                        "HTTPS evidence URL required")
            except ValueError as exc:
                raise KIFError("invalid source URL") from exc
            if tier in COMPUTABLE:
                sha(e["artifact_sha256"],"computable assertion artifact")
            if tier in {"independent_repeated","longitudinal_independent"}:
                nonempty(e["assessor_ref"],"claimed independent assessor")
        occurred,published,recorded=[timestamp(e[k]) for k in
                                      ("event_occurred_at","source_published_at","fsl_recorded_at")]
        require(end<=occurred<=published<=recorded,"event chronology or incomplete observation window")
        d=e["data"]
        if kind=="trial":
            require(target in cases,"unknown trial target")
            exact(d,TRIAL,"trial")
            ident(d["arm_id"],"arm_id")
            require(d["arm_id"] in arms and d["case_id"]==target,"trial arm/case mismatch")
            validate_trial(d,cases[target])
            key=(kind,target,d["arm_id"])
        elif kind=="flow":
            require(target in flows,"unknown flow target")
            validate_flow(d,flows[target])
            key=(kind,target)
        else:
            require(target in populations,"unknown population target")
            validate_population(d,populations[target],dc)
            key=(kind,target)
        old=latest.get(key)
        require(e["supersedes_event_id"]==old,"duplicate active assertion or invalid correction target")
        if old is not None:
            p=by_id[old]
            require(recorded>p[2] and published>=p[1] and occurred>=p[0],"correction chronology")
        by_id[eid]=(occurred,published,recorded)
        latest[key]=eid
        events.append((key,e,occurred,published,recorded))
    return arms,cases,flows,populations,events,reg


def audit(payload,*,as_of,mode="strict_known_at_time"):
    choice(mode,{"strict_known_at_time","retrospective_reconstruction"},"replay mode")
    catalog=load_catalog()
    arms,cases,flows,populations,events,reg=validate(payload)
    cutoff=timestamp(as_of,cutoff=True)
    active={}
    visible_count=0
    if reg<=cutoff:
        for key,e,occurred,published,recorded in events:
            if occurred<=cutoff and published<=cutoff and (mode=="retrospective_reconstruction" or recorded<=cutoff):
                active[key]=e
                visible_count+=1
    rows=[assess_trial(c,arms[a],active.get(("trial",cid,a)))
          for cid,c in sorted(cases.items()) for a in sorted(arms)] if reg<=cutoff else []
    summaries={a:arm_summary([r for r in rows if r["arm_id"]==a])
               for a in sorted(arms)} if rows else {}
    grouped=defaultdict(list)
    for r in rows:
        grouped[(r["arm_id"],r["domain_id"],r["task_kind"],r["novelty"])].append(r)
    strata=[{"arm_id":a,"domain_id":d,"task_kind":k,"novelty":n,"summary":arm_summary(v)}
            for (a,d,k,n),v in sorted(grouped.items())]
    result={"trial_rows":rows,"arm_summaries":summaries,"strata":strata,
            "paired_outcomes":paired(rows,arms) if rows else [],
            "knowledge_flow_frames":[flow_summary(f,active.get(("flow",fid)))
                for fid,f in sorted(flows.items())] if reg<=cutoff else [],
            "population_frames":[population_summary(f,active.get(("population",fid)))
                for fid,f in sorted(populations.items())] if reg<=cutoff else []}
    syn=payload["data_class"]=="synthetic"
    return {"schema_version":SCHEMA,"catalog_axis_count":len(catalog["axes"]),
            "study_id":payload["study_id"],"comparison_mode":payload["comparison_mode"],
            "currency_minor_units":payload["currency"],"data_class":payload["data_class"],
            "as_of_utc":cutoff.isoformat(),"mode":mode,"visible_event_count":visible_count,
            "active_event_count":len(active),"synthetic_scenario":result if syn else None,
            "recorded_observational_assertions":None if syn else result,
            "independent_empirical_certification":False,"global_novelty_certified":False,
            "causal_effect_certified":False,"universal_intelligence_score":None,
            "human_replacement_rate":None,"neural_mechanism_certified":False}
