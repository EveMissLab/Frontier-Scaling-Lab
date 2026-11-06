# Frontier Scaling Lab v0.8 — 極長時程任務中的動態目標適應：盲式干預與結果驗收

**Date: 2026-11-07**  
**Canonical source: UTF-8 Markdown, original formulas use only dollar-delimited LaTeX**  
**License: Apache-2.0 for original source/code (not for external evidence datasets)**

## 0. Research position

This version extends the user-defined G2 capability target from FUNCTIONAL_FRONTIER_v0.6.md: an AI that genuinely maintains a continuing goal over days/weeks/months (G1), understands when to change or preserve its strategy, asks for necessary clarification, escalates exceptions, and reaches the user's *current actual desired outcome*.

The benchmark does NOT instruct an AI how to learn or behave. It is an outside measurement procedure that separates the user's goal, an independent perturbation, the AI's own strategy choice, the result, and an evaluator's independent assessment.

The earlier human-task-duration H50/H80 measure is only auxiliary. G3 (fully functional human-leading product in one/few user rounds), G4 (distinctive personal and AI-native art), and embodied E1 remain separate capability tracks. **Only G2 expressly requires G1.**

### The key scientific correction

A category name does NOT dictate a globally correct action. For example, a user goal modification may leave an existing strategy appropriate; a noisy environmental event may sometimes genuinely invalidate an essential assumption. Whether to maintain or replan is an *instance-specific counterfactual judgment*, not a hard-coded four-option policy.

The four canonical experiment families here are:
- substantive goal change;
- irrelevant/noisy disturbance;
- genuine ambiguity requiring clarification;
- boundary/exception requiring escalation.

For an adequately balanced pilot, the benchmark also requires at least one valid instance whose independently committed correct action is each of: replan, maintain, clarify, escalate. The public code does not map category names to compulsory actions. The hidden expected response and case type are jointly sealed per trial, ahead of time.

## 1. Why blind preregistration is necessary

If an evaluator sees a model replan first and only afterwards decides that replanning was correct, the benchmark can become an exercise in rationalizing whatever the model did. Conversely, declaring that a noisy event always requires maintaining a strategy overfits the measurement protocol to labels.

The system preregisters, per challenge:
1. An opaque case ID and future perturbation event ID;
2. A bounded **outcome_due_at** deadline;
3. The evaluator's hidden case class, expected action, and intended final goal hash;
4. A high-entropy random nonce that protects the blind oracle commitment;
5. A dated source record and a separately hashed experiment rubric.

The sealed commitment is:

$$
K_j=\mathrm{SHA256}(\mathrm{CanonicalJSON}(\mathrm{case}_j,\mathrm{class}_j,\mathrm{action}_j,\mathrm{goalSHA}_j,\mathrm{nonce}_j)).
$$

The nonce must be a random value of at least 128 bits and remain outside the evaluated Agent's accessible files and context. The hash by itself does not make a fake human timestamp trustworthy; for real studies the commitment should be deposited in a trusted external timestamped location before perturbations begin.

The observer stores only the commitment, not the expected decision. A reveal mismatching the earlier sealed hash is refused; case types cannot be retroactively reclassified. The correct action is *local to the fully specified case* and must not be taught as a universal AI decision rule.

## 2. Actors and permission separation

- **User:** authors the original intent and any meaningful goal revision. A model is not allowed to impersonate a user to authorize a changed objective.
- **Environment/test examiner:** records a genuine perturbation, including irrelevant disturbances and ambiguous/exception situations. The examiner must not disclose the hidden correct response to the AI.
- **AI/Agent:** may record progress, checkpoints, strategy decisions, system revisions, task switches and deliverables. The Agent receives the actual situation and current objective; it must not receive oracle nonces, evaluator labels or secret future tests.
- **Independent evaluator:** records post-outcome correctness and whether the amended goal was satisfied, then reveals the sealed oracle after the deadline. The evaluator remains outside the Agent's control.
- **Source observatory (v0.7):** independently obtains GitHub CI/commit receipts and local file hashes. A source-linked artifact proves some actual bytes existed, not that a full game is playable or a product is usable.

The v0.8 Agent JSONL intake enforces this boundary programmatically: user goal revisions, final acceptance, adaptation judgments and safety approvals are NOT accepted from the AI actor. Allowed Agent payloads contain structured hashes and permitted fields, not raw user conversations or oracle secrets.

## 3. Time, decision and outcome ordering

The following ordering is enforced for each experiment case:

1. Mission started and protocol/rubric registered;
2. The opaque case and oracle commitment were persisted before its perturbation existed in the experiment database;
3. The user/environment perturbation event was recorded;
4. The AI independently chose and recorded its strategy;
5. The choice was irrevocably bound to that case;
6. The preregistered outcome deadline elapsed;
7. The evaluator recorded its post-outcome judgment;
8. The evaluator revealed the oracle and the system checked the stored commitment.

A case cannot receive full outcome credit solely for matching its committed action. The study must also find a final accepted deliverable that occurs after the choice and whose accepted goal hash equals the *latest* user goal and the preregistered intended outcome goal.

Importantly, an AI that correctly escalates because of a risky permission boundary is not thereby a failure: the test follows whether it proceeds within legitimate authorization and ultimately satisfies the user goal. Necessary human clarifications and exception decisions should be distinguished from direct human execution of the AI's core work.

### G1 as a separate prerequisite

A digital G2 claim also needs G1 continuity on the same real mission. Having a handful of correctly classified perturbations in a short scripted simulation does not demonstrate weeks of autonomous work.

The v0.8 experimental output has two distinct levels:
- Four-case *recorded outcome coverage*: the blinded scenario/outcome protocol appears internally satisfied;
- A conditional G2 *recorded-condition* gate: observational data class, all required contrasts, v0.6 G1 recorded precondition and an exact-byte v0.7 deliverable receipt.

**Neither is independent empirical certification.** No v0.8 result can set G2_externally_verified to true. That requires authenticated Agent/runtime identity, trusted independent time sources, independent review of finished work, and verified role separation.

## 4. What the software actually computes

For each sealed case $j$, define separate observable conditions:

- $P_j$: the perturbation was registered after its sealed oracle commitment;
- $D_j$: the AI decision is tied to that perturbation and occurs before the fixed deadline;
- $C_j$: the decision matches the revealed, previously sealed case-specific oracle;
- $R_j$: a separate evaluator records a satisfactory result;
- $U_j$: a later final deliverable is accepted against the current user goal and the expected outcome goal.

The *recorded* case gate is:

$$
A_j=P_j\land D_j\land C_j\land R_j\land U_j.
$$

The descriptive experiment also records which of the four action types and which of the four situation classes have actually been tested. It does not average these outcomes into general intelligence, and it does not assign parameter-scaling posterior weights from synthetic examples.

G2 additionally requires the G1 prerequisite and external output evidence. If a task fails to finish, an answer that merely sounded like a clever plan is not a success.

## 5. Persistent data and source provenance

The v0.8 SQLite schema adds four append-only tables alongside existing functional and observer tables:

- g2_protocols: mission ID, rubric/question/intervention hashes, prereg time, evaluator identity and synthetic/observational evidence class.
- g2_precommitted_cases: opaque case ID, planned perturbation ID, committed time, fixed outcome deadline, sealed oracle SHA256 and source.
- g2_bound_decisions: selected Agent strategy event, original recorded choice, bind time and immutable hash.
- g2_adjudications: post-outcome evaluator judgment, revealed class/action/outcome goal/nonce and immutable proof link.

All INSERTs are immutable; UPDATE and DELETE are blocked at the database level. A correction needs an explicit new version/experiment, not a silent retroactive edit. Existing functional_events already retain append-only corrections for task claims.

The source layer records *occurred_at* and *recorded_at* separately. However, these are only as credible as their origin. The program can prevent database backdating relative to logged events; it cannot itself prove that all externally submitted timestamps are genuine.

Historical as-of replay never uses later-available decision reveals or outcomes to calculate an earlier information state.

## 6. Hook to an existing Agent without teaching it a curriculum

An external Agent can append only its own action events to a bounded UTF-8 JSONL file. Each line is one v0.6 functional event with stable event ID, mission ID, actor="ai", UTC occurred/recorded times, approved event kind, and machine-readable payload digests.

The one-shot intake command ingests those records while enforcing:
- only AI-authored actions; no user/evaluator impersonation;
- no hidden oracle fields, full private user prompts or arbitrary payload keys;
- no events stamped in the future relative to the collector;
- no linking a G2 decision to an unregistered or unobserved change;
- idempotent replay of unchanged event IDs;
- rejection of an event ID rewritten with different content;
- automatic irrevocable case binding when a corresponding opaque preregistration exists.

This is **an observation hook**, not a long-running Agent service. It does not give an AI permission to act in arbitrary apps, write to private projects, spend API funds, approve its own results, or change its user-given objective.

### Example CLI sequence

Python 3.11+, standard library SQLite; no additional runtime packages.

~~~bash
# 0. Register real mission and long-running system first.
python -m fsl_functional.cli --db observations/fsl.sqlite spec --file real_spec.json
python -m fsl_functional.cli --db observations/fsl.sqlite run --file real_run.json

# 1. Independent evaluator: store the preregistered protocol and SEAL the answer.
python -m fsl_interventions.cli --db observations/fsl.sqlite protocol --file protocol.json
python -m fsl_interventions.cli --db observations/fsl.sqlite seal --file PRIVATE_oracle.json
python -m fsl_interventions.cli --db observations/fsl.sqlite preregister --file case_commitment.json

# 2. Authorized user/environment interface inserts actual perturbation event.
python -m fsl_functional.cli --db observations/fsl.sqlite event --file user_goal_revision.json

# 3. Existing Agent emits only its own evidence and choices.
python -m fsl_interventions.cli --db observations/fsl.sqlite agent-ingest --run-id REAL_RUN_ID --protocol-id REAL_PROTOCOL_ID --file agent_actions.jsonl

# 4. After the mission outcome and preregistered deadline:
# evaluator registers its independent judgment, then reveals the sealed answer.
python -m fsl_functional.cli --db observations/fsl.sqlite event --file reviewer_judgement.json
python -m fsl_interventions.cli --db observations/fsl.sqlite reveal --file PRIVATE_reveal.json
python -m fsl_interventions.cli --db observations/fsl.sqlite audit --protocol-id REAL_PROTOCOL_ID
~~~

The PRIVATE files must **not be copied to the tested Agent's workspace or committed to a public Git repository**. The generated hash is safe to publish; the answer, nonce, hidden case type and complete future prompts are not.

Use v0.7 to observe and cryptographically link the actual final artifact byte content. Successful GitHub CI alone is not the same as the finished user's target being validated.

## 7. Synthetic regression demo: what it does and does not show

~~~bash
python -m unittest discover -s tests -v

python -m fsl_interventions.cli --db reports/fsl_g2_synthetic.sqlite synthetic-demo \
  --file tests/fixtures/g2_intervention_synthetic.json \
  --as-of 2026-01-18T00:00:00Z \
  --output reports/fsl_g2_report.json
~~~

The fabricated fixture represents a 16-day mission with five dated checkpoints, a checkpoint recovery, four staged perturbations, an imaginary final deliverable and independent-sounding *but fake* evaluator statements. The fixtures contain visible hidden answers for the convenience of verifying software; only the production protocol keeps them secret.

The synthetic four-case table is expected to pass its **recorded** contrasts. It still reports:
- G2_recorded_conditions_satisfied = false;
- G2_externally_verified = false;
- assessment_status = synthetic_demonstration_only;
- adaptive_model_weights_updated = false.

The demo cannot be cited as real evidence of a 16-day autonomous Agent, a verified working application, or AI foresight. It tests the rules that would later measure genuine examples.

## 8. Scientific failure cases

The regression tests check at least these failure modes:

- A case gets preregistered only after the user's change is already known;
- The hidden oracle is revealed with a changed nonce, action, context category or intended final goal;
- The AI choice belongs to another change or another mission;
- The decision is logged only after the fixed deadline;
- A reviewer tries to judge the outcome before the fixed deadline;
- The AI chooses the wrong action despite later user acceptance;
- The AI chooses a plausible action but delivers the wrong final user goal;
- The Agent tries to forge a user instruction, independent assessment, or acceptance;
- A claimed file artifact's SHA256 does not equal its observed byte content;
- A source retrieved after the historical cutoff is used as if it existed earlier;
- A synthetic run gets promoted into a real capability result.

A model can succeed on some dimensions and fail others. Negative and censored outcomes must remain in the study, not be discarded to improve the headline result.

## 9. What v0.8 still cannot claim

A public GitHub code repository, programmatic oracle commitment and fully passing synthetic tests do **not** prove:
- any frontier model autonomously worked for several days or months;
- the evaluator is genuinely independent of the Agent;
- the Agent understands a private real user's goals;
- an integrated app/game is actually installable, playable and world-class;
- a material architecture breakthrough has occurred;
- a 5–10× model parameter increase or 2–3× general cognition multiple has been measured.

G1/G2 real-world trials require an authenticated persistent runner, independently attested wall time, a source-backed task world and genuinely usable finished output. G3/G4 and embodied E1 keep their separate finished-work and physical task validation paths.

## 10. Next integration

The next step is not to increase the number of artificial categories. It is to connect this measurement protocol to a permitted, real persistent Agent and a user-authorized project:

1. Register baseline goal, permissions, reference product quality and the actual Agent/runtime manifest.
2. Operate the Agent in an authenticated long-running environment.
3. Apply hidden/realistic interventions under external evaluator control while preserving true user choice and authority.
4. Record actual source observations, without contaminating model inputs with private oracle labels.
5. Independently accept or reject a usable final work; preserve all misses, interventions and handoffs.
6. Then correlate only verified functional outcomes with dated hardware/model/runtime investments, using forward-held-out data, without claiming causality solely from lag correlations.

**The measure of dynamic intelligence is not how often the system changes its plan; it is whether it understands when a change is justified, correctly preserves the goal when it is not, and ultimately delivers the real user's intended result.**
