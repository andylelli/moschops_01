# 00 System Charter

System ID: TS-003
System Name: Cross-Asset Momentum Rotation
Version: 0.1
Status: In discovery
Owner: Trading + AI Engineering
Last updated: 2026-05-27

## Mission
Capture persistent relative-strength dynamics by rotating exposure toward stronger instruments on H4 while enforcing strict risk limits.

## Scope
1. In scope: H4 decision engine, momentum ranking signals, risk-weighted position eligibility.
2. Out of scope: discretionary event overrides, leverage scaling beyond approved risk budgets.

## Business objective
1. Target profile: consistent post-cost expectancy with stable fold-level behavior.
2. Drawdown tolerance: acceptance drawdown ceiling of -15%.
3. Capital usage constraints: paper then micro-live ladder only after all gates pass.

## Non-negotiable principles
1. No holdout retuning.
2. Full auditability.
3. Fail-closed safety behavior.

## Success criteria
1. Quantitative: positive median OOS expectancy, PF floor, DD ceiling, and minimum-trade threshold.
2. Operational: deterministic run pack generation and reproducible artifacts.
3. Governance: no holdout reuse for tuning and complete lineage for each accepted run.

## Failure criteria
1. No feasible parameter set under hard risk and activity constraints.
2. Any leakage, undocumented rerun, or missing lineage evidence.

## Dependencies
1. Data providers: backend historical route with H4 support.
2. Execution venues: MT5 via controlled execution policy.
3. Infrastructure: backend API, persistence, artifact store, and run indexing.

