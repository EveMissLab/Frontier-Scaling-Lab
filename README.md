# Frontier Scaling Lab

A reproducible and evidence-aware research engine for **reverse-estimating feasible AI training compute and parameter-size intervals** from publicly disclosed infrastructure and hardware specifications.

The code does **not** claim to reveal private GPT, Claude, Gemini, Grok or other models' parameter counts. Conditional parameter intervals are not capability predictions.

## v0.1 runnable features

- Multi-campus capacity and connected **single-run** compute are separated.
- Vendor peaks, data-center MW, system PUE, MFU and training fractions are separately modeled.
- Bounded FLOPs, effective active parameters and total MoE parameters can be estimated.
- Sources are revisioned in append-only JSONL; later evidence overrides a field without erasing history.
- Observational timelines exclude unbuilt facilities by default.
- As-of evaluation and provenance hashes support reproducibility.
- Out-of-sample parameter disclosure comparisons have a strict leakage guard.
- The hypothesis of **2–3x effective cognitive capability** is tracked separately and is explicitly *not inferred* from parameter counts.

Requires Python 3.11+; no third-party dependencies.

~~~bash
python -m unittest discover -s tests -v
python frontier_scaling.py forecast --scenario rubin_100mw_reference --as-of 2026-11-06 --output results/example.json
python frontier_scaling.py evidence --as-of 2026-11-06
python frontier_scaling.py forecast --scenario planned_campuses_2028 --include-unbuilt
~~~

To add an event, create a JSON object per docs/RESEARCH.md and run:

~~~bash
python frontier_scaling.py record --event path/to/new_event.json
python frontier_scaling.py forecast --scenario rubin_100mw_reference
~~~

Backtest against independently disclosed **later** model parameter values:

~~~bash
python frontier_scaling.py backtest --forecast results/example.json --actuals data/my_actuals.json
~~~

The initial NVIDIA 100 MW factory is a **manufacturer's reference design, not an operating factory**. NVIDIA lists 40,000 Rubin GPUs and 160 EFLOP/s theoretical BF16 peak across that design (4 PFLOP/s per GPU):

https://www.nvidia.com/en-sg/data-center/vera-rubin-nvl72/

All other initial numbers are **synthetic assumption ranges**. The resulting envelopes are not statistical confidence intervals. See docs/RESEARCH.md for mathematical scope, provenance protocol, and next research milestones.

## Licensing

No software license has yet been granted. Public visibility does not automatically authorize reuse.
