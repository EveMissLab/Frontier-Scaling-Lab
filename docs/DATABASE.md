# Database and evidence protocol (v0.2)

## Database model

The SQLite schema is in \`fsl_adaptive/registry.py\`. Its data is **append-only**. A stored event is an assertion with provenance, not a true fact merely because a URL was provided.

\`evidence_events\` columns:
\`event_id, entity_id, entity_kind, field, value_json, unit, state, source_kind, source_url, published_on, recorded_on, effective_on, supersedes_id, note, payload_sha256\`.

\`forecasts\` columns:
\`forecast_id, as_of, target_year, target_key, calibration_group, target_class, input_sha256, output_json\`.

\`feedback\` columns:
\`feedback_id, forecast_id, observed_multiplier, published_on, recorded_on, model_source_url, baseline_source_url, note\`.

The project uses ASCII ISO dates (YYYY-MM-DD). More precise timestamps and source-document version references are future migration items.

## Assertion example

This record is **synthetic**; do not treat the number as a real data-center deployment.

~~~json
{
  "event_id": "synthetic-site-amendment-01",
  "entity_id": "demo-planned-2027",
  "entity_kind": "site",
  "field": "site.gpus",
  "value": 40000,
  "unit": "GPU",
  "state": "asserted",
  "source_kind": "assumption",
  "published_on": "2026-11-06",
  "recorded_on": "2026-11-06",
  "note": "Illustrative revision only"
}
~~~

An independently sourced assertion needs \`source_kind\` such as manufacturer, filing, model_card, public_record or research_paper **and** an HTTPS \`source_url\`. Published and recorded dates must reflect when the evidence was accessible, not when a future buildout is hoped to complete.

## Retraction example

~~~json
{
  "event_id": "synthetic-site-retraction-02",
  "entity_id": "demo-planned-2027",
  "entity_kind": "site",
  "field": "site.gpus",
  "value": null,
  "state": "retracted",
  "supersedes_id": "synthetic-site-amendment-01",
  "source_kind": "assumption",
  "published_on": "2026-11-07",
  "recorded_on": "2026-11-07"
}
~~~

## Later disclosure feedback (SCHEMA ONLY)

Do not paste this demonstration into a live observational study: \`example.org\` is not actual evidence.

~~~json
{
  "feedback_id": "example-disclosure-001",
  "forecast_id": "REPLACE_WITH_REAL_SAVED_FORECAST_ID",
  "observed_multiplier": 4.25,
  "published_on": "2030-01-20",
  "recorded_on": "2030-01-21",
  "model_source_url": "https://example.org/model-card",
  "baseline_source_url": "https://example.org/comparable-baseline",
  "note": "Illustrative schema, no actual disclosed model"
}
~~~

The \`observed_multiplier\` must compare like-for-like publicly disclosed model **total parameters**, not model names, API marketing labels, or benchmark scores. Its denominator and numerator must both be disclosed, sourced, compatible, and publicly available.

The code refuses feedback for \`target_class=synthetic\`, feedback published before the saved forecast, invalid URLs, and future feedback when replaying as-of an earlier date. It deduplicates a later disclosure about the same target-year cohort during fitting, so issuing multiple forecasts does not multiply the same outcome's evidential weight.

## Facility data roadmap

\`site.gpus\` is currently a scenario quantity, not a normalized GPU inventory. Before building a real facility database, introduce a separate fact schema with project status, quantity units, site hierarchy, contract capacity, energy delivery, GPU deployment and interconnect boundaries.

The **source event date**, **announcement date**, **expected completion date**, **grid live date**, **installed GPU date**, and **training availability date** can all differ. Never use only the later expected date as proof that a facility exists.

The \`effective_on\` field is preserved as metadata. In v0.2, the numerical forecasting layer does *not* automatically elevate a future-effective announcement to an actual operational stage. Use explicit planning status and conservative as-of constraints; future physical-event handling requires a dedicated migration and further validation.

## No automated data polling in this version

Data entry is manual and reviewable. To automate later: fetch official filings/model cards with rate limits, snapshot the original, log content hashes, require schema review, then append new events. Any change must be auditable and replayable. Do not quietly overwrite previous claims.
