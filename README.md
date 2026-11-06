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
python -m fsl_adaptive.cli forecast --year 2030 --include-planned --persist \
  --target my-public-comparable-model-series --target-class observational
python -m fsl_adaptive.cli feedback --event real_later_disclosure.json
python -m fsl_adaptive.cli weights --as-of 2030-01-31
~~~

**Do not calibrate from the repository's synthetic example**, and do not invent a disclosure for a closed model. Feedback needs a matched public baseline and new-model source. A hypothesis's probability-like weight is only an online relative loss weight, not a calibrated probability.

## What adaptive actually means in v0.2

- Each scenario carries deployment lag, maturity timescale, model-release lag, compute elasticity, hypothesized parameter ceiling, and efficiency yield.
- Alternative scenarios receive equal initial weights.
- Only later, published, independently sourced parameter multiplier feedback can update those weights.
- Updates use robust log error and prevent one outlier from assigning zero weight to every alternative.
- Consecutive large misses set a **drift alert** rather than silently relabeling a forecast.
- Immutable SQLite \`evidence_events\`, \`forecasts\`, \`feedback\` preserve history; no UPDATE/DELETE on those records.
- \`as_of\` excludes facts that were not published or recorded by the cutoff, including future-effective revisions.
- Planned and built facilities are **never interchangeable**; independently disconnected campuses do **not** become a single training supercomputer by addition.

**Current limit:** the hypothesis family is not autonomously regenerated yet; drift triggers an explicit research review. There is no built-in live scraping job or automatic verification of cited sites.

## Evidence & scientific boundaries

\`data/adaptive_scenarios.json\` is intentionally labeled **SYNTHETIC**; its projected site capacities and accelerator upgrades are not claims about any named company.

This project does not infer ability from model parameter ratios, and it does not treat model release cadence as training cadence. Real sourced measurements, benchmark controls and forward validation are necessary before making quantitative claims about industry trajectories.

See [v0.2 research protocol](docs/ADAPTIVE_RESEARCH_v0.2.md), [database design](docs/DATABASE.md), and [v0.1 protocol](docs/RESEARCH.md).

## License / 授權

Copyright 2026 EveMissLab contributors. The original software and documentation in this repository are licensed under **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The project does not relicense or claim ownership of linked third-party source documents, model names, brands, data or trademarks.
