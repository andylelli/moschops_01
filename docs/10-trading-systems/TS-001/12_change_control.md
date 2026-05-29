# 12 Change Control

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Change request table
| Change ID | Type | Description | Risk impact | Approval required | Status |
|---|---|---|---|---|---|
| CR-001 | Training pipeline | Added historical split runner and strategy backtest metrics | Medium | Yes | Implemented |
| CR-002 | Documentation | Created TS-001 full governance documentation set | Low | No | Implemented |
| CR-003 | Validation protocol | Introduce purged walk-forward + stress-cost matrix | High | Yes | Planned |

## Change categories
1. Parameter-only updates.
2. Strategy logic updates.
3. Data and feature contract updates.
4. Model family and threshold updates.
5. Risk and safety policy updates.

## Approval policy
1. High-risk changes require pre-approval and rationale before test execution.
2. Any holdout-touching change requires a new holdout definition and explicit prior-run invalidation if reused.
3. Promotion-affecting changes require full gate re-evaluation.

## Traceability expectations
1. Every change ID must reference affected docs and run artifacts.
2. Each change must map to one hypothesis in experiment log.
3. Unapproved production-path changes are prohibited.
