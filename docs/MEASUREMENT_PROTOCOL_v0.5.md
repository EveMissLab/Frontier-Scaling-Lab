# FSL v0.5 — 可辨識的 AI 能力量測、延遲實現與收益遞減檢驗協定

**2026-11-07 | UTF-8 canonical Markdown | Apache-2.0 original document**

**Research status:** Task-horizon numerical estimator implemented and tested on **synthetic** fixtures. No empirical 2–3× cognitive improvement, 5–10× model-size growth, or causal hardware-payback result is claimed.

## 1. What is measured?

FSL does **not** assume that general intelligence is a unique scalar. Use a vector of six dimensions: mathematical/formal correctness, software engineering success, coherent long-horizon task reliability, domain transfer/novel task performance, robustness and recovery, and Agent/tool-system effect. Keep inference price and physical training input separate.

For each *fixed task distribution, evaluation protocol, model version, scaffold and inference budget*, estimate the probability $p_m(d)$ of completing a self-contained task as a function of human expert task difficulty duration $d$.

We adapt the concept of METR's H50/H80 task-completion time horizons (the horizontal axis is **human expert completion time**, not AI runtime):

$$
p_m(d)=\frac{1}{1+\exp[-(a_m+b_m\log d)]},\quad b_m<0.
$$

The threshold $H_{q,m}$ solves $p_m(H_{q,m})=q$ for $q\in\{0.5,0.8\}$. We report $H_{50}$ and $H_{80}$ **only inside the evaluated human-task duration range**, with a task-cluster bootstrap interval where estimable.

Two model versions with the *same* task SHA-256, human expert difficulty anchors, prompt/tool rules, scaffolding and budget can be compared within the same domain:

$$
R_{q,k}=\frac{H_{q,k}^{\mathrm{new}}}{H_{q,k}^{\mathrm{base}}}.
$$

A ratio $R_{80,k}=2.5$ would mean a 2.5× longer *human-expert task-duration horizon* on that task domain at 80% success under the fixed experimental conditions. **It does not mean 2.5× general intelligence, 2.5× model parameters, or 2.5× AI working time.** The ratio may be undefined if either horizon lies outside the evaluation support.

METR's public page (last updated September 8, 2026) provides a well-developed reference method, but its limited software/ML task distribution is not a universal census of labor or knowledge. It is not currently actively updated. We implement our own estimator, not a copy of METR's model weights or its private task data.

## 2. Test design

For each task family, initially establish **at least 100 well-specified tasks** across a broad human difficulty range, with **at least six independent model attempts per task**. The v0.5 software validation gate intentionally allows 12 tasks and three attempts so small synthetic tests can run; these numbers are **not** adequate for all publishable H80 estimates.

Every trial must record: exact task ID and task-set SHA-256; human-expert minutes and estimation method; binary success/failure; model and revision; task domain; scaffold; tool and prompt hashes; benchmark version; max total tokens, wall time and USD budget per task; actual resource consumption (future field); API or deployment version; evaluation/publication/recording dates; source URL; verification class; whether real or synthetic.

Report attempt-level stability, timeouts, protocol violations, model-version changes and contamination risks. Frozen model weights are especially valuable as **measurement negative controls**.

Do not treat human preferences, Arena ratings, downloads, public model names or raw user comments as task-success results. Those remain separate observational dimensions.

## 3. Factorial comparison separating weights and Agent systems

Run a controlled 2×2 design at each fixed budget level:

| Condition | Model revision | Scaffold / Agent |
|---|---|---|
| A | Old | Original |
| B | New | Original |
| C | Old | Updated |
| D | New | Updated |

At fixed task protocol and budget, measure A→B (model-version effect), A→C (Agent-system effect), B→D (Agent effect on the new model) and A→D (user-visible combined change). If model and scaffold both change in a single comparison, the v0.5 program labels the difference **confounded**, rather than assigning it to weights.

Repeat the experiment on at least three explicit inference-budget tiers; derive domain-specific task-success frontiers and the cost to achieve a *fixed target reliability* where available. A fixed budget cap does not prove equal actual cost, so real token, wall-time and dollar usage must eventually be recorded before cost-effectiveness claims.

## 4. Separating the three clocks

The timestamp model should distinguish:

1. **Infrastructure:** announcement, permit, construction, power available, GPUs installed, GPUs connected, measured capacity. Only measured/verified availability enters the observed physical input; planned MW stays in a scenario branch.
2. **Training:** start/end intervals if disclosed, GPU count/interconnect, numeric precision, active tokens, architecture, estimated training FLOPs with source confidence tier.
3. **Capability realization:** public release, stable pinned serving revision, independent fixed-budget task tests, product Agent changes, sustained user adoption.

When training dates are undisclosed, treat them as latent *intervals* with explicit prior assumptions. Do not substitute product release dates for training dates, do not sum disconnected GPU fleets into one training run, and do not assume all live GPU capacity is allocated to pretraining.

## 5. Lagged payback vs plateau vs architectural change

For properly observed monthly series only, let $G_t$ be a source-audited **connected training-compute capacity** (with precision and MFU assumptions) and let $H_{80,k,t}$ be the domain-$k$ 80% horizon measured with stable task protocol.

Candidate research models are:

- **M0: clock-time baseline** — trend without hardware as a predictor.
- **M1: contemporaneous capacity** — outcomes associated with verified capacity at time $t$.
- **M2: distributed lag** — outcomes associated with capacity observed at $t-\ell$, with $\ell$ evaluated over preregistered lag windows (e.g., 0–24 months).
- **M3: saturation / plateau** — declining marginal change of task horizons with added usable compute, under fixed architecture families.
- **M4: change point** — model architecture, tool systems or training recipe changed, so a former slope should not be extrapolated unchanged.
- **M5: measurement artifact** — an apparently large score jump can be explained by benchmark method or sample composition change.

Simple descriptive distributed lag:

$$
\Delta\log H_{80,k,t}
=\alpha_k+\sum_{\ell=0}^{L}\beta_{\ell,k}\Delta\log G_{t-\ell}
+\gamma_k X_t+\varepsilon_{k,t}.
$$

The nuisance vector $X_t$ should include as much as can be observed: release cohorts, changes in data mixture, post-training, hardware generation/precision, benchmark/scaffold revisions, inference budget and calendar effects. Missing terms are recorded, not imputed as zero.

**Time-series correlation is not causal identification.** Reverse timing, endogenous investment, delayed public disclosure, changing model evaluation policy, and unobserved training compute are major confounders. Report forecast improvements over M0, intervals, residuals, matched negative controls, and sensitivity to lag assumptions. Do not claim "2026's growth was prior investment payback" unless alternative explanations are tested and source quality supports it.

## 6. Testing the 5–10× parameter and 2–3× capability scenarios

Two independent hypotheses may coexist:

- $H_P$: a future *specific, versioned model's* total trainable parameters could be 5–10× a stated 2026 baseline under a declared architectural continuation scenario.
- $H_C$: measured domain-specific horizons, reliability or frontier task difficulty may have 2–3× improvement under specified frozen evaluation budgets and task distributions.

Test $H_P$ using explicitly disclosed, auditable total/active model parameter counts. Total parameters and per-token active parameters must remain separate. Secret counts may be bounded conditionally using FLOPs/Token/MoE assumptions but **cannot** be treated as observed values.

Test $H_C$ separately, through preregistered tasks and audited results. A single domain improving 2.5× does not license a universal cognitive capacity multiplier. The research should publish a multidimensional vector and Pareto frontiers instead of inventing a global intelligence index.

**Stable interval test:** If repeated measured domain horizons fail to improve substantially while directly measured resource budgets continue increasing, evaluate evidence for diminishing marginal returns. The same observation could also result from evaluation saturation, different benchmark samples, reduced per-response budget, new safety policies or use of added hardware for wider serving; these counter-hypotheses must be checked.

## 7. Adaptive updating and validation

- **Capture:** immutable source observations with publication, ingestion and effective timestamps; source hashes and original licensing.
- **Measure:** freeze task protocols; log attempts; validate success and compute H50/H80 only where identifiable.
- **Calibrate:** fit each hypothesis on past *issued* data, not retrospective projections pretending they were issued before outcomes.
- **Backtest:** expanding-window prequential forecast; include a naïve no-change baseline, error intervals, negative results and observed-vs-predicted residuals.
- **Drift:** when two or more independent out-of-sample periods miss every current hypothesis beyond a preregistered threshold, flag review of structural alternatives, but never silently rewrite a committed forecast.
- **Publish:** source SHA-256, model identity and task-set hash, CI failures, missing data, held-out coverage, known methodology change points.

Current v0.5 gives a working *task-horizon measurement layer*. It **does not yet implement** the full causal lag regression or the permanent real-world, source-verified task trial acquisition system. Future integration is blocked until sufficient data exist.

## 8. Executable v0.5

The GitHub repository includes synthetic examples to exercise the estimator:

~~~bash
python -m unittest discover -s tests -v

python -m fsl_timecourse.horizon_cli estimate \
  --input tests/fixtures/synthetic_horizon_baseline.json \
  --as-of 2026-11-07

python -m fsl_timecourse.horizon_cli compare \
  --baseline tests/fixtures/synthetic_horizon_baseline.json \
  --candidate tests/fixtures/synthetic_horizon_candidate.json \
  --as-of 2026-11-07
~~~

In these fabricated tasks, the 50%-horizon ratio happens to be around 2.6×. **This is a program test, not an observation about a named real AI model.** User-facing products, task scopes, and human time estimates were not actually evaluated in these fixtures.

Code: `fsl_timecourse/horizon.py` and `fsl_timecourse/horizon_cli.py`. Original software and documentation are Apache-2.0. Neither the Arena CC BY 4.0 dataset nor METR's underlying material is relicensed by this work.

## Primary methodological references

1. METR, Task-Completion Time Horizons of Frontier AI Models: https://metr.org/time-horizons/
2. METR / Kwa et al., Measuring AI Ability to Complete Long Tasks: https://arxiv.org/abs/2503.14499
3. Arena, historical leaderboard and methodology notes: https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset
4. Epoch AI, Data on AI Models, sourced estimates and confidence classification: https://epoch.ai/data/ai-models
