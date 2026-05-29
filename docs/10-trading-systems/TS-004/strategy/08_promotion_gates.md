# 08 Promotion Gates

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Gate summary

| Gate | Requirement | Evidence document | Status |
|---|---|---|---|
| A Data and Lineage | Full reproducible artifacts, lineage, no leakage flags | [13_audit_traceability.md](13_audit_traceability.md) | Not started |
| B Statistical Robustness | Positive out-of-sample expectancy across ≥ 60% of folds, AUC ≥ 0.53, PBO < 0.40 | [06_validation_protocol.md](06_validation_protocol.md) | Not started |
| C Trading Risk | PF ≥ 1.25, max DD ≤ 20%, ≥ 60 holdout trades, expectancy > 5 bps | [07_risk_safety.md](07_risk_safety.md) | Not started |
| D Operational Reliability | Logging, latency, safety checks, circuit breaker verified in paper mode | [09_live_operations.md](09_live_operations.md) | Not started |
| E Live Readiness | Paper trading pass ≥ 30 days before micro-live | [09_live_operations.md](09_live_operations.md) | Not started |

## Numeric thresholds

### Gate B: Statistical Robustness

| Metric | Threshold | Measured on |
|---|---|---|
| Out-of-sample AUC (median across folds) | ≥ 0.53 | Dev CV |
| Brier score | ≤ 0.25 | Dev CV |
| Probability of backtest overfitting (PBO) | < 0.40 | Dev CV |
| CV fold consistency (% folds with PF > 1.00) | ≥ 60% | Dev CV |

### Gate C: Trading Risk

| Metric | Threshold | Measured on |
|---|---|---|
| Holdout trade count | ≥ 60 | Holdout run |
| Profit factor | ≥ 1.25 | Holdout run |
| Maximum drawdown | ≤ 20% | Holdout run |
| Expectancy per trade | > 5 bps (after base costs) | Holdout run |
| P95 Monte Carlo drawdown | ≤ 25% | MC simulation on holdout |
| Stress PF (2× spread, 3× slippage) | ≥ 1.00 | EXP-005 stress test |

### Gate D: Operational Reliability

| Check | Threshold |
|---|---|
| Backend API P95 latency | ≤ 100 ms |
| Signal delivery latency | ≤ 200 ms (FMP fetch + inference + DB write) |
| Logging coverage | 100% signals logged with probability and metadata |
| Circuit breaker functional test | Verified to trip and cool down correctly |
| Fail-closed test | EA confirmed to not trade when backend unreachable |

### Gate E: Live Readiness

| Check | Threshold |
|---|---|
| Paper trading duration | ≥ 30 calendar days |
| Paper signal count | ≥ 20 valid signals in paper window |
| Paper vs. backtest expectancy deviation | < 15% |
| No system incidents (P1/P2) during paper period | 0 unresolved incidents |

## Current gate posture

TS-004 is in the Discovery phase. No training runs have been executed. All gates are **Not started**.

The ordered progression is:
1. Complete EXP-001 through EXP-005 in dev window.
2. Select best dev config by constrained optimisation.
3. Execute single locked holdout run.
4. Evaluate Gates B and C against holdout evidence.
5. If Gates B and C pass: proceed to paper trading for Gate D + E evidence.
6. If any gate fails: document result in `11_experiment_log.md` and assess retirement.

## Current decision

| Field | Value |
|---|---|
| Result | REJECT for promotion |
| Reason | Discovery phase — no evidence collected yet |
| Allowed path | Research and development experiments only |
| Decision owner | Trading + AI Engineering |
| Decision date | 2026-05-28 |
| Next review trigger | After locked holdout run |
