# Frontier Scaling Lab v0.8.1｜長時程 Agent 訂閱可達性與有效成本

Date: 2026-11-07  
Canonical source: UTF-8 Markdown, math delimiters exclusively $...$ / $$...$$  
Status: executable accounting prototype; only **synthetic** examples have been tested.  
License: Apache-2.0 for original research and software (not external pricing datasets).

## 1. A functional-capability correction

For G1 and G2, the research must measure **what actual users can sustain with their real plan, allowance, quota resets, autonomous runtime, and cash budget**, not only what the underlying AI might achieve without limits.

The hypothesis: in 2026, a 24–48 hour long-running Agent may be feasible under clear goals and delegated autonomy. Higher-use tiers such as ChatGPT Pro and Claude Max plausibly reach this earlier than Free or standard paid access because they offer more usable allowance and specialized Agent features. That is **not** a claim of intrinsic cognitive inferiority in lower plans, or a guarantee that any Pro account can run for 48 hours nonstop.

## 2. Official subscription cohorts, 2026-11-07

| Provider route | USD monthly list price | Research cohort |
|---|---:|---|
| ChatGPT Free | 0 | low-budget baseline |
| ChatGPT Plus | 20 | standard paid baseline |
| ChatGPT Pro 100 | 100 | high-usage candidate |
| ChatGPT Pro 200 | 200 | higher-usage primary candidate |
| ChatGPT Pro 500 | 500 | highest-usage/speed candidate |
| Claude Free | 0 | low-budget baseline |
| Claude Pro | 20 | normal Claude Code candidate |
| Claude Max 5× | 100 | high-usage candidate |
| Claude Max 20× | 200 | higher-usage primary candidate |

Source URLs:
- https://chatgpt.com/pricing
- https://help.openai.com/en/articles/9793128-about-chatgpt-pro-tiers
- https://help.openai.com/en/articles/20001625-understanding-chatgpt-and-codex-usage-limits
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://claude.com/pricing
- https://support.claude.com/en/articles/11049762-choose-a-claude-plan

These are illustrative **US dollar list prices**, not Taiwan checkout receipts; taxes, local currency, promotions and individual access can vary. Never invent a precise quota in hours or tokens from a tier name. OpenAI has announced a new shared ChatGPT/Codex allowance regime beginning December 2026; log the actual plan rules and reset periods in force on the experiment date.

### Distinguish three access comparisons

A. **Matched model, matched task**: when available across tiers, keep the model revision, tools, autonomous runtime, task, quality validator and evaluation budget fixed; vary entitlement and observe interruptions and recovery.

B. **Natural product path**: compare what real Free, Plus, Pro, Claude Pro, Claude Max and API customers can actually use, including plan-specific models and work tools. This estimates customer access, not inherent model strength.

C. **Same cash budget**: compare subscription, purchased usage credits, API and local compute when they actually fit the permitted budget. Record their different engineering effort and runtime constraints.

## 3. Cash, allocation and variable billing are different

Full monthly outlay is:

$$
C_{\mathrm{cash}}=C_{\mathrm{month}}+C_{\mathrm{extra}}.
$$

Even if only two days are used, a USD 200 monthly subscription is still a USD 200 monthly financial commitment. An optional fraction $f$ can allocate subscription expenses *for research accounting*:

$$
C_{\mathrm{allocated}}=fC_{\mathrm{month}}+C_{\mathrm{extra}},\qquad 0\le f\le 1.
$$

This allocated cost is **not** the platform's actual marginal charge. If the subscription was already paid for unrelated usage, incremental cost may be lower than monthly outlay, but the monthly subscription remains part of the economic access condition.

For separately metered API tokens, use the actual model, date and sourced USD-per-million rate:

$$
C_{\mathrm{API}}=
\frac{n_{\mathrm{input}}r_{\mathrm{input}}+
n_{\mathrm{cached}}r_{\mathrm{cached}}+
n_{\mathrm{output}}r_{\mathrm{output}}}{10^6}.
$$

API and subscription usage are separate billing systems. Extra purchased credits, external tools, GPU/electricity and cloud hosting have independent line items. Credits already included in a subscription are **consumed entitlement value**, not another cash payment. Do not double-count API bills and credits representing the same underlying charge. Official API rate source: https://developers.openai.com/api/docs/pricing.

## 4. What an actual 48-hour mission must record

Keep these distinct:

- Calendar run time: start to declared end, including idle/waiting/paused time.
- Active tool/model execution: union of dated, source-backed intervals, with overlaps counted only once.
- Quota interruptions: exhausted allowances, rate-limit resets, purchases needed to continue and exact waiting periods.
- Goal-relevant progress: verified new facts, experiments, counterexamples, code/QA improvements, checkpoints and recovery.
- Final accepted outcome: user intention fulfilled, product or research results independently checked.

A 48-hour run with only 8 hours of observed activity is **not** automatically 48 hours of autonomous research. Likewise, a high-priced Pro subscription with no accepted result cannot be rated a success.

When external independent validation exists, cost per accepted result may be computed:

$$
C_{\mathrm{accepted}}=\frac{C_{\mathrm{total}}}{N_{\mathrm{accepted}}}.
$$

If the accepted-output count is zero or unverified, that quotient stays undefined, not zero.

## 5. Software and validation

New files:
- fsl_affordability/ledger.py — strict Decimal USD accounting, append-only SQLite, actual calendar/active times, overlapping activity union, quota interruptions, included versus purchased credits, API rates and sources.
- fsl_affordability/cli.py — offline calculation and immutable record storage.
- data/access_plan_reference_2026-11-07.json — dated provider plan cohort list. No invented entitlement limits.
- tests/test_affordability.py and tests/fixtures/affordability_synthetic_48h.json — offline synthetic price, idle time, billing and negative-case tests.

Commands:

~~~bash
python -m unittest discover -s tests -v
python -m fsl_affordability.cli analyze --file tests/fixtures/affordability_synthetic_48h.json
python -m fsl_affordability.cli save --db reports/affordability_demo.sqlite --file tests/fixtures/affordability_synthetic_48h.json
~~~

The **fictional** 48-hour scenario uses Pro 200 (USD 200/month), USD 16 purchased credits/tools/local compute, 8 hours of assumed active execution and one claimed two-hour quota pause. It therefore shows USD 216 full monthly cash obligation, or USD 36 *allocated* project cost using an explicitly assumed 10% monthly allocation. None of these amounts are actual platform bills or evidence of an autonomous model finishing a task.

The output deliberately sets:
- remaining_plan_allowance = unknown_not_inferred_from_price
- can_sustain_24h_verified = false
- can_sustain_48h_verified = false
- mission_completed_and_independently_verified = false
- cost_per_independently_verified_result_usd = null

## 6. Next empirical step

Attach this ledger to an actual persistent AMRAL mathematics research epoch and its FELRA independent replay, with a date-stamped, permitted model/runtime access path. Measure actual spend, remaining allowance, resets, checkpoint recovery and **new valid mathematical work**, not just 18 hours of generated output. Preserve the original private research; publish only attributable, permission-compatible summaries.

Research conclusion to test: **more generous access may bring functional 24–48 hour Agent autonomy earlier, while improvements in state management, strategy, cost efficiency and recovery may make the same achievement accessible at lower prices later.**
