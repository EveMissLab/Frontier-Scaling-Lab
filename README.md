# Frontier Scaling Lab

**An open, falsifiable research engine for frontier AI scaling.**  
**開源研究：從公開硬體、數據中心、模型揭露與時間序列，建立可重算的條件式估算與自適應假說。**

[License: Apache-2.0](LICENSE) · [Adaptive research / 自適應研究](docs/ADAPTIVE_RESEARCH_v0.2.md) · [Database protocol / 資料庫設計](docs/DATABASE.md)

## Research question / 研究問題

How much of a visible model improvement is delayed realization of prior compute/data investment? How might planned accelerator deployments affect future feasible parameter scale, and what evidence would signal a stable plateau or an architectural break?

**The project cannot reveal undisclosed GPT, Gemini, Claude, Grok or other proprietary parameters.** Public product generations are not a uniform sequence of training runs, parameter counts, or intelligence scores.

**Three separated targets:**
1. Infrastructure and hardware: announced → permitted → built → powered → GPUs installed → connected training capacity.
2. Model scale: achieved training compute and tokens → conditional active/total-parameter *envelopes*.
3. Effective capability: budget-matched, tool-controlled task performance. **Not estimated in v0.1 or v0.2.**

A *5–10x total-parameter* scenario and a *2–3x effective-cognition* hypothesis may coexist. Neither is a verified prediction today. v0.2 explicitly models release lag, hardware maturation and candidate parameter plateaus.

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
