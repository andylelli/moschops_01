# 08 Promotion Gates

System ID: TS-002

## Gate summary
| Gate | Requirement | Evidence | Status |
|---|---|---|---|
| A Data and Lineage | Reproducible, complete lineage, no leakage | Run pack + lineage manifest | Pending |
| B Statistical Robustness | Positive median OOS expectancy and stable fold behavior | Walk-forward report | Pending |
| C Trading Risk | Hard DD and minimum-trade constraints satisfied | Gate evaluator output | Pending |
| D Operational Reliability | Logs/latency/safety pass | Ops validation report | Pending |
| E Live Readiness | Paper then micro-live pass | Paper and micro-live reviews | Pending |

## Numeric thresholds
1. Minimum trades: 80 median across development folds.
2. PF floor: 1.05 post-cost in holdout.
3. DD ceiling: -15.0% max drawdown in acceptance evidence.
4. Expectancy floor: positive median post-cost expectancy across folds.

## Decision
- Result: REJECT / PAPER_ONLY / MICRO_LIVE / PROMOTE
- Decision owner: Pending assignment
- Decision date: Pending
- Override rationale (if any): None

