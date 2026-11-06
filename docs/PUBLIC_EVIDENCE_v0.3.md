# FSL v0.3 — 公開模型、競技場與使用者體驗證據層

**Date:** 2026-11-06  
**Status:** executable public-source adapter + offline test fixtures; no real provider snapshots are committed by default.

## 0. Purpose and scientific separation

Frontier Scaling Lab historically estimates *conditional* compute and parameter ranges. This evidence layer provides **multiple distinct observable channels** that can later falsify or refine a growth hypothesis:

1. **Physical input:** data centers, interconnect, GPUs, energy capacity, training days.
2. **Model metadata:** publicly released weight files, source model cards and architecture descriptions.
3. **Preference:** human comparison ratings, category-specific Arena scores and uncertainty intervals.
4. **Benchmark:** task and agent evaluation, benchmark version, methodology and evaluation budget.
5. **Community:** coded anonymous aggregates of experience, not personally identifying anecdotes.

**Never conflate** model weights, active parameters, popularity, votes, benchmark scores, user preference and cognitive capability. An advertised model version or release date alone is not evidence of parameter changes.

For future parameter-inversion / capability-conversion research, maintain different calibration objectives and show uncertainty and missing controls. No universal "AI intelligence number" is assumed.

## 1. Official sources & acquisition

### Hugging Face Hub

Hub API: https://huggingface.co/docs/hub/api

Endpoint: GET https://huggingface.co/api/models/{namespace}/{model}

Example:

~~~bash
python -m fsl_sources.cli hf-model --id Qwen/Qwen3-0.6B
~~~

The importer stores the URL, API response SHA-256, retrieval date, model revision label, declared model license, and limited numeric fields such as likes, downloads and serialized safetensors elements. It **does not** download model weights.

**Caveats:**
- A safetensors element count may include multiple files or adapter weights; it is not guaranteed to equal a model's unique architectural parameter count.
- Quantization, tied weights, and expert routing mean total weights and activated parameters differ.
- Likes and downloads measure platform behavior, not competence.
- Repository card license values vary; unknown means **not** automatically permitted for redistribution.
- Hugging Face enforces API rate limits; follow published limits and avoid broad high-frequency scraping.

### Arena (Arena.ai / LMArena)

Official research release:
https://arena.ai/blog/arena-leaderboard-dataset

Published historical dataset:
https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset

Dataset card declares **CC BY 4.0**. Attribution: Arena, original dataset, snapshot version and publication date. That license is specific to the dataset and does not confer an Apache license on Arena's raw content.

Official Hugging Face Dataset Viewer:
https://huggingface.co/docs/dataset-viewer/rows

~~~bash
python -m fsl_sources.cli arena-splits
python -m fsl_sources.cli arena --config text --split latest --offset 0 --limit 100
python -m fsl_sources.cli arena --config text --split full --offset 0 --limit 100
python -m fsl_sources.cli arena --config agent --split latest --offset 0 --limit 100
~~~

- Use live splits to enumerate valid `config` names; do not assume the same arenas stay available forever.
- Each request reads at most **100 rows**, in accordance with the documented API maximum. Full history must be paginated and preserved with dated source records.
- Text/vision preference ratings and Agent Arena IPS score have **different units** and must stay separate.
- Arena scoring methods, category membership, style controls, and sample selection can change. Scores from different periods are not automatically comparable just because their column names are equal.
- Rank alone is especially unstable with a changing candidate pool; v0.3 stores scored metrics, sample sizes and CIs rather than treating ranks as stable capability multipliers.
- The program does not ingest raw battles, individual voters, personally identifying content, or prompts.

### Hugging Face official benchmark leaderboard API

Documentation:
https://huggingface.co/docs/hub/leaderboard-data-guide

Endpoint:
GET https://huggingface.co/api/datasets/{dataset_id}/leaderboard

Example:

~~~bash
python -m fsl_sources.cli hf-benchmark --dataset SWE-bench/SWE-bench_Verified
~~~

A submission appearing on a benchmark leaderboard is not automatic confirmation of independent replication. The endpoint provides the model ID, numeric value, metadata and a `verified` flag; v0.3 preserves that distinction. The numeric score unit remains **benchmark-defined** unless a verified benchmark-specific adapter is added.

Coding agent performance may include scaffolding, tools, prompts, cost and wall-clock resources. This cannot be attributed solely to base-model weights.

### Artificial Analysis, LiveBench and other evaluations

Candidate future connectors:

- Artificial Analysis: https://artificialanalysis.ai/data-api
  * Documented API needs a user-generated API key; attribution is required.
  * Free and commercial versions differ in request limits and **redistribution rights**.
  * No automatic scraping, no key committed to Git, and no API integration is asserted for v0.3.
- LiveBench: inspect official benchmark/repository license and release schema before implementing a versioned adapter.
- SWE-bench original leaderboards: keep task subset, agent scaffold, budget, test harness and time of evaluation.
- Other task-specific suites: favor primary sources with reproducible score provenance.

**The project Apache-2.0 license applies to its own software and documentation. Third-party datasets remain under their respective terms.**

## 2. User feedback without privacy or selection-bias confusion

Rather than mass-copying Reddit, community discussions or personal ChatGPT histories, v0.3 only accepts **manually sourced, consent-compatible, aggregated** experience counts.

Accepted input fields are exactly:

~~~json
{
  "external_model_id": "provider/model-id-with-version",
  "category": "coding_reliability",
  "counts": {"positive": 12, "neutral": 5, "negative": 8},
  "sampling_method": "opt_in_survey",
  "collected_on": "2026-11-06",
  "source_url": "https://example.org/published-aggregate-report",
  "source_license": "owner-confirmed-permission",
  "attribution": "Study / public aggregate owner",
  "sample_window_id": "study-wave-01"
}
~~~

Example schema only: the URL is **not** evidence of a real study. For an offline demonstration, use `tests/fixtures/community_synthetic.json`.

The importer calculates a positive fraction with Wilson interval, retains sample size and adds an explicit **selection-bias** flag. If the sampling method is self-selected, the interval does not justify claims about the general population. Neutral is included in the denominator.

No reviewer name, handle, contact, raw comment, full quote, conversation log, account identifier or personal health information is accepted. Personal text needs permission and separate privacy review; in this version it is deliberately excluded.

The community channel is **never** allowed into the v0.2 model-parameter feedback table. It can inform future external-validity studies only after rigorous study design.

## 3. Database extension (same local SQLite file)

Tables created by `fsl_sources.catalog.connect`:

- **public_snapshots**: external resource, retrieval/publication dates, attribution, original source license, raw-document SHA256 and notes.
- **public_observations**: external model ID, source snapshot, numerical measure, exact unit, channel, category, methodology, publication date, sample count, interval bounds and provenance flags.
- **public_aliases**: manually sourced, immutable cross-platform identity mapping. Conflicts are rejected instead of silently overwriting.

All three tables are append-only via SQLite triggers. Snapshots store **hashes and normalized numeric extracts**, not copyrighted raw documents or individual opinions. A same-day identical capture is idempotent; subsequent days remain independently dated.

The old `evidence_events`, `forecasts` and `feedback` remain untouched. The latter is reserved for independently verified later **parameter** disclosures, not popularity or Arena preferences.

To create the schema:

~~~bash
python -m fsl_sources.cli init
~~~

## 4. Model matching and as-of replay

A name like "Model X Fast" in Arena is not automatically equivalent to the HF repo "publisher/Model-X" or a commercial API deployment. Model aliasing requires an explicit source URL:

~~~bash
python -m fsl_sources.cli alias \
  --source-type hf_model --external-id hf:publisher/model \
  --canonical-key publisher:model:version --source-url https://example.org/source-evidence

python -m fsl_sources.cli alias \
  --source-type arena --external-id 'arena:Model X Fast' \
  --canonical-key publisher:model:version --source-url https://example.org/source-evidence
~~~

These are placeholders, **not** validated equivalences.

Then request separated evidence channels:

~~~bash
python -m fsl_sources.cli dossier \
  --canonical-key publisher:model:version --as-of 2026-11-06
~~~

For one exact methodology stratum:

~~~bash
python -m fsl_sources.cli trend \
  --model-id 'arena:Model X Fast' \
  --channel preference --measure arena_rating \
  --category overall \
  --methodology arena-dataset:text:arena_rating \
  --as-of 2026-11-06
~~~

A date-scoped result includes only data **published and retrieved** no later than the requested cutoff; this prevents treating a newly obtained retrospective dataset as evidence that the research engine had already observed months earlier.

Other series are strictly kept separate. No universal ranking or conversion scalar is produced.

## 5. Offline test fixtures and validation

~~~bash
python -m unittest discover -s tests -v

python -m fsl_sources.cli --db /tmp/fsl_sources.sqlite \
  --retrieved-on 2026-11-06 hf-model \
  --id synthetic/research-model \
  --offline-json tests/fixtures/hf_model_synthetic.json

python -m fsl_sources.cli --db /tmp/fsl_sources.sqlite \
  --retrieved-on 2026-11-06 arena --config text \
  --offline-json tests/fixtures/arena_synthetic.json

python -m fsl_sources.cli --db /tmp/fsl_sources.sqlite \
  --retrieved-on 2026-11-06 hf-benchmark \
  --dataset SWE-bench/SWE-bench_Verified \
  --offline-json tests/fixtures/hf_benchmark_synthetic.json

python -m fsl_sources.cli --db /tmp/fsl_sources.sqlite \
  --retrieved-on 2026-11-06 community \
  --file tests/fixtures/community_synthetic.json
~~~

All four files are **fabricated fixtures** and cannot be cited as external facts. Offline imported documents carry an unauthenticated-source warning.

The CI pipeline is intentionally fully offline and does not consume external API quotas. Live data import must be run intentionally by the operator, with original source terms, consent and provenance reviewed.

## 6. Next scientific milestone

M3: grounded multi-source **metric vector** and longitudinal capability conversion study:

- independently verify identity/version pairs;
- preserve benchmark versions, task budgets and evaluators;
- obtain comparable *real* weight/compute disclosures;
- measure effective ability changes in narrow task domains;
- test delayed-payback / saturation / architectural-shift hypotheses;
- conduct forward held-out validation and uncertainty calibration;
- publish negative outcomes alongside successes.

A public leaderboard can test the **behavioral side** of a scaling hypothesis, but alone cannot identify the number of hidden parameters that generated it.
