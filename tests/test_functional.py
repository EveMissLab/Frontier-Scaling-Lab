"""Synthetic only: multi-week product completion and embodied task switching.

Never interpret fictitious event dates or evaluator URLs as actual benchmarks.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import sqlite3
import unittest

from fsl_functional.store import MissionError, add_spec, add_run, add_event, connect
from fsl_functional.audit import evaluate


A="a"*64
B="b"*64
C="c"*64
D="d"*64
R="https://example.org/SYNTHETIC-NOT-REAL-EVIDENCE/"


def spec(kind="game", run_id="test-long-game"):
    from fsl_functional.store import MANDATORY
    return {
        "spec_id":"spec-"+kind,
        "track":"embodied" if kind=="embodied" else "digital",
        "kind":kind,
        "title":"SYNTHETIC full mission demonstration, NOT an actual completed game/robot",
        "reference_url":R+"benchmark-reference",
        "reference_date":"2025-12-01",
        "created_at":"2025-12-31T00:00:00Z",
        "min_duration_days":0 if kind=="embodied" else 28,
        "max_user_rounds":3,
        "required_criteria":sorted(MANDATORY[kind]),
        "evidence_class":"synthetic",
    }


def run(kind="game"):
    return {
        "run_id":"synthetic-"+kind,
        "spec_id":"spec-"+kind,
        "system_key":"FICTIONAL-AI-SYSTEM",
        "system_revision":"synthetic-v0",
        "initiated_at":"2026-01-01T00:00:00Z",
        "evidence_class":"synthetic",
    }


def event(eid,kind,day,payload=None,actor="ai",hour=12,source=True):
    return {
        "event_id":eid,"run_id":"synthetic-game","kind":kind,
        "actor":actor,
        "occurred_at":f"{day}T{hour:02d}:00:00Z",
        "recorded_at":f"{day}T{hour+1:02d}:00:00Z",
        "payload":payload or {},
        **({"source_url":R+eid} if source else {}),
    }


def game_events():
    things=[event("intent","intent","2026-01-01",
                  {"goal_sha256":A},actor="user")]
    for i,day in enumerate(("2026-01-02","2026-01-08","2026-01-15",
                            "2026-01-22","2026-01-30")):
        things.append(event("checkpoint"+str(i),"checkpoint",day,{"evidence_sha256":C}))
    things.append(event("recover","recovery","2026-01-03",
                        {"checkpoint_event_id":"checkpoint0",
                         "restored_state_sha256":C,"cause":"restart"}))
    things.extend([
        event("goal-change","goal_revision","2026-01-10",
              {"goal_sha256":B},actor="user",hour=10),
        event("replan","strategy_decision","2026-01-10",
              {"change_event_id":"goal-change","choice":"replan",
               "reason_sha256":D},hour=11),
        event("review-replan","adaptation_judgement","2026-01-10",
              {"decision_event_id":"replan","correct":True,
               "revised_goal_met":True},actor="evaluator",hour=13),
        event("env-shift","environment_change","2026-01-12",
              {"disturbance_sha256":D},actor="environment",hour=10),
        event("maintain","strategy_decision","2026-01-12",
              {"change_event_id":"env-shift","choice":"maintain",
               "reason_sha256":D},hour=11),
        event("review-maintain","adaptation_judgement","2026-01-12",
              {"decision_event_id":"maintain","correct":True,
               "revised_goal_met":True},actor="evaluator",hour=13),
        event("build","deliverable","2026-02-04",
              {"artifact_sha256":D,"artifact_type":"playable integrated game build"},hour=10),
    ])
    criteria=spec()["required_criteria"]
    for i,c in enumerate(criteria):
        things.append(event("qa-"+str(i),"quality_review","2026-02-04",
                            {"criterion":c,"passed":True,"reviewer":"reviewer-"+str(i%2),
                             "deliverable_event_id":"build"},
                            actor="evaluator",hour=12))
    for axis in ("personal_author","ai_native"):
        for i in range(2):
            things.append(event("style-"+axis+"-"+str(i),"style_review",
                                "2026-02-04",
                                {"axis":axis,"passed":True,
                                 "reviewer":"style-reviewer-"+str(i),
                                 "deliverable_event_id":"build"},
                                actor="evaluator",hour=15))
    things.append(event("accepted","final_acceptance","2026-02-05",
                        {"deliverable_event_id":"build","accepted":True,
                         "goal_sha256":B},actor="evaluator",hour=10))
    return things


def robot_events():
    things=[
        event("robot-intent","intent","2026-01-01",{"goal_sha256":A},
              actor="user"),
        event("robot-new-goal","goal_revision","2026-01-02",
              {"goal_sha256":B},actor="user",hour=9),
        event("robot-replan","strategy_decision","2026-01-02",
              {"change_event_id":"robot-new-goal","choice":"replan",
               "reason_sha256":C},hour=10),
        event("robot-judgement","adaptation_judgement","2026-01-02",
              {"decision_event_id":"robot-replan",
               "correct":True,"revised_goal_met":True},
              actor="evaluator",hour=12),
    ]
    domains=("navigation","manipulation","inspection")
    for i,domain in enumerate(domains):
        things.append(event("outcome-"+str(i),"domain_outcome",
                            "2026-01-0"+str(i+3),
                            {"domain":domain,"accepted":True},actor="evaluator"))
    for i in (0,1):
        things.append(event("switch-"+str(i),"task_switch","2026-01-07",
                            {"from_domain":domains[i],"to_domain":domains[i+1]},
                            hour=10+i))
    things.extend([
        event("robot-incident","safety_incident","2026-01-08",
              {"severity":"minor"}),
        event("robot-resolved","safety_resolution","2026-01-09",
              {"incident_event_id":"robot-incident","resolved":True},
              actor="evaluator"),
    ])
    for thing in things:
        thing["run_id"]="synthetic-embodied"
    return things


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        self.db=connect(":memory:")
        add_spec(self.db,spec())
        add_run(self.db,run())

    def tearDown(self):
        self.db.close()

    def fill(self,objects=None):
        for e in objects if objects is not None else game_events():
            add_event(self.db,e)

    def audit(self,day="2026-02-06T00:00:00Z"):
        return evaluate(self.db,"synthetic-game",as_of=day)

    def test_all_four_digital_upper_goal_gates_remain_synthetic_only(self):
        self.fill()
        result=self.audit()
        for name in ("G1_extreme_long_duration_completion",
                     "G2_dynamic_autonomous_adaptation",
                     "G3_few_round_world_class_usable_delivery",
                     "G4_personal_and_ai_native_creative_styles"):
            g=result["gates"][name]
            self.assertTrue(g["recorded_conditions_satisfied"],name)
            self.assertEqual(g["state"],"simulated_candidate_not_empirical")
            self.assertFalse(g["independently_verified"])
        self.assertFalse(result["externally_certified_result"])
        self.assertFalse(result["empirical_capability_ceiling_established"])
        self.assertEqual(result["user_instruction_rounds"],2)
        self.assertGreater(result["calendar_days_claimed"],28)

    def test_short_idle_interval_not_passed_as_long_duration_work(self):
        self.fill()
        res=self.audit()
        self.assertGreaterEqual(
            res["gates"]["G1_extreme_long_duration_completion"]
               ["measurements"]["source_backed_progress_days"],4)
        missing=copy.deepcopy(game_events())
        missing=[e for e in missing if e["kind"]!="checkpoint"]
        # A recovery without its checkpoint cannot count as a demonstrated
        # state return, and no real progress dates survive.
        self.db.close()
        self.db=connect(":memory:")
        add_spec(self.db,spec())
        add_run(self.db,run())
        self.fill(missing)
        result=self.audit()
        self.assertFalse(result["gates"]["G1_extreme_long_duration_completion"]
                         ["recorded_conditions_satisfied"])

    def test_true_final_goal_link_required(self):
        events=game_events()
        receipt=next(e for e in events if e["event_id"]=="accepted")
        receipt["payload"]["goal_sha256"]=A
        self.fill(events)
        r=self.audit()
        self.assertFalse(r["gates"]["G1_extreme_long_duration_completion"]
                         ["recorded_conditions_satisfied"])

    def test_goal_change_needs_good_revision_and_good_hold(self):
        events=[e for e in game_events() if e["event_id"]!="review-maintain"]
        self.fill(events)
        r=self.audit()
        self.assertTrue(r["gates"]["G1_extreme_long_duration_completion"]
                        ["recorded_conditions_satisfied"])
        self.assertFalse(r["gates"]["G2_dynamic_autonomous_adaptation"]
                         ["recorded_conditions_satisfied"])

    def test_world_class_is_not_artwork_screenshot_or_user_turn_count_only(self):
        events=game_events()
        events=[e for e in events if e["event_id"]!="qa-0"]
        self.fill(events)
        r=self.audit()
        self.assertTrue(r["gates"]["G1_extreme_long_duration_completion"]
                        ["recorded_conditions_satisfied"])
        self.assertFalse(r["gates"]["G3_few_round_world_class_usable_delivery"]
                         ["recorded_conditions_satisfied"])

    def test_more_than_three_user_instruction_rounds_blocks_G3(self):
        events=game_events()
        events.extend([
            event("extra-instruction-1","user_round","2026-01-20",
                  {"instruction_sha256":C},actor="user"),
            event("extra-instruction-2","user_round","2026-01-25",
                  {"instruction_sha256":C},actor="user"),
        ])
        self.fill(events)
        r=self.audit()
        self.assertEqual(r["user_instruction_rounds"],4)
        self.assertFalse(r["gates"]["G3_few_round_world_class_usable_delivery"]
                         ["recorded_conditions_satisfied"])

    def test_ai_native_style_cannot_be_substituted_by_personal_style(self):
        events=[e for e in game_events()
                if not e["event_id"].startswith("style-ai_native")]
        self.fill(events)
        r=self.audit()
        self.assertTrue(r["gates"]["G3_few_round_world_class_usable_delivery"]
                        ["recorded_conditions_satisfied"])
        self.assertFalse(r["gates"]["G4_personal_and_ai_native_creative_styles"]
                         ["recorded_conditions_satisfied"])

    def test_human_direct_execution_is_not_autonomous_success(self):
        events=game_events()+[event("human-fix","human_assist","2026-01-25",
                                   {"level":"direct_execution"},actor="operator")]
        self.fill(events)
        r=self.audit()
        self.assertFalse(r["gates"]["G1_extreme_long_duration_completion"]
                         ["recorded_conditions_satisfied"])
        self.assertEqual(r["human_interventions"]["direct_execution"],1)

    def test_history_cutoff_cannot_see_future_final_work(self):
        self.fill()
        result=self.audit("2026-01-28T23:59:59Z")
        self.assertIsNone(result["calendar_days_claimed"])
        self.assertFalse(result["gates"]["G1_extreme_long_duration_completion"]
                         ["recorded_conditions_satisfied"])

    def test_event_corrections_are_append_only_and_change_future_cutoff(self):
        self.fill()
        correction=event("correction-accepted","correction","2026-02-06",
                         {"supersedes_event_id":"accepted"})
        add_event(self.db,correction)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM functional_events WHERE event_id='accepted'")
        early=self.audit("2026-02-05T13:00:00Z")
        later=self.audit("2026-02-07T00:00:00Z")
        self.assertTrue(early["gates"]["G1_extreme_long_duration_completion"]
                        ["recorded_conditions_satisfied"])
        self.assertFalse(later["gates"]["G1_extreme_long_duration_completion"]
                         ["recorded_conditions_satisfied"])

    def test_embodied_separate_lower_completion_bar_with_safe_switches(self):
        add_spec(self.db,spec("embodied"))
        add_run(self.db,run("embodied"))
        for e in robot_events():
            add_event(self.db,e)
        result=evaluate(self.db,"synthetic-embodied",
                        as_of="2026-01-10T00:00:00Z")
        self.assertEqual(result["gates"]["G1_extreme_long_duration_completion"]
                         ["state"],"not_applicable_separate_track")
        self.assertTrue(result["gates"]["E1_embodied_multi_domain_adaptation"]
                        ["recorded_conditions_satisfied"])
        self.assertFalse(result["externally_certified_result"])

    def test_embodied_unresolved_safety_blocks_acceptance(self):
        add_spec(self.db,spec("embodied"))
        add_run(self.db,run("embodied"))
        for e in robot_events():
            if e["event_id"]!="robot-resolved":
                add_event(self.db,e)
        result=evaluate(self.db,"synthetic-embodied",as_of="2026-01-10T00:00:00Z")
        self.assertFalse(result["gates"]["E1_embodied_multi_domain_adaptation"]
                         ["recorded_conditions_satisfied"])

    def test_spec_does_not_allow_single_screenshot_in_place_of_game(self):
        bad=spec()
        bad["spec_id"]="weak-gate"
        bad["required_criteria"]=["visual_or_distinctive_style"]
        with self.assertRaises(MissionError):
            add_spec(self.db,bad)

    def test_event_cannot_be_backdated_or_edited(self):
        bad=event("future","checkpoint","2026-01-02",
                  {"evidence_sha256":C})
        bad["recorded_at"]="2026-01-01T10:00:00Z"
        with self.assertRaises(MissionError):
            add_event(self.db,bad)
        self.fill([game_events()[0]])
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE functional_runs SET system_key='fake'")

    def test_g1_does_not_claim_certification_from_user_supplied_urls(self):
        self.fill()
        r=self.audit()
        self.assertEqual(r["evidence_class"],"synthetic")
        self.assertFalse(r["externally_certified_result"])
        self.assertIsNone(r["general_intelligence_score"])
        self.assertEqual(len(r["evidence_manifest_sha256"]),64)


if __name__=="__main__":
    unittest.main()
