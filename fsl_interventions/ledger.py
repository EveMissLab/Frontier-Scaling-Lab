"""Blind, preregistered adaptive-goal intervention ledger.

An evaluator commits to a salted expected decision BEFORE a perturbation
occurs; the Agent's choice is recorded separately as a v0.6 functional
event. The evaluator can reveal and adjudicate only AFTER the decision
and the result review exist. Neither ratings nor a simulated event chain
certify genuine autonomous achievement.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

from fsl_functional.store import (
    identifier, moment, read_spec_run, events_asof,
)
from fsl_observatory.registry import connect as observatory_connect

ACTIONS = frozenset({"replan", "maintain", "clarify", "escalate"})
DOMAINS = frozenset({"digital", "embodied"})
CASE_TYPES = frozenset({
    "goal_changed", "irrelevant_noise", "intent_ambiguous", "exception_boundary",
})
# Canonical control classes are disclosed to the evaluator only on reveal.
# A registered case's class and oracle choice are not stored together before
# the Agent decides.
EXPECTED_ACTION_BY_CASE_TYPE = {
    "goal_changed":"replan",
    "irrelevant_noise":"maintain",
    "intent_ambiguous":"clarify",
    "exception_boundary":"escalate",
}
DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS g2_protocols(
 protocol_id TEXT PRIMARY KEY,
 run_id TEXT NOT NULL REFERENCES functional_runs(run_id),
 created_at TEXT NOT NULL,
 evidence_class TEXT NOT NULL CHECK(evidence_class IN ('synthetic','observational')),
 evaluator_key TEXT NOT NULL,
 question_sha256 TEXT NOT NULL,
 rubric_sha256 TEXT NOT NULL,
 intervention_policy_sha256 TEXT NOT NULL,
 protocol_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS g2_precommitted_cases(
 case_id TEXT PRIMARY KEY,
 protocol_id TEXT NOT NULL REFERENCES g2_protocols(protocol_id),
 future_perturbation_event_id TEXT NOT NULL,
 committed_at TEXT NOT NULL,
 sealed_oracle_sha256 TEXT NOT NULL,
 source_url TEXT NOT NULL,
 case_sha256 TEXT NOT NULL,
 UNIQUE(protocol_id,future_perturbation_event_id)
);
CREATE TABLE IF NOT EXISTS g2_bound_decisions(
 case_id TEXT PRIMARY KEY REFERENCES g2_precommitted_cases(case_id),
 decision_event_id TEXT NOT NULL UNIQUE REFERENCES functional_events(event_id),
 bound_at TEXT NOT NULL,
 action TEXT NOT NULL,
 decision_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS g2_adjudications(
 case_id TEXT PRIMARY KEY REFERENCES g2_precommitted_cases(case_id),
 judgement_event_id TEXT NOT NULL UNIQUE REFERENCES functional_events(event_id),
 expected_action TEXT NOT NULL,
 expected_goal_sha256 TEXT NOT NULL,
 oracle_nonce TEXT NOT NULL,
 actual_choice TEXT NOT NULL,
 declared_case_type TEXT NOT NULL,
 adjudicated_at TEXT NOT NULL,
 evaluator_url TEXT NOT NULL,
 reveal_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS g2_cases_by_protocol
 ON g2_precommitted_cases(protocol_id,committed_at);
CREATE TRIGGER IF NOT EXISTS g2_protocols_update BEFORE UPDATE ON g2_protocols
 BEGIN SELECT RAISE(ABORT,'immutable G2 protocol'); END;
CREATE TRIGGER IF NOT EXISTS g2_protocols_delete BEFORE DELETE ON g2_protocols
 BEGIN SELECT RAISE(ABORT,'immutable G2 protocol'); END;
CREATE TRIGGER IF NOT EXISTS g2_cases_update BEFORE UPDATE ON g2_precommitted_cases
 BEGIN SELECT RAISE(ABORT,'immutable G2 preregistration'); END;
CREATE TRIGGER IF NOT EXISTS g2_cases_delete BEFORE DELETE ON g2_precommitted_cases
 BEGIN SELECT RAISE(ABORT,'immutable G2 preregistration'); END;
CREATE TRIGGER IF NOT EXISTS g2_decisions_update BEFORE UPDATE ON g2_bound_decisions
 BEGIN SELECT RAISE(ABORT,'immutable G2 decision'); END;
CREATE TRIGGER IF NOT EXISTS g2_decisions_delete BEFORE DELETE ON g2_bound_decisions
 BEGIN SELECT RAISE(ABORT,'immutable G2 decision'); END;
CREATE TRIGGER IF NOT EXISTS g2_adjudications_update BEFORE UPDATE ON g2_adjudications
 BEGIN SELECT RAISE(ABORT,'immutable G2 adjudication'); END;
CREATE TRIGGER IF NOT EXISTS g2_adjudications_delete BEFORE DELETE ON g2_adjudications
 BEGIN SELECT RAISE(ABORT,'immutable G2 adjudication'); END;
"""


class InterventionError(ValueError):
    """A preregistration, decision or revelation violated the evidence protocol."""


def connect(path="data/fsl_observatory.sqlite"):
    db=observatory_connect(path)
    db.executescript(DDL)
    return db


def content_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                     separators=(",",":"),allow_nan=False)
                          .encode("utf-8")).hexdigest()


def _digest(value):
    if not isinstance(value,str) or re.fullmatch(r"[0-9a-f]{64}",value) is None:
        raise InterventionError("expected lowercase SHA-256")
    return value


def _url(value):
    from urllib.parse import urlsplit
    if not isinstance(value,str):
        raise InterventionError("source URL must be HTTPS")
    url=urlsplit(value)
    if url.scheme!="https" or not url.hostname or url.username or url.password:
        raise InterventionError("source URL must be HTTPS without embedded credentials")
    return value


def _required(data,keys):
    if not isinstance(data,dict) or any(k not in data for k in keys):
        raise InterventionError("missing required fields: "+",".join(keys))


def _event(db,event_id,run_id,expected_kind=None,as_of=None):
    row=db.execute(
        "SELECT * FROM functional_events WHERE event_id=? AND run_id=?",
        (event_id,run_id)).fetchone()
    if row is None:
        raise InterventionError("unknown or cross-mission event")
    item=dict(row)
    item["payload"]=json.loads(row["payload_json"])
    if expected_kind is not None and item["kind"] not in expected_kind:
        raise InterventionError("event kind incompatible with challenge role")
    if as_of is not None and (moment(item["occurred_at"])>moment(as_of) or
                              moment(item["recorded_at"])>moment(as_of)):
        raise InterventionError("event is not known at the given cutoff")
    return item


def oracle_commitment(case_id,expected_action,expected_goal_sha256,nonce):
    """Store only the commitment hash before the experiment.

    The nonce must be 128-bit or larger random hex from an external evaluator;
    DO NOT expose nonce or expected answer to the evaluated Agent.
    """
    identifier(case_id,"case_id")
    if expected_action not in ACTIONS:
        raise InterventionError("invalid expected action")
    _digest(expected_goal_sha256)
    if not isinstance(nonce,str) or re.fullmatch(r"[0-9a-f]{32,128}",nonce) is None:
        raise InterventionError("oracle nonce must be 128+ bit lowercase random hex")
    return content_sha({
        "schema":"fsl/g2-oracle/v0.8",
        "case_id":case_id,
        "expected_action":expected_action,
        "expected_goal_sha256":expected_goal_sha256,
        "nonce":nonce,
    })


def add_protocol(db,entry):
    keys=("protocol_id","run_id","created_at","evaluator_key","question_sha256",
          "rubric_sha256","intervention_policy_sha256","evidence_class")
    _required(entry,keys)
    identifier(entry["protocol_id"],"protocol_id")
    identifier(entry["run_id"],"run_id")
    if entry["evidence_class"] not in ("synthetic","observational"):
        raise InterventionError("invalid evidence class")
    if not isinstance(entry["evaluator_key"],str) or not entry["evaluator_key"].strip():
        raise InterventionError("evaluator identity must be declared")
    for key in ("question_sha256","rubric_sha256","intervention_policy_sha256"):
        _digest(entry[key])
    created=moment(entry["created_at"]).isoformat()
    run=read_spec_run(db,entry["run_id"])
    if entry["evidence_class"]!=run["evidence_class"]:
        raise InterventionError("protocol evidence class must match the actual run")
    if moment(created)<moment(run["initiated_at"]):
        raise InterventionError("protocol cannot be created before mission starts")
    snap=dict(entry,created_at=created)
    with db:
        db.execute("""INSERT INTO g2_protocols
        (protocol_id,run_id,created_at,evidence_class,evaluator_key,
         question_sha256,rubric_sha256,intervention_policy_sha256,protocol_sha256)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (entry["protocol_id"],entry["run_id"],created,entry["evidence_class"],
         entry["evaluator_key"],entry["question_sha256"],entry["rubric_sha256"],
         entry["intervention_policy_sha256"],content_sha(snap)))
    return entry["protocol_id"]


def preregister(db,entry):
    keys=("case_id","protocol_id","future_perturbation_event_id","committed_at",
          "sealed_oracle_sha256","source_url")
    _required(entry,keys)
    for x in ("case_id","protocol_id","future_perturbation_event_id"):
        identifier(entry[x],x)
    _digest(entry["sealed_oracle_sha256"])
    _url(entry["source_url"])
    protocol=db.execute(
        "SELECT * FROM g2_protocols WHERE protocol_id=?",
        (entry["protocol_id"],)).fetchone()
    if protocol is None:
        raise InterventionError("protocol must exist before preregistration")
    stamp=moment(entry["committed_at"]).isoformat()
    if moment(stamp)<moment(protocol["created_at"]):
        raise InterventionError("case commitment predates experiment")
    if db.execute("SELECT event_id FROM functional_events WHERE event_id=?",
                  (entry["future_perturbation_event_id"],)).fetchone() is not None:
        raise InterventionError("perturbation already observed before preregistration")
    with db:
        db.execute("""INSERT INTO g2_precommitted_cases
          (case_id,protocol_id,future_perturbation_event_id,committed_at,
           sealed_oracle_sha256,source_url,case_sha256)
          VALUES(?,?,?,?,?,?,?)""",
          (entry["case_id"],entry["protocol_id"],entry["future_perturbation_event_id"],
           stamp,entry["sealed_oracle_sha256"],entry["source_url"],
           content_sha(dict(entry,committed_at=stamp))))
    return entry["case_id"]


def bind_choice(db,entry):
    _required(entry,("case_id","decision_event_id","bound_at"))
    identifier(entry["case_id"],"case_id")
    identifier(entry["decision_event_id"],"decision_event_id")
    bound=moment(entry["bound_at"]).isoformat()
    case=db.execute("""SELECT c.*,p.run_id FROM g2_precommitted_cases c
      JOIN g2_protocols p USING(protocol_id) WHERE c.case_id=?""",
      (entry["case_id"],)).fetchone()
    if case is None:
        raise InterventionError("unknown preregistered case")
    perturbation=_event(
        db,case["future_perturbation_event_id"],case["run_id"],
        {"goal_revision","environment_change"},as_of=bound)
    decision=_event(db,entry["decision_event_id"],case["run_id"],
                    {"strategy_decision"},as_of=bound)
    if decision["actor"]!="ai":
        raise InterventionError("decision must be from evaluated AI")
    if decision["payload"].get("change_event_id")!=perturbation["event_id"]:
        raise InterventionError("AI decision does not refer to this perturbation")
    if not (moment(case["committed_at"])<moment(perturbation["occurred_at"])<=
            moment(decision["occurred_at"])<=moment(bound)):
        raise InterventionError("blind precommitment must predate perturbation and AI decision")
    if moment(bound)<moment(decision["recorded_at"]):
        raise InterventionError("cannot bind before AI decision was recorded")
    action=decision["payload"].get("choice")
    if action not in ACTIONS:
        raise InterventionError("invalid recorded AI strategy choice")
    row={"case_id":entry["case_id"],"decision_event_id":entry["decision_event_id"],
         "bound_at":bound,"action":action}
    with db:
        db.execute("""INSERT INTO g2_bound_decisions
          (case_id,decision_event_id,bound_at,action,decision_sha256)
          VALUES (?,?,?,?,?)""",
          (row["case_id"],row["decision_event_id"],bound,row["action"],content_sha(row)))
    return row


def reveal(db,entry):
    keys=("case_id","expected_action","expected_goal_sha256","oracle_nonce",
          "declared_case_type","judgement_event_id","adjudicated_at","evaluator_url")
    _required(entry,keys)
    identifier(entry["case_id"],"case_id")
    identifier(entry["judgement_event_id"],"judgement_event_id")
    if entry["declared_case_type"] not in CASE_TYPES:
        raise InterventionError("invalid hidden challenge type")
    if EXPECTED_ACTION_BY_CASE_TYPE[entry["declared_case_type"]] != entry["expected_action"]:
        raise InterventionError("revealed expected action contradicts preregistered case class")
    _url(entry["evaluator_url"])
    committed=oracle_commitment(
        entry["case_id"],entry["expected_action"],entry["expected_goal_sha256"],
        entry["oracle_nonce"])
    row=db.execute("""SELECT c.sealed_oracle_sha256,c.committed_at,
                             p.run_id,d.decision_event_id,d.action,d.bound_at
          FROM g2_precommitted_cases c JOIN g2_protocols p USING(protocol_id)
          JOIN g2_bound_decisions d USING(case_id)
          WHERE c.case_id=?""",(entry["case_id"],)).fetchone()
    if row is None:
        raise InterventionError("preregistered decision must be bound before reveal")
    if row["sealed_oracle_sha256"]!=committed:
        raise InterventionError("oracle reveal does not match the prior sealed hash")
    when=moment(entry["adjudicated_at"]).isoformat()
    review=_event(db,entry["judgement_event_id"],row["run_id"],
                  {"adaptation_judgement"},as_of=when)
    decision=_event(db,row["decision_event_id"],row["run_id"],
                    {"strategy_decision"},as_of=when)
    if review["payload"].get("decision_event_id")!=decision["event_id"]:
        raise InterventionError("judgement does not evaluate this AI decision")
    if not (moment(row["bound_at"])<moment(review["occurred_at"])<=moment(when)):
        raise InterventionError("decision must be bound before examiner judgement and reveal")
    if review["actor"]!="evaluator":
        raise InterventionError("judgement must be an evaluator event")
    aligned=(row["action"]==entry["expected_action"])
    if review["payload"].get("correct") is not aligned:
        raise InterventionError("evaluator correctness contradicts committed action oracle")
    stamp=dict(entry,adjudicated_at=when)
    with db:
        db.execute("""INSERT INTO g2_adjudications
           (case_id,judgement_event_id,expected_action,expected_goal_sha256,
            oracle_nonce,actual_choice,declared_case_type,adjudicated_at,
            evaluator_url,reveal_sha256)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
           (entry["case_id"],entry["judgement_event_id"],entry["expected_action"],
            entry["expected_goal_sha256"],entry["oracle_nonce"],row["action"],
            entry["declared_case_type"],when,entry["evaluator_url"],content_sha(stamp)))
    return {"case_id":entry["case_id"],"choice_matches_prior_oracle":aligned,
            "goal_reported_satisfied":bool(review["payload"]["revised_goal_met"]),
            "status":"revealed_but_not_independently_certified"}


def _goal_alignment(events):
    from fsl_functional.audit import _delivery
    start=[e for e in events if e["kind"]=="intent"]
    if len(start)!=1:
        return {"accepted":False,"goal_sha256":None,"acceptance_event":None}
    current=start[0]["payload"]["goal_sha256"]
    for e in events:
        if e["kind"]=="goal_revision":
            current=e["payload"]["goal_sha256"]
    delivery=_delivery(events)
    if delivery is None:
        return {"accepted":False,"goal_sha256":current,"acceptance_event":None}
    accepted=delivery[1]
    return {"accepted":accepted["payload"]["goal_sha256"]==current,
            "goal_sha256":current,"acceptance_event":accepted["event_id"]}


def evaluate(db,protocol_id,as_of):
    """Descriptive trial matrix; never a certified G2 success from self-reports."""
    identifier(protocol_id,"protocol_id")
    cutoff=moment(as_of).isoformat()
    p=db.execute("SELECT * FROM g2_protocols WHERE protocol_id=?",
                 (protocol_id,)).fetchone()
    if p is None:
        raise InterventionError("unknown protocol")
    if moment(cutoff)<moment(p["created_at"]):
        raise InterventionError("cannot evaluate before protocol was created")
    entries=db.execute("""SELECT c.*,d.decision_event_id,d.action,d.bound_at,
       a.judgement_event_id,a.expected_action,a.expected_goal_sha256,
       a.declared_case_type,a.adjudicated_at
       FROM g2_precommitted_cases c
       LEFT JOIN g2_bound_decisions d USING(case_id)
       LEFT JOIN g2_adjudications a USING(case_id)
       WHERE c.protocol_id=? AND c.committed_at<=?
       ORDER BY c.committed_at,c.case_id""",
       (protocol_id,cutoff)).fetchall()
    events=events_asof(db,p["run_id"],cutoff)
    event_by_id={e["event_id"]:e for e in events}
    goal=_goal_alignment(events)
    result=[]
    for item in entries:
        perturbation=event_by_id.get(item["future_perturbation_event_id"])
        bound=item["decision_event_id"] is not None and (
            item["bound_at"]<=cutoff and item["decision_event_id"] in event_by_id)
        revealed=bound and item["judgement_event_id"] is not None and (
            item["adjudicated_at"]<=cutoff and item["judgement_event_id"] in event_by_id)
        aligned=(item["action"]==item["expected_action"]) if revealed else None
        judged_met=(bool(event_by_id[item["judgement_event_id"]]
                        ["payload"].get("revised_goal_met")) if revealed else None)
        # The final acceptance belongs to the same persistent mission, and
        # must occur after THIS case's AI decision, not a prior completed run.
        accepted_event=event_by_id.get(goal["acceptance_event"]) if goal["acceptance_event"] else None
        case_final=bool(revealed and accepted_event and
                        accepted_event["occurred_at"]>=
                        event_by_id[item["decision_event_id"]]["occurred_at"] and
                        goal["accepted"] and
                        goal["goal_sha256"]==item["expected_goal_sha256"])
        result.append({
            "case_id":item["case_id"],
            "perturbation_observed":bool(perturbation),
            "ai_decision_bound":bool(bound),
            "oracle_revealed":bool(revealed),
            "expected_action_hidden_until_reveal":not bool(revealed),
            "revealed_case_type":item["declared_case_type"] if revealed else None,
            "choice":item["action"] if bound else None,
            "choice_matches_precommitted_oracle":aligned,
            "reviewed_goal_met":judged_met,
            "accepted_final_user_goal_matched":case_final,
            "recorded_outcome_gate":bool(aligned and judged_met and case_final),
            "independently_verified":False,
        })
    counts={kind:{"tested":0,"recorded_pass":0} for kind in sorted(CASE_TYPES)}
    for entry in result:
        if entry["revealed_case_type"] is not None:
            segment=counts[entry["revealed_case_type"]]
            segment["tested"]+=1
            segment["recorded_pass"]+=int(entry["recorded_outcome_gate"])
    from fsl_functional.audit import evaluate as functional_eval
    f=functional_eval(db,p["run_id"],as_of=cutoff)
    prereg_complete=all(
        counts[kind]["tested"]>0 for kind in CASE_TYPES)
    recorded_outcomes_all=(
        prereg_complete and
        all(x["recorded_outcome_gate"] for x in result)
        and all(x["perturbation_observed"] for x in result))
    g1=f["gates"]["G1_extreme_long_duration_completion"]
    g2_gate=bool(
        p["evidence_class"]=="observational" and recorded_outcomes_all
        and g1["recorded_conditions_satisfied"])
    return {
        "schema":"fsl/g2-controlled-adaptation/v0.8",
        "protocol_id":protocol_id,
        "mission_run_id":p["run_id"],
        "as_of":cutoff,
        "evidence_class":p["evidence_class"],
        "total_cases_preregistered":len(result),
        "four_scenario_case_coverage":counts,
        "case_records":result,
        "final_goal_alignment_claim":goal,
        "g1_prerequisite":{"recorded_conditions_satisfied":
                            g1["recorded_conditions_satisfied"],
                           "independently_verified":False},
        "four_case_recorded_outcomes_satisfied":bool(recorded_outcomes_all),
        "G2_recorded_conditions_satisfied":g2_gate,
        "G2_externally_verified":False,
        "adaptive_model_weights_updated":False,
        "assessment_status":(
            "synthetic_demonstration_only" if p["evidence_class"]=="synthetic"
            else "observational_claims_need_independent_verification"),
        "limits":[
            "Sealed adjudication avoids post-hoc relabeling but does not prove the evaluator is independent.",
            "A human goal change is assessed against the final accepted goal; it cannot be inferred from agent plans alone.",
            "A declared satisfactory outcome and an HTTPS URL are not independent proof that the work is complete.",
            "G2 requires real G1 continuity on the same persistent mission, not a short synthetic simulation.",
            "No feedback enters parameter-scaling posterior weights before external outcome verification.",
        ],
    }
