# AI Trading System Low-Level Design (LLD) - v2

Version: 1.0
Last updated: 2026-05-21
Coverage: `v2.0` to `v2.1` from `../01-roadmap/coding_plan.md`

## Contents
- [1. Scope](#1-scope)
- [2. v2.0 Architecture Delta](#2-v20-architecture-delta)
- [3. Multi-Strategy Contracts](#3-multi-strategy-contracts)
- [4. Model Promotion Orchestration](#4-model-promotion-orchestration)
- [5. Data Model Extensions (v2)](#5-data-model-extensions-v2)
- [6. v2.1 Managed Cloud Architecture](#6-v21-managed-cloud-architecture)
- [7. Reliability and Security](#7-reliability-and-security)
- [8. Testing and Acceptance](#8-testing-and-acceptance)
- [9. Alignment with Coding Plan](#9-alignment-with-coding-plan)
- [10. UI Evolution (v2.x)]
- [11. News v2 Execution (Post-v2.0)](#11-news-v2-execution-post-v20)

### AI Fallback Behavior in Multi-Strategy

Each strategy in the multi-strategy runtime can define its AI dependency as:
1. **Mandatory**: Strategy execution pauses if AI inference is unavailable.
2. **Optional**: Strategy falls back to rule-based execution if AI inference is unavailable.

The strategy registry must enforce these settings and log fallback events for auditability.

## Progress Table
| Step | Version target | Related tech | Implementation language/runtime | Component placement | Status | Notes |
|---|---|---|---|---|---|---|
| 1. Implement strategy registry runtime | v2.0 | Node.js, TypeScript, plugin loader | TypeScript on Node.js | Backend strategy orchestration service | Planned | Multi-strategy enable/disable and scoped routing |
| 2. Add strategy isolation supervisor | v2.0 | Process supervision, health checks | TypeScript on Node.js | Backend supervision and health module | Planned | One strategy failure cannot halt all strategies |
| 3. Build shared portfolio allocator | v2.0 | Risk engine extensions, portfolio math | TypeScript on Node.js | Backend risk and allocation core module | Planned | Cross-strategy budget and concentration controls |
| 4. Add cross-strategy attribution service | v2.0 | PostgreSQL analytics, reporting API | TypeScript on Node.js + SQL | Backend analytics/reporting service | Planned | Performance by strategy/model/version |
| 5. Implement retraining orchestrator | v2.0 | Python pipeline runner, scheduler | Python (training jobs) + TypeScript coordinator | Training pipeline + backend orchestration endpoint | Planned | Drift/schedule-based retraining triggers |
| 6. Implement model promotion workflow | v2.0 | Model registry, validation gates | TypeScript on Node.js | Backend model governance service | Planned | candidate -> validation -> staged -> active |
| 7. Implement one-step rollback controls | v2.0 | Model version manager, audit logs | TypeScript on Node.js | Backend model governance service | Planned | Safe revert to prior active model |
| 8. Migrate DB to managed service | v2.1 | Azure Database for PostgreSQL | SQL migration tooling + TypeScript migration runners | Database platform and backend data layer | Planned | Migration rehearsal and data integrity checks |
| 9. Containerize and deploy services | v2.1 | Containers, Azure runtime services | Docker + TypeScript/Node.js + Python | Backend and training runtime platform | Planned | Backend and training workloads in managed runtime |
| 10. Add environment promotion pipeline | v2.1 | CI/CD, release gates, policy checks | YAML pipeline configs + TypeScript validation scripts | Deployment automation and release workflow | Planned | dev -> demo -> pilot with approvals |
| 11. Implement backup/restore drills | v2.1 | Backup automation, restore verification | Shell/automation scripts + SQL checks | Ops automation and database recovery workflow | Planned | Recovery objectives verified in rehearsal |
| 12. Activate SLO monitoring and alerting | v2.1 | Vue 3, Tailwind CSS, metrics, dashboards, alert routing | Vue 3 SPA + telemetry configuration + TypeScript health emitters | Observability platform, dashboard frontend, and backend health endpoints | Planned | API/DB/model-serving reliability tracking with light/dark mode |

## 1. Scope
In scope:
- `v2.0`: Multi-strategy platform integration and shared portfolio allocator
- `v2.1`: Managed Azure migration, environment promotion, and SLO operations

Depends on:
- All `v1.x` controls and contracts from `lld_v1.md`

## 2. v2.0 Architecture Delta
New capabilities over v1:
- Multi-strategy runtime with registry-based plugin loading
- Shared allocator enforcing risk budgets across strategies
- Strategy/model promotion orchestration with rollback
- Cross-strategy attribution and portfolio reporting

Logical components:
- `Strategy Registry Service`
- `Portfolio Allocator Service`
- `Retraining Orchestrator`
- `Model Promotion Orchestrator`
- `Strategy Isolation Supervisor`
- `Cross-Strategy Performance Service`

Execution flow (v2.0):
1. Scheduler gathers eligible strategies per symbol/timeframe.
2. Strategy plugins propose candidate plans.
3. Shared allocator applies budget and concentration constraints.
4. Risk engine applies global and strategy-level vetoes.
5. Approved plans return to EA execution path with trace IDs.
6. Attribution service records outcome by strategy/model/version.

## 3. Multi-Strategy Contracts
Strategy registry contract:
- Register strategy id/version/profile
- Enable or disable by environment
- Assign symbol universe and timeframe constraints
- Define AI mandatory/optional mode per strategy
- Pin active model version per strategy and environment

Allocator input contract:
- Open risk by strategy
- Correlation buckets (currency and asset class)
- Strategy priority and minimum trade allocation
- Current drawdown and recent performance state

Allocator output contract:
- Approved budget fraction per strategy
- Rejected plans with structured risk reasons
- Remaining portfolio budget snapshot

## 4. Model Promotion Orchestration
Lifecycle states:
- `candidate`
- `validation`
- `staged`
- `active`
- `rollback`

Promotion requirements:
- Out-of-sample improvement vs active model
- Calibration pass
- Trade-count sufficiency
- No regression in risk constraints

Rollback requirements:
- One-step rollback to prior `active` model version
- Full audit record of promotion and rollback decision

Retraining orchestration requirements:
- Trigger retraining from drift, calibration degradation, or schedule policy.
- Produce candidate artifacts and register them before promotion evaluation.
- Enforce environment-aware promotion gates so a model can be staged in demo before pilot/live use.

## 5. Data Model Extensions (v2)
Additional tables:
- `strategy_registry`
- `strategy_allocations`
- `allocation_events`
- `model_promotions`
- `model_rollbacks`
- `environment_deployments`
- `slo_snapshots`
- `incident_events`

Mandatory lineage fields:
- `strategy_id`
- `strategy_version`
- `model_version`
- `allocation_id`
- `deployment_id`
- `created_at`

## 6. v2.1 Managed Cloud Architecture
Target Azure services:
- Managed PostgreSQL
- Container runtime for backend services
- Managed model artifact storage
- CI/CD environment promotion (dev -> demo -> pilot)

Operational capabilities:
- Automated backup/restore verification
- Health/SLO dashboard and alerting
- Environment-specific feature toggles
- Controlled rollout and rollback by environment

## 7. Reliability and Security
Reliability:
- Strategy isolation: one strategy failure cannot stop all strategies
- Graceful degradation: allocator/service failures block only unsafe actions
- Environment promotion gates require test and risk checks

Security:
- Secret management by environment
- Least-privilege service identities
- Authenticated service-to-service calls
- Auditable change history for promotions/deployments

## 8. Testing and Acceptance
v2.0 acceptance:
- Concurrent multi-strategy simulation without key collisions
- Portfolio allocator enforces caps under stress
- Promotion and rollback flow tested end-to-end

v2.1 acceptance:
- Successful migration rehearsal from VM baseline to managed services
- Backup and restore drill pass
- Environment promotion reproducible without manual reconfiguration
- SLO alerts verified for API, DB, and model-serving paths

## 9. Alignment with Coding Plan
Version mapping:
- `v2.0` aligns to `Phase 11` and `Phase 12` in `../01-roadmap/coding_plan.md`
- `v2.1` aligns to `Phase 13` in `../01-roadmap/coding_plan.md`

Compatibility rule:
- v2 does not replace v1 safeguards; it layers orchestration and managed operations on top.

Quality notes:
- This v2 LLD assumes all v1 safety and risk guardrails remain mandatory.
- Any allocator or orchestration failure must fail closed for new risk while preserving protective exits.

## 10. UI Evolution (v2.x)
UI stack continuity:
- Continue using Vue 3 + Tailwind CSS from v1.
- Preserve Pinia and Vue Router patterns for operational workflows.

v2 UI extensions:
- Add multi-strategy attribution screens (strategy/model/version comparisons).
- Add environment and promotion workflow views (candidate/staged/active/rollback states).
- Add SLO and incident dashboards for managed-cloud operations.

Theme requirements:
- Light and dark mode remain mandatory for all new v2 views.
- Any new component must support both themes with consistent design tokens.

## 11. News v2 Execution (Post-v2.0)
Provider baseline:
- Selected provider: Financial Modeling Prep (FMP).
- Pricing reference: https://site.financialmodelingprep.com/developer/docs/pricing
- `v2+` runtime tier: `BASIC` (with `v1.x` history on `FREE`).

Execution gate:
- Live-news reaction work in this section starts only after v2.0 baseline capabilities are complete (strategy registry, shared allocator, and strategy isolation).
- If any v2.0 baseline capability is incomplete, live-news reaction implementation must not start.

Prerequisites checklist:
- Strategy registry enforces environment and symbol/timeframe constraints.
- Shared allocator is active in runtime decisioning and emits attributable rejection reasons.
- Strategy isolation supervisor is active so one strategy incident path cannot halt all strategies.
- v1 scheduled-news controls are stable in production-like operation.

Purpose:
- Extend scheduled-news controls from v1 into live breaking-news reaction suitable for multi-strategy runtime operation.

Scope in v2:
- Ingest live headline or incident feeds suitable for unscheduled market events.
- Persist incident lifecycle with explicit states (`OPEN`, `ACKNOWLEDGED`, `CLEARED`, `EXPIRED`).
- Apply incident-driven risk actions (`PAUSE`, `EXIT_ONLY`) by strategy, symbol scope, and environment.
- Preserve protective exits while failing closed for new risk.
- Provide operator visibility and controls for incident acknowledgement and clearing.

Required v2 contracts and lineage:
- Incident decisions must carry `strategy_id`, `strategy_version`, and environment identifiers.
- Incident-driven rejections must be attributed to allocator and strategy context.
- Multi-strategy policy resolution must be deterministic when strategies have different incident modes.

Conflict resolution rule:
- When strategy incident modes conflict, the stricter action must win for new entries (`PAUSE` > `EXIT_ONLY` > `ALLOW`).
- Protective exits remain allowed under all incident modes.

Required data extensions:
- Add incident-oriented tables or extensions that map incident state to strategy and environment scopes.
- Record incident action history for audit replay and post-incident review.

Acceptance additions for v2 news:
- Incident open and clear flow works end-to-end across at least two enabled strategies.
- Incident-driven `PAUSE` blocks new entries while allowing protective exits.
- Environment-specific incident policy behaves correctly across dev, demo, and pilot scopes.
- Incident telemetry is visible in UI and health surfaces with clear operator status.
- Re-running the same incident scenario with unchanged inputs yields the same per-strategy decisions and audit records.
