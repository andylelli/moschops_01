# Backtest and Validation Methodology

Version: 1.0  
Last updated: 2026-05-21

## Purpose
Define the minimum backtest and validation standards before AI or live rollout.

## Methodology
- Use completed-bar logic only.
- Use realistic spread, commission, and slippage assumptions.
- Test across multiple symbols and market regimes.
- Avoid cherry-picked single-window optimization.
- Use real historical data for strategy validation and model promotion decisions.

## Data Collection Requirements

- Primary source for operational validation data: MT5 terminal and broker history.
- Store bars, signal payload features, execution quality, and outcomes in PostgreSQL.
- Ensure runtime/training feature parity, including required volatility input.
- Keep immutable lineage keys so any training row can be traced to original signal and outcome.
- For news-guard validation slices, use Financial Modeling Prep (FMP) normalized event lineage with recorded provider tier (`FREE` for `v1.x`, `BASIC` for `v2+`).

## Required Checks
- No look-ahead bias.
- No survivorship assumptions hidden in the dataset.
- Stable parameter zones preferred over single best-fit points.
- AI promotion must improve out-of-sample quality, not only in-sample fit.

## Pass/Fail Criteria
- Base strategy must be validated before AI is enabled.
- Results must be documented per symbol, regime, and cost assumption.
- Failure cases must be captured and retained for review.

## Outputs
- Validation report
- Dataset export for training
- Parameter sensitivity summary
- Cost-assumption summary
