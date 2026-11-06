# Frontier Scaling Lab

**An open, falsifiable research engine for frontier AI scaling.**  
**開源研究：從公開硬體、數據中心、模型揭露與時間序列，建立可重算的條件式估算與自適應假說。**

[License: Apache-2.0](LICENSE) · [Adaptive research / 自適應研究](docs/ADAPTIVE_RESEARCH_v0.2.md) · [Database protocol / 資料庫設計](docs/DATABASE.md)

## v0.8.3 — Time-aware evidence vintage / 時間與資料截止日鎖定

[**Canonical UTF-8 temporal study**](docs/TEMPORAL_VINTAGE_AND_ACCESS_v0.8.3.md) ·
[Official 2024/2026 source-date anchors](data/verified_release_and_price_vintage_2026-11-07.json)

An AI-era comparison without dates is not scientifically interpretable.
v0.8.3 records separate:
- **Event / effective calendar date**: e.g., a model launch, price quote, tool
  availability change, or the shutdown of a specific old model snapshot.
- **Original publisher date**: when a source publicly claimed an event.
- **First FSL capture date**: when *this study* first actually retrieved it.
- **Real task instants**: timezone-aware goal freeze, start, last progress,
  finish, acceptance, and evidence capture, preserving local +08:00 and UTC.

The first verified publisher-date anchors (2024-05-13 OpenAI GPT-4o,
2024-06-21 Anthropic Claude 3.5 Sonnet and launch-price quote,
2026-10-23 legacy GPT-4o API shutdown) were **first catalogued by FSL in
Taiwan on 2026-11-07**. Their presence today does not establish they were
observed by this study in 2024, and the 2024 API price is not silently
carried into 2026.

The new time-anchored economics adapter requires an exact model/runtime
identity and a time spine for **every attempt** (including failed/censored),
with no future observations past its declared cutoff. Full Agent autonomy,
task correctness, subscription quotas and accepted product quality still
require separate independent evidence.

~~~bash
python -m unittest discover -s tests -v

python -m fsl_economics.timeaxis_cli audit-sources \
  --catalog data/verified_release_and_price_vintage_2026-11-07.json \
  --as-of 2024-05-13 --mode strict_known_at_time

python -m fsl_economics.timeaxis_cli audit-sources \
  --catalog data/verified_release_and_price_vintage_2026-11-07.json \
  --as-of 2024-05-13 --mode retrospective_reconstruction

python -m fsl_economics.timeaxis_cli audit-panel \
  --file tests/fixtures/time_anchored_task_panel_synthetic.json
~~~

All task times in these examples are **synthetic**, not evidence of 24–48h
successful autonomous Agent work. Every generated report includes its
actual UTC and Asia/Taipei generation timestamps; publisher-only dates
remain day-precision and are never made into invented midnight UTC instants.

---

## v0.8.2 — Effective Task Purchasing Power / 同期跨 AI 與歷史反事實成本

[**Canonical v0.8.2 UTF-8 research document**](docs/EFFECTIVE_TASK_PURCHASING_POWER_v0.8.2.md) ·
[Historical source directory](data/historical_source_catalog_2026-11-07.json)

We now distinguish:
- **Same era, matched task**: frontier and nonfrontier models, plus different
  Free/Plus/Pro/Claude/API/local access paths, compared under a shared task,
  quality gate, source window and declared budget.
- **Effective task purchasing power**: reported accepted functional outcomes
  per explicit allocated USD, including retry failures and keeping full monthly
  cash obligation distinct from optional subscription allocation.
- **Actual historical observation**: dated, sourced attempts that really
  happened in their original era.
- **Modern replay of a legacy model**: a new experiment with today's runtime,
  hardware and price, **not** what a user could buy at the original release.
- **Historical counterfactual**: tool availability, model release, price vintage,
  and probability assumptions; outputs a conditional cost range only when
  all required inputs are given. Unknown => not identifiable; unbuilt historical
  prerequisites => not feasible.

No source has been verified by the comparator itself; synthetic fixtures cannot
become a real provider ranking or a measured 24/48-hour Agent outcome.

~~~bash
python -m unittest discover -s tests -v
python -m fsl_economics.cli compare \
  --input tests/fixtures/task_purchasing_power_synthetic.json \
  --output reports/contemporaneous_synthetic.json
python -m fsl_economics.cli history \
  --input tests/fixtures/historical_task_cost_synthetic.json \
  --output reports/historical_counterfactual_synthetic.json
~~~

**This does not manufacture old-model success rates or retrofit today's API
rates to historical dates.** Cross-time gains can be evaluated only with true
historical evidence, faithfully replayed legacy models or openly conditional
assumptions. Differences in a high-priced tier's quota and the model's
intrinsic task capability are independent hypotheses.

---

## v0.8.1 — Long-running Agent access, subscriptions and actual costs

[**Canonical v0.8.1 cost/allowance research source**](docs/AUTONOMY_ACCESS_AND_COST_v0.8.1.md) ·
[Official plan cohort snapshot](data/access_plan_reference_2026-11-07.json)

**A working 24–48-hour Agent requires a real access path, adequate usage
allowance, sufficient cash, effective checkpoint recovery and an independently
accepted result.** A higher-tier subscription can enable earlier demonstrations
because it offers more capacity, but it never proves the underlying model is
inherently more intelligent or guarantees 48 hours.

The new immutable cost ledger separates:
- actual USD monthly subscription cash outlay from amortized experiment allocation;
- included plan credit consumption (NOT new cash) from purchased usage credits;
- separately billed API tokens, cache rates, tools and local GPU/cloud compute;
- real elapsed calendar time from overlapping active work windows and quota downtime;
- recorded account entitlement from **unknown, never inferred** plan token limits;
- experimental spend from cost per *independently accepted* final result.

~~~bash
python -m unittest discover -s tests -v
python -m fsl_affordability.cli analyze \
  --file tests/fixtures/affordability_synthetic_48h.json
~~~

The illustrated 48-hour Pro-200 example is **synthetic**, not an observed
subscription invoice, completed long-running Agent mission, or proof that
any named tier can sustain 24–48 hours uninterrupted. Plan pricing and
feature availability can change; 2026-12 announced shared ChatGPT/Codex
allowances must be captured with an exact experimental date.

---

## v0.8 — Blind dynamic goal adaptation (G2) / 盲式適應干預

This phase extends the **functional completion** goals rather than replacing
them with short-test scores. It measures whether a continuing AI understands
**when to change its strategy, when to maintain it, and when to clarify or
escalate**, then genuinely completes the user's latest goal.

[Canonical UTF-8 v0.8 research protocol](docs/BLIND_DYNAMIC_GOAL_ADAPTATION_v0.8.md) ·
[Latest real first-party GitHub evidence observer](.github/workflows/observatory-pilot.yml)

- An independent evaluator **seals** a hidden, case-specific oracle before
  a user/environment perturbation occurs. Its scenario context, expected action,
  final-goal hash, and random nonce are sealed as one SHA-256 commitment.
- No universal rule maps every goal change to replanning; one goal change
  might appropriately leave the current strategy intact. Four scenario
  categories and four alternative actions are measured separately.
- An experimental case includes a fixed completion deadline. The AI's
  recorded decision must refer to that change, occur in time, and be
  irrevocably attached before the evaluator reveals any answers.
- Final credit additionally requires externally claimed success of the
  **latest user goal**, the G1 continuation prerequisite, and actual artifact
  hash receipts (v0.7). No internal record automatically certifies completion.
- A bounded **Agent JSONL intake** accepts only its own actions: progress,
  checkpoint, strategy, deliverable, runtime change and physical task switch.
  It cannot write user intentions, evaluator success claims or hidden oracles.

~~~bash
python -m unittest discover -s tests -v
python -m fsl_interventions.cli --db reports/g2_synthetic.sqlite synthetic-demo \
  --file tests/fixtures/g2_intervention_synthetic.json \
  --as-of 2026-01-18T00:00:00Z \
  --output reports/g2_synthetic_result.json
~~~

The provided simulated "16 days" of AI work, reviewers and final application
are FICTIONAL software regression inputs. The synthetic demonstration cannot
confirm real long-duration autonomy, world-class apps, or Agent cognition.
The experiment's hidden nonce and oracle label for a real study must never
be included in public repos or shared with the tested model.

The original G1–G4 digital and E1 embodied goals remain primary. In particular,
**only G2 is dependent on G1**, while G3/G4 can be achieved independently.

---

## v0.7 — Functional Mission Observatory / 真實任務證據觀測層

**The functional G1–G4/E1 targets remain primary.** This version observes
the execution trails of existing Agents and engineering repos; it does not
invent a new AI learner or compress outcomes into an intelligence number.

The new read-only source layer checks official GitHub commit SHA / CI run
metadata / artifact presence and computes actual local file hashes. It
links only compatible receipts to immutable v0.6 mission events, preserves
what was known as-of each UTC timestamp, and reports missing source proofs.

**First live first-party pilot succeeded:** the observer captured the
project's actual GitHub commit, its Actions-run metadata and the SHA-256
of local README bytes. This is evidence of source existence, *not* of
autonomous days-to-months of work or finished AAA game quality.

~~~bash
python -m unittest discover -s tests -v

python -m fsl_observatory.cli --db reports/mission.sqlite init
python -m fsl_observatory.cli --db reports/mission.sqlite session \
  --id fsl-observe-001 --project EveMissLab/YourProject

python -m fsl_observatory.cli --db reports/mission.sqlite github-commit \
  --session fsl-observe-001 --repo EveMissLab/YourProject --sha EXACT_COMMIT_SHA

python -m fsl_observatory.cli --db reports/mission.sqlite local-file \
  --session fsl-observe-001 --root . --path README.md

python -m fsl_observatory.cli --db reports/mission.sqlite audit \
  --session fsl-observe-001
~~~

For mission-linked experiments, preregister the v0.6 mission spec/run first,
then attach real receipts using the supported event link roles; see
[**canonical v0.7 observatory protocol (UTF-8 MD)**](docs/FUNCTIONAL_OBSERVATORY_v0.7.md).
The database must persist in an actual Agent environment across dates;
an ephemeral GitHub Actions run alone cannot measure a months-long mission.
CI success and file hashes never certify product functionality by themselves.

[Live first-party pilot workflow](.github/workflows/observatory-pilot.yml) ·
[Functional source standard v0.6](docs/FUNCTIONAL_FRONTIER_v0.6.md)

---

## Primary research target — FSL v0.6 functional frontier / 功能性智能完成度

**The primary measurement is no longer a short-task or METR-style H50/H80 time
horizon.** The user-defined upper-target framework evaluates genuine multi-day,
multiweek and multi-month **start-to-finished-outcome** autonomy (G1); knowing
**when to revise, maintain, clarify or escalate** strategies to satisfy a changing
user goal (G2); creation in **one/few user instruction rounds** of fully functional,
world-class games or high-value apps (G3); and both personal-author and distinctive
AI-native creative style in finished artistic works (G4).
**Only G2 depends on G1. G3 and G4 are independent functional end-state goals.**

**Embodied adaptive intelligence (E1) is a separate track**, requiring a single
physical AI system to recognize and switch between multiple real task categories,
with safety gating. It does not inherit the digital AAA-game standard. The
specific original reason for the user's lower embodied completion threshold is
not assumed by this implementation.

Original theory and operative requirements:
[**FSL v0.6 — Functional Frontier, canonical UTF-8 Markdown**](docs/FUNCTIONAL_FRONTIER_v0.6.md).

This repository includes a first **append-only event and assessment schema**:
system identity and runtime changes, persistent checkpoints/recovery, user goals,
strategy decisions with change/no-change controls, human assistance, real output
artifacts and independent product/style evaluations. It can *audit recorded
claims*, not independently prove that a months-long system ran or produced an
actual AAA game.

~~~bash
python -m unittest discover -s tests -v
python -m fsl_functional.cli --db reports/functional_demo.sqlite init
python -m fsl_functional.cli --db reports/functional_demo.sqlite ingest-example --file tests/fixtures/functional_game_synthetic.json
python -m fsl_functional.cli --db reports/functional_demo.sqlite audit --run-id synthetic-game --as-of 2026-02-07T00:00:00Z
~~~

The bundled game/robot mission logs are **fictitious synthetic test data**:
no real weeks/months of AI activity, gameplay build, artwork or robot has been
verified. The output explicitly refuses empirical certification. The older
v0.5 H50/H80 module remains available as an *optional secondary diagnostic*,
not as the ceiling definition.

---

## Research question / 研究問題

How much of a visible model improvement is delayed realization of prior compute/data investment? How might planned accelerator deployments affect future feasible parameter scale, and what evidence would signal a stable plateau or an architectural break?

**The project cannot reveal undisclosed GPT, Gemini, Claude, Grok or other proprietary parameters.** Public product generations are not a uniform sequence of training runs, parameter counts, or intelligence scores.

**Three separated targets:**
1. Infrastructure and hardware: announced → permitted → built → powered → GPUs installed → connected training capacity.
2. Model scale: achieved training compute and tokens → conditional active/total-parameter *envelopes*.
3. Effective capability: budget-matched, tool-controlled task performance. **Not estimated in v0.1 or v0.2.**

A *5–10x total-parameter* scenario and a *2–3x effective-cognition* hypothesis may coexist. Neither is a verified prediction today. v0.2 explicitly models release lag, hardware maturation and candidate parameter plateaus.

## v0.5: actual task-horizon measurement protocol

[Measurement research note](docs/MEASUREMENT_PROTOCOL_v0.5.md)

**Separate** (1) the public compute/parameter *scenario* (v0.2),
(2) descriptive Arena/benchmark measurement and method drift (v0.3–0.4),
and (3) controlled **task completion** (v0.5).

The v0.5 pure-Python estimator fits a binomial logistic task-success curve
against the **human-expert task duration**, reporting H50/H80 only inside the
observed difficulty range. It preregisters task-set hashes, exact model
revisions, scaffold, prompt/tool hashes, and fixed per-task token/time/cost caps.
It uses task-level bootstrap resampling and refuses incompatible comparisons.

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

**The bundled trials are synthetic, not evaluated frontier models.** A 2–3×
task-horizon ratio in synthetic tests is *not* 2–3× general intelligence.
The v0.5 module does **not** infer hidden parameter counts, training
start dates or a causal hardware-payback lag. These remain separately
auditable investigations, subject to actual task and hardware evidence.


## v0.4: methodological timecourses + reproducible historical control

[Full v0.4 research note](docs/LONGITUDINAL_MEASUREMENT_v0.4.md) ·
[Historical Arena source workflow](.github/workflows/arena-parquet-history.yml)

The first audited historical example contains **190 publication dates**
(2024-08-28 through 2026-10-15) for the exact public model label
`gpt-4o-2024-05-13`, Arena `text_style_control` / `overall`.
The source Parquet bytes and SHA-256 are recorded; source license is **CC BY 4.0**.

It is a **measurement negative control**, not a reconstruction of GPT-4o
weight changes. Fixed model labels can show fluctuating ratings while their
reported vote counts stay unchanged. We therefore block naive inferences
across known Arena methodology changes, including the 2025-05-16 style-control
shift and 2025-07-23 frequency reweighting.

The large `/filter` and `/search` dataset viewer queries returned HTTP 500
on the original historical run. The working implementation uses the official
**Parquet** index, bounded downloads and a local DuckDB projection into
append-only SQLite. This optional dependency is installed only in the
historical retrieval workflow.

~~~bash
python -m fsl_timecourse.cli method-breaks
python -m fsl_timecourse.cli --db reports/arena_parquet.sqlite readiness
python -m fsl_timecourse.cli --db reports/arena_parquet.sqlite series \
  --model-id arena:gpt-4o-2024-05-13 \
  --measure arena_rating --category overall \
  --methodology arena-dataset:text_style_control:arena_rating \
  --channel preference --mode retrospective --as-of 2026-11-06

python -m scripts.report_arena_timecourse \
  --db reports/arena_parquet.sqlite \
  --model gpt-4o-2024-05-13 \
  --config text_style_control --as-of 2026-11-06
~~~

Also new: `fsl_timecourse/controlled.py` preregisters exact task sets,
scoring, budgets and model/Agent modes in immutable SQLite tables.
Its **capability vector** returns per-domain task success changes without
collapsing them to one general intelligence multiplier. It does not yet
contain independently verified real-world controlled evaluations.

See [v0.4 measurement protocol](docs/LONGITUDINAL_MEASUREMENT_v0.4.md).
The v0.3 317 cross-sectional observations and v0.4 190 historical dates
are *different statistical units*; do not add them as independent models.


## v0.3: Hugging Face + Arena + benchmark + anonymous user-experience evidence

New **source-observation layer**: open-weight metadata, Arena leaderboard history,
HF official benchmark submissions, and manually curated *aggregate-only* community
feedback. Evidence is append-only in the **same SQLite database** as v0.2, but
ratings and subjective experiences can never be mistaken for model parameter
disclosures or inserted into the parameter-inversion calibration table.

~~~bash
python -m fsl_sources.cli init
python -m fsl_sources.cli arena-splits
python -m fsl_sources.cli hf-model --id Qwen/Qwen3-0.6B
python -m fsl_sources.cli arena --config text --split latest --offset 0 --limit 100
python -m fsl_sources.cli arena --config agent --split latest --limit 100
python -m fsl_sources.cli hf-benchmark --dataset SWE-bench/SWE-bench_Verified
python -m fsl_sources.cli observations --channel preference --limit 40
~~~

The above live commands require network access and are **not** automatically run
by CI. Rate limits, dataset attribution, source terms, units, and methodology
changes are observed. For use with no network, see the fabricated examples
in tests/fixtures and the accompanying instructions.

Read [v0.3 public evidence protocol](docs/PUBLIC_EVIDENCE_v0.3.md)
for dataset licenses, the 100-row paginated Arena API, data schema, feedback
privacy protections, identity crosswalk, and strict as-of leakage guards.

**Public evidence refresh:** the repository also has a separate read-only
[weekly workflow](.github/workflows/public-evidence-refresh.yml) (Monday
03:19 UTC, or manual dispatch). It fetches one Hugging Face model, the latest
Arena text/agent pages and a bounded SWE-bench leaderboard sample.
The normalized SQLite file and retrieval manifest are uploaded as GitHub
Actions artifacts, retained for **90 days**. This workflow does not push
third-party results or user content into source control. Researchers should
archive important observations in a durable, licensed dataset before
these temporary workflow artifacts expire.

**Do not multiply a leaderboard score by a parameter count** to invent a
universal cognition score. Model parameter ratios, user preferences and
task benchmarks stay independent until a controlled longitudinal study
supports combining them.


## Two compatible runnable modules

### v0.1: physical compute/parameter interval engine

Python 3.11+; no external runtime packages.

~~~bash
python -m unittest discover -s tests -v
python frontier_scaling.py forecast --scenario rubin_100mw_reference --as-of 2026-11-06
python frontier_scaling.py forecast --scenario planned_campuses_2028 --include-unbuilt
~~~

The NVIDIA 100 MW/40,000 Rubin-GPU number in v0.1 is a **vendor reference design, not a live 100 MW deployment**:
https://www.nvidia.com/en-sg/data-center/vera-rubin-nvl72/

Other initial v0.1 inputs are explicitly research assumptions.

### v0.2: delayed-payback adaptive engine + immutable SQLite registry

~~~bash
# Establish an append-only local SQLite registry.
python -m fsl_adaptive.cli init

# Observational inputs are absent by default, so this is a SYNTHETIC example.
python -m fsl_adaptive.cli forecast --year 2029 --include-planned --output reports/demo_2029.json

# For operational-only scenarios, omit --include-planned.
python -m fsl_adaptive.cli forecast --year 2029

# Inspect the online hypothesis weights (uniform until later real disclosures).
python -m fsl_adaptive.cli weights --as-of 2026-11-06

# Preview which source-backed facts were known at a historical date.
python -m fsl_adaptive.cli snapshot --as-of 2026-11-06
~~~

To register a cited new fact, create an event JSON as described in [docs/DATABASE.md](docs/DATABASE.md), then:

~~~bash
python -m fsl_adaptive.cli ingest --event my_evidence.json
python -m fsl_adaptive.cli forecast --year 2030 --include-planned --as-of 2026-11-06
~~~

A persisted observational forecast is immutable and can be scored against *later, independently sourced, comparable* model parameter disclosures:

~~~bash
python -m fsl_adaptive.cli forecast --config my_verified_observational_config.json \
  --year 2030 --include-planned --persist \
  --target my-public-comparable-model-series --target-class observational
python -m fsl_adaptive.cli feedback --event real_later_disclosure.json
python -m fsl_adaptive.cli weights --as-of 2030-01-31
~~~

**For observational forecasts:** the separate configuration must declare `data_classification=observational`, contain a sourced baseline, and cite each currently operational cohort. The included synthetic file is blocked from that path.

**Do not calibrate from the repository's synthetic example**, and do not invent a disclosure for a closed model. Feedback needs a matched public baseline and new-model source. A hypothesis's probability-like weight is only an online relative loss weight, not a calibrated probability.

## What adaptive actually means in v0.2

- Each scenario carries deployment lag, maturity timescale, model-release lag, compute elasticity, hypothesized parameter ceiling, and efficiency yield.
- Alternative scenarios receive equal initial weights.
- Only later, published, independently sourced parameter multiplier feedback can update those weights.
- Updates use robust log error and prevent one outlier from assigning zero weight to every alternative.
- Consecutive large misses set a **drift alert** rather than silently relabeling a forecast.
- Immutable SQLite `evidence_events`, `forecasts`, `feedback` preserve history; no UPDATE/DELETE on those records.
- `as_of` excludes facts that were not published or recorded by the cutoff, including future-effective revisions.
- Planned and built facilities are **never interchangeable**; independently disconnected campuses do **not** become a single training supercomputer by addition.

**Current limit:** the hypothesis family is not autonomously regenerated yet; drift triggers an explicit research review. There is no built-in live scraping job or automatic verification of cited sites.

## Evidence & scientific boundaries

`data/adaptive_scenarios.json` is intentionally labeled **SYNTHETIC**; its projected site capacities and accelerator upgrades are not claims about any named company.

This project does not infer ability from model parameter ratios, and it does not treat model release cadence as training cadence. Real sourced measurements, benchmark controls and forward validation are necessary before making quantitative claims about industry trajectories.

See [v0.3 public evidence protocol](docs/PUBLIC_EVIDENCE_v0.3.md), [v0.2 research protocol](docs/ADAPTIVE_RESEARCH_v0.2.md), [database design](docs/DATABASE.md), and [v0.1 protocol](docs/RESEARCH.md).

## License / 授權

Copyright 2026 EveMissLab contributors. The original software and documentation in this repository are licensed under **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The project does not relicense or claim ownership of linked third-party source documents, model names, brands, data or trademarks.
