# TS-001: AI-Filtered Daily Breakout

Version: 1.0
Last updated: 2026-05-27
Status: In discovery
Owner: Trading + AI Engineering

## 1) System Summary
TS-001 is a trend-following breakout strategy that combines deterministic rules with AI quality filtering.

Base idea:
1. Rules define candidate breakouts on completed candles.
2. Risk engine validates whether a trade is allowed.
3. AI score can scale conviction or block weak setups.
4. Execution remains fail-closed and auditable.

Primary objective:
- Produce positive expectancy after realistic costs, with bounded drawdown and stable out-of-sample behavior.

## 2) Instrument and Timeframe Scope
Initial scope:
1. Instrument class: FX majors.
2. Initial symbol: EURUSD.
3. Decision timeframe: D1 in live profile.
4. Test profile supports shorter timeframe only for integration checks, not promotion evidence.

## 3) Strategy Logic (Deterministic Core)
From implementation and LLD intent:
1. Long candidate when Close[1] is above trend filter and above prior breakout high window.
2. Short candidate when Close[1] is below trend filter and below prior breakout low window.
3. Exit long when Close[1] falls below fast SMA filter.
4. Exit short when Close[1] rises above fast SMA filter.
5. Initial stop distance uses ATR multiple.

Current key runtime parameters:
1. Breakout lookback: 55 bars.
2. Fast SMA: 100.
3. Trend SMA: 200.
4. ATR period: 20.
5. Risk per trade default: 0.5%.
6. Max spread guard in EA input.

## 4) Runtime Components and Data Flow
### 4.1 Components
1. MT5 EA for market data capture, rule checks, and order submission.
2. Backend endpoints for signal, risk, and logging.
3. Model inference layer for AI score routing.
4. Training pipeline for model refresh and artifact export.
5. Dashboard/reporting for operator audit and health.

### 4.2 End-to-End Flow
1. EA evaluates a newly completed bar.
2. EA builds market snapshot and sends decision request.
3. Backend applies rule logic + AI gating + risk veto.
4. Decision is returned and persisted with lineage.
5. EA executes or holds according to final action.
6. Trade/risk events are logged for audit and retraining.

## 5) AI Inputs and Model Behavior
### 5.1 Current historical-split run feature set
From training runner implementation:
1. trend_strength = (SMA50 - SMA200) / close.
2. volatility20 = rolling std of 1-bar returns.
3. atr14_norm = ATR14 / close.
4. breakout_distance = (close - prior 55-bar high) / close.
5. ret10 = 10-bar momentum proxy.

Label definition (current run):
1. Binary label = 1 if close(t+h)/close(t) - 1 > 0 over horizon bars.

### 5.2 Model and prediction policy
1. Model family in current split run: logistic regression with balanced class weight.
2. Inputs are standardized before fit/inference.
3. Predicted probability is thresholded for signal-on/signal-off decision proxy.

### 5.3 How parameters interact
1. Trend and breakout features identify directional context.
2. Volatility and ATR normalization stabilize behavior across volatility regimes.
3. Probability threshold controls trade frequency versus selectivity.
4. Risk-per-trade and stop distance convert signal confidence into bounded exposure.

## 6) Risk Controls and Safety Model
1. One-position-per-symbol policy.
2. Spread and gap guards reject poor execution conditions.
3. Sizing uses instrument metadata and must reject missing/inconsistent metadata.
4. Backend-unavailable or invalid-response paths are fail-closed for new entries.
5. Protective behavior remains enabled even in degraded mode.

## 7) Validation Approach (No-Bending Compliant)
TS-001 must follow:
- [../robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md)

Practical application for TS-001:
1. Freeze train/validation/final-holdout windows before each experiment cycle.
2. Use purged walk-forward folds for model and threshold selection.
3. Reserve final holdout for one-time acceptance evaluation only.
4. Include realistic spread, slippage, and commission in promotion decisions.
5. Record trial count and reject hidden cherry-picked runs.

## 8) Promotion Gates for TS-001 (Draft)
A TS-001 candidate can move forward only if all pass:
1. Data and lineage gate: complete reproducibility and no leakage flags.
2. Statistical gate: positive median out-of-sample expectancy across folds.
3. Risk gate: drawdown and trade-count thresholds satisfied.
4. Operational gate: no critical logging or execution safety failures.
5. Live-readiness gate: paper window pass before micro-live.

## 9) Current Known Limitations
1. Some training paths still rely on synthetic profile workflows.
2. Current quick backtest proxy uses simplified return assumptions and not full broker execution simulation.
3. Parameter defaults are still in discovery and must not be considered production-locked.

## 10) Evidence and Artifacts
Key related artifacts:
1. EA implementation: [mql5/Experts/DailyBreakoutEA.mq5](../../../mql5/Experts/DailyBreakoutEA.mq5)
2. Historical split runner: [training/run_historical_split.py](../../../training/run_historical_split.py)
3. Historical run report example: [docs/09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md](../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md)
4. No-bending governance plan: [docs/10-trading-systems/robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md)

## 11) Next System Expansion Path
Potential TS-00x candidates for the catalogue:
1. TS-002: Mean-reversion intraday volatility compression strategy.
2. TS-003: Cross-asset momentum rotation with portfolio risk allocator.
3. TS-004: Event-aware trend continuation with scheduled-news guard coupling.

All future systems must start from the template and follow no-bending governance.
