# 11 Experiment Log

System ID: TS-002

## Experiment entries
| Date | Experiment ID | Hypothesis | Single change made | Result | Decision |
|---|---|---|---|---|---|
| 2026-05-27 | EXP-001 | Compression confirmation reduces false entries after volatility spikes versus pure overextension entries | Add compression confirmation feature and baseline threshold policy | Pending execution | Continue |
| 2026-05-27 | EXP-002 | Adaptive stop distance by volatility regime lowers drawdown without killing expectancy | Replace fixed stopAtr with regime-conditioned stop multiplier | Pending execution | Continue |
| 2026-05-27 | EXP-003 | News/session blackout filter improves risk-adjusted outcomes by removing structurally adverse windows | Add deterministic blackout filter only | Pending execution | Continue |

## Required fields per entry
1. Pre-registered hypothesis.
2. Exact config diff versus prior run.
3. Train/validation/holdout windows used.
4. Trial count to date.
5. Links to artifacts and report.

## Integrity rules
1. No deletion of failed experiments.
2. No undocumented reruns.
3. Mark invalid runs explicitly.
4. If hard feasibility constraints fail, mark run block as POLICY_BLOCKED and do not execute holdout.


