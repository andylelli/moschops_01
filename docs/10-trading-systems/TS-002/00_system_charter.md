# 00 System Charter

System ID: TS-002
System Name: Mean-Reversion Volatility Compression
Version: 0.1
Status: In discovery
Owner: Trading + AI Engineering
Last updated: 2026-05-27

## Mission
Capture short-horizon mean reversion after volatility spikes while keeping risk tightly bounded under hard fail-closed controls.

## Scope
1. In scope: FX majors, initial EURUSD, H1 primary and H4 secondary signal contexts.
2. Out of scope: Cross-asset allocation, event-driven discretionary overrides, holdout retuning.

## Business objective
1. Target profile: robust post-cost expectancy and stable fold/regime behavior.
2. Drawdown tolerance: max drawdown ceiling of -15% at promotion gate level.
3. Capital usage constraints: initial live ladder remains paper then micro-live only after all gates pass.

## Non-negotiable principles
1. No holdout retuning.
2. Full auditability.
3. Fail-closed safety behavior.

## Success criteria
1. Quantitative: positive median out-of-sample expectancy, PF floor met, DD within ceiling, minimum-trade threshold met.
2. Operational: deterministic run packs and complete lineage artifacts for every reviewed run.
3. Governance: no undocumented reruns and no promotion overrides without explicit rationale and expiry.

## Failure criteria
1. No feasible configuration under declared risk and trade constraints.
2. Any missing lineage, leakage, or invalid holdout usage.

## Dependencies
1. Data providers: backend historical bars from approved provider routes.
2. Execution venues: MT5 execution profile with spread/slippage safeguards.
3. Infrastructure: backend API, database lineage logging, model artifact store.

