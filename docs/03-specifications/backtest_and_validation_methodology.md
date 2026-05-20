# Backtest and Validation Methodology

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the minimum backtest and validation standards before AI or live rollout.

## Methodology
- Use completed-bar logic only.
- Use realistic spread, commission, and slippage assumptions.
- Test across multiple symbols and market regimes.
- Avoid cherry-picked single-window optimization.

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
