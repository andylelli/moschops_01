# Recipe: [Strategy Name]

System ID: TS-0XX
Recipe number: nn
Recipe status: Draft
Created: YYYY-MM-DD
Owner: [Name]
Palette version: strategy-design-palette.md v1.0

---

## Instructions for use

1. Copy this file and rename it `nn-recipe-ts-xxx.md` (e.g. `04-recipe-ts-004.md`).
2. Fill in every section before declaring the recipe signed off.
3. Use [../../11-trading-tools/strategy-design-palette.md](../../11-trading-tools/strategy-design-palette.md) to understand the available options for each dimension.
4. Use [../../11-trading-tools/future-design-palette.md](../../11-trading-tools/future-design-palette.md) to identify options that are not yet implemented — note them under Section 7 (Open Questions / Future Extensions) rather than selecting them here.
5. When every section is complete, change Recipe status to `Signed-off`, add your name and date to the sign-off block at the bottom, and proceed to TS folder generation using [00_copilot_prompt.md](00_copilot_prompt.md) Phase 2.

**Required fields (recipe cannot be signed off until all are complete):**
- Section 1: Strategy concept
- Section 2.1 through 2.11: All 11 palette dimensions
- Section 3: Signal knob values
- Section 4: Experiment plan with at least one hypothesis and proposed lab windows
- Section 5: Risk and safety constraints

---

## 1. Strategy Concept

### Thesis

*One to three sentences stating why this strategy should have durable edge. Be specific about the market inefficiency being exploited.*

> TODO: Write the thesis here.

### Market inefficiency targeted

*What behaviour are we betting on persisting? (e.g. momentum, mean reversion, volatility compression/expansion, regime persistence, carry, liquidity patterns)*

> TODO:

### Why this is not a duplicate of an existing TS

*Compare explicitly to TS-001, TS-002, TS-003 and explain the differentiation.*

> TODO:

### Expected regime profile

*In which market conditions do you expect this strategy to work well? In which will it fail?*

| Condition | Expected performance |
|---|---|
| Low vol trending | TODO |
| High vol trending | TODO |
| Range-bound / choppy | TODO |
| Crisis / structural break | TODO |

---

## 2. Design Palette Selections

*For each dimension, select one option from the current palette. Reference [strategy-design-palette.md Section 4](../../11-trading-tools/strategy-design-palette.md) for the current pick-list at each step. Mark any option that requires a code change with [CODE CHANGE NEEDED].*

### 2.1 Instrument and Timeframe

| Field | Selection |
|---|---|
| Primary instrument | TODO (e.g. EURUSD) |
| Timeframe | TODO (D1 / H4 / H1 / M15) |
| Additional instruments (if any) | TODO or N/A |

**Rationale:** *Why this instrument and timeframe pair?*

> TODO:

**Data availability confirmed?** Yes / No / Pending download

**Expected trade frequency (from palette table):** ~N trades / month

---

### 2.2 Model Estimator

| Field | Selection |
|---|---|
| Estimator | TODO (logreg / rf / xgb / lgbm) |
| Calibration method | TODO (isotonic / platt / none) |
| Code change required? | Yes / No |

**Rationale:** *Why this estimator for this strategy type?*

> TODO:

---

### 2.3 Feature Set

*List every feature included. Start from the current default set and note additions or removals.*

**Default features (always active — retain unless explicitly removing):**

| Feature | Include? | Notes |
|---|---|---|
| ret1 to ret5 (lagged log returns) | Yes / No | |
| ret10 (10-bar log return) | Yes / No | |
| volatility20 | Yes / No | |
| volatility100 | Yes / No | |
| volatility_regime (vol20/vol100) | Yes / No | |
| above_sma (close > SMA200) | Yes / No | |
| trend_strength (20-bar return / ATR20) | Yes / No | |
| breakout_distance (distance from 55-bar high/low / ATR20) | Yes / No | |
| atr_normalised (ATR20 / close) | Yes / No | |

**Additional features to add:**

| Feature | Type | Code change required? | Rationale |
|---|---|---|---|
| TODO | | | |

**Feature schema version that will result:** v1.X (increment from current)

---

### 2.4 Label Objective

| Field | Selection |
|---|---|
| Label mode | TODO (direction / edge) |
| Horizon (bars) | TODO |
| Minimum edge threshold (bps) | TODO (e.g. 8 bps) |
| Class balance handling | TODO (upsample minority / class_weight / none) |

**Rationale:** *Why this label objective for this strategy?*

> TODO:

**Expected label frequency (% positive bars):** ~X%

---

### 2.5 Signal Variant

| Field | Selection |
|---|---|
| Variant | TODO (baseline / trend-follow / regime-split) |
| Regime gate active? | Yes / No |
| Regime gate type | TODO (volatility_regime threshold / HMM state / efficiency_ratio / none) |

**Variant-specific knobs:**

*Fill in the knobs relevant to the chosen variant. Leave others as N/A.*

| Knob | Value | Notes |
|---|---|---|
| trend_follow_sma_window | TODO or N/A | |
| trend_follow_min_strength | TODO or N/A | |
| regime_split_vol_threshold | TODO or N/A | |
| regime_gate_min_ratio | TODO or N/A | |
| regime_gate_max_ratio | TODO or N/A | |
| Other custom knob | | |

**Rationale:**

> TODO:

---

### 2.6 Regime Gate

*Complete this section only if a regime gate is active (Section 2.5 = Yes).*

| Field | Selection |
|---|---|
| Gate metric | TODO (volatility_regime / efficiency_ratio / HMM_state / none) |
| Lower bound | TODO (e.g. 0.8 — block entries when vol is unusually low) |
| Upper bound | TODO (e.g. 2.0 — block entries when vol is unusually high) |
| Gate action | TODO (block-all / reduce-size / log-only) |

**Rationale:**

> TODO:

---

### 2.7 Probability Threshold Strategy

| Field | Selection |
|---|---|
| Threshold selection method | TODO (constrained-optimisation / fixed / per-regime) |
| Minimum trade count constraint | TODO (e.g. 60 trades in test window) |
| Maximum drawdown constraint | TODO (e.g. 25%) |
| Probability floor (hard minimum) | TODO (e.g. 0.52) |

**Rationale:** *Why these constraint targets for this timeframe / instrument?*

> TODO:

---

### 2.8 Walk-Forward CV Design

| Field | Selection |
|---|---|
| Number of folds | TODO (4–7 recommended) |
| Embargo (bars) | TODO (3–10) |
| Horizon (bars per test fold) | TODO (3–10) |
| Window type | TODO (rolling / expanding) |

**Rationale:**

> TODO:

---

### 2.9 Training Window

| Field | Selection |
|---|---|
| Training start date | TODO (e.g. 2012-01-01) |
| Dev/test split date | TODO (e.g. 2022-01-01) |
| Holdout start date | TODO (e.g. 2023-01-01) |
| Holdout end date | TODO (e.g. 2024-12-31) |
| Minimum training bars | TODO |

**Rationale:** *Why these dates? Reference any known structural breaks or data quality issues near boundaries.*

> TODO:

---

### 2.10 Cost Model

| Field | Selection |
|---|---|
| Spread assumption (bps) | TODO (e.g. 2.0 bps D1 conservative) |
| Commission assumption (bps) | TODO (e.g. 1.0 bps) |
| Slippage assumption (bps) | TODO (e.g. 0.5 bps) |
| Overnight swap assumption (bps/night) | TODO or N/A |
| Stress test multiplier | TODO (e.g. 2x spread, 3x slippage) |

**Rationale:** *Are these conservative enough for live trading conditions?*

> TODO:

---

### 2.11 Promotion Gate Thresholds

*These are the numeric targets the strategy must meet to progress through each gate stage.*

| Gate | Metric | Threshold |
|---|---|---|
| Minimum trades (holdout) | Trade count | TODO (e.g. 60) |
| Profit factor floor | PF | TODO (e.g. 1.2) |
| Maximum drawdown ceiling | Max DD % | TODO (e.g. 20%) |
| Expectancy floor (per trade) | Avg R multiple or bps | TODO |
| Fold consistency floor | % folds profitable | TODO (e.g. 60%) |
| Calmar ratio floor (if used) | Calmar | TODO or N/A |
| Sortino ratio floor (if used) | Sortino | TODO or N/A |

**Rationale:** *Why these thresholds? Compare to TS-001/003 baseline for calibration.*

> TODO:

---

## 3. Signal Knob Summary

*Consolidate the exact parameter values that will be passed to the training scripts. This becomes the command-line recipe for the lab.*

```
python run_historical_split.py \
  --symbol          TODO \
  --timeframe       TODO \
  --label-mode      TODO \
  --min-edge-bps    TODO \
  --horizon         TODO \
  --signal-variant  TODO \
  --model           TODO \
  --folds           TODO \
  --embargo         TODO \
  --spread-bps      TODO \
  --commission-bps  TODO \
  --slippage-bps    TODO \
  --min-trades      TODO \
  --max-dd          TODO
```

*Add any additional flags for non-default features, regime gates, or custom knobs.*

---

## 4. Experiment Plan

### Primary hypothesis

*State a single, falsifiable hypothesis. Example: "A trend-following logistic regression model on EURUSD H4 with volatility regime gating will produce a profit factor > 1.2 after realistic costs on the 2022-2024 holdout window."*

> Hypothesis: TODO

### Success definition

*What outcome would confirm the hypothesis?*

> TODO:

### Failure definition

*What outcome would falsify the hypothesis and require a different design?*

> TODO:

### Proposed lab windows

| Phase | Train window | Test window | Purpose |
|---|---|---|---|
| EXP-001 baseline | TODO | TODO | Establish baseline behaviour |
| EXP-002 (if needed) | TODO | TODO | TODO |

### Ordered experiment sequence

*List the experiments in priority order. Change only one major variable per experiment.*

1. EXP-001: TODO (e.g. baseline logistic regression, no regime gate)
2. EXP-002: TODO (e.g. add volatility regime gate)
3. EXP-003: TODO (e.g. swap estimator to XGBoost)

### Stopping criteria

*Under what conditions will you stop experimenting and either promote or retire the strategy?*

> TODO:

---

## 5. Risk and Safety Constraints

### Hard position limits

| Parameter | Limit |
|---|---|
| Max risk per trade (% of account) | TODO (e.g. 1%) |
| Max open trades simultaneously | TODO |
| Max correlated exposure | TODO or N/A |

### Stop loss policy

| Field | Value |
|---|---|
| Stop type | TODO (fixed pips / ATR multiple / support/resistance) |
| Stop distance | TODO |
| Trailing stop? | Yes / No |

### Capital constraints

| Field | Value |
|---|---|
| Minimum account size for this strategy | TODO |
| Target lot size (micro / mini / standard) | TODO |
| Max drawdown tolerance before system pause | TODO (e.g. 15% from peak) |

### Operational dependencies

*List any services, data feeds, or external dependencies this strategy requires at runtime.*

| Dependency | Required? | Fallback if unavailable |
|---|---|---|
| Backend API (localhost:3000) | Yes | Fail-closed — EA does not trade |
| FMP historical data feed | Yes (training only) | Re-run blocked until restored |
| MT5 terminal | Yes (live) | N/A |
| TODO: other | | |

---

## 6. What This Recipe Drives

*Map each recipe section to the TS documentation files it primarily informs. Use this as a checklist when generating the TS folder.*

| Recipe section | Drives TS document(s) |
|---|---|
| 1. Strategy concept and thesis | 00_system_charter, 01_strategy_spec |
| 2.1 Instrument / timeframe | 00_system_charter, 02_instruments_execution, 03_data_contract |
| 2.2 Model estimator | 05_model_training |
| 2.3 Feature set | 03_data_contract, 04_feature_schema |
| 2.4 Label objective | 01_strategy_spec, 05_model_training |
| 2.5 Signal variant | 01_strategy_spec |
| 2.6 Regime gate | 01_strategy_spec |
| 2.7 Threshold strategy | 01_strategy_spec, 08_promotion_gates |
| 2.8 CV design | 05_model_training, 06_validation_protocol |
| 2.9 Training window | 05_model_training, 06_validation_protocol |
| 2.10 Cost model | 06_validation_protocol, 08_promotion_gates |
| 2.11 Gate thresholds | 08_promotion_gates |
| 3. Signal knob summary | 05_model_training, 06_validation_protocol, 11_experiment_log |
| 4. Experiment plan | 11_experiment_log, 06_validation_protocol |
| 5. Risk and safety constraints | 07_risk_safety, 02_instruments_execution |

---

## 7. Open Questions and Future Extensions

*Note any unresolved design questions and any future-palette items you considered but deferred.*

### Unresolved questions

| Question | Owner | Target date |
|---|---|---|
| TODO | | |

### Future palette items considered but deferred

*Reference [future-design-palette.md](../../11-trading-tools/future-design-palette.md) for item names.*

| Item | Section in future palette | Why deferred | Future priority |
|---|---|---|---|
| TODO | | | |

---

## 8. Amendments

*Add entries here if this recipe is modified after sign-off. Do not delete or overwrite prior content.*

| Date | Changed by | What changed | Reason |
|---|---|---|---|
| *(none)* | | | |

---

## Sign-off

| Field | Value |
|---|---|
| Recipe status | Draft / Signed-off |
| Signed off by | TODO |
| Sign-off date | TODO |
| Palette version referenced | strategy-design-palette.md v1.0 |
| Next action | Create TS-0XX folder using 00_copilot_prompt.md Phase 2 |
