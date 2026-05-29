# Trading Systems Lab Operating Model

Version: 1.0
Last updated: 2026-05-27
Status: Active

## Mission
Turn this folder into a repeatable strategy lab that produces robust, promotable systems with clear evidence and no backtest bending.

## What Counts As A Winning System
A system is considered winning only when all are true:
1. Positive out-of-sample expectancy after realistic costs.
2. Drawdown and risk metrics remain inside hard limits.
3. Results are stable across folds, regimes, and stress scenarios.
4. Evidence is reproducible and auditable end-to-end.

## Lab Workflow (Stage Gates)
1. Idea intake.
2. Design specification.
3. Data and feature contract lock.
4. Validation execution.
5. Gate evaluation.
6. Paper-trading qualification.
7. Micro-live qualification.

No stage can be skipped.

## Folder Conventions
1. One folder per system: TS-001, TS-002, and so on.
2. Shared templates live only in templates.
3. Every TS folder must contain README, _INDEX, and required core docs.
4. Every TS must include an experiment log and promotion gate record.

## Experiment Rules
1. One hypothesis at a time.
2. One major change per experiment batch.
3. Track all attempts, including failures.
4. Holdout is acceptance-only, never tuning.
5. Any invalid run is marked INVALID_FOR_PROMOTION.

## Standard Run Pack
Each promoted evidence run must produce:
1. Run report with windows, metrics, and gate outcomes.
2. Artifact manifest with model path, config hash, and data window metadata.
3. Cost assumptions and stress matrix outcomes.
4. Fold-level statistics and regime slices.

## Decision Cadence
1. Weekly: strategy review for each active TS.
2. Bi-weekly: gate review board for readiness decisions.
3. Monthly: threshold and process governance review.

## Roles
1. Strategy owner: hypothesis quality and strategy logic.
2. Data owner: data integrity and feature contract.
3. Validation owner: protocol execution and statistical integrity.
4. Risk owner: risk controls and safety readiness.
5. Approver: final promotion decision sign-off.

## Mandatory Controls
1. No promotion without all gates PASS.
2. No manual overrides without documented rationale and expiry.
3. No missing lineage fields in promotion artifacts.
4. No paper-to-live jump without required observation period.

## Initial 30-Day Execution Plan
1. Freeze TS-001 thresholds and gate owners.
2. Implement walk-forward plus embargo in training pipeline.
3. Add cost stress matrix to validation outputs.
4. Build gate evaluator output file for deterministic decisions.
5. Launch TS-002 from template with contrasting strategy thesis.

## References
1. [README.md](README.md)
2. [robust_trading_no_curve_fit_plan.md](robust_trading_no_curve_fit_plan.md)
3. [templates/README.md](templates/README.md)
