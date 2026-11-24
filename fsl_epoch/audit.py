"""HCAO v0.23: typed evidence and conditional model replay. Apache-2.0."""
from urllib.parse import urlsplit
import re

from .common import (ROOT, HCAOError, load_json, require, exact, choice, ident, sha,
                     integer, nonempty, timestamp, index_rows)
from .topology import topology, LAYERS
from .coupling import coupling
from .absorption import absorption

SCHEMA="fsl/hcao/0.23"
CATALOG_PATH=ROOT/"data/hcao_indicator_catalog_v0.23.json"
GICCF_PATH=ROOT/"data/giccf_capability_catalog_v0.13.json"
TIERS={"unobserved","provider_claim","provider_demo","repeatable_test",
       "independent_repeated","longitudinal_independent","synthetic_fixture"}
COMPUTABLE={"repeatable_test","independent_repeated","longitudinal_independent","synthetic_fixture"}
KINDS={"topology","coupling","absorption"}
TOP="schema_version catalog_version study_id data_class registered_at registration_sha256 window_start window_end frames events".split()
FRAME="frame_id kind context_id domain_ids contract_sha256 unit_contract_sha256 model_assumptions_sha256 currency min_public_cell".split()
EVENT="event_id frame_id kind event_occurred_at source_published_at fsl_recorded_at evidence_tier source_url artifact_sha256 assessor_ref supersedes_event_id data".split()


def load_catalog(path=CATALOG_PATH):
    c=load_json(path)
    require(c.get("catalog_id")=="HCAO" and c.get("version")=="0.23.0","catalog version")
    ids=[f"SET{i:02d}" for i in range(1,13)]+[f"CFA-{i:02d}" for i in range(1,13)]+[f"C{i:02d}" for i in range(1,13)]
    axes=c.get("axes")
    require(isinstance(axes,list) and [a.get("id") for a in axes]==ids,"catalog IDs")
    require(c.get("layers")==LAYERS,"eight-layer identity")
    for a in axes:
        require("value" in a and a["value"] is None and a.get("status")=="not_measured",
                "catalog is definitions only")
        for k in ("label_zh","source","implementation"):
            nonempty(a.get(k),k)
    return c


def guard_coverage(c,frame):
    if c is None:
        return
    # Basic same-frame public aggregate disclosure guard, not a privacy guarantee.
    n,a,b,h=(c[k] for k in ("population","left_count","right_count","joint_count"))
    vals=[n,a,b,h]
    if None not in (n,a,b,h):
        vals.extend([a-h,b-h,n-a-b+h])
    else:
        for x in (a,b):
            if n is not None and x is not None:
                vals.append(n-x)
            if x is not None and h is not None:
                vals.append(x-h)
    require(all(x is None or x==0 or x>=frame["min_public_cell"] for x in vals),
            "small coverage cell or complement must be suppressed")


def run_model(data,frame,dc,start,end):
    kind=frame["kind"]
    if kind=="topology":
        result=topology(data,frame)
        if dc=="observational":
            guard_coverage(data["joint_coverage"],frame)
        return result
    if kind=="coupling":
        return coupling(data,frame,start,end,dc)
    return absorption(data,frame,dc)


def validate(payload):
    exact(payload,TOP,"study")
    require(payload["schema_version"]==SCHEMA and payload["catalog_version"]=="0.23.0","version")
    ident(payload["study_id"],"study")
    dc=payload["data_class"]
    choice(dc,{"synthetic","observational"},"data class")
    sha(payload["registration_sha256"],"registration receipt")
    reg,start,end=[timestamp(payload[k]) for k in ("registered_at","window_start","window_end")]
    require(reg<=start<end,"registration must precede observation window")
    domains={d["id"] for d in load_json(GICCF_PATH)["civilization_domains"]}
    frames=index_rows(payload["frames"],FRAME,"frame_id","frame")
    require(0<len(frames)<=128,"frame count 1..128")
    for f in frames.values():
        choice(f["kind"],KINDS,"frame kind")
        ident(f["context_id"],"context")
        ds=f["domain_ids"]
        require(isinstance(ds,list) and bool(ds) and
                all(isinstance(d,str) and d in domains for d in ds) and len(set(ds))==len(ds),
                "valid unique GICCF domain references")
        if f["kind"]=="coupling":
            require(len(ds)==2,"coupling frame must register exactly two domains")
        for k in ("contract_sha256","unit_contract_sha256","model_assumptions_sha256"):
            sha(f[k],k)
        require(isinstance(f["currency"],str) and re.fullmatch(r"[A-Z]{3}",f["currency"]),"currency")
        integer(f["min_public_cell"],"minimum public cell",minimum=10)
    require(isinstance(payload["events"],list) and len(payload["events"])<=1024,"events array <=1024")
    events,latest,by_id=[],{},{}
    for e in payload["events"]:
        exact(e,EVENT,"event")
        eid,fid,kind,tier=(e[k] for k in ("event_id","frame_id","kind","evidence_tier"))
        ident(eid,"event");ident(fid,"frame")
        ident(e["supersedes_event_id"],"supersedes",nullable=True)
        require(eid not in by_id and fid in frames,"duplicate event or unknown frame")
        choice(kind,KINDS,"event kind")
        require(kind==frames[fid]["kind"],"frame kind mismatch")
        choice(tier,TIERS,"tier")
        require((dc=="synthetic")==(tier=="synthetic_fixture"),"synthetic/observational mixing")
        sha(e["artifact_sha256"],"artifact",nullable=True)
        nonempty(e["source_url"],"source",nullable=True)
        nonempty(e["assessor_ref"],"assessor",nullable=True)
        if dc=="synthetic":
            require(e["source_url"] is None and e["assessor_ref"] is None,"synthetic external source/assessor forbidden")
        elif tier!="unobserved":
            try:
                u=urlsplit(e["source_url"] or "")
                require(u.scheme=="https" and bool(u.hostname) and u.username is None and u.password is None,
                        "HTTPS source URL without credentials required")
            except ValueError as exc:
                raise HCAOError("invalid source URL") from exc
            if tier in COMPUTABLE:
                sha(e["artifact_sha256"],"computable assertion artifact")
            if tier in {"independent_repeated","longitudinal_independent"}:
                nonempty(e["assessor_ref"],"claimed independent assessor")
        happened,published,recorded=[timestamp(e[k]) for k in
            ("event_occurred_at","source_published_at","fsl_recorded_at")]
        require(end<=happened<=published<=recorded,"event chronology or incomplete observation window")
        old=latest.get(fid)
        require(e["supersedes_event_id"]==old,"duplicate active event or invalid correction target")
        if old is not None:
            p=by_id[old]
            require(recorded>p[2] and published>=p[1] and happened>=p[0],"correction chronology")
        # Validate the complete snapshot even if later suppressed by time/evidence gates.
        result=run_model(e["data"],frames[fid],dc,start,end)
        by_id[eid]=(happened,published,recorded)
        latest[fid]=eid
        events.append((fid,e,happened,published,recorded,result))
    return frames,events,reg


def audit(payload,*,as_of,mode="strict_known_at_time"):
    choice(mode,{"strict_known_at_time","retrospective_reconstruction"},"mode")
    cat=load_catalog()
    frames,events,reg=validate(payload)
    cutoff=timestamp(as_of,cutoff=True)
    active={}
    seen=0
    if reg<=cutoff:
        for fid,e,h,p,r,result in events:
            if h<=cutoff and p<=cutoff and (mode=="retrospective_reconstruction" or r<=cutoff):
                active[fid]=(e,result)
                seen+=1
    rows=[]
    if reg<=cutoff:
        for fid,f in sorted(frames.items()):
            item=active.get(fid)
            e,result=item if item else (None,None)
            receipt=None if e is None else {k:e[k] for k in ("event_id","evidence_tier","source_url",
                "artifact_sha256","assessor_ref","event_occurred_at","source_published_at","fsl_recorded_at")}
            eligible=e is not None and e["evidence_tier"] in COMPUTABLE
            rows.append({"frame":f,"receipt":receipt,"conditional_result":result if eligible else None,
                         "status":"conditional_from_recorded_inputs" if eligible else "unmeasured"})
    result={"frames":rows,"not_observed_or_not_eligible":sum(x["conditional_result"] is None for x in rows)}
    synthetic=payload["data_class"]=="synthetic"
    return {"schema_version":SCHEMA,"catalog_axis_count":len(cat["axes"]),"study_id":payload["study_id"],
            "data_class":payload["data_class"],"as_of_utc":cutoff.isoformat(),"mode":mode,
            "visible_event_count":seen,"active_event_count":len(active),
            "synthetic_scenario":result if synthetic else None,
            "recorded_observational_assertions":None if synthetic else result,
            "independent_empirical_certification":False,"causal_acceleration_certified":False,
            "global_epoch_rank":None,"global_replacement_rate":None,
            "systemic_singularity_certified":False,"civilizational_singularity_certified":False}
