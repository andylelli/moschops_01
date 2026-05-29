# TS-002: Mean-Reversion Volatility Compression

Version: 0.1
Last updated: 2026-05-27
Status: In discovery
Owner: Trading + AI Engineering

## 1) System Summary
TS-002 targets short-horizon mean reversion after volatility spikes and range extension.

Base idea:
1. Detect volatility expansion and local overextension.
2. Permit entry only when compression evidence appears.
3. Use strict risk containment and fail-closed execution guards.
4. Require out-of-sample stability before any promotion consideration.

Primary objective:
1. Positive out-of-sample expectancy after realistic costs.
2. Max drawdown at or above -15% under gate definitions.
3. Stable fold/regime behavior with auditable lineage.

## 2) Scope
1. Instruments: FX majors.
2. Initial symbol: EURUSD.
3. Timeframes: H1 primary, H4 secondary.
4. This system is intentionally distinct from TS-001 trend breakout behavior.

## 3) Document Map
1. [_INDEX.md](_INDEX.md)
2. [00_system_charter.md](00_system_charter.md)
3. [01_strategy_spec.md](01_strategy_spec.md)
4. [06_validation_protocol.md](06_validation_protocol.md)
5. [07_risk_safety.md](07_risk_safety.md)
6. [08_promotion_gates.md](08_promotion_gates.md)
7. [11_experiment_log.md](11_experiment_log.md)

## 4) First Sprint Priorities
1. Finalize data contract and feature schema for H1/H4 volatility-compression features.
2. Execute first three pre-registered experiments in [11_experiment_log.md](11_experiment_log.md).
3. Produce one full 9-dev plus 1 holdout evidence cycle under fail-closed gate policy.

## 5) Governance References
1. [../robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md)
2. [../LAB_OPERATING_MODEL.md](../LAB_OPERATING_MODEL.md)
3. [../TS_BACKLOG.md](../TS_BACKLOG.md)