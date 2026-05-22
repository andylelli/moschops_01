# v1.1 News Implementation Plan

Version: 1.1
Last updated: 2026-05-21
Status: Execution in progress
Scope target: v1.1 scheduled-news delivery only

## Progress Tracker
| Workstream | Status | Owner | Target milestone | Evidence link/status |
|---|---|---|---|---|
| A. Persistence and schema | Complete | Backend Lead | Phase 1 complete | Migrations applied successfully after DB unblock |
| B. Provider client and ingestion runtime | Complete | Backend Lead | Phase 2 complete | FMP client, scheduler, budget guard, and freshness updates implemented |
| C. Normalization and window resolver | Complete | Backend Lead | Phase 3 complete | Mapping, dedup key policy, and window materialization implemented |
| D. Risk integration | Complete | Backend + Risk Lead | Phase 4 complete | Policy integrated into signal, risk-check, and portfolio flows |
| E. API and dashboard exposure | Complete | Backend + Frontend Lead | Phase 5 complete | News routes, health telemetry, and dashboard build verification completed |
| F. Verification and operations | In progress | QA + Ops Lead | Phase 6 complete | Backend test suite passed; evidence package assembly pending |

Status legend:
- Not started: no implementation work begun.
- In progress: active implementation or validation underway.
- Blocked: cannot proceed due to unresolved dependency.
- At risk: work is moving but milestone risk is elevated.
- Complete: implementation and evidence accepted.

### Progress Dashboard
| Item | Value | Notes |
|---|---|---|
| Overall completion | 92% | 11 of 12 task rows complete |
| Current phase | Phase 6 | Verification and evidence packaging |
| Current critical path | F1 -> F2 | Test execution and evidence acceptance |
| Open blockers | 0 | Track in blocker register below |
| Evidence artifacts completed | 1/4 | Backend tests/build and migration verification captured |
| Go-live readiness | Not ready | Requires section 12 checklist completion |

### Phase Gate Tracker
| Phase | Gate objective | Owner | Status | Percent complete | Dependencies | Target date | Actual completion | Gate evidence |
|---|---|---|---|---:|---|---|---|---|
| Phase 1 | Schema and lineage foundation complete | Backend Lead | Complete | 100 | None | 2026-05-21 | 2026-05-21 | Prisma migration applied after DB unblock |
| Phase 2 | Provider ingestion stable with budget controls | Backend Lead | Complete | 100 | Phase 1 | 2026-05-21 | 2026-05-21 | Sync service implemented with cadence and budget reserve policy |
| Phase 3 | Guard windows materialized deterministically | Backend Lead | Complete | 100 | Phase 2 | 2026-05-21 | 2026-05-21 | Severity mapping and deterministic upsert/materialization implemented |
| Phase 4 | Risk integration parity across all decision routes | Backend + Risk Lead | Complete | 100 | Phase 3 | 2026-05-21 | 2026-05-21 | Shared news policy integrated into signal, risk-check, portfolio |
| Phase 5 | News and health APIs exposed with dashboard binding | Backend + Frontend Lead | Complete | 100 | Phase 4 | 2026-05-21 | 2026-05-21 | News routes active and dashboard build passes |
| Phase 6 | Demonstration evidence package accepted | QA + Ops Lead | In progress | 70 | Phase 5 | TBD | TBD | Backend tests passed; remaining evidence artifacts pending |

### Workstream Detail Tracker
| Workstream | Task ID | Task summary | Status | Owner | Dependency | Blocker | Start date | Target date | Done criteria met |
|---|---|---|---|---|---|---|---|---|---|
| A | A1 | Add news tables and indexes | Complete | Backend Lead | None | None | 2026-05-21 | 2026-05-21 | Yes |
| A | A2 | Extend lineage fields and verify migrations | Complete | Backend Lead | A1 | None | 2026-05-21 | 2026-05-21 | Yes |
| B | B1 | Implement economic-calendar client and auth policy | Complete | Backend Lead | A2 | None | 2026-05-21 | 2026-05-21 | Yes |
| B | B2 | Implement scheduler, budget guard, and reserve floor | Complete | Backend Lead | B1 | None | 2026-05-21 | 2026-05-21 | Yes |
| C | C1 | Implement normalization and deterministic dedup | Complete | Backend Lead | B2 | None | 2026-05-21 | 2026-05-21 | Yes |
| C | C2 | Materialize active windows and mapping coverage gate | Complete | Backend Lead | C1 | None | 2026-05-21 | 2026-05-21 | Yes |
| D | D1 | Integrate evaluator into /signal | Complete | Backend + Risk Lead | C2 | None | 2026-05-21 | 2026-05-21 | Yes |
| D | D2 | Integrate evaluator into /risk-check and /portfolio/evaluate | Complete | Backend + Risk Lead | D1 | None | 2026-05-21 | 2026-05-21 | Yes |
| E | E1 | Add /news/upcoming, /news/active, /news/providers | Complete | Backend Lead | D2 | None | 2026-05-21 | 2026-05-21 | Yes |
| E | E2 | Bind dashboard views and provider status indicators | Complete | Frontend Lead | E1 | None | 2026-05-21 | 2026-05-21 | Yes |
| F | F1 | Complete unit, integration, and system test suite | Complete | QA Lead | E2 | None | 2026-05-21 | 2026-05-21 | Yes |
| F | F2 | Complete evidence package and go or no-go review | Not started | Ops Lead | F1 | None | TBD | TBD | No |

### Blocker Register
| Blocker ID | Description | Impacted phase | Owner | Mitigation plan | ETA | Status |
|---|---|---|---|---|---|---|
| BL-01 | Local database unavailable at localhost:5432 (migration apply failed P1001) | Phase 1, 3, 6 | Backend Lead | Resolved by clearing port conflict and starting compose postgres service | 2026-05-21 | Closed |
| BL-02 | Node runtime version incompatible with vitest/vite dependency requirements | Phase 6 | QA + Frontend Lead | Upgraded Node runtime and reran toolchain verification | 2026-05-21 | Closed |

### Progress Update Rules
1. Update the status and percent complete fields at least twice per week during active implementation.
2. A task can be marked complete only when its done criteria and evidence references are present.
3. Any blocked task must include an active blocker record with mitigation and ETA.
4. Phase gate status must remain Not started or In progress until all child tasks are complete.
5. Overall completion should be derived from completed task count in the workstream detail tracker.

## Contents
- [1. Purpose](#1-purpose)
- [2. Authority and Alignment](#2-authority-and-alignment)
- [3. Scope and Non-Goals](#3-scope-and-non-goals)
- [4. Delivery Principles](#4-delivery-principles)
- [5. Traceability Matrix to LLD v1.1](#5-traceability-matrix-to-lld-v11)
- [6. Implementation Workstreams](#6-implementation-workstreams)
- [7. Sequenced Execution Plan](#7-sequenced-execution-plan)
- [8. Detailed Task Breakdown](#8-detailed-task-breakdown)
- [9. Testing and Evidence Plan](#9-testing-and-evidence-plan)
- [10. Operational Rollout Plan](#10-operational-rollout-plan)
- [11. Risks and Mitigations](#11-risks-and-mitigations)
- [12. Exit Readiness Checklist](#12-exit-readiness-checklist)

## 1. Purpose
Define a concrete, implementation-ready execution plan for v1.1 scheduled-news controls using Financial Modeling Prep economic-calendar data, aligned to the approved design boundaries.

This plan is execution-focused. It translates LLD requirements into ordered engineering tasks, verification gates, and demonstration evidence.

## 2. Authority and Alignment
Authority order for this plan:
1. `docs/02-architecture/lld_v1.md`
2. `docs/02-architecture/lld_v1_1_news.md`
3. `docs/02-architecture/lld_v2.md`
4. `docs/01-roadmap/coding_plan.md`

Supporting plan references:
- `docs/06-plans/news_integration_plan.md`
- `docs/06-plans/news_findings_leverage_plan.md`

If any conflict appears, the higher-authority document wins.

## 3. Scope and Non-Goals
In scope for v1.1 implementation:
- Scheduled economic-calendar ingestion from FMP.
- UTC-normalized event storage.
- Deterministic guard-window materialization.
- Risk-policy integration into `/signal`, `/risk-check`, and `/portfolio/evaluate`.
- Required news read routes: `/news/upcoming`, `/news/active`, `/news/providers`.
- Provider freshness telemetry and stale-provider fail-closed behavior for new entries.
- Dashboard data binding for upcoming and active scheduled windows.

Scope boundary rule for decision authority:
- Scheduled calendar windows are the only news input allowed to modify v1.1 trade decisions.
- FMP general-news, stock-news, and press-release feeds may be ingested for operator visibility only and must not alter v1.1 decisions.

Out of scope for v1.1 implementation:
- Live headline reaction and incident lifecycle automation.
- NLP or sentiment-based decision overrides.
- Strategy-specific differentiated incident policies.
- Press-release-driven execution behavior.

## 4. Delivery Principles
- Deterministic first: identical inputs must produce identical policy outcomes.
- Safety first: stale-provider states block new entries for impacted symbols while allowing protective exits.
- Backend-owned truth: provider ingestion and normalization happen only server-side.
- Auditability: decision lineage and provider freshness context must be persisted.
- Budget discipline: free-tier call budget must be enforced by scheduler and guardrails.

## 5. Traceability Matrix to LLD v1.1
| LLD area | Implementation requirement | Plan section |
|---|---|---|
| Runtime architecture | Add ingestion, normalization, window resolver, policy evaluator | 6, 7, 8 |
| Data model additions | Add `news_events`, `news_provider_status`, `news_guard_windows` | 8.1 |
| API and route changes | Add required read routes and health telemetry | 8.3 |
| Risk policy | Implement severity windows and stale fallback behavior | 8.4 |
| Reason code contract | Return required reason codes for block, reduce, and stale states | 8.4, 9 |
| Operational controls | Enforce sync cadence, budget reserve, freshness thresholds | 8.2, 10 |
| Testing and demonstration | Unit, integration, system evidence package | 9 |

## 6. Implementation Workstreams
Workstream A: Persistence and schema
- Deliver schema migrations, indexes, and lineage storage fields.

Workstream B: Provider client and ingestion runtime
- Deliver FMP client, auth, polling scheduler, budget guard, and freshness state updates.

Workstream C: Normalization and window resolver
- Deliver deterministic mapping, dedup/upsert logic, and active-window materialization.

Workstream D: Risk integration
- Deliver policy checks and reason-code integration across all required routes.

Workstream E: API and dashboard exposure
- Deliver required read routes and dashboard bindings for upcoming and active windows.

Workstream F: Verification and operations
- Deliver tests, replay evidence package, runbook updates, and rollout checks.

## 7. Sequenced Execution Plan
Phase 1: Foundation and schema
1. Implement news tables and indexes.
2. Implement required lineage additions in risk and rejection records.
3. Add migration and rollback verification.

Phase 2: Provider ingestion and normalization
1. Implement FMP economic-calendar client with required request parameters.
2. Implement 10-minute scheduler with free-tier call-budget enforcement.
3. Implement deterministic normalization and idempotent upsert.
4. Persist provider freshness state on each attempt.

Phase 3: Guard-window materialization
1. Implement severity-to-window matrix.
2. Implement symbol-to-currency impact mapping.
3. Materialize active windows in query-efficient form.

Phase 4: Risk decision integration
1. Integrate policy evaluation into `/signal`.
2. Integrate same policy evaluation into `/risk-check` and `/portfolio/evaluate`.
3. Ensure shared evaluator is used to prevent endpoint drift.

Phase 5: Exposure APIs and health telemetry
1. Add `/news/upcoming`, `/news/active`, `/news/providers`.
2. Extend `/health` with provider freshness telemetry.
3. Expose enough metadata for dashboard and operator audit.

Phase 6: Demonstration and release readiness
1. Execute replay tests for one high-impact and one medium-impact event.
2. Collect evidence package with UTC timestamps and correlation identifiers.
3. Complete rollout checklist and go/no-go review.

## 8. Detailed Task Breakdown
### 8.1 Schema and persistence tasks
1. Add `news_events` with normalized and raw payload fields.
2. Add `news_provider_status` with freshness state transitions.
3. Add `news_guard_windows` for deterministic runtime lookups.
4. Add indexes for event time, symbol scope, and active window queries.
5. Extend lineage payloads in risk and rejection records.

Definition of done:
- Migrations are reversible.
- Query plans for active-window lookup are validated.
- Duplicate event ingestion results in idempotent upsert behavior.

### 8.2 Provider and scheduler tasks
1. Implement FMP client for economic-calendar endpoint.
2. Enforce required `from` and `to` query parameters and max 90-day range constraints.
3. Implement provider auth policy: prefer `apikey` header, with query-parameter fallback.
4. Implement deterministic rolling UTC fetch window with short lookback for revisions.
5. Implement default 10-minute sync cadence.
6. Enforce free-tier daily budget policy at 250 calls/day with explicit reserve floor.
7. Model baseline consumption at default cadence (about 144 calls/day) and track remaining budget.
8. Enforce reserve floor of at least 25% of daily budget for retries, startup sync, and recovery.
9. Implement retry and backoff with degradation on reserve exhaustion.
10. Update provider freshness status on success and failure paths.

Definition of done:
- Default cadence remains under free-tier budget with retry reserve.
- Freshness transitions are observable and deterministic.

### 8.3 API and contract tasks
1. Add `/news/upcoming` with normalized event output.
2. Add `/news/active` with currently active guard-window output.
3. Add `/news/providers` with freshness and sync diagnostics.
4. Extend `/health` to include provider freshness signals.

Definition of done:
- Routes return stable schema.
- Routes expose normalized server-side truth, not raw provider payload.

### 8.4 Risk evaluator tasks
1. Implement shared scheduled-news evaluator module.
2. Implement required reason codes:
3. `NEWS_BLOCK_HIGH_IMPACT`.
4. `NEWS_REDUCE_MEDIUM_IMPACT`.
5. `NEWS_PROVIDER_STALE`.
6. Implement severity matrix:
7. HIGH and CRITICAL: block new entries T-30 to T+60.
8. MEDIUM: reduce T-15 to T+30.
9. LOW: allow with monitoring.
10. Implement stale-provider conservative fallback behavior with `NEWS_PROVIDER_STALE`.
11. Preserve protective-exit allow behavior under all conditions.

Definition of done:
- `/signal`, `/risk-check`, and `/portfolio/evaluate` agree for identical inputs.
- Protective exits are never blocked by scheduled-news controls.
- Reason-code outputs are stable and auditable in response and persistence payloads.

### 8.6 Normalization and deduplication contract tasks
1. Map provider fields into internal schema exactly per LLD mappings.
2. Persist `unit` into normalized payload when supplied by provider.
3. Use deterministic provider-event upsert key:
4. Use provider event id when available.
5. Otherwise use stable composite fields (`date`, `event`, `country`, `currency`).
6. Require symbol-to-currency mapping coverage for all enabled symbols before policy activation.

Definition of done:
- Re-ingesting same provider payload does not create duplicate events.
- Mapping behavior is versioned and reproducible across releases.

### 8.5 Dashboard and operator tasks
1. Bind upcoming events view to `/news/upcoming`.
2. Bind active windows view to `/news/active`.
3. Bind provider status view to `/news/providers` and `/health`.
4. Display reason-code details for recent veto outcomes.

Definition of done:
- Operator can see upcoming and active windows without direct provider access.
- Provider degraded or stale state is clearly visible.

## 9. Testing and Evidence Plan
Unit tests:
1. Normalization mapping and severity conversion.
2. Dedup/upsert key generation, including fallback composite key behavior.
3. Window generation at boundary times.
4. Stale-provider fallback logic.

Integration tests:
1. Active high-impact window blocks new entries in `/signal`.
2. Same window yields deterministic outputs in `/risk-check` and `/portfolio/evaluate`.
3. Provider stale state produces conservative block behavior.
4. Replay of same request preserves reason-code output and persistence lineage.
5. Required reason codes are emitted correctly for high-impact, medium-impact, and stale-provider scenarios.

System tests:
1. Provider outage transitions to degraded or stale and triggers conservative policy.
2. Active calendar window is visible via API and dashboard.
3. Protective exits remain allowed while new entries are blocked.

Evidence package artifacts:
1. Timeline for one high-impact event and one medium-impact event.
2. API responses before, during, and after windows.
3. Database records for events, windows, and risk outcomes.
4. Dashboard screenshots for upcoming, active, and provider status views.

## 10. Operational Rollout Plan
Stage 1: Development rollout
1. Enable ingestion with conservative thresholds.
2. Validate cadence and budget behavior for 48 hours.

Stage 2: Demo environment rollout
1. Enable scheduled-news policy in decision path.
2. Monitor stale and degraded transitions and route parity.

Stage 3: Pilot-readiness gate
1. Confirm evidence package completeness.
2. Confirm runbook procedures for provider degradation and rollback.
3. Confirm legal and data-use constraints for selected tier.

Operational controls:
1. Configurable sync interval and freshness thresholds.
2. Configurable symbol-to-currency map version.
3. Configurable severity window matrix.
4. Manual policy disable and rollback switch.

## 11. Risks and Mitigations
Risk: Provider timestamp inconsistency causes incorrect windows.
- Mitigation: UTC-only normalization plus boundary tests and replay validation.

Risk: Quota exhaustion causes stale state during critical periods.
- Mitigation: call-budget governor, reserve floor, and controlled retry policy.

Risk: Symbol mapping incompleteness causes false negatives.
- Mitigation: activation gate requires mapping coverage for all enabled symbols.

Risk: Endpoint drift causes inconsistent decisions.
- Mitigation: one shared evaluator used by all decision routes.

Risk: Overblocking reduces trade opportunity unnecessarily.
- Mitigation: post-demo review of severity matrix and impact map with replay metrics.

## 12. Exit Readiness Checklist
- [ ] Schema, indexes, and lineage fields implemented and validated.
- [ ] FMP ingestion and normalization stable at configured cadence.
- [ ] Budget guard and reserve floor proven under load simulation.
- [ ] Guard-window materialization deterministic and queryable.
- [ ] Decision parity confirmed across `/signal`, `/risk-check`, `/portfolio/evaluate`.
- [ ] Required routes `/news/upcoming`, `/news/active`, `/news/providers` available.
- [ ] `/health` includes provider freshness telemetry.
- [ ] Protective exits verified to remain allowed during active blocks.
- [ ] Evidence package complete with UTC timestamps and correlation IDs.
- [ ] Runbook updates complete for degraded, stale, disable, and rollback operations.
