# AI Training Run Report

## Run Metadata
- Run ID: run-2026-05-27_19-29
- Run Timestamp (UTC): 2026-05-27T18:29:34.0882596Z
- Run Timestamp (Local): 2026-05-27:19:29
- Environment: local-dev
- Operator: Copilot automation run
- Git Branch: main
- Commit Hash: n/a
- Notes: Timestamp folder uses yyyy-MM-dd_HH-mm on Windows because ':' is not valid in folder names.

## Training Parameters
- Model Type: logreg
- Dataset Profile: rolling-90d
- CV Folds: 5
- Horizon Bars: 6
- Calibration: isotonic
- Include Macro: true
- Include News Windows: true
- Include Session Features: true
- Enable Class Weights: true
- Training Output Path: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-29\artifacts

## Validation Parameters
- Symbol: EURUSD
- Date Range: 2023-01-01 to 2023-12-31
- Starting Capital: 10000.0
- Risk Per Trade: 0.5%
- Lookback Periods: 55
- ATR Period: 20
- SMA Fast: 100
- SMA Trend: 200
- Spread Pips: 2.0
- Slippage Pips: 1.0
- Commission %: 0.02%

## Raw Results
### Training Metrics
- AUC Mean: 0.73765
- AUC Min: 0.660413
- Brier Mean: 0.208921
- Brier Max: 0.230657

### Backtest Metrics
- Total Trades: 3
- Win Rate: 33.33%
- Net Profit: $-337.86
- Profit Factor: 0.88
- Max Drawdown %: 15.16
- Sharpe Ratio: 0.646

## Scoring Model (0-100)
- Training Quality Score (%): 56.72
- Validation Performance Score (%): 19.86
- Risk Control Score (%): 57.72
- Run Reliability Score (%): 100

## Overall Score
- Weighted Overall Score (%): 48.35
- Run Verdict: FAIL

## Evidence
- Training Log: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-29\run_output.log
- Training Report Artifact: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-29\artifacts\training_report.json
- Baseline Report Artifact: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-29\artifacts\baseline.md
- ONNX Model Artifact: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-29\artifacts\daily_breakout_model.onnx

## Assessment Summary
- What went well: Training and validation completed and artifacts were produced.
- What failed: Baseline PnL/profit factor did not pass profitability threshold.
- Risks: Very low trade count limits confidence in backtest stability.
- Recommended next run changes: Compare rf model and event-focused profile; increase sample horizon and trade opportunities.
