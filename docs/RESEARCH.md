# Frontier Scaling Lab — research protocol (2026-11-06)

## Why this approach?

Publicly observable GPU announcements, factory capacity, delivery timelines, training specifications, and open-weight disclosures can restrict the space of plausible future **training budgets**. They do not identify undisclosed model weights or a universal scale of cognition.

Separate at least five causal transitions:

1. Announced campus → permitted → built → powered → GPU installed and online.
2. Installed GPUs → synchronous topology → training allocation → realized model FLOP utilization (MFU).
3. Training compute + pretraining fraction + actual tokens + architectural overhead → conditional active parameters.
4. Active parameters + per-token MoE activation ratio → conditional total parameters.
5. Weights + post-training + inference budget + tool/Agent environment + task distribution → measured abilities.

For a group of connected GPUs, simple compute accounting is:

$$
C = G_{\mathrm{connected}} f_{\mathrm{train}} P_{\mathrm{peak}} u_{\mathrm{MFU}} (86400 T_{\mathrm{days}})
$$

A rough transformer pretraining operation-count model is:

$$
C_{\mathrm{pretrain}} \approx 6 N_{\mathrm{active}} D h
$$

Here $D$ denotes training tokens and $h$ explicitly accounts for overhead. $N_{\mathrm{total}} \approx N_{\mathrm{active}}/r$ uses the MoE active fraction $r$. These relations are *approximations*, not universally accurate equations for all multimodal, long-context, MoE or RL-based training.

## Critical unit distinctions

- Number of buildings is not number of data-center campuses.
- Power contracted (MW) is not power delivered; power delivered is not power used by GPUs.
- Vendor peak FLOP/s is not sustained training FLOP/s.
- Total installed fleet is not one interconnected training run.
- A model's total parameters are not its per-token activated parameters.
- Neither determines useful cognition independently of training recipe and evaluation budget.

When deriving GPUs from MW, **system_w_per_gpu must include proportional host/network power**, not GPU board TDP alone. If actual GPU count is known, the direct-count mode is preferable.

## Data, versioning and correction

Initial reference facts: NVIDIA Rubin NVL72 specs (accessed 2026-11-06):
https://www.nvidia.com/en-sg/data-center/vera-rubin-nvl72/

All other v0.1 values in data/scenarios.json are adjustable *illustrative* assumptions. Evidence events are line-oriented UTF-8 JSON in data/evidence.jsonl.

Each event requires id, recorded_at, scenario_id, field, value, source_kind, state, plus an HTTPS source_url for non-assumptions. Use state = asserted for a revision; state = retracted with value = null to nullify a prior assertion at later cutoffs. Both events remain in Git history.

Sample synthetic event (NOT a reported fact):

~~~json
{
  "id": "synthetic-e1",
  "recorded_at": "2027-01-01T00:00:00+00:00",
  "scenario_id": "rubin_100mw_reference",
  "field": "run.mfu",
  "value": [0.30, 0.45],
  "source_kind": "assumption",
  "state": "asserted"
}
~~~

The input baseline has a known date; a backdated evaluation before it is refused. This guards some retrospective leakage, but full prequential evaluation additionally needs faithful archived training/configuration snapshots.

## Explicit cognitive hypothesis

The proposed **2–3x ability multiplier** is currently an *unmeasured research hypothesis*. Do not conflate it with 2–3x GPU counts, FLOPs, active parameters, total parameters, scores, or economic utility.

Proper tests require stable, budget-matched agent/tool policy, inference tokens, time, success metrics, task difficulty, leakage controls, and multi-domain task vectors. A single scalar intelligence measure is not assumed.

## Temporal milestones

- M0 (this commit): reproducible conditional interval core, evidence event log, as-of replay, basic backtest, tests, offline CI.
- M1: verified facility registry with stable IDs, legal/physical stages, commissioning timelines, and duplicate detection.
- M2: sourced GPU product and topology catalogs, measured MFU distribution, precision reconciliation, power profiles.
- M3: model-disclosure collection, scored retrospective experiments, and published uncertainty audits.
- M4: probabilistic multi-stage forecasts with calibrated uncertainty, benchmark-vector ability studies, independent replication.

## Copyright and scientific status

This is an engineering research scaffold, not a paper claiming proof, an observation of actual vendor deployments, or a valuation/financial recommendation.
