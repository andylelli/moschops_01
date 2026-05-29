# Training Run Index

Generated: 2026-05-27 21:09:00

| Run Folder | Local Timestamp | Overall % | Verdict | Trades | Profit Factor | Net Profit | Report |
|---|---:|---:|---|---:|---:|---:|---|
| 2026-05-27_19-29 | 2026-05-27:19:29 | 48.35 | FAIL | 3 | 0.88 | -337.86 | [2026-05-27_19-29](runs/2026-05-27_19-29/RUN_REPORT.md) |
| 2026-05-27_19-34 | 2026-05-27:19:34 | 48.35 | FAIL | 3 | 0.88 | -337.86 | [2026-05-27_19-34](runs/2026-05-27_19-34/RUN_REPORT.md) |
| 2026-05-27_19-43-historical-10y-2y | 2026-05-27:19:54 | 36.94 | FAIL | 96 | 2.43 | 26.97% | [2026-05-27_19-43-historical-10y-2y](runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md) |

## Notes
- Folder names use yyyy-MM-dd_HH-mm because Windows does not allow : in folder names.

## TS-001 10-Run Lab Cycle

| Run Folder | Protocol | Result | Holdout Executed | Evidence |
|---|---|---|---|---|
| 2026-05-27_21-00-ts001-10run-lab | Unconstrained fallback allowed | Completed; best dev selected and holdout executed; holdout drawdown remained above target | Yes | [summary.csv](runs/2026-05-27_21-00-ts001-10run-lab/summary.csv) |
| 2026-05-27_21-04-ts001-10run-lab | Hard constraints requested but fallback still allowed | Completed; all dev runs infeasible (`constraintsSatisfied=false`) yet holdout still executed due to fallback | Yes | [summary.csv](runs/2026-05-27_21-04-ts001-10run-lab/summary.csv) |
| 2026-05-27_21-07-ts001-10run-lab | Hard constraints with fail-closed policy | Blocked by policy: zero feasible dev runs; holdout intentionally not executed | No | [summary.csv](runs/2026-05-27_21-07-ts001-10run-lab/summary.csv), [selection_blocker.json](runs/2026-05-27_21-07-ts001-10run-lab/selection_blocker.json) |
