# 17 Promotion Readiness Gap Review

System ID: TS-001
Review date: 2026-05-27
Reviewer: Copilot (GPT-5.3-Codex)
Status: Action required

## Update
2026-05-27 update: the historical runner now includes walk-forward threshold selection with embargo and cost-aware plus stress-cost reporting. Remaining blockers are promotion-grade selection objective hardening, fuller execution-cost realism, and gate sign-off evidence completion.

## Scope
This review evaluates TS-001 promotion readiness against the gate framework defined in [08_promotion_gates.md](08_promotion_gates.md) and the governance policy in [../robust_trading_no_curve_fit_plan.md](../robust_trading_no_curve_fit_plan.md).

## Findings (Ordered by Severity)

### Critical
1. No walk-forward or embargo implementation exists in the active historical runner.
Evidence:
- Validation policy requires purged walk-forward testing in [06_validation_protocol.md#L19](06_validation_protocol.md#L19).
- Runner uses a fixed train/test split and chunked train windows only in [../../../training/run_historical_split.py#L194](../../../training/run_historical_split.py#L194) and [../../../training/run_historical_split.py#L199](../../../training/run_historical_split.py#L199).
Risk:
- High overfitting risk and non-robust model selection confidence.
Required action:
- Add explicit walk-forward fold generation, purge/embargo controls, and fold-level artifact outputs.

2. Trading metrics are computed from simplified return proxy and are not cost-complete for promotion decisions.
Evidence:
- Strategy metrics are generated directly from future returns in [../../../training/run_historical_split.py#L105](../../../training/run_historical_split.py#L105) and net return in [../../../training/run_historical_split.py#L123](../../../training/run_historical_split.py#L123).
- Validation policy marks cost-stress testing as mandatory in [06_validation_protocol.md#L20](06_validation_protocol.md#L20).
Risk:
- Promotion could be based on inflated expectancy and PF.
Required action:
- Integrate spread/slippage/commission assumptions and stress-matrix scenarios into the runner artifacts.

### High
3. Gate ownership and verification are incomplete.
Evidence:
- All gates are not complete in [08_promotion_gates.md#L10](08_promotion_gates.md#L10) through [08_promotion_gates.md#L14](08_promotion_gates.md#L14).
- Traceability verification remains pending in [13_audit_traceability.md#L25](13_audit_traceability.md#L25) through [13_audit_traceability.md#L29](13_audit_traceability.md#L29).
Risk:
- No accountable sign-off trail for promotion decisions.
Required action:
- Assign named reviewers/owners and completion dates for each gate and traceability row.

4. Live-readiness gate has no executed evidence path yet.
Evidence:
- Gate E is Not started in [08_promotion_gates.md#L14](08_promotion_gates.md#L14).
- Live operations profile defines process but not completed evidence records in [09_live_operations.md#L7](09_live_operations.md#L7).
Risk:
- Micro-live progression may occur without prior paper validation.
Required action:
- Add paper-run evidence artifact schema and enforce 6-week minimum pass requirement before micro-live.

### Medium
5. Metric thresholds are still draft and not approved as release policy.
Evidence:
- Draft threshold language in [08_promotion_gates.md#L16](08_promotion_gates.md#L16) and [16_metric_definitions.md](16_metric_definitions.md).
Risk:
- Inconsistent decisions between runs or operators.
Required action:
- Freeze threshold table version and require change-control approval for modifications.

6. Documentation completeness is good, but gate-readiness remains explicitly blocked.
Evidence:
- Docs marked complete in [14_document_completion_checklist.md#L8](14_document_completion_checklist.md#L8).
- Gate readiness all No in [14_document_completion_checklist.md#L27](14_document_completion_checklist.md#L27) with blockers in [14_document_completion_checklist.md#L37](14_document_completion_checklist.md#L37).
Risk:
- False sense of readiness from documentation completeness alone.
Required action:
- Keep separate statuses for doc-complete vs gate-complete and report both in every run.

## Gate-by-Gate Readiness
1. Gate A Data/Lineage: In progress, not ready.
2. Gate B Statistical Robustness: Not ready (no WF/embargo evidence).
3. Gate C Trading Risk: Not ready (cost-complete risk evidence missing).
4. Gate D Operational Reliability: In progress, not ready.
5. Gate E Live Readiness: Not started.

## Recommended Execution Plan

### Phase 1 (Immediate)
1. Implement purged walk-forward folds and fold-level reporting in the historical runner.
2. Add explicit cost model parameters and stress scenarios.
3. Emit a gate-evaluator JSON with PASS/FAIL per gate.

### Phase 2 (Evidence Hardening)
1. Add reviewer ownership and sign-off fields to gate and traceability docs.
2. Produce paper-trading evidence template and first paper run.
3. Update run reports to include both gate outcomes and invalid-run checks.

### Phase 3 (Promotion Decision)
1. Re-run TS-001 under new protocol.
2. Re-score all gates from evidence, not narrative.
3. Decide REJECT, PAPER_ONLY, MICRO_LIVE, or PROMOTE.

## Conclusion
TS-001 documentation structure is strong, but promotion readiness is not yet met. The blocking technical gap is lack of purged walk-forward plus cost-complete stress validation evidence.