# Moschops User Guide

Version: 1.0  
Last updated: 2026-05-24  
Audience: Operators, analysts, admins, QA, and strategy/ML contributors

## 1. Purpose
This guide explains how to use the full Moschops platform from first startup through daily operation, with deeper focus on AI model training and training-quality interpretation.

Primary goals:
- Run the system safely with risk-first behavior.
- Operate the dashboard efficiently by role.
- Train and evaluate AI models using reproducible workflows.
- Understand what model metrics do and do not imply for live trading.

## 2. Safety-First Principles
Before any use, align with these non-negotiables:
- Fail-closed posture: if required systems are unavailable, no unsafe implicit trade behavior should occur.
- Risk gates before speed: risk and kill-switch controls are more important than convenience.
- Auditability: every operationally meaningful action should be traceable.
- No single-metric decisions: never rely on one model metric alone to approve live use.

## 3. System Overview
Moschops includes:
- MQL5 Expert Advisor runtime (execution and broker interaction).
- Backend API (Fastify + TypeScript) for signal/risk/training/services.
- Dashboard (Vue) as operator console.
- PostgreSQL persistence for runs, metrics, lineage, and operational records.
- Python training pipeline for walk-forward model development and ONNX export.

At a high level:
1. Data is ingested/stored.
2. Models are trained and validated.
3. Model artifacts are loaded by runtime.
4. Signal/risk logic uses configured thresholds and controls.
5. Operators monitor outcomes and retrain when needed.

## 4. Roles and Responsibilities
Use the dashboard role controls to reflect real responsibilities.

### Viewer
- Read-only monitoring.
- No training/runtime policy changes.

### Analyst
- Launch training and inspect diagnostics.
- Tune strategy runtime settings within policy.
- Investigate failed runs and data quality issues.

### Admin
- Full operational control.
- Policy-sensitive actions (promotion/rollback, toggles, emergency procedures).
- Accountable for change governance and incident decisions.

## 5. Accessing the Platform
Typical local URLs:
- Backend API: http://localhost:3000
- Dashboard: Vite local URL (for example http://127.0.0.1:5175)

Recommended startup sequence:
1. Start database.
2. Start backend and verify health endpoint.
3. Start dashboard.
4. Confirm key surfaces (risk banner, system health, training studio).

## 6. Dashboard Navigation Guide
Main views are arranged by operational function.

### Overview
Use for quick posture checks:
- Global risk state.
- Active strategy and latest model.
- Incident summary and high-level health.

### Portfolio
Use for exposure/risk distribution checks and position-level context.

### Trades and Signals
Use for signal lifecycle tracing and acceptance/rejection understanding.

### AI and Models
Use for model metadata, score behaviors, and quality/drift context.

### Training Studio (core AI workflow)
Primary workspace for training launch, diagnostics, and evidence review.

### Risk and Safety
Use for kill-switch state, limits, and veto visibility.

### System Health
Use for dependency/runtime status and service degradations.

### Incidents and Runbooks
Use when triaging operational issues or policy breaks.

### Admin / Settings
Use for controlled configuration updates.

## 7. Training Studio Deep Guide
Training Studio is the main AI lifecycle interface.

It provides:
- Preset launcher for quick, safe starts.
- Advanced parameters for controlled experimentation.
- Runtime preflight check for Python/training dependency readiness.
- Historical data download and preview.
- Diagnostic charts and confusion matrix.
- Session timeline with outcome metrics.

### 7.1 Preset Launcher
Use presets when you want predictable defaults.

Typical operator flow:
1. Select Easy or Advanced mode.
2. Choose preset (Balanced Intraday, High Precision, High Recall).
3. Review runtime estimate and resource profile.
4. Launch run or switch to wizard for guided setup.

### 7.2 Runtime Preflight Check
Use Check Training Runtime before launch if there is any environment uncertainty.

What it validates:
- Python interpreter resolution.
- Python version visibility.
- Required package imports (pandas, numpy, sklearn, onnx, skl2onnx).

If preflight fails:
- Do not launch training until corrected.
- Fix interpreter path/dependencies first.

### 7.3 Historical Data Download and Validation
Before model training, verify data coverage.

Workflow:
1. Select symbol/timeframe/date range.
2. Download and persist historical bars.
3. Review job history (inserted/skipped/error).
4. Validate range continuity in preview chart/table.

Do not trust training results built on incomplete or incorrect data slices.

### 7.4 Strategy Runtime Settings and AI Policy
These settings are operationally sensitive and should reflect governance decisions.

Key controls:
- AI full threshold.
- AI half threshold.
- AI mandatory mode.
- Risk profile label.
- Training defaults (dataset profile, folds, calibration, feature toggles).

Save strategy settings before or with launch so runtime and training assumptions stay aligned.

### 7.5 Guided Training Wizard (6-step)
Wizard steps:
1. Workflow (mode + preset)
2. Data and validation
3. Feature toggles
4. AI runtime policy
5. Review and launch
6. Completion (links back to diagnostics/timeline)

Recommended use:
- Prefer wizard for production-like runs.
- Use direct launch for quick exploratory checks only.

### 7.6 Launching a Training Run
When launching:
1. Backend persists run as RUNNING.
2. Python pipeline executes with selected parameters.
3. Artifact/metrics are loaded and persisted.
4. Run transitions to COMPLETED or FAILED.

If FAILED:
- Read failure reason and execution telemetry.
- Check runtime preflight, data profile validity, and package availability.

## 8. AI Training Metrics: How to Read Them
This section explains practical interpretation.

### 8.1 Outcome Percentages (Latest Completed Run)
Training Studio surfaces percentage-style metrics for quick interpretation:
- Estimated Successful Trade Likelihood.
- Overall Accuracy.
- Positive Capture Rate.
- Signal Coverage Rate.
- Model Skill vs Random.
- Calibration Alignment.
- Worst Fold Strength.
- Probability Stability.
- Overall Training Effectiveness (prominent summary score).

Important:
- Estimated Successful Trade Likelihood is derived from historical precision from the training session.
- It is an estimate, not a live-profit guarantee.

### 8.2 Core Definitions
- Precision: $TP/(TP+FP)$
- Recall: $TP/(TP+FN)$
- Accuracy: $(TP+TN)/(TP+TN+FP+FN)$
- AUC: Ranking quality across thresholds (higher generally better).
- Brier score: Probability error magnitude (lower better).
- Calibration drift: Gap between predicted and observed frequencies (lower better).

### 8.3 Why Multiple Metrics Matter
A model can appear strong on one metric but weak operationally:
- High precision with very low coverage may under-trade.
- Good AUC with poor calibration can mis-size risk.
- Acceptable mean quality with weak worst-fold can be unstable.

Use the combined panel and diagnostics, not a single number.

### 8.4 Overall Training Effectiveness
Overall Training Effectiveness is a weighted summary designed for quick operator triage.

Use it as:
- A top-level indicator for relative comparison between runs.

Do not use it as:
- A standalone promotion decision.

Always pair with:
- Confusion matrix.
- ROC/PR shape.
- Calibration bins.
- Feature importance plausibility.
- Strategy/risk context.

## 9. Diagnostic Visuals: Practical Reading
### ROC Curve
- Closer to upper-left is better discrimination.
- If close to baseline diagonal, discrimination is weak.

### Precision-Recall Curve
- More informative than ROC for imbalanced positive classes.
- Watch precision degradation as recall increases.

### Calibration Reliability Bins
- Predicted vs observed should align reasonably.
- Large systematic offsets indicate calibration risk.

### Feature Importance
- Validate top drivers are plausible and stable.
- Sudden rank inversions may indicate data or leakage problems.

### Confusion Matrix
- Use to understand operational consequences of thresholding:
  - False positives: low-quality entries.
  - False negatives: missed opportunities.

## 10. End-to-End AI Workflow (Recommended)
1. Verify backend and runtime health.
2. Refresh/download historical data for intended symbol/timeframe.
3. Run runtime preflight.
4. Launch training via wizard.
5. Confirm run completion and inspect outcomes.
6. Review diagnostics for consistency and robustness.
7. Compare against recent runs in timeline.
8. Save decision rationale before any promotion step.

## 11. Troubleshooting
### Training launch fails immediately
Check:
- Backend is reachable.
- CORS/preflight is configured for required methods.
- Strategy settings save endpoint is available.

### Runtime check fails
Check:
- Interpreter path configuration.
- Missing Python packages.
- Windows alias/path confusion for python command.

### Run status is FAILED
Check:
- Failure reason in run payload.
- Execution telemetry stderr/stdout tails.
- Dataset profile and parameter compatibility.
- Generated artifact validity/parsing.

### Metrics show N/A
Common causes:
- No completed runs yet in current state.
- Diagnostics payload unavailable/invalid.
- Data not loaded for latest run view.

## 12. Operational Best Practices
- Run preflight before important launches.
- Keep parameter changes small between comparison runs.
- Track rationale for each run (why this config, expected effect).
- Treat high uncertainty runs as exploratory, not promotable.
- Favor consistency across folds and calibration over isolated peak metrics.

## 13. Governance and Change Discipline
For changes to runtime policy or training defaults:
- Prefer explicit save/apply actions.
- Validate in dashboard immediately after write.
- Record reason and expected impact.
- Roll back quickly if health/risk posture degrades.

## 14. Quick Operator Checklists
### Pre-Launch Checklist
- Backend/API healthy.
- Historical coverage validated.
- Runtime preflight green.
- Threshold policy reviewed.
- Wizard review step passed.

### Post-Launch Checklist
- Run completed.
- Outcome percentages reviewed.
- Diagnostics reviewed.
- Timeline comparison done.
- Decision/rationale captured.

## 15. Glossary
- AUC: Area under ROC curve.
- Brier: Mean squared probability error.
- Calibration: Agreement between predicted probabilities and realized frequencies.
- Coverage: Fraction of cases predicted positive at threshold.
- Drift: Deviation between expected and observed distributions/behavior.
- Precision: Correct positive predictions among all positive predictions.
- Recall: Correct positive predictions among all actual positives.

## 16. Related References
- ../05-ui/ui_design.md
- ../03-specifications/api_contract_specification.md
- ../03-specifications/data_dictionary_and_lineage.md
- ../03-specifications/model_governance_standard.md
- ../04-operations/incident_and_operations_runbooks.md
- ../00-governance/implementation_runbook.md

## 17. Guide Maintenance
Update this guide when any of the following change:
- Dashboard workflows or labels.
- Training API payload/behavior.
- Model quality metrics semantics.
- Risk policy controls.
- Promotion/rollback procedures.

## 18. How-To Playbooks (Task-Based)
This section provides direct task recipes for all core workflows covered in this guide.

### 18.1 How to Start the Full Local Stack
1. Start the database service.
2. Start backend services.
3. Start dashboard services.
4. Confirm backend health endpoint returns status ok.
5. Confirm dashboard loads and navigation renders.

### 18.2 How to Verify Backend and Runtime Health
1. Check backend health endpoint.
2. Open System Health view and confirm database and model status.
3. In Training Studio, run Check Training Runtime.
4. Proceed only if runtime check is healthy or remediation is complete.

### 18.3 How to Set Operator Context Safely
1. Choose correct environment selector value (dev, demo, pilot, live).
2. Select the correct operator role.
3. Select intended strategy and dataset profile context.
4. Confirm date range context before interpreting metrics.

### 18.4 How to Perform a Pre-Session Go or No-Go Check
1. Open Overview and verify risk posture.
2. Check kill-switch status is expected.
3. Review active incidents and alert severity.
4. Open Risk and Safety for limit posture.
5. If severe warning exists, pause non-essential launches.

### 18.5 How to Download and Validate Historical Training Data
1. Open Training Studio historical data controls.
2. Set symbol, timeframe, and date range.
3. Run Download Historical Data.
4. Inspect inserted vs skipped counts in job history.
5. Validate first and last bar timestamps and price continuity in preview.

### 18.6 How to Run Python Training Runtime Preflight
1. In Training Studio, click Check Training Runtime.
2. Confirm interpreter path and Python version are shown.
3. Confirm required package checks pass.
4. If any package is missing, install dependencies before launching training.

### 18.7 How to Configure AI Runtime Policy
1. Set AI full threshold and AI half threshold with half below full.
2. Set AI mandatory mode according to policy.
3. Select risk profile label.
4. Save Strategy Settings.
5. Confirm persisted timestamp updates.

### 18.8 How to Launch a Quick Training Run
1. Select Easy mode.
2. Choose a preset.
3. Review launch summary values.
4. Click Launch Training Run.
5. Confirm session appears in timeline with RUNNING then COMPLETED or FAILED.

### 18.9 How to Launch Training Through the Wizard
1. Click Open Training Wizard.
2. Complete workflow/preset step.
3. Set data and validation parameters.
4. Set feature toggles.
5. Confirm AI runtime policy.
6. Review final launch summary.
7. Click Save Settings and Launch.
8. Use completion shortcuts to jump to diagnostics and timeline.

### 18.10 How to Read the Overall Training Effectiveness Percentage
1. Open Training Outcome panel in Training Studio.
2. Read Overall Training Effectiveness as an at-a-glance quality indicator.
3. Treat it as comparative guidance, not a standalone approval signal.
4. Validate supporting percentage cards below it before decisions.

### 18.11 How to Interpret Estimated Successful Trade Likelihood
1. Locate Estimated Successful Trade Likelihood in Training Outcome.
2. Read it as training precision-derived estimate.
3. Cross-check with coverage and recall metrics.
4. Do not treat it as guaranteed live hit-rate or profitability.

### 18.12 How to Review Model Diagnostics Before Promotion Consideration
1. Check confusion matrix for false-positive and false-negative balance.
2. Check ROC and PR shapes for discrimination quality.
3. Check calibration bins for predicted vs observed alignment.
4. Check feature importance plausibility.
5. Compare against recent completed sessions.

### 18.13 How to Compare Training Runs in the Timeline
1. Open Training Sessions and Timeline table.
2. Filter mentally by dataset profile, model version, and creation time.
3. Compare AUC, Brier, and outcome percentages across runs.
4. Prefer stable improvements over one-off spikes.

### 18.14 How to Investigate a Failed Training Run
1. Find failed run entry in timeline.
2. Inspect failure reason and execution telemetry.
3. Verify runtime preflight status.
4. Verify dataset profile and parameter validity.
5. Fix root cause and rerun with same config for reproducibility check.

### 18.15 How to Use AI and Models View for Readiness Context
1. Open AI and Models view.
2. Review score distribution and drift indicators.
3. Compare active model context with latest training outcomes.
4. Escalate if drift or inconsistency exceeds expected bounds.

### 18.16 How to Validate Signal Quality in Trades and Signals
1. Open Trades and Signals view.
2. Inspect accepted and rejected signal patterns.
3. Cross-check with configured AI thresholds and risk gates.
4. Confirm rejection reasons match policy expectations.

### 18.17 How to Perform Risk and Safety Verification
1. Open Risk and Safety view.
2. Confirm kill-switch status and recent history.
3. Review daily and weekly loss posture.
4. Check veto breakdown by cause.
5. Pause risky operations if limits or veto behavior are abnormal.

### 18.18 How to Handle Incidents Using Runbooks
1. Open Incidents and Runbooks view.
2. Identify incident severity and affected subsystem.
3. Execute runbook steps in order.
4. Record action, reason, and timestamps.
5. Verify recovery and close with evidence.

### 18.19 How to Perform Admin Changes with Change Control
1. Confirm you are in admin role and correct environment.
2. Make one policy or config change at a time.
3. Save and validate immediate health impact.
4. Record rationale, expected outcome, and rollback criteria.
5. If negative impact appears, rollback immediately.

### 18.20 How to Shut Down Safely After a Session
1. Confirm no critical job is mid-flight unless intentionally stopped.
2. Capture any unresolved warnings or incident notes.
3. Stop dashboard.
4. Stop backend.
5. Stop local database if appropriate for your environment.
