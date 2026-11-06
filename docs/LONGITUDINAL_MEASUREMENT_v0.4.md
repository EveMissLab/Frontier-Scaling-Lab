# Frontier Scaling Lab v0.4 — 歷史評分的測量中介與多維能力向量

Date: 2026-11-06 (source acquisition UTC), documentation revised 2026-11-07.
Status: implemented research software and controlled-evaluation schemas; **no causal estimate of cognitive growth**.

## 1. Research goal

The laboratory's target is not to count every AI release and claim "X times smarter."
It is to separate physical capacity, training investment, model parameters,
end-to-end Agent behavior, measured human preference, and controlled task success.

Hypotheses:
- H1 (delayed investment): compute/data/Agent investments become publicly visible at different later dates.
- H2 (capacity growth): future installed, mutually connected accelerators could support much larger models, conditional on deployment and training allocation.
- H3 (parameter plateau): within a relatively stable architecture, incremental useful returns may diminish.
- H4 (ability decoupling): total weights could grow 5–10x while some measured task capabilities rise much less, remain flat, or improve differently.
- H5 (measurement mediation): leaderboard scores can change without a change in one fixed model's weights.

None is established by a model release name. H4's "2–3x cognition" is a **research hypothesis**, not yet identified by the current dataset.

## 2. First historical negative control

Source: Arena official historical dataset (CC BY 4.0),
https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset

Access path: Hugging Face official Parquet endpoint; source file:
https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/resolve/refs%2Fconvert%2Fparquet/text_style_control/full/0000.parquet

Source Parquet SHA-256:
`669e6c2a2743bbbb0022b27b7f6b1ef2dcc9715428a41c927a4b9f281aba4aaf`

Captured UTC 2026-11-06. Exact model_name:
`gpt-4o-2024-05-13`, category `overall`, subset `text_style_control`.
**190 historical published dates, 2024-08-28 to 2026-10-15**.
The timestamp range is the dataset's publication history, not 190 newly conducted experiments.

| Conservative methodology regime | Dates | Observations | First-last rating delta | Same published count, score changed | Material count drop |
|---|---|---:|---:|---:|---:|
| Before style-control becomes default | 2024-08-28 to 2025-05-11 | 54 | +2.4324 | 2 | 0 |
| After style-control default, before reweighting | 2025-05-19 to 2025-07-17 | 14 | +19.4470 | 10 | 0 |
| After 2025-07-23 reweighting | 2025-07-25 to 2026-10-15 | 122 | +3.5466 | 114 | 1 |

The official Arena card documents method changes on 2024-01-09,
2025-05-16, 2025-07-23, and 2026-10-12 (agent bash signal).
This project conservatively divides the timeline by relevant dates instead
of asserting cross-regime equivalence.

**Specific comparison:** Between 2025-05-11 and 2025-05-19, the published
score moved by roughly +59.96, while the published vote count remained 117741.
This interval crosses the 2025-05-16 method change, so the movement is not
evidence that the fixed model gained +59.96 points of intrinsic capability.

There are many same-count/rating-change transitions, even within a single
methodology regime. A fixed reported count does **not** prove the ballot
population is identical, nor does a score difference establish an algorithmic
cause. It is an empirical warning against naive ability inference.

In the last regime, at least one large sample-count drop was flagged:
2025-09-08 to 2025-09-17 (117747 to 113568). This indicates another
comparability risk deserving a source-method audit.

## 3. Formal measurement decomposition

For model version $m$ and observation time $t$, define a score projection:

$$
S_{m,t} = F_t(W_m, D_t, V_t, O_t, B_t)
$$

Where $W_m$ denotes the evaluated model weights/system identity,
$D_t$ the task/input distribution, $V_t$ sampled human preferences,
$O_t$ the opponent pool or evaluation environment, $B_t$ the inference
budget, and $F_t$ the published scoring method.

The claim is **not** that this formula identifies any hidden factor.
Rather, a changed $S_{m,t}$ does not logically require a changed $W_m$.
A stable model label alone also does not prove immutable backend weights;
documentation and revision matching are still necessary.

## 4. The code now enforces three temporal and measurement modes

1. `strict_asof`: uses only leaderboard records that were actually retrieved
   and published no later than the specified historical cutoff.
2. `retrospective`: may show a historically published 2024 row downloaded
   in 2026, clearly labeled **NOT prequential**.
3. `controlled`: uses preregistered task protocols, identical
   task-set SHA256, same scoring scheme, prompt/tool policy, and per-task
   token cap. Only comparable trial pairs may produce task-wise success
   percentage-point differences.

The retrospective series reports:
- separated methodology eras,
- raw source URLs and capture hashes,
- first/last scores, level differences, and descriptive Theil–Sen slope,
- sample count shifts and same-count score revisions,
- warnings about source methods and inability to infer general cognition.

It **does not** divide Arena scores to create a cognitive multiplier.
A static model's rating drift is a useful *measurement negative control*,
not a forecast of what an expanded future model can do.

## 5. Matched-task capability vector protocol

A controlled protocol records:
- domain/axis (coding, mathematics, reasoning, reliability, etc.),
- benchmark version, exact task-set SHA256 and task count,
- scoring unit (currently binary success),
- maximum tokens permitted per task,
- prompt/tool setup and dated source.

A controlled trial records:
- precise model/version, run mode (base or Agent),
- evaluation/publication/recording dates, source URL,
- successful task count and task count,
- whether synthetic, reported, or independently verified.

For domain $k$, success fraction is:

$$
p_{m,k} = \frac{s_{m,k}}{n_k}
$$

For matched trials, a descriptive domain change is:

$$
\Delta p_k = p_{\mathrm{target},k} - p_{\mathrm{baseline},k}
$$

A ratio of success fractions may also be shown as a task-specific descriptive
quantity. **It is not a universal "intelligence multiplier."**

Comparisons changing Agent scaffolds are explicitly classified as
`agent_system_change` and cannot be attributed solely to base weights.
Different task-set hashes, token ceilings, or scoring protocols are refused.
No synthetic-to-real comparison is permitted.

Wilson intervals describe individual success proportions under assumptions;
separately calculated Wilson intervals are **not** a valid paired-effect CI.
Those limitations appear in the output, not only in this document.

## 6. Technical pieces

- `fsl_timecourse/arena_history.py`: official Dataset Viewer `/filter`
  and safe exact-name `/search` fallback (both returned HTTP 500 on the
  large historical split during the initial live test; fail explicitly).
- `fsl_timecourse/parquet_history.py`: official Parquet index, size caps,
  downloaded-file SHA256, isolated local DuckDB projection, exact-name match,
  dated SQLite snapshot, CC BY 4.0 attribution.
- `fsl_timecourse/analysis.py`: method regimes, conflict checks, as-of
  replay, sample-count change flags, non-ratio longitudinal score deltas,
  readiness checks.
- `fsl_timecourse/controlled.py` and
  `fsl_timecourse/controlled_cli.py`: immutable matched protocols and
  non-scalar task vectors.
- `scripts/report_arena_timecourse.py`: regenerate source-hashed
  CSV/JSON/UTF-8 MD from archived SQLite without live API access.
- GitHub Actions `arena-parquet-history.yml`: strictly scoped retrieval
  and 90-day artifact retention; source data not auto-committed.

## 7. Example execution

```bash
python -m unittest discover -s tests -v

python -m fsl_timecourse.cli method-breaks
python -m fsl_timecourse.cli --db reports/arena_parquet.sqlite readiness

python -m fsl_timecourse.cli --db reports/arena_parquet.sqlite series \
  --model-id 'arena:gpt-4o-2024-05-13' --channel preference \
  --measure arena_rating --category overall \
  --methodology 'arena-dataset:text_style_control:arena_rating' \
  --mode retrospective --as-of 2026-11-06

python -m scripts.report_arena_timecourse \
  --db reports/arena_parquet.sqlite \
  --model 'gpt-4o-2024-05-13' \
  --config text_style_control --as-of 2026-11-06 --out-dir reports
```

For real-data matched tasks, first create and audit a JSON controlled protocol
and trial records; see `fsl_timecourse/controlled_cli.py`.
The repository provides **synthetic test cases only**, not a claim that
a real matched 2–3x capability experiment has already been conducted.

## 8. Scientific limits and next step

The original v0.3 cross-sectional sample of 317 numerical observations
and this v0.4 190-date history are **different statistical units**.
Do not report them as "507 independent AI models".

A valid hardware-to-capability transformation study still requires:
- dated physical GPU availability, precision and connected-run partition,
- disclosed compatible total/active parameter measurements,
- paired, budget-controlled independent task trials,
- publicly issued predictions prior to outcome release,
- methods-version and sample-selection audits.

Only then should the adaptive hypothesis weights for delayed-payback,
parameter saturation, and architectural transition be updated from
held-out observations.

## References

- Arena public leaderboard dataset and method change notes:
  https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset
- HF Parquet file index:
  https://huggingface.co/docs/dataset-viewer/parquet
- HF filtering API and limitations:
  https://huggingface.co/docs/dataset-viewer/filter
- HF official benchmark scores, verified flag and submissions:
  https://huggingface.co/docs/hub/leaderboard-data-guide

The source documents retain their original rights and licenses.
Apache-2.0 covers the project code and original research documentation,
not third-party score datasets.
