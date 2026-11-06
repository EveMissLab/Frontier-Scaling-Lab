# FSL v0.2 — 延遲實現、硬體世代、參數平台與自適應更新

Date: 2026-11-06
Status: engineering prototype; **not** a proprietary-model disclosure.

## I. Core hypothesis

Observed model capability in a given calendar year is not the direct product of that year's new GPU purchases. It can depend on older data-center commissioning, accelerator supply, topology tuning, data preparation, pretraining, post-training, inference budget, and Agent/tool integration. Capacity announcements, live deployment, model development, public release, and user-perceived gains are different clocks.

**H-LAG:** earlier infrastructure investment may yield a delayed capability/payback period.
**H-PLATEAU:** under a substantially continuous architecture, parameters and/or capability may encounter diminishing marginal gains.
**H-EXPAND:** next-gen accelerator deployments could permit much larger total weights, potentially an illustrative 5–10x parameter envelope.
**H-DECOUPLING:** 5–10x weights is not 5–10x effective cognition. A 2–3x capability scenario is separately testable.

These are alternative hypotheses. None is verified by the public disclosure of a building or a product release label.

## II. Release clock caution

Official publication landmarks:

- OpenAI GPT-4o: 2024-05-13, https://openai.com/index/hello-gpt-4o/
- OpenAI GPT-5: 2025-08-07, https://openai.com/index/introducing-gpt-5/
- OpenAI GPT-6 Astra: 2026-09-03, see https://openai.com/research/index/release/

The dates do not constitute training starts, end dates, parameter disclosures, or uniform generation increments. GPT-5 described a system including model routing, so a product label is not synonymous with one fixed-size model. The series is not sufficient on its own to recover the compute-to-parameter multiplier.

## III. Model implemented in v0.2

For a hardware cohort $i$, its *conditional* available compute is:

$$
H_i(t)=G_i P_i f_i m_i(t)
$$

where $G_i$ is the scenario GPU count, $P_i$ the precision-compatible assumed FLOP/s per GPU, $f_i$ the assumed connected fraction, and $m_i$ a maturation factor. This implementation uses:

$$
m_i(t)=0.5+0.5(1-e^{-a_i/\tau})
$$

where $a_i$ is years since the conditional ready date; if $a_i<0$, the cohort is ineligible. The half-at-launch starting factor is an illustrative research assumption, **not** an empirical hardware law.

Planned construction is excluded unless the user explicitly enables `--include-planned`. Each hypothesis can specify commissioning delay and a *separate* model-release lag. The active training capacity is **the largest eligible connected site**, not the sum of all geographically distributed GPUs. This intentionally produces a restrictive envelope until verified cross-site training fabrics can be incorporated.

The release-lag adjusted hardware time is $t-\ell$. With $H_0$ at the baseline date, the resource ratio is:

$$
R_H(t)=H_{\max}(t-\ell)/H_{\max}(t_0)
$$

The model has distinct scenario parameters: a parameter-vs-compute elasticity $\alpha$, an assumed annual algorithmic yield $g$, and a conjectural ceiling $M$. First define:

$$
R_U(t)=R_H(t)^\alpha(1+g)^{t-t_0}
$$

Then a smoothly saturating **scenario parameter multiplier** is:

$$
R_P(t)=1+(M-1)(1-e^{-\max(0,R_U(t)-1)/(M-1)})
$$

This saturation is *chosen for stress testing*, not learned as a physical law, and the limits 5/8/10 are scenario inputs, not empirical discoveries. A future measured value beyond every limit should trigger drift review and a new hypothesis family, not quiet truncation of evidence.

No equation here predicts generalized cognition. A multidomain, budget-matched evaluation system is a distinct future layer.

## IV. Online revisions

Each candidate hypothesis $i$ starts with an equal weight; only **independently sourced, subsequently published** parameter ratios may update it. For a known outcome $y$, use a robust logarithmic loss comparing $y$ with that hypothesis's archived prediction $\hat y_i$:

$$
L_i=\operatorname{Huber}(|\ln(y/\hat y_i)|)
$$

The current code uses a multiplicative update with learning rate 0.6 and a 1% uniform mixture to avoid irrevocably eliminating a hypothesis. These weights are relative model-selection heuristics, **not** calibrated probabilities that a company uses a particular architecture.

A drift alert is raised if two consecutive disclosed outcomes miss *all* hypotheses by more than a 2.5x multiplicative factor. The mechanism flags structural inadequacy; it does not assert a new architecture or silently invent a physical deployment.

Actual model disclosures are currently missing from the sample registry. Therefore initial weights remain uncalibrated and no "5–10x is likely" claim is made.

## V. Temporal rules and leakage prevention

Facts must have stable event IDs, published_on and recorded_on dates, source classification and an optional effective date. At date $t$, the database materializes only facts published and recorded no later than $t$. Retractions are new events, never deletions.

A forecast receives a deterministic content hash and may be persisted as an immutable snapshot. A later disclosure can update hypotheses only if it was published after that forecast's issue date and recorded by the new scoring cutoff. Duplicate forecasts about the same later target are de-duplicated during learning.

*Warning:* manual source submission does not verify authenticity. A genuine research-quality observation needs independent checking of the source page, unit conversion, release type, baseline, and whether the model series is comparable. Synthetic examples cannot enter the training feedback path.

## VI. Database v0.2 and intended v0.3

Implemented now in SQLite:
- **evidence_events**: entity/field, value, unit, source, publication, recording, effective date, supersession, SHA-256. UPDATE/DELETE blocked.
- **forecasts**: immutable issued prediction including configuration/input hash, hypothetical target key and scenario variants.
- **feedback**: later sourced parameter-multiplier disclosure referring to a saved forecast. UPDATE/DELETE blocked.

Recommended normalized extensions in M2/M3:
- `source_document`: URL, published_at, fetched_at, source hash, original excerpt, edition.
- `facility` / `campus` / `building`: stable non-interchangeable IDs and geography.
- `grid_interconnect`: requested MW, contracted MW, energized MW, date/time.
- `hardware_sku` and `deployment_batch`: precision, theoretical vs actual throughput, shipment vs installation.
- `compute_partition`: locally connected GPUs, interconnect topology, dedicated training allocation, MFU distribution.
- `training_run`: estimated epoch, reported vs inferred tokens, architecture family, training fractions.
- `model_release`: public release, model weights disclosure, token cost, benchmark configuration.
- `evaluation_trial`: inference budget, tools/agents, tasks, scoring, repetition, provenance.
- `forecast_revision`: algorithm/config hash, as-of, data lineage, residual and structural-change alerts.

**Never add campus MW, buildings, racks and accelerator counts as if they shared units.** A planned project is not a live GPU; total model parameters are not activated parameters; parameters are not a general intelligence score.

## VII. Execution

Python 3.11+ and SQLite bundled in the standard library:

~~~bash
python -m unittest discover -s tests -v
python -m fsl_adaptive.cli init
python -m fsl_adaptive.cli forecast --year 2029 --include-planned --output reports/example_2029.json
python -m fsl_adaptive.cli forecast --year 2029 --include-planned --persist --target my-research-series --target-class observational
python -m fsl_adaptive.cli weights --as-of 2026-11-06
~~~

The second command is purely synthetic until true site/model evidence is registered. An observational target must have real sourced baseline and outcomes before its weights have scientific meaning.

An event can be appended with `python -m fsl_adaptive.cli ingest --event file.json`. A *verified* later model outcome can be appended using `python -m fsl_adaptive.cli feedback --event disclosure.json`. Sample source schema appears in docs/DATABASE.md.

This project is not an automated crawler and does not periodically claim to have gathered data. These remain separately auditable ingestion tasks.

## VIII. Validation gates

Unit tests cover future hardware exclusion, single-site connectivity, temporal as-of, immutable forecasts, retractions, source requirements, later disclosure scoring, and drift detection.

Quality gates for publication:
1. Preserve the complete UTF-8 Markdown original with dollar-delimited LaTeX.
2. Preserve source URLs, units, original data timestamps and SHA256.
3. Run tests and issue forecast snapshot before outcome publication.
4. Do not relabel a hypothetical projection as an observed result.
5. Record negative results and discard no prior forecast version.

## References

- NVIDIA Vera Rubin official product/reference design: https://www.nvidia.com/en-us/data-center/technologies/rubin/
- NVIDIA Vera Rubin architecture: https://www.nvidia.com/en-sg/data-center/vera-rubin-nvl72/
- OpenAI GPT-4o release: https://openai.com/index/hello-gpt-4o/
- OpenAI GPT-5 release: https://openai.com/index/introducing-gpt-5/
- OpenAI GPT-6 releases: https://openai.com/research/index/release/
