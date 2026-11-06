"""One-shot, permission-separated ingestion of existing Agent event logs.

Agent-originated events can describe *its own actions only*. They cannot create
user goals, evaluator verdicts, final acceptance, or hidden oracle answers.
Runs are external and must separately persist their real time and state.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from fsl_functional.store import (
    add_event, fingerprint, moment, read_spec_run, validate_event,
)
from .ledger import InterventionError, bind_choice

ALLOWED_AGENT_EVENTS = frozenset({
    "progress", "checkpoint", "strategy_decision", "deliverable",
    "stack_change", "task_switch",
})


def load_jsonl(path, *, max_events=1000, max_bytes=8*1024*1024):
    """Bound log size and emit parsed records; never evaluate Agent-generated code."""
    file=Path(path)
    if not file.is_file() or file.stat().st_size>max_bytes:
        raise InterventionError("event log must be a bounded regular file")
    records=[]
    for lineno,line in enumerate(file.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip():
            continue
        if len(records)>=max_events:
            raise InterventionError("event log exceeds per-batch item cap")
        try:
            item=json.loads(line)
        except ValueError as exc:
            raise InterventionError(f"invalid UTF-8 JSON on line {lineno}") from exc
        if not isinstance(item,dict):
            raise InterventionError(f"line {lineno}: expected event object")
        records.append(item)
    if not records:
        raise InterventionError("empty Agent event batch")
    return records


def ingest(db, *, run_id, events, collector_at, protocol_id=None):
    """Ingest Agent's own actions and optionally bind preregistered G2 choices.

    Source events in this API remain Agent-authored claims, not external proof.
    Event IDs are idempotent and immutable. A repeated ID with different bytes
    is rejected; partial batches may be resumed unchanged after an error.
    """
    run=read_spec_run(db,run_id)
    now=moment(collector_at)
    if now<moment(run["initiated_at"]):
        raise InterventionError("collector timestamp predates mission")
    if not isinstance(events,list) or not 1<=len(events)<=1000:
        raise InterventionError("events must be a bounded nonempty list")

    if protocol_id is not None:
        row=db.execute("SELECT run_id FROM g2_protocols WHERE protocol_id=?",
                       (protocol_id,)).fetchone()
        if row is None or row["run_id"]!=run_id:
            raise InterventionError("G2 protocol not registered for this mission")

    # Full preflight: prevent an Agent from injecting evaluator/user records
    # before performing any mutations.
    planned=[]
    for ev in events:
        if not isinstance(ev,dict) or ev.get("actor")!="ai":
            raise InterventionError("this intake only accepts AI-authored events")
        if ev.get("kind") not in ALLOWED_AGENT_EVENTS:
            raise InterventionError("Agent may not impersonate user or evaluator events")
        if ev.get("run_id")!=run_id:
            raise InterventionError("cross-mission event rejected")
        validate_event(ev)
        if moment(ev["occurred_at"])>now or moment(ev["recorded_at"])>now:
            raise InterventionError("Agent events cannot be stamped in the future")
        existing=db.execute("SELECT event_sha256 FROM functional_events WHERE event_id=?",
                            (ev["event_id"],)).fetchone()
        incoming=fingerprint(ev)
        if existing is not None and existing["event_sha256"]!=incoming:
            raise InterventionError("event_id conflict: immutable event contents changed")
        case_id=None
        if ev["kind"]=="strategy_decision" and protocol_id is not None:
            case=db.execute("""SELECT c.case_id FROM g2_precommitted_cases c
             WHERE c.protocol_id=? AND c.future_perturbation_event_id=?""",
             (protocol_id,ev["payload"]["change_event_id"])).fetchone()
            if case is None:
                raise InterventionError("strategy decision has no preregistered intervention")
            case_id=case["case_id"]
        planned.append((ev,existing is None,case_id))

    created=[]
    skipped=[]
    bound=[]
    for ev,is_new,case_id in planned:
        if is_new:
            add_event(db,ev)
            created.append(ev["event_id"])
        else:
            skipped.append(ev["event_id"])
        if case_id is not None:
            prior=db.execute("SELECT decision_event_id FROM g2_bound_decisions WHERE case_id=?",
                             (case_id,)).fetchone()
            if prior is None:
                bind_choice(db,{
                    "case_id":case_id,"decision_event_id":ev["event_id"],
                    "bound_at":now.isoformat(),
                })
                bound.append(case_id)
            elif prior["decision_event_id"]!=ev["event_id"]:
                raise InterventionError("a different AI decision is already bound to this case")
    return {
        "schema":"fsl/agent-event-intake/v0.8",
        "run_id":run_id,
        "collector_at":now.isoformat(),
        "events_created":created,
        "idempotent_replays":skipped,
        "blinded_cases_bound":bound,
        "user_or_evaluator_verdicts_written":False,
        "claim_grade":"agent_self_report_not_independent_work_proof",
        "oracle_answers_visible_to_agent":False,
        "warning":"External source receipts and an evaluator are needed; this API does not grant autonomous execution.",
    }
