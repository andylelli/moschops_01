# Platform Full Setup Execution Plan and Daily Tracker

Version: 2.0  
Date: 2026-05-21  
Purpose: A single execution control document for delivery planning, progress tracking, risk control, and go or no-go decisions across backend, data, AI, MT5, and dashboard operations.

## Table of Contents
- [1. How to Use This Document](#1-how-to-use-this-document)
- [2. Execution Plan Overview](#2-execution-plan-overview)
- [3. Critical Path and Blockers](#3-critical-path-and-blockers)
- [4. Stream Checklist: Data and Provider Ingestion](#4-stream-checklist-data-and-provider-ingestion)
- [5. Stream Checklist: AI Training and Validation](#5-stream-checklist-ai-training-and-validation)
- [6. Stream Checklist: Backend and DB](#6-stream-checklist-backend-and-db)
- [7. Stream Checklist: MT5 and EA](#7-stream-checklist-mt5-and-ea)
- [8. Stream Checklist: Dashboard and Operations](#8-stream-checklist-dashboard-and-operations)
- [9. Go or No-Go Gate Table by Release](#9-go-or-no-go-gate-table-by-release)
- [10. Sprint-Ready Backlog View](#10-sprint-ready-backlog-view)
- [11. Risk Register with Mitigation and Rollback](#11-risk-register-with-mitigation-and-rollback)
- [12. Automation Hooks](#12-automation-hooks)
- [13. Traceability Matrix (Runbook and LLD)](#13-traceability-matrix-runbook-and-lld)
- [14. Daily Progress Tracker Format](#14-daily-progress-tracker-format)

## 1. How to Use This Document
1. Update this document daily during active implementation.
2. Every completed task must include objective evidence (command output, report, screenshot, or query result).
3. Do not mark a gate as Go until all measurable criteria in section 9 are met.
4. Keep blocker state and risk state updated in sections 3 and 11 on the same day issues are discovered.

Status values:
- `Not Started`
- `In Progress`
- `Blocked`
- `Done`

Owner roles:
- `Platform Lead`
- `Backend Lead`
- `Data Lead`
- `ML Lead`
- `Quant Lead`
- `EA Lead`
- `UI Lead`
- `Ops Lead`
- `QA Lead`

## 2. Execution Plan Overview

| Plan ID | Stream | Deliverable | Owner | Effort (days) | Planned Start | Planned Finish | Depends On | Status |
|---|---|---|---|---:|---|---|---|---|
| EP-01 | Data/Provider | Provider entitlement and ingestion baseline validated | Data Lead | 2 | 2026-05-22 | 2026-05-23 | None | In Progress |
| EP-02 | Backend/DB | Backend APIs, schema, and audit persistence hardened | Backend Lead | 4 | 2026-05-22 | 2026-05-27 | EP-01 | In Progress |
| EP-03 | MT5/EA | EA runtime integration and safety controls validated | EA Lead | 4 | 2026-05-24 | 2026-05-29 | EP-02 | Not Started |
| EP-04 | AI | Training, validation, and ONNX export operational | ML Lead | 5 | 2026-05-26 | 2026-06-02 | EP-02 | Not Started |
| EP-05 | Dashboard/Ops | Monitoring, degraded modes, and runbooks validated | UI Lead + Ops Lead | 4 | 2026-05-27 | 2026-06-02 | EP-02 | In Progress |
| EP-06 | Release Controls | Go or no-go gates, demo evidence package complete | Platform Lead + QA Lead | 3 | 2026-06-02 | 2026-06-05 | EP-03, EP-04, EP-05 | Not Started |

## 3. Critical Path and Blockers

Critical path order:
1. CP-01: Provider entitlement and ingestion proof (EP-01).
2. CP-02: Backend and DB determinism plus API contract hardening (EP-02).
3. CP-03: EA execution and safety roundtrip (EP-03).
4. CP-04: AI training and ONNX promotion candidate (EP-04).
5. CP-05: Monitoring and operational readiness package (EP-05).
6. CP-06: Formal go or no-go review (EP-06).

Current blocker board:

| Blocker ID | Blocker | Impacted Path Step | Owner | Open Date | Target Clear Date | Current Mitigation | Status |
|---|---|---|---|---|---|---|---|
| BL-01 | Historical economic calendar access returns provider-tier error | CP-01 | Data Lead | 2026-05-21 | 2026-05-23 | Revalidated on 2026-05-21 (`402` stable historical, `403` v3); maintain explicit disabled mode and treat historical as entitlement-blocked | Open |
| BL-02 | Model version endpoint has no active model row | CP-04 | ML Lead | 2026-05-21 | 2026-05-27 | Resolved by bootstrap metadata seed from local ONNX/training artifacts; `/model-version` now returns active row | Closed |

## 4. Stream Checklist: Data and Provider Ingestion

| Done | Task ID | Task | Owner | Effort (days) | Planned Start | Depends On | Evidence Required | Automation Hook | Traceability | Status | Evidence Link | Notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| [x] | DPI-01 | Validate provider key for current-day endpoint | Data Lead | 0.5 | 2026-05-22 | None | Status code and item count report | `backend` provider probe command | `lld_v1` news provider decision, runbook phase 9 addendum | Done | docs/07-temp/evidence/provider_probe_2026-05-21.txt | Current-day stable endpoint returned `200` with `count:126` |
| [ ] | DPI-02 | Validate historical date-range entitlement | Data Lead | 0.5 | 2026-05-22 | DPI-01 | Historical query output with response status and count | `backend` provider probe command with historical date range | `lld_v1` section 5 news profile, runbook addendum | Blocked | docs/07-temp/evidence/provider_probe_2026-05-21.txt | Historical stable returned `402`; v3 historical returned `403`; tracked by BL-01 |
| [x] | DPI-03 | Configure sync mode and failure reason policy | Backend Lead | 0.5 | 2026-05-23 | DPI-02 | Health payload includes deterministic provider failure reason | `npm run build` plus API probe | `lld_v1` section 8 fail-closed behavior | Done | docs/07-temp/evidence/news_disabled_probe_2026-05-21.txt | Disabled mode verified: `failureReason=NEWS_SYNC_DISABLED` in `/health` and `/news/providers` |
| [x] | DPI-04 | Validate freshness state transitions (fresh/degraded/stale/down) | Data Lead | 1 | 2026-05-23 | DPI-03 | Transition test report with timestamps | API probe plus controlled sync timing | `lld_v1_1_news` freshness behavior, runbook phase 9 | Done | docs/07-temp/evidence/freshness_transition_report_2026-05-21.json | Controlled timestamp transitions validated across `/health` and `/news/providers` (`4/4` pass) |
| [ ] | DPI-05 | Validate symbol-currency mapping completeness | Quant Lead | 0.5 | 2026-05-23 | DPI-03 | Mapping coverage report for enabled symbols | backend symbol mapping utility check | `lld_v1` section 5, runbook phase 8/9 | Not Started | Pending |  |

## 5. Stream Checklist: AI Training and Validation

| Done | Task ID | Task | Owner | Effort (days) | Planned Start | Depends On | Evidence Required | Automation Hook | Traceability | Status | Evidence Link | Notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| [ ] | AIV-01 | Lock feature schema parity contract | ML Lead | 0.5 | 2026-05-26 | EP-02 | Feature schema document and runtime comparison output | training schema check script | `lld_v1` section 3 and section 7 | Not Started | Pending |  |
| [ ] | AIV-02 | Run data extraction and label generation pipeline | Data Lead | 1 | 2026-05-26 | AIV-01 | Label distribution and extraction summary | training extraction command | coding plan phase 6, runbook phase 6 | Not Started | Pending |  |
| [ ] | AIV-03 | Execute walk-forward training and calibration checks | ML Lead | 2 | 2026-05-27 | AIV-02 | Validation report with Brier/reliability metrics | training run command | `lld_v1` section 7, runbook phase 6 | Not Started | Pending |  |
| [ ] | AIV-04 | Export ONNX and persist model metadata | ML Lead | 1 | 2026-05-29 | AIV-03 | ONNX artifact hash plus metadata row | model export command plus DB check | `lld_v1` section 7, runbook phase 7 | Not Started | Pending |  |
| [ ] | AIV-05 | Verify inference path and threshold policy in runtime | Backend Lead | 1 | 2026-05-30 | AIV-04 | API probe showing full/half/skip behavior | backend signal integration test | `lld_v1` section 7 and section 9 | Not Started | Pending |  |

## 6. Stream Checklist: Backend and DB

| Done | Task ID | Task | Owner | Effort (days) | Planned Start | Depends On | Evidence Required | Automation Hook | Traceability | Status | Evidence Link | Notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| [x] | BDB-01 | Run schema generation and migrations cleanly | Backend Lead | 0.5 | 2026-05-22 | None | Migration log and successful schema generation output | `npm run prisma:generate`, `npm run prisma:deploy` | runbook phase 3, `lld_v1` section 6 | Done | docs/07-temp/evidence/prisma_migration_check_2026-05-21.txt | Prisma client generated; deploy completed with no pending migrations |
| [x] | BDB-02 | Validate API contract matrix with valid payloads | QA Lead | 1 | 2026-05-23 | BDB-01 | Endpoint test report including status and summary fields | API probe harness | `lld_v1` section 4 and section 9 | Done | docs/07-temp/evidence/api_test_report_2026-05-21.json | Backend matrix now `14` pass, `0` fail; provider entitlement constraints tracked under BL-01 |
| [x] | BDB-03 | Validate idempotency replay behavior | Backend Lead | 0.5 | 2026-05-23 | BDB-02 | Duplicate request test output and stable response proof | signal and portfolio replay tests | `lld_v1` section 4 | Done | docs/07-temp/evidence/idempotency_test_report_2026-05-21.json | Signal and portfolio replay checks passed with stable responses (`4/4` pass) |
| [x] | BDB-04 | Validate traceability chain signal-trade-outcome | Backend Lead | 1 | 2026-05-24 | BDB-03 | SQL query proof chain for IDs and versions | DB lineage query script | runbook phase 3 exit criteria | Done | docs/07-temp/evidence/lineage_test_report_2026-05-21.json | SQL join proof includes decisionId, signalId, strategy/model versions, and linked trade (`3/3` pass) |
| [x] | BDB-05 | Validate risk veto and news parity across endpoints | QA Lead | 1 | 2026-05-24 | BDB-02, DPI-04 | Cross-endpoint parity test report | parity integration tests | `lld_v1` section 5 and section 9 | Done | docs/07-temp/evidence/parity_test_report_2026-05-21.json | `/signal`, `/risk-check`, and `/portfolio/evaluate` all applied `NEWS_PROVIDER_STALE` veto consistently (`4/4` pass) |

## 7. Stream Checklist: MT5 and EA

| Done | Task ID | Task | Owner | Effort (days) | Planned Start | Depends On | Evidence Required | Automation Hook | Traceability | Status | Evidence Link | Notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| [ ] | MTE-01 | Compile EA and confirm baseline startup | EA Lead | 0.5 | 2026-05-24 | EP-02 | Compile output and startup logs | MT5 compile command | runbook phase 1, coding plan phase 1 | Not Started | Pending |  |
| [ ] | MTE-02 | Validate completed-candle signal logic only | EA Lead | 1 | 2026-05-24 | MTE-01 | Backtest evidence showing no look-ahead behavior | MT5 strategy tester run | `lld_v1` section 3 | Not Started | Pending |  |
| [ ] | MTE-03 | Validate local safety checks before order send | EA Lead | 1 | 2026-05-25 | MTE-02 | Guardrail test evidence for lot/stops/spread/margin | EA simulation scenario set | `lld_v1` section 8 | Not Started | Pending |  |
| [ ] | MTE-04 | Validate EA-backend decision roundtrip | EA Lead + Backend Lead | 1 | 2026-05-26 | MTE-03, BDB-02 | End-to-end request/response logs with IDs | integration roundtrip script | `lld_v1` section 2 and section 4 | Not Started | Pending |  |
| [ ] | MTE-05 | Validate trade and open-trade snapshot posting | EA Lead | 0.5 | 2026-05-26 | MTE-04 | Backend `trades/open` evidence linked to EA actions | endpoint verification command | `lld_v1` section 2 and section 10 | Not Started | Pending |  |

## 8. Stream Checklist: Dashboard and Operations

| Done | Task ID | Task | Owner | Effort (days) | Planned Start | Depends On | Evidence Required | Automation Hook | Traceability | Status | Evidence Link | Notes |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| [ ] | DOP-01 | Validate app shell and route stability | UI Lead | 0.5 | 2026-05-27 | EP-02 | Route walkthrough and build output | `dashboard` build and route smoke | `ui_design` sections 4 and 15 | In Progress | Pending |  |
| [ ] | DOP-02 | Validate health and risk telemetry bindings | UI Lead | 1 | 2026-05-27 | BDB-02, DPI-04 | UI screenshots plus API payload correlation | dashboard smoke + API probe | `ui_design` section 10 and `lld_v1` section 10 | In Progress | Pending |  |
| [ ] | DOP-03 | Validate degraded and disabled state messaging | UI Lead + Ops Lead | 0.5 | 2026-05-28 | DOP-02 | Operator view evidence for disabled/stale/down states | dashboard behavior test | `ui_design` section 9.3 and 9.5 | In Progress | Pending |  |
| [ ] | DOP-04 | Finalize incident and recovery runbooks | Ops Lead | 1 | 2026-05-29 | DOP-03 | Runbook review and sign-off notes | runbook checklist command set | runbook phase 9 and phase 10 | Not Started | Pending |  |
| [ ] | DOP-05 | Validate release evidence package completeness | QA Lead | 1 | 2026-06-02 | DOP-04, EP-03, EP-04 | Evidence bundle index and gate checklist | gate validation script | runbook phase 10 and coding plan phase 10 | Not Started | Pending |  |

## 9. Go or No-Go Gate Table by Release

| Release | Gate ID | Measurable Criteria | Target | Evidence Required | Decision Owner | Go/No-Go | Decision Date | Notes |
|---|---|---|---|---|---|---|---|---|
| v1.0 | G-100 | API contract pass rate | 100% of mandatory endpoints pass valid payload tests | API matrix report | Platform Lead + QA Lead | Pending | Pending |  |
| v1.0 | G-101 | Audit lineage completeness | 100% of sampled decisions have traceable IDs and versions | DB lineage query report | Backend Lead | Pending | Pending |  |
| v1.0 | G-102 | Deterministic strategy validation | No look-ahead defects in baseline report | Baseline validation report | Quant Lead | Pending | Pending |  |
| v1.1 | G-110 | Training reproducibility | Re-run within tolerance on same dataset | Training run report and artifact hashes | ML Lead | Pending | Pending |  |
| v1.1 | G-111 | Inference parity | Runtime feature schema matches training schema exactly | Parity report and startup check logs | Backend Lead + ML Lead | Pending | Pending |  |
| v1.1 | G-112 | News decision policy parity | `/signal`, `/risk-check`, `/portfolio/evaluate` return consistent policy effects | Parity integration test report | QA Lead | Pending | Pending |  |
| v1.2 | G-120 | Portfolio guard compliance | No exposure cap violations in multi-symbol simulation | Portfolio simulation report | Risk Lead | Pending | Pending |  |
| v1.2 | G-121 | Risk event coverage | 100% of forced guard scenarios emit expected risk events | Risk event test report | Backend Lead | Pending | Pending |  |
| v1.3 | G-130 | Monitoring readiness | Health/risk/news operator views pass evidence checklist | Dashboard evidence set | UI Lead + Ops Lead | Pending | Pending |  |
| v1.3 | G-131 | Demo readiness | Evidence package complete and runbook approved | Demo gate dossier | Platform Lead + Ops Lead | Pending | Pending |  |

## 10. Sprint-Ready Backlog View

| Ticket ID | Title | Stream | Owner | Effort (story points) | Sprint Target | Depends On | Acceptance Criteria | Evidence | Status |
|---|---|---|---|---:|---|---|---|---|---|
| PLAT-001 | Validate provider entitlement matrix | Data/Provider | Data Lead | 3 | Sprint 1 | None | Current-day and historical endpoint matrix captured | Provider test report | In Progress |
| PLAT-002 | Harden provider failure-state semantics | Backend/DB | Backend Lead | 2 | Sprint 1 | PLAT-001 | Failure reason contract deterministic in health and providers route | API payload proof | In Progress |
| PLAT-003 | Complete backend API pass matrix | Backend/DB | QA Lead | 5 | Sprint 1 | PLAT-002 | All mandatory routes tested with valid payloads | API matrix report | In Progress |
| PLAT-004 | Implement DB lineage verification queries | Backend/DB | Backend Lead | 3 | Sprint 1 | PLAT-003 | Query output proves decision-trade-outcome traceability | SQL output | Not Started |
| PLAT-005 | Lock feature schema contract | AI | ML Lead | 3 | Sprint 2 | PLAT-003 | Training and runtime feature list identical | Schema parity report | Not Started |
| PLAT-006 | Run walk-forward model training and calibration | AI | ML Lead | 8 | Sprint 2 | PLAT-005 | Validation metrics meet threshold policy | Validation report | Not Started |
| PLAT-007 | Export ONNX and seed model metadata | AI | ML Lead | 3 | Sprint 2 | PLAT-006 | ONNX artifact loaded and model-version endpoint no longer empty | ONNX + endpoint proof | Not Started |
| PLAT-008 | Validate MT5 EA safety controls | MT5/EA | EA Lead | 5 | Sprint 2 | PLAT-003 | Guard checks prevent unsafe order scenarios | Tester evidence | Not Started |
| PLAT-009 | Validate EA-backend roundtrip and open-trade bridge | MT5/EA | EA Lead | 5 | Sprint 3 | PLAT-008, PLAT-003 | Roundtrip and open-trade snapshot persistence verified | End-to-end logs | Not Started |
| PLAT-010 | Finalize dashboard degraded-state UX evidence | Dashboard/Ops | UI Lead | 3 | Sprint 3 | PLAT-003, PLAT-001 | Operator screens show deterministic stale/down/disabled states | UI evidence pack | In Progress |
| PLAT-011 | Finalize incident runbooks and demo gate dossier | Dashboard/Ops | Ops Lead | 5 | Sprint 3 | PLAT-010, PLAT-009, PLAT-007 | All release gate evidence assembled and reviewed | Gate dossier | Not Started |

## 11. Risk Register with Mitigation and Rollback

| Risk ID | Risk Description | Probability | Impact | Trigger Signal | Mitigation Plan | Rollback Action | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | Provider historical endpoint access unavailable | High | High | 402 or 403 on historical query | Validate entitlement, document supported ranges, add explicit disabled mode | Force `NEWS_SYNC_ENABLED=false`; preserve operator visibility only | Data Lead | Open |
| R-02 | Runtime feature schema diverges from training schema | Medium | High | Inference errors or unstable predictions | Enforce schema parity checks in startup and CI | Disable AI gate and run rule-only profile | ML Lead | Open |
| R-03 | DB write path intermittently fails under load | Medium | High | Persistence warnings or missing rows | Add retry-safe writes and DB health checks | Block new entries and allow protective exits only | Backend Lead | Open |
| R-04 | EA sends malformed payload or stale snapshots | Medium | Medium | Endpoint validation failures | Tighten EA payload serializer and contract tests | Stop EA posting; run local-only safeguards | EA Lead | Open |
| R-05 | Dashboard misrepresents degraded states | Medium | Medium | UI does not match API telemetry | Add UI evidence checks and parity tests | Revert to minimal health-only status view | UI Lead | Open |
| R-06 | Go/no-go evidence package incomplete at release cut | Medium | High | Gate checklist has unresolved evidence rows | Weekly evidence audit and owner escalation | Delay promotion, keep environment in prior stage | Platform Lead | Open |

## 12. Automation Hooks

| Area | Hook ID | Command or Script | Expected Output | Frequency | Owner |
|---|---|---|---|---|---|
| Backend build | AH-BE-01 | `cd backend && npm run build` | TypeScript compile success | Per commit | Backend Lead |
| Backend tests | AH-BE-02 | `cd backend && npm test` | Test suite pass | Daily | QA Lead |
| DB schema | AH-DB-01 | `cd backend && npm run prisma:generate` | Prisma client generated | Per schema change | Backend Lead |
| DB migrations | AH-DB-02 | `cd backend && npm run prisma:deploy` | Migration apply success | Per release candidate | Backend Lead |
| API matrix | AH-BE-03 | `cd backend && npm run verify:api` | Endpoint status matrix with summaries plus JSON report | Daily | QA Lead |
| Lineage proof | AH-BE-04 | `cd backend && npm run verify:lineage` | SQL traceability chain report for signal-trade linkage | Daily | Backend Lead |
| Policy parity | AH-BE-05 | `cd backend && npm run verify:parity` | Cross-endpoint news/risk parity report | Daily | QA Lead |
| Provider probe | AH-DP-01 | `cd backend && npm run verify:provider` | Current and historical provider status report | Daily | Data Lead |
| Freshness transitions | AH-DP-02 | `cd backend && npm run verify:freshness` | Fresh/degraded/stale/down transition validation report | Daily | Data Lead |
| Dashboard build | AH-UI-01 | `cd dashboard && npm run build` | Frontend compile success | Per commit | UI Lead |
| Training pipeline | AH-ML-01 | `cd training && python train.py --config config.yaml` | Training artifacts and metrics report | Per model cycle | ML Lead |
| ONNX export | AH-ML-02 | `cd training && python export_onnx.py --run-id <id>` | ONNX artifact plus metadata | Per candidate model | ML Lead |
| Evidence pack | AH-OPS-01 | Manual package checklist from section 9 gates | Complete gate dossier | Weekly | Ops Lead |

## 13. Traceability Matrix (Runbook and LLD)

| Item Group | Primary Source | Secondary Source | Traceability Notes |
|---|---|---|---|
| Backend API contracts | `docs/02-architecture/lld_v1.md` section 4 | `docs/00-governance/implementation_runbook.md` phase 2 | Mandatory route set and idempotency behaviors map to API tasks in section 6 and backlog PLAT-003 |
| Risk controls and veto logic | `docs/02-architecture/lld_v1.md` section 5 | Runbook phase 4 | Risk-check, signal veto, and portfolio guard tasks map to BDB-05 and MTE-03 |
| Data model and audit lineage | `docs/02-architecture/lld_v1.md` section 6 | Runbook phase 3 | Schema, migrations, and lineage proof tasks map to BDB-01 and BDB-04 |
| AI training and promotion | `docs/02-architecture/lld_v1.md` section 7 | Runbook phases 6 and 7 | Feature parity, training, calibration, and ONNX tasks map to AIV-01 through AIV-05 |
| Safety and degraded modes | `docs/02-architecture/lld_v1.md` section 8 | Runbook phase 9 and phase 10 | Fail-closed behavior and incident response map to DOP-03, DOP-04, and risk register |
| News provider integration | `docs/02-architecture/lld_v1.md` news provider section and section 5 | Runbook news addendum tracking | Provider entitlement and freshness tasks map to DPI-01 through DPI-05 |
| UI operational requirements | `docs/05-ui/ui_design.md` sections 9, 10, 15 | Runbook phase 9 | Health/risk visibility and stale handling tasks map to DOP-01 through DOP-03 |
| Release readiness and rollout | `docs/01-roadmap/coding_plan.md` phase 10 | Runbook phase 10 | Gate table in section 9 and evidence package in DOP-05 map to release controls |

## 14. Daily Progress Tracker Format

### 14.1 Daily Summary Board

| Date | Stream | Owner | Planned Tasks | Completed Tasks | Blocked Tasks | Percent Complete | Notes |
|---|---|---|---:|---:|---:|---:|---|
| 2026-05-22 | Data and Provider Ingestion | Data Lead | 2 | 0 | 1 | 0% | Waiting on entitlement confirmation |
| 2026-05-22 | Backend and DB | Backend Lead | 3 | 1 | 0 | 33% | API matrix in progress |
| 2026-05-21 | Data and Provider Ingestion | Data Lead | 4 | 3 | 1 | 75% | DPI-01, DPI-03, DPI-04 complete; DPI-02 remains entitlement-blocked |
| 2026-05-21 | Backend and DB | QA Lead | 5 | 5 | 0 | 100% | BDB-01 through BDB-05 complete; schema/migration, contract, replay, lineage, and parity checks are green |
| 2026-05-22 | AI Training and Validation | ML Lead | 0 | 0 | 0 | 0% | Not started |
| 2026-05-22 | MT5 and EA | EA Lead | 0 | 0 | 0 | 0% | Not started |
| 2026-05-22 | Dashboard and Operations | UI Lead | 2 | 1 | 0 | 50% | Degraded-state UX evidence in progress |

### 14.2 Daily Log Template

| Date | Item ID | Update Type | Summary | Evidence | Next Action | Owner |
|---|---|---|---|---|---|---|
| 2026-05-21 | BDB-02 | Progress | API probe rerun with valid payload set; backend `13/14` pass and one known `MODEL_NOT_FOUND` gap | docs/07-temp/evidence/api_test_report_2026-05-21.json | Resolve model metadata gap under BL-02 and rerun matrix | QA Lead |
| 2026-05-21 | DPI-03 | Progress | Disabled sync policy verified in health and provider payloads with deterministic failure reason | docs/07-temp/evidence/news_disabled_probe_2026-05-21.txt | Keep disabled-mode telemetry as fallback until entitlement issue resolves | Backend Lead |
| 2026-05-21 | BDB-02 | Completion | API probe rerun after metadata bootstrap seed; backend contract matrix is now `14/14` pass | docs/07-temp/evidence/api_test_report_2026-05-21.json | Keep provider entitlement failures isolated under DPI-02 and BL-01 | QA Lead |
| 2026-05-21 | BL-02 | Resolution | `/model-version` endpoint now returns active model metadata (`200`) | docs/07-temp/evidence/model_version_probe_2026-05-21.json | Keep model metadata seed in startup path until formal training promotion pipeline is active | ML Lead |
| 2026-05-21 | BDB-03 | Completion | Idempotency replay verification passed for both `/signal` and `/portfolio/evaluate` duplicate requests | docs/07-temp/evidence/idempotency_test_report_2026-05-21.json | Proceed to BDB-04 lineage verification queries | Backend Lead |
| 2026-05-21 | BDB-04 | Completion | SQL lineage probe verified signal to trade chain with strategy/model identifiers and linked trade state | docs/07-temp/evidence/lineage_test_report_2026-05-21.json | Proceed to BDB-05 parity checks after DPI-04 completion | Backend Lead |
| 2026-05-21 | DPI-04 | Completion | Freshness transitions validated for `FRESH`, `DEGRADED`, `STALE`, and `DOWN` with controlled timestamps | docs/07-temp/evidence/freshness_transition_report_2026-05-21.json | Keep entitlement blocker BL-01 open for historical provider access only | Data Lead |
| 2026-05-21 | BDB-05 | Completion | Cross-endpoint parity probe confirmed consistent news veto behavior and reason code propagation | docs/07-temp/evidence/parity_test_report_2026-05-21.json | Proceed to remaining backend DB task BDB-01 cleanup and close | QA Lead |
| 2026-05-21 | BDB-01 | Completion | Prisma generation and migration deploy validation passed after clearing local file lock | docs/07-temp/evidence/prisma_migration_check_2026-05-21.txt | Keep backend workspace node processes scoped during migration operations | Backend Lead |

### 14.3 Blocker Log Template

| Date Raised | Blocker ID | Affected Item IDs | Description | Mitigation | Escalation Needed | Owner | ETA |
|---|---|---|---|---|---|---|---|
| 2026-05-21 | BL-01 | DPI-02 | Historical provider calls remain entitlement-blocked (`402` stable historical, `403` v3 historical) | Confirm exact subscription scope with provider and keep disabled mode explicit | Yes | Data Lead | 2026-05-23 |
| 2026-05-21 | BL-02 | BDB-02 | `/model-version` had no active metadata row (returned `404`) | Seed model metadata from local ONNX/training artifacts and verify endpoint payload | No | ML Lead | 2026-05-21 |

### 14.4 Evidence Registry Template

| Evidence ID | Date | Item ID | Evidence Type | Location | Verified By | Verification Date |
|---|---|---|---|---|---|---|
| EV-001 | 2026-05-21 | DPI-01 | Provider probe report | docs/07-temp/evidence/provider_probe_2026-05-21.txt | Data Lead | 2026-05-21 |
| EV-002 | 2026-05-21 | BDB-02 | API matrix report | docs/07-temp/evidence/api_test_report_2026-05-21.json | QA Lead | 2026-05-21 |
| EV-003 | 2026-05-21 | DPI-03 | Disabled-mode telemetry probe | docs/07-temp/evidence/news_disabled_probe_2026-05-21.txt | Backend Lead | 2026-05-21 |
| EV-004 | 2026-05-21 | EP-01/EP-02 | Consolidated verification summary | docs/07-temp/evidence/verification_summary_2026-05-21.md | Platform Lead | 2026-05-21 |
| EV-005 | 2026-05-21 | BL-02 | Model-version endpoint probe | docs/07-temp/evidence/model_version_probe_2026-05-21.json | ML Lead | 2026-05-21 |
| EV-006 | 2026-05-21 | BDB-03 | Idempotency replay report | docs/07-temp/evidence/idempotency_test_report_2026-05-21.json | Backend Lead | 2026-05-21 |
| EV-007 | 2026-05-21 | BDB-04 | SQL lineage chain report | docs/07-temp/evidence/lineage_test_report_2026-05-21.json | Backend Lead | 2026-05-21 |
| EV-008 | 2026-05-21 | DPI-04 | Freshness transition report | docs/07-temp/evidence/freshness_transition_report_2026-05-21.json | Data Lead | 2026-05-21 |
| EV-009 | 2026-05-21 | BDB-05 | Cross-endpoint parity report | docs/07-temp/evidence/parity_test_report_2026-05-21.json | QA Lead | 2026-05-21 |
| EV-010 | 2026-05-21 | BDB-01 | Prisma generation/deploy check | docs/07-temp/evidence/prisma_migration_check_2026-05-21.txt | Backend Lead | 2026-05-21 |

---

Update policy:
1. Update section 14 daily.
2. Update section 3 and section 11 immediately when blockers or risks change.
3. Update section 9 only during formal gate review meetings.
