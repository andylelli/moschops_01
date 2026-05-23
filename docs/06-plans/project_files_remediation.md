# Project Files Remediation Plan

Version: 1.0
Last updated: 2026-05-22
Status: Proposed

## 0) Validation Status (10 Passes Completed)
This remediation plan was re-validated in 10 passes against repository state and authority documents.

Pass summary:
1. Structure and scope completeness: PASS
2. Authority alignment (LLD/API/spec/roadmap): PASS with minor drift notes
3. Governance consistency checks: PASS with confirmed contradictions
4. Backend route coverage checks: PASS with confirmed missing news routes
5. Data model coverage checks: PASS with confirmed missing news tables
6. Risk and strategy behavior checks: PASS with confirmed control gaps
7. Frontend contract conformance checks: PASS with confirmed placeholder/state gaps
8. Workstream-to-finding mapping check: PASS with additions required
9. Endpoint response semantics check: FAIL initially, remediated in this revision
10. Verification/testability check: PASS with dependency/CI evidence caveat

Validation outcome:
- Accurate overall direction: YES
- Complete as originally written: NO
- Added missing findings in this revision: YES

## 1) Objective
Run a full documentation and implementation consistency remediation across docs, backend, and dashboard with explicit classification:
- `CODE_WRONG`: implementation does not meet authoritative requirement.
- `DOC_WRONG`: documentation conflicts with authority or observed implementation.
- `BOTH_WRONG`: both implementation and docs need updates.

## 2) Three-Pass Review Method
### Pass 1: Authority and Internal Documentation Consistency
Compared authority stack and governance state:
- `docs/02-architecture/lld_v1.md`
- `docs/02-architecture/lld_v2.md`
- `docs/02-architecture/lld_v1_1_news.md`
- `docs/03-specifications/api_contract_specification.md`
- `docs/03-specifications/data_dictionary_and_lineage.md`
- `docs/01-roadmap/coding_plan.md`
- `docs/00-governance/implementation_runbook.md`
- `docs/00-governance/documentation_checklist.md`
- `docs/00-governance/requirements_traceability_matrix.md`

### Pass 2: Backend and Data Model Contract Conformance
Checked code and schema against contractual requirements:
- `backend/src/routes/*.ts`
- `backend/src/services/*.ts`
- `backend/src/plugins/*.ts`
- `backend/src/types/contracts.ts`
- `backend/prisma/schema.prisma`

### Pass 3: Frontend, Testing Reality, and Governance Evidence
Checked UI and evidence readiness against UI and runbook claims:
- `dashboard/src/**/*.vue`
- `dashboard/src/stores/ui.ts`
- `README.md`
- `backend/README.md`
- `backend/test/*.ts`

## 3) Full Findings List

## A. Authority/Documentation Findings

1. Finding A1 - Phase completion contradiction in governance docs (`BOTH_WRONG`, High)
- Evidence: `docs/00-governance/implementation_runbook.md` marks multiple phases complete at dashboard level while many phase tasks and exit criteria remain unchecked in the same file.
- Evidence: `docs/00-governance/requirements_traceability_matrix.md` still marks all requirements `Not verified`.
- Required change:
  - Normalize phase statuses in `implementation_runbook.md` to match unchecked tasks and non-verified RTM entries.
  - Add explicit blocker notes and verification evidence links.

2. Finding A2 - Documentation checklist status drift (`DOC_WRONG`, High)
- Evidence: `docs/00-governance/documentation_checklist.md` marks multiple docs `Not started` despite existing files populated under `docs/03-specifications` and `docs/04-operations`.
- Required change:
  - Reassess each checklist row against done criteria and set true status (`In progress` or `Done`) with owner and notes.

3. Finding A3 - Endpoint contract inconsistency for `/portfolio/evaluate` (`DOC_WRONG`, High)
- Evidence: `docs/03-specifications/api_contract_specification.md` and `docs/02-architecture/lld_v1_1_news.md` require `/portfolio/evaluate` participation.
- Evidence: `docs/02-architecture/lld_v1.md` endpoint list omits `/portfolio/evaluate`.
- Required change:
  - Update `lld_v1.md` API section to include `/portfolio/evaluate` or explicitly scope it to v1.2 with cross-reference.

4. Finding A4 - Data dictionary overstates implemented persistence entities (`DOC_WRONG`, Medium)
- Evidence: `docs/03-specifications/data_dictionary_and_lineage.md` lists entities not present in current Prisma schema (for current repo baseline), including news entities and additional training/raw market entities.
- Required change:
  - Add implementation-status markers per entity (planned vs implemented) or align schema in code.

## B. Backend/API/Data Findings

5. Finding B1 - Required news routes missing (`CODE_WRONG`, Critical)
- Missing routes:
  - `GET /news/upcoming`
  - `GET /news/active`
  - `GET /news/providers`
- Evidence: required by `docs/02-architecture/lld_v1_1_news.md` and `docs/03-specifications/api_contract_specification.md`.
- Required change:
  - Implement routes + schemas + tests + route registration.

6. Finding B2 - Health telemetry missing required news fields (`CODE_WRONG`, High)
- Evidence: `backend/src/routes/health.ts` only returns backend/database/model telemetry.
- Missing required fields:
  - `telemetry.newsProvider`
  - `telemetry.newsProviderTier`
  - `telemetry.newsFreshness`
- Required change:
  - Extend health payload and source values from provider status store.

7. Finding B3 - News persistence tables missing (`CODE_WRONG`, Critical)
- Evidence: `backend/prisma/schema.prisma` lacks:
  - `news_events`
  - `news_provider_status`
  - `news_guard_windows`
- Required change:
  - Add Prisma models + migration + indexes + repository access layer.

8. Finding B4 - `/signal` does not persist required feature lineage and prediction records (`CODE_WRONG`, High)
- Evidence: `backend/src/routes/signal.ts` stores `Signal` only.
- Missing persistence expected by docs:
  - `Feature` row with feature hash/dataset lineage.
  - `ModelPrediction` row with model/version/score linkage.
- Required change:
  - Add transactional writes for signal + features + model_prediction.

9. Finding B5 - Risk policy coverage incomplete vs LLD (`CODE_WRONG`, High)
- Evidence: `backend/src/services/risk-engine.ts` enforces only a subset.
- Missing/partial controls called out in LLD:
  - one-position-per-symbol
  - slippage guard behavior
  - correlation/directional exposure controls
  - metadata validation (`MISSING_METADATA` path)
  - kill-switch state machine semantics
- Required change:
  - Expand risk engine contracts and implement missing checks with reason codes.

10. Finding B6 - Strategy logic missing documented exit behavior (`CODE_WRONG`, High)
- Evidence: `backend/src/services/strategy.ts` only returns `BUY|SELL|HOLD`.
- LLD expects exit logic and decision path supporting `CLOSE|REDUCE` conditions.
- Required change:
  - Add exit rules and test fixtures for long/short exits and reduction cases.

11. Finding B7 - Plugin architecture not actually used by signal path (`BOTH_WRONG`, Medium)
- Evidence: `backend/src/plugins/strategy-plugin.ts` exists, but `/signal` uses `evaluateDailyBreakout` directly from service.
- Impact: runbook claims around plugin-swappability are not satisfied end-to-end.
- Required change:
  - Implement plugin registry and route decisioning through strategy plugin resolution.

12. Finding B8 - `/risk-check` audit logging is partial (`CODE_WRONG`, Medium)
- Evidence: `backend/src/routes/risk.ts` logs only vetoed events.
- Contract text states decisions should be logged for auditability.
- Required change:
  - Persist both approved and vetoed risk-check evaluations with standardized event types.

13. Finding B9 - Open trades contract is snapshot-history oriented, not clear current-state contract (`BOTH_WRONG`, Medium)
- Evidence: `backend/src/routes/trades-open.ts` returns last 100 records.
- Spec wording says current open-trade snapshot for dashboard.
- Required change:
  - Clarify contract in docs or change implementation to return latest per account/strategy/symbol projection.

## C. Frontend/UI and Evidence Findings

14. Finding C1 - Dashboard pages are mostly placeholders while runbook marks monitoring complete (`BOTH_WRONG`, High)
- Evidence: `dashboard/src/views/*.vue` frequently return `N/A` placeholders without live bindings.
- Required change:
  - Reclassify phase status as `In progress` until core KPI/risk/model/health bindings are live.
  - Implement missing data integrations.

15. Finding C2 - Required navigation surfaces missing (`CODE_WRONG`, Medium)
- Evidence: `dashboard/src/App.vue` navigation omits `Incidents and Runbooks` and `Settings` defined in UI spec.
- Required change:
  - Add routes/views and minimum functional shells with data contracts.

16. Finding C3 - Health/system view lacks required provider visibility (`CODE_WRONG`, High)
- Evidence: `dashboard/src/views/SystemHealthView.vue` has static placeholders and no provider/tier/freshness rendering.
- Required change:
  - Bind to health/news provider endpoints and display provider status per spec.

17. Finding C4 - Polling/freshness behavior not implemented per UI spec (`CODE_WRONG`, Medium)
- Evidence: limited one-shot fetch patterns (for example in `OverviewView.vue` and `TradesSignalsView.vue`).
- Required change:
  - Add polling cadence controls, stale-state indicators, and updated-at semantics per panel.

## D. Verification and Build Findings

18. Finding D1 - Local quality gate execution not reproducible without dependency install (`DOC_WRONG`, Medium)
- Observed in review environment: backend scripts fail because local toolchain dependencies not yet installed (`tsc` and `vitest` unavailable).
- Required change:
  - Ensure bootstrap instructions are always executed before claiming evidence.
  - Add CI-required checks to guarantee build/test evidence is present in PRs.

## E. Additional Contract Findings (Added During 10-Pass Validation)

19. Finding E1 - `/performance` contract coverage mismatch (`CODE_WRONG`, High)
- Evidence: API spec states `GET /performance` returns performance snapshots, risk events, and summary metrics.
- Evidence: implementation currently returns only recent performance snapshots.
- Required change:
  - Expand `GET /performance` response to include risk-event feed and summary aggregates, or narrow spec and update dependent docs in same change.

20. Finding E2 - Duplicate/conflict status semantics unclear vs implementation (`BOTH_WRONG`, Medium)
- Evidence: API spec includes `409` for duplicate/conflicting decision key.
- Evidence: `/signal` currently returns cached existing response on duplicate `decisionId` or `decisionKey` and does not emit `409` conflict path.
- Required change:
  - Clarify idempotent replay vs conflicting-request behavior in API contract.
  - Implement deterministic behavior: replay-safe duplicates return cached `200`; true conflicts return `409` with explicit error code.

## 4) Remediation Work Plan

### Workstream 1: Governance Truth Alignment (Priority P0)
- Update `implementation_runbook.md` to accurate phase/task statuses.
- Synchronize `documentation_checklist.md` statuses and owners.
- Link RTM verification evidence where available; mark explicit gaps.
- Exit criterion:
  - No contradiction between phase dashboard, task checklists, and RTM status.

### Workstream 2: News v1.1 Contract Implementation (Priority P0)
- Add Prisma models and migration for news entities.
- Implement provider status ingestion skeleton + freshness state source.
- Add `/news/upcoming`, `/news/active`, `/news/providers`.
- Extend `/health` telemetry with provider details and freshness.
- Add unit/integration tests for route contracts.
- Exit criterion:
  - All required v1.1 news routes and health telemetry are operational and tested.

### Workstream 3: Signal Lineage Completeness (Priority P0)
- Persist feature vectors and model prediction rows during `/signal` evaluation.
- Ensure decision lineage fields are linked across signal/prediction/features.
- Exit criterion:
  - Query path exists for `decisionId -> signal + features + model prediction`.

### Workstream 4: Risk Engine Coverage Completion (Priority P0)
- Implement missing risk controls and reason codes:
  - one-position-per-symbol
  - slippage guard
  - correlation exposure
  - metadata validation with `MISSING_METADATA`
  - kill-switch state model
- Exit criterion:
  - Risk simulation tests cover every LLD-mandated control.

### Workstream 5: Strategy/Plugin Contract Hardening (Priority P1)
- Route `/signal` through plugin registry abstraction.
- Add swap test proving strategy replacement without shared-module edits.
- Implement exit-rule behavior (`CLOSE`, optional `REDUCE`).
- Exit criterion:
  - Plugin swap and exit-rule tests pass.

### Workstream 6: Dashboard Contract Completion (Priority P1)
- Implement missing views/routes (`Incidents and Runbooks`, `Settings`).
- Replace placeholder cards with API-backed data for health/risk/model/trades.
- Add polling + stale indicators + UTC updated timestamps.
- Display news provider/tier/freshness in System Health and Risk panels.
- Exit criterion:
  - Phase 9 acceptance criteria demonstrably met in UI.

### Workstream 7: Contract and Doc Harmonization (Priority P1)
- Resolve `/portfolio/evaluate` inconsistency in `lld_v1.md`.
- Add implementation-state annotations for data dictionary entities.
- Clarify current-vs-history semantics for `GET /trades/open`.
- Resolve `GET /performance` response-shape mismatch (risk events + summary metrics).
- Clarify duplicate-replay vs conflict semantics for `/signal` (`200` replay vs `409` conflict).
- Exit criterion:
  - No API/data-model contradictions across LLD/spec docs.

### Workstream 8: Verification and CI Evidence (Priority P1)
- Enforce CI checks for build, lint, tests, and migration validity.
- Require evidence artifacts for runbook status changes.
- Exit criterion:
  - Status changes in governance docs are evidence-backed and reproducible.

## 5) Recommended Execution Sequence
1. P0 governance truth alignment (Workstream 1) to stop status drift.
2. P0 news contracts and health telemetry (Workstream 2).
3. P0 signal lineage + risk coverage completion (Workstreams 3-4).
4. P1 plugin/strategy and dashboard completion (Workstreams 5-6).
5. P1 contract harmonization + CI evidence enforcement (Workstreams 7-8).

## 6) Definition of Remediation Done
- Governance files are internally consistent and evidence-linked.
- Backend contract matches LLD/API spec for v1.0-v1.1 scope.
- Required v1.1 scheduled-news controls are implemented and test-covered.
- Dashboard meets stated v1.3 minimum operational visibility and provider-health requirements.
- Build/lint/test/migration checks run in CI with passing artifacts.
