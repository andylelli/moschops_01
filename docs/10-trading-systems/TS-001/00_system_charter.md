# 00 System Charter

System ID: TS-001
System Name: AI-Filtered Daily Breakout
Version: 1.0
Status: In discovery
Owner: Trading + AI Engineering
Last updated: 2026-05-27

## Mission
Build a robust, auditable FX strategy that combines deterministic trend-breakout rules with AI quality filtering, targeting positive expectancy after costs while preserving strict risk controls.

## Scope
1. In scope: EURUSD initial deployment profile, D1 decisioning, backend-driven risk veto and audit logging, AI scoring pipeline, walk-forward validation.
2. Out of scope: multi-strategy portfolio allocator behavior, cloud-managed production deployment, discretionary override trading.

## Business objective
1. Target profile: durable, moderate-return profile with controlled drawdown.
2. Drawdown tolerance: stay inside hard gate limits defined in promotion policy.
3. Capital usage constraints: risk-per-trade and open-risk caps are mandatory.

## Non-negotiable principles
1. No holdout retuning.
2. Full signal-risk-trade lineage.
3. Fail-closed behavior on critical dependency failures.
4. Promotion only through gate evidence.

## Success criteria
1. Quantitative: positive out-of-sample expectancy with realistic costs and acceptable drawdown.
2. Operational: complete logs, repeatable runs, stable runtime behavior.
3. Governance: full compliance with no-bending policy and documentation completion.

## Failure criteria
1. Evidence of leakage, holdout reuse, or hidden experiment cherry-picking.
2. Risk/safety controls violated or incomplete audit traceability.
3. Strategy profitability collapses under realistic cost assumptions.

## Dependencies
1. Data providers: backend historical data endpoints (FMP path currently in use).
2. Execution venues: MT5 terminal via DailyBreakoutEA.
3. Infrastructure: backend API, PostgreSQL persistence, training and ONNX artifact path.

## Governing references
1. [../robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md)
2. [../../02-architecture/lld_v1.md](../../02-architecture/lld_v1.md)
3. [README.md](README.md)
