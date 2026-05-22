# AI Trading System Low-Level Design (LLD) - v1.1 News Addendum

Version: 1.1
Last updated: 2026-05-21
Coverage: Scheduled economic-calendar news controls for v1 execution
Parent design: docs/02-architecture/lld_v1.md
Related plan: docs/06-plans/news_integration_plan.md

## Provider Baseline (Normative)
- Selected news provider: Financial Modeling Prep (FMP).
- API documentation reference: https://site.financialmodelingprep.com/developer/docs/stable/economics-calendar
- Pricing reference: https://site.financialmodelingprep.com/developer/docs/pricing
- `v1.x` execution tier: `FREE`.
- `v2+` execution tier: `BASIC`.
- `FREE` tier implementation budget baseline: 250 calls/day.
- Provider cadence assumption for scheduling: economic calendar refresh around 10 minutes; headline feeds are not v1.1 decision inputs.
- LLD integration rule: scheduled-event ingestion in this document must use the FMP calendar/news API integration path and emit provider lineage as `FMP`.

## Contents
- [1. Purpose](#1-purpose)
- [2. Scope](#2-scope)
- [3. Entry and Exit Criteria](#3-entry-and-exit-criteria)
- [4. Runtime Architecture Changes](#4-runtime-architecture-changes)
- [5. Data Model Additions](#5-data-model-additions)
- [6. API and Route Changes](#6-api-and-route-changes)
- [7. Risk Policy Specification](#7-risk-policy-specification)
- [8. Implementation Sequence](#8-implementation-sequence)
- [9. Testing and Demonstration](#9-testing-and-demonstration)
- [10. Operational Controls](#10-operational-controls)
- [11. Explicit Non-Goals for v1.1 News](#11-explicit-non-goals-for-v11-news)

## 1. Purpose
Define an additional, executable LLD for v1 scheduled-news functionality without rewriting or replacing the existing v1 baseline design.

This document is additive. It assumes the baseline behavior in docs/02-architecture/lld_v1.md is already implemented and remains authoritative for all non-news behavior.

## 2. Scope
In scope for this addendum:
- Scheduled economic-calendar ingestion.
- Deterministic pre-event and post-event guard windows.
- News-aware veto or size-reduction decisions for affected symbols.
- Persistence of news-driven risk outcomes for auditability.
- Dashboard visibility of upcoming and active scheduled event windows.
- Strategy-suitable FMP API implementation profile for the current daily-breakout execution path.

Out of scope for this addendum:
- Live breaking-news reaction from headline streams.
- Incident lifecycle automation (OPEN, ACKNOWLEDGED, CLEARED, EXPIRED).
- NLP classification of free-text headlines.
- Multi-strategy differentiated news policies.

Strategy suitability rule for v1.1:
- v1.1 decisioning must use scheduled economic-calendar data only.
- FMP general-news, stock-news, and press-release endpoints may be collected for operator visibility only and must not change v1.1 trade decisions.

## 3. Entry and Exit Criteria
Entry criteria:
- Existing v1 API and risk pipeline are operational (`/signal`, `/risk-check`, `/portfolio/evaluate`, `/health`).
- Existing persistence and idempotency behavior is operational.
- Existing dashboard shell is available for data binding.
- FMP `FREE` tier terms are reviewed and accepted for `v1.x` scheduled-event ingestion, storage, and operational use.

Exit criteria:
- Scheduled events are ingested and normalized into persistent storage.
- Active event windows are computed deterministically for configured symbols.
- During active windows, new entries are blocked or reduced according to policy.
- News decision reason codes are returned in decision responses.
- News-driven outcomes are persisted for replay and audit.
- System demonstrates that blocked new entries do not block protective exits.

Non-negotiable acceptance rule:
- If this rule cannot be shown with evidence, v1.1 news is not complete: scheduled-event blocks must never prevent protective exits.

## 4. Runtime Architecture Changes
Additional v1 runtime components:
- Scheduled calendar ingestion service.
- Event normalization service.
- News state resolver for active windows.
- News policy evaluator integrated into existing risk flow.

Execution flow for v1 scheduled news:
1. Ingestion service polls the configured calendar provider and stores normalized events.
2. Window resolver materializes active guard windows per symbol and time range.
3. `/signal` calls scheduled-news policy evaluation after payload validation and before final action.
4. `/risk-check` and `/portfolio/evaluate` call the same policy evaluation to avoid cross-endpoint drift.
5. Responses include existing reason code fields augmented with scheduled-news reason codes.
6. Risk and rejection persistence records include scheduled-news context.

FMP API implementation profile (strategy-suitable for v1 daily-breakout):
- Primary provider endpoint: `https://financialmodelingprep.com/stable/economic-calendar`.
- Required provider parameters: `from` and `to`; requests must respect max 90-day date range.
- Provider auth: prefer `apikey` in request header; query parameter is allowed fallback.
- Ingestion window policy: use a rolling UTC window to capture near-term events plus recent revisions (minimum requirement: include upcoming horizon and short lookback).
- Sync cadence policy on `FREE`: default 10-minute polling aligned to provider cycle-time, governed by daily call budget limits and retry caps.
- Budget baseline for default cadence: 10-minute polling consumes about 144 calls/day, leaving reserve for retries, startup sync, and health checks.
- Budget guard policy: preserve reserve budget for retries and operational checks; if reserve is exhausted, mark provider freshness degraded and enforce stale fallback behavior.
- Determinism policy: provider payload normalization must run server-side only; EA must not call provider APIs directly.
- Deduplication policy: event upsert key must be deterministic using provider event id when available, otherwise stable composite fields (`date`, `event`, `country`, `currency`).

## 5. Data Model Additions
Add these tables for v1 scheduled news:
- `news_events`
- `news_provider_status`
- `news_guard_windows`

Minimum fields:

`news_events`
- `news_event_id`
- `provider`
- `provider_event_id`
- `event_type`
- `title`
- `country_code`
- `currency_code`
- `severity`
- `scheduled_at_utc`
- `forecast_value`
- `previous_value`
- `actual_value` (nullable before release)
- `status`
- `raw_json`
- `normalized_json`
- `created_at`
- `updated_at`

`news_provider_status`
- `provider`
- `last_successful_sync_utc`
- `last_attempted_sync_utc`
- `freshness_state` (`FRESH`, `DEGRADED`, `STALE`, `DOWN`)
- `failure_reason`
- `updated_at`

`news_guard_windows`
- `guard_window_id`
- `news_event_id`
- `symbol_scope`
- `currency_scope`
- `policy_action` (`BLOCK_NEW`, `REDUCE`, `ALLOW`)
- `starts_at_utc`
- `ends_at_utc`
- `severity`
- `reason_code`
- `metadata_json`
- `created_at`

Required provider-to-model normalization (FMP to internal schema):
- `date` -> `scheduled_at_utc`.
- `event` -> `title` and `event_type`.
- `country` -> `country_code`.
- `currency` -> `currency_code`.
- `impact` -> `severity` (`Low` -> `LOW`, `Medium` -> `MEDIUM`, `High` -> `HIGH`, unknown/highest provider class -> `CRITICAL` by policy mapping).
- `estimate` -> `forecast_value`.
- `previous` -> `previous_value`.
- `actual` -> `actual_value`.
- `unit` -> `normalized_json.unit` when supplied by provider.
- `provider_event_id` must be deterministic; when provider ID is missing, generate from stable source fields and normalize as idempotent key.

Required lineage additions to existing records:
- `RiskEvent.detailsJson` includes `newsEventId`, `policyAction`, `provider`, `freshnessState` where applicable.
- `RejectedSignal.detailsJson` includes scheduled-news veto context where applicable.
- `Signal.responseJson` includes scheduled-news reason codes where applicable.

## 6. API and Route Changes
No request shape changes are required for v1 scheduled-news execution.

Required additions:
- `GET /news/upcoming`
- `GET /news/active`
- `GET /news/providers`

Provider integration requirements:
- Backend must call FMP directly and persist normalized results; client-facing API routes must not proxy raw provider responses as decision truth.
- `/news/upcoming` and `/news/active` must expose normalized scheduled-event data relevant to configured symbols and currency mappings.
- `/news/providers` must expose provider freshness, last successful sync, and failure reason summary.

Required behavior changes:
- `/signal` integrates scheduled-news policy check.
- `/risk-check` integrates scheduled-news policy check.
- `/portfolio/evaluate` integrates scheduled-news policy check.
- `/health` includes scheduled-news provider freshness telemetry.

## 7. Risk Policy Specification
Policy intent:
- Scheduled economic events are deterministic guard inputs.
- Policy must be time-window based, symbol-aware, and auditable.

Determinism requirement:
- Window calculations must use `scheduled_at_utc` only.
- Local timezone conversions are not allowed in policy evaluation.
- For the same event and policy matrix, every endpoint must return the same decision outcome.

Initial baseline matrix:
- `HIGH` and `CRITICAL`: `BLOCK_NEW` from T-30 minutes to T+60 minutes.
- `MEDIUM`: `REDUCE` from T-15 minutes to T+30 minutes.
- `LOW`: `ALLOW` with monitoring only.

Symbol mapping requirement:
- Policy must resolve impact by symbol currency exposure.
- Mapping must be explicit and versioned.
- All enabled symbols in runtime configuration must have explicit currency mapping before policy activation.

Required reason codes:
- `NEWS_BLOCK_HIGH_IMPACT`
- `NEWS_REDUCE_MEDIUM_IMPACT`
- `NEWS_PROVIDER_STALE`

Required stale-provider fallback:
- If provider freshness is `STALE` or `DOWN`, new entries for impacted symbols must be blocked conservatively and return `NEWS_PROVIDER_STALE`.

Strategy-suitable policy boundary for v1.1:
- Scheduled calendar windows are authoritative for entry-block and size-reduction decisions.
- Headline-derived sentiment or article text must not be used to override scheduled-news policy in v1.1.

Safety requirement:
- Blocking policy applies to new entries only.
- Protective exits remain allowed.

## 8. Implementation Sequence
Step 1: Schema and migrations
- Create tables for events, provider status, and guard windows.
- Add indexes for event time and active-window lookups.

Step 2: Ingestion and normalization
- Implement provider client, parser, deduplication, and upsert behavior.
- Persist provider freshness status on every sync attempt.

Step 3: Window resolver
- Generate active windows from normalized events and policy matrix.
- Materialize current windows for deterministic endpoint evaluation.

Step 4: Risk integration
- Add news policy checks to `/signal`, `/risk-check`, and `/portfolio/evaluate`.
- Merge reason codes into existing response shape.

Step 5: Observability and UI
- Extend `/health` telemetry with provider freshness.
- Provide upcoming and active windows endpoints.
- Bind dashboard risk view to scheduled-news window and veto data.

Step 6: Demo verification
- Replay at least one known high-impact event and one medium-impact event.
- Capture response evidence, stored records, and dashboard evidence.

## 9. Testing and Demonstration
Unit tests:
- event normalization and deduplication
- window generation across time boundaries
- severity-to-action mapping
- stale provider behavior

Integration tests:
- `/signal` vetoes new entries during active high-impact windows
- `/risk-check` returns deterministic news veto outputs
- `/portfolio/evaluate` rejects conflicting plans during windows
- idempotent replay preserves news reason codes
- persistence includes news lineage in risk and rejection records

System tests:
- provider outage sets degraded or stale status and triggers conservative behavior
- active calendar window appears in API and dashboard
- blocked new entries still permit protective exits

Demonstration evidence package:
- one known event timeline with timestamps
- API response samples before, during, and after window
- DB records for event, window, and risk outcomes
- dashboard screenshot set for upcoming and active windows

Evidence quality rule:
- Each evidence item must include UTC timestamps and correlation identifiers so behavior can be replayed and verified.

## 10. Operational Controls
Environment configuration:
- provider endpoint and credentials (FMP)
- provider tier by version (`FREE` for `v1.x`, `BASIC` for `v2+`)
- sync interval
- freshness thresholds
- symbol impact map version
- severity window matrix

Required default implementation controls for current strategy profile:
- Default sync interval: 10 minutes, with budget-aware retry limits.
- Daily API call budget guard for `FREE` tier, including reserved retry allowance.
- Reserve budget floor: keep at least 25% of daily call capacity unallocated for retries and recovery operations.
- UTC-only ingestion and storage path for all provider timestamps.
- Provider-field mapping versioning so policy behavior is reproducible across releases.

Runbook requirements:
- provider degraded handling
- stale-data fallback behavior
- manual disable and rollback of scheduled-news policy

## 11. Explicit Non-Goals for v1.1 News
The following are reserved for v2 and are not part of this v1.1 addendum execution:
- live headline feed reaction logic
- incident-state transitions and automation
- strategy-specific and environment-specific incident orchestration
- breaking-news pause and exit-only controls driven by unscheduled events
