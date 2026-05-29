# 08 Promotion Gates

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Gate summary
| Gate | Requirement | Evidence | Status |
|---|---|---|---|
| A Data and Lineage | Reproducible artifacts, full lineage, no leakage flags | [13_audit_traceability.md](13_audit_traceability.md) | In progress |
| B Statistical Robustness | Positive median out-of-sample expectancy across folds | [06_validation_protocol.md](06_validation_protocol.md) | In progress |
| C Trading Risk | Profit factor and drawdown inside approved thresholds | [07_risk_safety.md](07_risk_safety.md) | In progress |
| D Operational Reliability | Logging, latency, and safety checks pass | [09_live_operations.md](09_live_operations.md) | In progress |
| E Live Readiness | Paper pass before micro-live | [09_live_operations.md](09_live_operations.md) | Not started |

## Draft numeric thresholds
1. Minimum holdout trades: 80.
2. Profit factor floor: 1.20.
3. Max drawdown ceiling: 12%.
4. Expectancy floor: positive after costs.

## Current gate posture
1. TS-001 remains in discovery and is not promotion-ready.
2. Current evidence includes one historical split run and strategy-proxy metrics.
3. Full walk-forward and stress-cost matrix still required.

## Current decision
- Result: REJECT for promotion.
- Allowed path: continue research and paper-only progression after protocol completion.
- Decision owner: Trading + AI Engineering.
- Decision date: 2026-05-27.
