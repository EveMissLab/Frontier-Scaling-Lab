# DAS-ARL — Deep Attention Spectrum and Autonomous Representation Learning

**Status:** candidate research indicators / definitions only. **Not a measured AI capability.**  
**Series:** six canonical UTF-8 Markdown papers, 2026-11-09.  
**Research author:** Neo.K / EveMissLab.  
**Scope:** independent additive track for [Frontier-Scaling-Lab](https://github.com/EveMissLab/Frontier-Scaling-Lab); does not replace existing SAS, scaling, manufacturing, legal or infrastructure indicators.

## Research papers

1. [01 — Foundations](DAS_ARL_01_Deep_Attention_Spectrum_Foundations_2026-11-09.md)
2. [02 — Formal Structure and Dynamic Control](DAS_ARL_02_Formal_Structure_Dynamic_Control_2026-11-09.md)
3. [03 — Intra-Domain / Cross-Domain and Hybrid Expert Routing](DAS_ARL_03_Intra_Domain_Cross_Domain_Hybrid_Expert_Routing_2026-11-09.md)
4. [04 — Learning Methodology and Gradient Adaptation](DAS_ARL_04_Learning_Methodology_Gradient_Adaptation_2026-11-09.md)
5. [05 — Learning Spectrum Ledger and Neural Coupling](DAS_ARL_05_Learning_Spectrum_Ledger_Representation_Trajectories_Neural_Coupling_2026-11-09.md)
6. [06 — Validation, Benefit and Cost Boundaries](DAS_ARL_06_Validation_Benefits_Cost_Boundaries_2026-11-09.md)

## Engineering implementation RFC (2026-11-09)

- [**RFC-001 — How to integrate DAS with current Transformer, optional MoE and Agent stacks**](DAS_ARL_ENGINEERING_RFC_001_2026-11-09.md)
- [**Task / cognitive-event / verification-receipt JSON Schema (draft v0.1)**](../../data/das_arl_engineering_contract_v0.1.schema.json)
- [**Experiment preregistration template (unregistered, unmeasured)**](../../data/das_arl_experiment_preregistration_template_v0.1.json)

**Document status:** PROPOSED_NOT_IMPLEMENTED. The RFC specifies an external orchestration MVP first, then an optional learned controller / adapter, and only then native recurrent hidden-state integration. It does not claim that any of these runtime modules or DAS models have been implemented or empirically validated. It requires verification receipts, budget-matched baselines, privacy and authorization gates, and an event ledger that separates inference from optimizer updates.

## Supplementary research

- [**SUP-01 — Synthetic Data Representational Re-mining and State-Dependent Relearning (2026-11-09)**](DAS_ARL_SUP_01_Synthetic_Data_Representational_Remining_2026-11-09.md)

This supplement explores conditional reuse of real/synthetic training sources, representation changes, verification boundaries, model-collapse risks, and equal-budget evaluation. It proposes 12 **additional unmeasured metric definitions (DAS-SR01–12)** only within the supplement; these are **not incorporated into or counted as part of the existing 72-item catalog**, and no model experiment or synthetic-data learning gain is claimed. The original six canonical papers remain unchanged.

## Candidate metric definitions

Machine-readable catalog: [data/das_arl_indicator_catalog_v0.1.json](../../data/das_arl_indicator_catalog_v0.1.json).

- 12 cognitive / expert routing metrics (DAS-R01–12; paper 03)
- 16 learning-control metrics (DAS-L01–16; paper 04)
- 20 event / ledger / neural observability metrics (DAS-LL01–20; paper 05)
- 24 experimental validation / costs metrics (DAS-V01–24; paper 06)

**All 72 metrics have `value: null`, `observation_state: not_measured`.** Theory, finite proofs and SYNTHETIC replay checks do not constitute real-model evidence. Exposure is not learning, attention is not explanation, retrieval is not a gradient update, and new representations are not automatically valid knowledge.

The canonical delimiter rules inside the formal original papers are `$...$` and `$$...$$`. The series includes reproducible synthetic fixtures and Python checks in the separately delivered archive; synthetic outcomes must never be placed into observational time series.

**Publication stance:** this is a falsifiable research program and candidate metric library, not a claim of demonstrated DAS capability or a peer-reviewed empirical breakthrough.
