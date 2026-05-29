# AI Training Run Report

## Run Metadata
- Run ID: run-2026-05-27_19-43-historical-10y-2y
- Run Timestamp (UTC): 2026-05-27T18:54:41.658857+00:00
- Run Timestamp (Local): 2026-05-27:19:54
- Environment: local-dev
- Operator: scripted run
- Git Branch: main
- Commit Hash: n/a
- Notes: Historical split run with explicit 10y train and last-2y test windows.

## Training Parameters
- Model Type: logreg
- Dataset Profile: historical-split
- Training Date Range: 2014-05-27 to 2024-05-27
- Training Chart Period/Timeframe: D1
- Horizon Bars: 5
- Calibration: none
- Include Macro: false
- Include News Windows: false
- Include Session Features: false
- Enable Class Weights: true
- Training Output Path: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-43-historical-10y-2y\artifacts

## Validation Parameters
- Symbol: EURUSD
- Date Range: 2024-05-28 to 2026-05-27
- Chart Period/Timeframe: D1
- Starting Capital: n/a (classification evaluation run)
- Risk Per Trade: n/a
- Lookback Periods: n/a
- ATR Period: n/a
- SMA Fast: n/a
- SMA Trend: n/a
- Spread Pips: n/a
- Slippage Pips: n/a
- Commission %: n/a

## Raw Results
### Training Metrics
- AUC Mean: 0.582934
- AUC Min: 0.582934
- Brier Mean: 0.247998
- Brier Max: 0.247998

### Backtest Metrics
- Total Trades: 96
- Win Rate: 67.71%
- Net Profit: 26.97%
- Profit Factor: 2.43
- Max Drawdown %: -6.66
- Sharpe Ratio: 2.61

## Scoring Model (0-100)
- Training Quality Score (%): 24.62
- Validation Performance Score (%): 30.17
- Risk Control Score (%): 38.82
- Run Reliability Score (%): 100

## Overall Score
- Weighted Overall Score (%): 36.94
- Run Verdict: FAIL

## Evidence
- Training Log: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-43-historical-10y-2y\run_output.log
- Training Report Artifact: c:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-43-historical-10y-2y\artifacts\historical_split_report.json
- Baseline Report Artifact: n/a
- ONNX Model Artifact: C:\moschops_01\docs\09-training-runs\runs\2026-05-27_19-43-historical-10y-2y\artifacts\historical_split_model.onnx

## Assessment Summary
- What went well: Successfully trained on 10-year window and evaluated on the latest 2-year out-of-sample window.
- What failed: Recall is relatively low, indicating missed positive cases in out-of-sample evaluation.
- Risks: PnL is based on a simplified signal-return proxy and excludes spread/slippage/commission.
- Recommended next run changes: try rf model, add richer features, and run a dedicated out-of-sample trade simulation.
