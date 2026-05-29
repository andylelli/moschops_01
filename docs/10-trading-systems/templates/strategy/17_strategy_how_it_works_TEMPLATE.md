# 17 Strategy How It Works

System ID: {{SYSTEM_ID}}
Version: 1.0
Last updated: {{DATE}}

## What this strategy does (plain language)

<!-- Write 2–3 sentences in plain English. State the instrument, timeframe, and the core
     market behaviour this strategy exploits. Avoid jargon — assume a non-technical reader. -->

{{SYSTEM_ID}} looks for opportunities to trade {{INSTRUMENT}} on {{TIMEFRAME}} charts.
Its core insight is: {{ONE_SENTENCE_THESIS}}.

## The big picture

<!-- Use an analogy or simple metaphor to describe the market dynamic the strategy exploits.
     Then explain what the strategy does in response to that dynamic. -->

{{BIG_PICTURE_ANALOGY}}

## How the AI works

<!-- Explain the model type, what data it was trained on, what it outputs, and why the
     train/test split makes it trustworthy. Use approximate human-readable time units
     (e.g. "40 hours" instead of "10 bars"). -->

An AI model ({{MODEL_TYPE}}) is trained on years of historical {{INSTRUMENT}} {{TIMEFRAME}} data.
It looks at a set of mathematical signals at each bar close and estimates the probability that the
next {{HORIZON_HUMAN}} will produce a meaningful move of {{MIN_EDGE_BPS}} basis points or more.

The AI was trained only on historical data up to {{DEV_SPLIT_YEAR}} and tested on
{{HOLDOUT_START_YEAR}}–{{HOLDOUT_END_YEAR}} data it has never seen. This prevents it from being
"fitted" to recent history and makes its conclusions more reliable.

## The key filter — {{KEY_FILTER_NAME}}

<!-- Describe the most important entry gate or filter in plain language. If the strategy has
     a regime gate, explain the three zones (too low / valid window / too high) with real values.
     If the key filter is something else (trend direction, momentum, etc.) adapt accordingly. -->

The most important filter in {{SYSTEM_ID}} is the **{{KEY_FILTER_NAME}}**.

- **{{FILTER_LOW_CONDITION}}**: {{FILTER_LOW_EXPLANATION}} No entry.
- **{{FILTER_VALID_CONDITION}}**: {{FILTER_VALID_EXPLANATION}} This is the entry window.
- **{{FILTER_HIGH_CONDITION}}**: {{FILTER_HIGH_EXPLANATION}} No entry.

{{KEY_FILTER_RATIONALE}}

## The trend filter — which way to trade

<!-- Explain the directional filter in plain language. State the look-back period in human
     terms (e.g. "approximately the last 5 months"). Confirm whether the strategy trades
     reversals or continuation only. -->

Before entering, {{SYSTEM_ID}} also checks that:
1. {{TREND_CONDITION_1}}
2. {{TREND_CONDITION_2}}

This means {{SYSTEM_ID}} only trades in the direction the market has been trending for
approximately {{TREND_LOOKBACK_HUMAN}}. It does {{REVERSAL_STATEMENT}}.

## What makes a good entry

<!-- List all required conditions in plain numbered form. Keep to 3–5 items maximum. -->

A trade is taken only when **all conditions** are met simultaneously:
1. {{ENTRY_CONDITION_1}}
2. {{ENTRY_CONDITION_2}}
3. {{ENTRY_CONDITION_3}}

## Risk management — how losses are controlled

<!-- Describe the stop loss mechanism in one paragraph. Then list the circuit breaker
     conditions using the actual numeric values from 07_risk_safety.md. -->

Every trade has a stop loss set at {{STOP_ATR_MULTIPLE}} times the current Average True Range (ATR).
This means the stop is automatically wider in volatile markets and tighter in quiet ones.

There is also a **circuit breaker** that pauses all trading if:
- Daily losses exceed {{CIRCUIT_BREAKER_DAILY_LOSS_PCT}}% of account equity
- Drawdown from the peak exceeds {{CIRCUIT_BREAKER_MAX_DD_PCT}}%
- {{CIRCUIT_BREAKER_CONSECUTIVE_LOSSES}} consecutive trades are losing trades

The circuit breaker cooldown lasts approximately {{COOLDOWN_HUMAN}} ({{COOLDOWN_BARS}} bars of
{{TIMEFRAME}} time). This prevents the strategy from compounding losses during adverse conditions.

## What {{SYSTEM_ID}} does NOT do

<!-- List 4–6 explicit exclusions. These should directly address likely misconceptions about
     the strategy. Write each as a "does not" statement. -->

- {{NOT_DO_1}}
- {{NOT_DO_2}}
- {{NOT_DO_3}}
- {{NOT_DO_4}}
- It does not react to tick-by-tick price movements (only acts at the close of each {{TIMEFRAME}} bar).

## How it connects to the rest of the platform

<!-- Keep this section identical in structure across all TS documents. Only adjust the
     bar-close timeframe reference to match the strategy's timeframe. -->

- The AI model runs in the backend (a local server on port 3000).
- The MetaTrader 5 trading platform runs an automated trading script (EA — Expert Advisor) that
  asks the backend for a signal at each {{TIMEFRAME}} bar close.
- If the signal passes all checks, the EA places a trade automatically.
- All signals and outcomes are logged to a database for monitoring and future model improvement.

## The journey from idea to live trading

<!-- Keep this table identical across all TS documents. Only update the final line
     to reflect the current phase of this strategy. -->

| Step | What happens |
|---|---|
| 1. Discovery | Run experiments on historical data |
| 2. Holdout validation | Test once on holdout data (never tuned on this) |
| 3. Paper trading | Run signals live but without real money for 30 days |
| 4. Micro-live | Trade very small positions |
| 5. Full live | Scale up position sizes after sustained profitability |

{{SYSTEM_ID}} is currently at **Step {{CURRENT_STEP}} ({{CURRENT_PHASE}})**.
{{CURRENT_PHASE_NOTE}}

---

<!-- Placeholder reference table — remove this section when writing the actual document -->
## Template placeholder reference

| Placeholder | Source |
|---|---|
| `{{SYSTEM_ID}}` | e.g. TS-004 |
| `{{DATE}}` | ISO date written |
| `{{INSTRUMENT}}` | e.g. EURUSD |
| `{{TIMEFRAME}}` | e.g. H4 |
| `{{ONE_SENTENCE_THESIS}}` | From 00_system_charter.md Mission |
| `{{BIG_PICTURE_ANALOGY}}` | Write freely — metaphor for the market dynamic |
| `{{MODEL_TYPE}}` | e.g. XGBoost |
| `{{HORIZON_HUMAN}}` | e.g. "40 hours" (= 10 × H4 bars) |
| `{{MIN_EDGE_BPS}}` | From 01_strategy_spec.md Label definition |
| `{{DEV_SPLIT_YEAR}}` | From 05_model_training.md Training window |
| `{{HOLDOUT_START_YEAR}}` / `{{HOLDOUT_END_YEAR}}` | From 05_model_training.md |
| `{{KEY_FILTER_NAME}}` | e.g. "volatility regime ratio" |
| `{{FILTER_LOW/VALID/HIGH_CONDITION}}` | From 01_strategy_spec.md Regime gate |
| `{{STOP_ATR_MULTIPLE}}` | From 07_risk_safety.md |
| `{{CIRCUIT_BREAKER_*}}` | From 07_risk_safety.md Circuit breaker spec |
| `{{COOLDOWN_BARS}}` / `{{COOLDOWN_HUMAN}}` | From 07_risk_safety.md |
| `{{CURRENT_STEP}}` / `{{CURRENT_PHASE}}` | 1–5 per deployment stage |
