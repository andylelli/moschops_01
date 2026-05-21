# News Integration Plan

Version: 1.0
Last updated: 2026-05-21
Status: Draft planning document

## Contents
- [1. Purpose](#1-purpose)
- [2. Scope](#2-scope)
- [3. Current System Review](#3-current-system-review)
- [4. Design Principles For News Integration](#4-design-principles-for-news-integration)
- [5. News Use Cases](#5-news-use-cases)
- [6. Version Split: v1 vs v2](#6-version-split-v1-vs-v2)
- [7. Target Operating Model](#7-target-operating-model)
- [8. Proposed Architecture](#8-proposed-architecture)
- [9. Options For Getting News Information](#9-options-for-getting-news-information)
- [10. Data Model Plan](#10-data-model-plan)
- [11. API and Contract Plan](#11-api-and-contract-plan)
- [12. Risk Policy Plan](#12-risk-policy-plan)
- [13. Integration Points In Current Codebase](#13-integration-points-in-current-codebase)
- [14. Implementation Phases](#14-implementation-phases)
- [15. Testing Plan](#15-testing-plan)
- [16. Key Configuration Decisions Needed](#16-key-configuration-decisions-needed)
- [17. Recommended First Delivery Slice](#17-recommended-first-delivery-slice)
- [18. Risks and Failure Modes](#18-risks-and-failure-modes)
- [19. Recommendation](#19-recommendation)

## 1. Purpose
Define a concrete, implementation-ready plan to integrate news into the current platform in a way that is deterministic, auditable, fail-closed for new entries, and aligned with the existing Fastify, Prisma, MQL5, and dashboard architecture.

This document does not change authoritative design or contract documents. It is a planning artifact intended to guide a future implementation change set.

## Provider Decision (Normative For Implementation)
- Selected provider: Financial Modeling Prep (FMP).
- Pricing reference: https://site.financialmodelingprep.com/developer/docs/pricing
- `v1.x` execution tier: `FREE`.
- `v2+` execution tier: `BASIC`.
- LLD integration anchor: `docs/02-architecture/lld_v1_1_news.md` for scheduled-event implementation and `docs/02-architecture/lld_v2.md` section 11 for live-news extension.

## 2. Scope
In scope:
- Scheduled financial calendar events such as rate decisions, CPI, NFP, GDP, PMIs, and central-bank speeches for the first implementation.
- Unscheduled breaking-news events such as geopolitical shocks, emergency central-bank actions, and major market-moving headlines as a later-version extension.
- News-aware veto, pause, and size-reduction logic in backend risk evaluation.
- Persistence, telemetry, and operator visibility for news-related decisions.

Out of scope for the first implementation slice:
- NLP-heavy discretionary headline interpretation.
- Auto-generated trade thesis from news text.
- Cross-strategy news optimization beyond the current daily-breakout strategy.
- Full retraining of AI models using news features in the first delivery slice.
- Automated live breaking-news reaction in the first delivery slice.

## 3. Current System Review
The current platform already has the core places where news control should attach.

### Runtime shape today
- The MQL5 EA in `mql5/Experts/DailyBreakoutEA.mq5` evaluates completed D1 bars locally and performs execution after safety checks.
- The backend Fastify app in `backend/src/app.ts` exposes `/signal`, `/risk-check`, `/portfolio/evaluate`, logging routes, `/health`, `/performance`, and `/trades/open`.
- Signal requests are validated in `backend/src/routes/signal.ts` and currently accept market/account snapshots plus optional AI score.
- Signal-level vetoes are evaluated in `backend/src/services/risk-engine.ts` and currently enforce ATR validity, spread guard, max open trades, and max open risk.
- Strategy direction is determined in `backend/src/services/strategy.ts` and is independent of risk controls.
- Portfolio aggregation is evaluated in `backend/src/routes/portfolio.ts` using the same account-level risk service.
- Risk veto events are persisted to `RiskEvent` through `backend/src/routes/risk.ts`.
- Audit logging routes persist signals, rejected signals, and trades in `backend/src/routes/logging.ts`.
- Health telemetry currently exposes backend, database, and model-loader state in `backend/src/routes/health.ts`.
- The dashboard risk view in `dashboard/src/views/RiskSafetyView.vue` is currently a static shell with no live risk-event binding.

### Persistence shape today
The Prisma schema in `backend/prisma/schema.prisma` already persists:
- signal decisions
- rejected signals
- model predictions
- trades
- positions
- risk events
- account snapshots
- portfolio decisions

There is no persisted entity yet for:
- normalized news events
- provider sync status for news feeds
- symbol-to-event impact mapping
- active news guard windows
- breaking-news incident state

### Gap relative to intended design
The existing design documents mention optional high-impact news guards and market guards in v1.2, but the current code path does not yet ingest or act on news. There are no news fields in the current request contracts, no news tables in Prisma, and no news telemetry in `/health`.

## 4. Design Principles For News Integration
- Deterministic first: news must drive explicit policy rules, not opaque discretion.
- Fail closed for new entries: stale or unavailable news data should not silently allow new trades on affected symbols.
- Auditable: every news-driven veto, reduction, or system pause must be persisted with source and reasoning.
- Provider-agnostic core: normalize multiple feed formats into one internal event model.
- Separate scheduled and unscheduled paths: calendar releases and breaking headlines require different handling.
- Symbol-aware impact mapping: event effect must be scoped by symbol group and currency exposure.
- Minimal disruption to current flow: add news checks into existing risk stages instead of inventing a parallel decision path.

## 5. News Use Cases
### 1. Scheduled financial calendar events
Examples:
- central-bank rate decisions
- CPI, PPI, NFP, unemployment, GDP
- PMIs
- scheduled speeches with known event windows

Primary use:
- pre-event and post-event trading guards
- symbol-specific veto or size reduction
- elevated monitoring and operator awareness

Target version:
- `v1` implementation target and demonstration scope

### 2. Unscheduled breaking news
Examples:
- surprise intervention
- emergency rate announcement
- war escalation
- exchange halt
- sudden sanctions or capital-control event

Primary use:
- rapid operator visibility
- instrument group pause or full kill-switch
- trading pause until event status is cleared or a cooldown expires

Target version:
- `v2` implementation target after the scheduled-event path is proven

## 6. Version Split: v1 vs v2
The version split should be explicit so delivery remains testable and aligned with the existing LLD boundaries.

### v1 objective
Demonstrate that the platform can ingest scheduled economic-calendar events and apply deterministic trade controls around them.

What v1 will do:
- ingest scheduled economic-calendar events from a machine-readable source
- normalize event time, currency, severity, and event type into backend-owned state
- compute pre-event and post-event guard windows for configured symbols
- block or reduce new entries around scheduled high-impact events
- persist news-driven vetoes and related risk events for auditability
- expose upcoming and active scheduled-event windows in backend read endpoints and dashboard views
- support replay and validation of calendar-driven decisions

What v1 will not do:
- automatically react to live breaking headlines
- open automated incident pauses from headline feeds
- perform NLP classification of free-text news
- make per-strategy differentiated news decisions beyond the current v1 single-strategy scope

Demonstration target for v1:
- show that a known economic-calendar event such as a rate decision or CPI release is ingested before the release
- show that the system marks the event window active for affected symbols
- show that `/signal` and `/portfolio/evaluate` return deterministic news reason codes during that window
- show that the dashboard and persisted risk records reflect the scheduled-event veto or size reduction

### v2 objective
Extend the platform from scheduled-event guards to live breaking-news reaction that can pause or constrain trading during unscheduled market shocks.

What v2 will do:
- ingest or receive live headline and incident feeds suitable for breaking-news workflows
- create `NewsIncident` records from provider events or operator actions
- support incident states such as `OPEN`, `ACKNOWLEDGED`, `CLEARED`, and `EXPIRED`
- enforce `PAUSE` or `EXIT_ONLY` controls on affected symbols or strategy scopes
- support environment-aware and strategy-aware incident policies in the v2 multi-strategy runtime
- preserve protective exits while failing closed for new risk

What v2 depends on from v1:
- a working scheduled-event ingestion and normalization pipeline
- audited persistence for news-driven decisions
- dashboard visibility for news state and provider freshness
- a stable backend-owned policy layer for news checks

Why this split is the right one:
- scheduled economic-calendar events are deterministic enough to validate safely in `v1`
- live breaking-news reaction has materially higher data-quality, latency, and policy risk and belongs in `v2`
- this aligns with `lld_v1.md`, where news guards sit inside v1.2 market guards, and with `lld_v2.md`, where environment-aware and strategy-aware orchestration becomes available

## 7. Target Operating Model
News should be treated as a first-class risk input rather than a strategy feature in the first phase.

Decision order should become:
1. EA produces market/account snapshot for a completed bar.
2. Backend `/signal` validates payload and computes deterministic strategy action.
3. Backend evaluates signal-level risk, including active news guard checks.
4. Backend returns action plus structured reason codes when news blocks or reduces the trade.
5. Backend `/risk-check` and `/portfolio/evaluate` re-check account and portfolio risk with the same news state to prevent inconsistencies.
6. All news-driven vetoes, reductions, and pauses are persisted as risk events.
7. Dashboard exposes current news guard state, provider freshness, upcoming windows, and recent news vetoes.

For `v1`, this operating model applies to scheduled economic-calendar events only.
For `v2`, the same model is extended with incident-driven handling for unscheduled breaking news.

## 8. Proposed Architecture
### A. News ingestion service
Add a backend service layer responsible for:
- polling one or more calendar/headline providers
- normalizing feed payloads into an internal event shape
- de-duplicating events by provider event ID and normalized fingerprint
- computing freshness status and staleness thresholds
- persisting normalized news events and provider sync status

Suggested placement:
- `backend/src/services/news-ingestion.ts`
- `backend/src/services/news-normalization.ts`
- `backend/src/services/news-state.ts`

### B. Normalized news domain model
Add normalized entities for:
- `news_events`: one row per normalized event
- `news_event_impacts`: per symbol group/currency impact classification
- `news_provider_status`: feed freshness and last successful sync
- `news_guard_windows`: materialized active block/reduce windows for fast risk checks
- optional `news_incidents`: manual or automated breaking-news pause records for `v2`

### C. News-aware risk policy layer
Add a dedicated policy module that is called by both signal-level and account-level risk checks.

Suggested placement:
- `backend/src/services/news-policy.ts`

Responsibilities:
- determine whether a symbol is currently inside an active news window
- determine policy outcome: allow, reduce size, block new entries, exit-only, strategy pause
- return deterministic reason codes and metadata suitable for persistence

### D. Dashboard and telemetry layer
Extend health and risk surfaces to expose:
- provider freshness
- last successful news sync
- count of active guard windows
- symbols currently blocked
- recent news-driven vetoes and incidents
- upcoming high-impact events by time horizon

For `v1`, the dashboard requirement is upcoming and active scheduled events.
For `v2`, add live incident visibility and operator workflow around breaking news.

## 9. Options For Getting News Information
This system needs two different data acquisition paths:
- structured scheduled-event data for deterministic calendar guards
- fast incident or headline data for breaking-news pause logic

The right acquisition path depends heavily on budget. Prices and quotas change frequently, so the bands below should be treated as planning guidance rather than fixed procurement commitments.

### Free
Typical options:
- public economic-calendar pages or feeds with limited redistribution rights
- central-bank and government release calendars consumed directly from official sources
- manual operator-entered event schedules for the highest-impact events only
- free-tier market-data or news APIs with strict request caps

What this tier is good for:
- a prototype for scheduled calendar guards
- a narrow symbol list such as `EURUSD`, `GBPUSD`, and `XAUUSD`
- storing top-tier events only: rate decisions, CPI, NFP, GDP, and major speeches

What to consider:
- licensing is the main constraint, not just technical access; many public calendars are viewable but not suitable for automated production reuse
- free sources often have weak SLAs, no freshness guarantee, and inconsistent event taxonomies
- revisions, forecast fields, and actual values may be delayed or missing
- breaking-news coverage is usually too weak for automated incident handling

Recommended use in this system:
- acceptable for a dev-only proof of concept
- best implemented as scheduled-event ingestion plus manual operator incident entry
- not strong enough on its own for fail-closed production-like operation

### Less than 20 GBP per month
Typical options:
- low-cost retail APIs for economic calendar data
- lightweight no-code or scraping-assisted feeds for event schedules
- chat, RSS, or webhook alerting products used only as an operator prompt rather than an automated trade input

What this tier is good for:
- early demo-stage calendar blocking for a small instrument universe
- getting normalized fields such as event title, currency, impact, scheduled time, forecast, previous, and actual when available

What to consider:
- many providers in this range are optimized for display, not machine-grade operational use
- request quotas may not support aggressive polling or multi-provider redundancy
- breaking-news speed and coverage are usually still insufficient for direct automated incident opening
- vendor stability can be a risk at this price point

Recommended use in this system:
- viable for Phase A and Phase B if the initial goal is scheduled calendar guards only
- use one provider for automated calendar events and keep breaking-news incidents operator-driven
- design the ingestion layer so the provider can be replaced later without schema changes

### Less than 50 GBP per month
Typical options:
- stronger retail or prosumer economic-calendar APIs
- one primary structured calendar feed plus a secondary low-cost alert feed for redundancy
- services that provide webhook delivery, event IDs, better filtering, and more complete actual versus forecast fields

What this tier is good for:
- a credible first live-like implementation of scheduled calendar guards
- narrow automation for breaking-news detection if used only to raise candidate incidents for operator review
- improved freshness monitoring and more reliable event normalization

What to consider:
- this band is usually enough for scheduled macro events, but still marginal for robust machine-actionable breaking news
- headline feeds may arrive fast enough for alerts but not with enough quality to safely automate pause decisions without review
- if the provider lacks historical archives, validation and replay quality will suffer

Recommended use in this system:
- strong candidate for the first real implementation slice
- use the main feed for `NewsEvent` and `NewsGuardWindow` generation
- optionally use a secondary alert source to create `NewsIncident` candidates in `ACKNOWLEDGED`-required mode rather than fully automatic `OPEN`

### Less than 200 GBP per month
Typical options:
- professional-grade economic calendar APIs with stronger coverage and support
- newswire or headline services suitable for faster incident detection
- dual-provider architecture with one source for structured macro events and another for breaking headlines

What this tier is good for:
- scheduled-event automation with better confidence in freshness and coverage
- more credible breaking-news incident handling for FX and macro-sensitive instruments
- historical event retention suitable for replay and validation
- provider redundancy, which is important if stale-data policy is fail-closed

What to consider:
- this band is usually where production-oriented operations become realistic, but only if licensing allows automated risk controls and persistence of normalized event data
- breaking-news quality still varies widely; faster is not always cleaner
- support for historical retrieval, replay rights, and retention terms matters as much as live delivery speed

Recommended use in this system:
- preferred target band for demo-to-pilot readiness
- use one provider as the authoritative scheduled calendar source and one as a breaking-news incident source
- enable stronger stale-data controls in `/health` because redundancy reduces the chance of unnecessary trading pauses

### Provider Selection Criteria
Regardless of budget, any chosen source should be assessed against these criteria:
- licensing permits automated ingestion, storage, normalization, and risk-based decisioning
- timestamps are precise and consistently UTC-normalizable
- event taxonomy includes country, currency, severity, and event type
- actual, forecast, and previous values are available for surprise calculations where needed
- historical access is available for backtesting and replay
- delivery model supports polling or webhooks without fragile scraping
- provider status can be monitored so `/health` can expose freshness and degradation state

### Practical Recommendation By Budget Band
- Free: use only for prototyping scheduled guards and manual incidents
- Less than 20 GBP: use for a narrow scheduled-event rollout, but do not automate breaking-news actions
- Less than 50 GBP: good starting point for calendar automation and operator-reviewed incident creation
- Less than 200 GBP: best fit for a resilient two-source design with scheduled events plus breaking-news incident support

### Best Fit For This Platform
Given the current architecture, the most pragmatic path is:
- if budget is minimal, implement scheduled calendar guards first and keep breaking-news incident creation manual
- if budget reaches the less-than-50-GBP range, introduce one machine-readable structured calendar provider as the backend source of truth
- if budget reaches the less-than-200-GBP range, add a second source for breaking-news incidents and provider redundancy

This sequence preserves the current backend-owned risk design and avoids overcommitting to low-quality headline automation too early.

## 10. Data Model Plan
### New Prisma models
Introduce the following models in a future implementation change:

#### `NewsEvent`
Fields:
- `newsEventId`
- `provider`
- `providerEventId`
- `eventType`
- `eventClass` (`CALENDAR`, `BREAKING`)
- `title`
- `countryCode`
- `currencyCode`
- `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `scheduledAtUtc`
- `publishedAtUtc`
- `actualValue`
- `forecastValue`
- `previousValue`
- `surpriseScore`
- `status` (`SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `STALE`)
- `rawJson`
- `normalizedJson`
- `createdAt`
- `updatedAt`

#### `NewsProviderStatus`
Fields:
- `provider`
- `lastSuccessfulSyncUtc`
- `lastAttemptedSyncUtc`
- `freshnessState` (`FRESH`, `DEGRADED`, `STALE`, `DOWN`)
- `failureReason`
- `updatedAt`

#### `NewsGuardWindow`
Fields:
- `guardWindowId`
- `newsEventId`
- `symbolScope`
- `currencyScope`
- `strategyScope` (optional in `v1`, required in `v2`)
- `environmentScope` (optional in `v1`, required in `v2`)
- `policyAction` (`ALLOW`, `REDUCE`, `BLOCK_NEW`, `EXIT_ONLY`, `PAUSE`)
- `startsAtUtc`
- `endsAtUtc`
- `severity`
- `reasonCode`
- `metadataJson`
- `createdAt`

#### `NewsIncident`
Fields:
- `newsIncidentId`
- `source` (`PROVIDER`, `SYSTEM`, `OPERATOR`)
- `headline`
- `severity`
- `status` (`OPEN`, `ACKNOWLEDGED`, `CLEARED`, `EXPIRED`)
- `affectedSymbolsJson`
- `strategyId` (optional in `v1`, required in `v2`)
- `strategyVersion` (optional in `v1`, required in `v2`)
- `environmentId` (optional in `v1`, required in `v2`)
- `policyAction`
- `startedAtUtc`
- `endsAtUtc`
- `detailsJson`
- `createdAt`
- `updatedAt`

`NewsIncident` is a `v2` entity. It is not required for the `v1` scheduled-event demonstration.

### Existing model changes
Future implementation should extend existing persistence with news lineage:
- `RiskEvent.detailsJson` should include `newsEventId`, `provider`, `policyAction`, and freshness state when news is involved.
- `RejectedSignal.detailsJson` should include news guard context when the signal is vetoed due to news.
- `Signal.responseJson` should include news reason codes when applicable.

For `v2`, news-derived records should carry strategy and environment lineage consistent with multi-strategy runtime constraints.

## 11. API and Contract Plan
The current contracts do not contain news fields. The first safe integration should avoid forcing the EA to provide news data in the request payload. The backend should own the news state.

### Phase 1 contract changes
No change to EA request payloads for `/signal` or `/risk-check`.

Add backend-owned read endpoints:
- `GET /news/upcoming`
- `GET /news/active`
- `GET /news/providers`

For `v1`, require:
- `GET /news/upcoming`
- `GET /news/active`
- `GET /news/providers`

For `v2`, add:
- `GET /news/incidents`

These endpoints are for dashboard and operator visibility.

### Phase 2 contract changes
If required for stronger traceability, add optional response metadata fields to `/signal`, `/risk-check`, and `/portfolio/evaluate`:
- `newsDecision`
- `newsReasonCodes`
- `newsContext`

This remains optional in the first delivery slice because existing reason-code fields can already carry news veto signals.

## 12. Risk Policy Plan
### Scheduled calendar event policy
Start with a deterministic rule matrix.

Example baseline policy:
- `HIGH` or `CRITICAL` events affecting a symbol's base or quote currency: block new entries from 30 minutes before until 60 minutes after scheduled release.
- `MEDIUM` events: reduce size for 15 minutes before until 30 minutes after release.
- `LOW` events: monitor only, no trade impact.
- Central-bank speeches: configurable reduce or block window because actual market impact is less deterministic than hard-data releases.

Symbol impact examples:
- `EURUSD`: monitor EUR and USD events.
- `GBPUSD`: monitor GBP and USD events.
- `XAUUSD`: monitor USD, Fed events, CPI, NFP, and emergency risk-off incidents.
- index or CFD symbols: map to a configurable country/index risk domain.

Outputs from the policy engine:
- `NEWS_BLOCK_HIGH_IMPACT`
- `NEWS_REDUCE_MEDIUM_IMPACT`
- `NEWS_EXIT_ONLY_CRITICAL`
- `NEWS_PROVIDER_STALE`
- `NEWS_INCIDENT_PAUSE`

For `v1`, implement only the scheduled-event outputs needed for calendar-event handling.
Reserve incident-specific outputs for `v2`.

### Unscheduled breaking-news policy
Handle breaking news separately from calendar events.

Suggested first implementation:
- breaking-news feed or operator-created incident opens a `NewsIncident`
- affected symbols or symbol groups are marked `PAUSE` or `EXIT_ONLY`
- new entries are blocked until the incident is cleared or a cooldown expires
- risk events are emitted immediately for operator visibility

This avoids premature dependence on NLP confidence scoring while still giving the platform a safe way to react to market shocks.

This entire subsection is `v2` scope.

### Provider failure policy
If provider freshness is not `FRESH`:
- affected symbols move to conservative mode
- at minimum, high-impact symbol groups block new entries
- `/health` exposes degraded news state
- dashboard makes stale state prominent

This must be configurable by environment because dev/demo may tolerate more permissive behavior than pilot/live.

## 13. Integration Points In Current Codebase
### Backend signal path
Integrate news checks into `backend/src/routes/signal.ts` after payload validation and before final action is returned.

Recommended shape:
- keep `evaluateDailyBreakout` unchanged for directional logic
- extend `evaluateSignalLevelRisk` or call a dedicated `evaluateNewsRisk` beside it
- merge returned reason codes into the existing `reasonCodes` array
- in `v1`, force `HOLD` for blocked scheduled-event entries while preserving existing exit behavior elsewhere in the flow
- in `v2`, support incident-driven `PAUSE` or `EXIT_ONLY` semantics without blocking protective exits

### Backend account risk path
Integrate the same policy into:
- `backend/src/routes/risk.ts`
- `backend/src/routes/portfolio.ts`

Reason:
- `/signal` and `/portfolio/evaluate` must not disagree about whether a trade is allowed during an active news window.

### Health and metrics
Extend `backend/src/routes/health.ts` with:
- `telemetry.newsProvider`
- `telemetry.newsFreshness`
- `telemetry.newsReason`

Add read endpoints in a new route file, for example:
- `backend/src/routes/news.ts`

### Prisma and migrations
Add normalized news tables through Prisma migrations and preserve raw provider payload for auditability.

### MQL5 EA
The EA does not need to ingest news feeds directly in the first phase. That is the correct tradeoff for now because:
- the backend already owns central risk decisions
- news sources are easier to normalize server-side
- idempotent audit behavior is already backend-centric

Optional later enhancement:
- add an EA-side read-only preflight endpoint for active news windows so the terminal can display operator diagnostics before sending `/signal`

### Dashboard
Extend the current risk and safety view to include:
- active news guard status
- next five high-impact events
- stale provider warnings
- recent news-driven vetoes from `risk_events`
- open breaking-news incidents

For `v1`, only the first four items are required.
Open breaking-news incidents are a `v2` dashboard requirement.

## 14. Implementation Phases
### Phase A - v1 foundation and scheduled-event ingestion
Deliver:
- provider selection and normalization contract
- Prisma models and migrations for news entities
- background sync service with freshness tracking
- internal symbol-impact mapping configuration

Exit criteria:
- normalized news events persist correctly
- provider freshness is visible in `/health`
- stale provider behavior is testable

### Phase B - v1 scheduled calendar guards
Deliver:
- news policy engine for scheduled events
- integration into `/signal`, `/risk-check`, and `/portfolio/evaluate`
- structured news reason codes in existing decision responses
- risk event persistence for every news veto or reduction

Exit criteria:
- affected symbols block or reduce deterministically around configured events
- idempotent signal replay returns the same news-driven decision
- dashboard shows active news windows and recent vetoes
- protective exits remain allowed during news guard windows while new entries are blocked

### Phase C - v2 breaking-news incidents
Deliver:
- `NewsIncident` persistence
- operator and provider driven incident opening/clearing
- pause and exit-only policy actions
- dashboard incident panel

Exit criteria:
- system can pause affected symbols without code changes
- incident state is auditable and time-bounded

### Phase D - v2 live-news validation and optimization
Deliver:
- historical news replay harness
- baseline comparison of no-news vs news-guard trading
- configuration tuning for pre/post windows and event severity

Exit criteria:
- guard policy shows acceptable tradeoff between avoided tail risk and missed opportunity

## 15. Testing Plan
### Unit tests
Add tests for:
- event normalization
- symbol-impact mapping
- guard-window computation
- scheduled-event policy decisions
- stale-provider fail-closed behavior

For `v2`, add unit tests for:
- incident open and clear logic

### Integration tests
Extend existing backend tests to cover:
- `/signal` vetoed by active news window
- `/risk-check` vetoed by stale provider
- `/portfolio/evaluate` rejecting plans during high-impact windows
- idempotent replay of news-driven responses
- persistence of `RiskEvent` and `RejectedSignal` with news metadata

For `v2`, add integration tests for:
- `/risk-check` vetoed by active incident
- incident lifecycle transitions and enforcement (`OPEN` -> `ACKNOWLEDGED` -> `CLEARED`)

### System tests
Add system-level verification for:
- provider outage -> degraded health -> blocked entries
- calendar event enters active window -> dashboard reflects state -> signals become blocked
- blocked new entries still permit protective exits

For `v1`, require only the scheduled-event system tests.
For `v2`, add: incident created -> new entries paused until clear.

### Validation and backtest requirements
Before enabling news guards in production-like environments:
- replay historical event calendars against historical decisions
- measure effect on expectancy, max drawdown, slippage exposure, and missed winners
- confirm no look-ahead leakage from post-release actual values into pre-event decisions

## 16. Key Configuration Decisions Needed
The implementation will need explicit answers for these items before coding starts:
- provider is fixed to Financial Modeling Prep (FMP) for scheduled data and v2 headline/incident candidate flow
- tier schedule is fixed: `FREE` for `v1.x`, `BASIC` for `v2+`
- which environments require fail-closed behavior on stale news data
- which symbols are in scope for the first rollout
- exact pre-event and post-event windows by event severity
- whether medium-impact events reduce size or only log warnings
- whether breaking-news incidents can be opened manually by operators
- whether critical incidents trigger strategy pause only or full system kill-switch

## 17. Recommended First Delivery Slice
The smallest safe slice is:
1. backend-owned scheduled calendar ingestion
2. provider freshness tracking in `/health`
3. deterministic scheduled-event guard policy for a narrow symbol set
4. integration into `/signal` and `/portfolio/evaluate`
5. `RiskEvent` persistence and dashboard visibility for news vetoes

This first slice is explicitly a `v1` scheduled economic-calendar delivery, not a live breaking-news implementation.

This keeps the first implementation aligned with the current architecture and avoids premature complexity from full headline interpretation.

## 18. Risks and Failure Modes
- Provider timestamps or timezone errors can create false windows.
- Duplicate provider events can create repeated vetoes if normalization is weak.
- Symbol-to-event mapping can be too broad and suppress valid trading unnecessarily.
- Overly aggressive stale-data policy can halt trading too often.
- Underly conservative stale-data policy can allow trading through macro risk blindly.
- Breaking-news automation can become noisy unless incident severity is tightly controlled.

## 19. Recommendation
Implement news in two clear versions.

For `v1`, build and demonstrate scheduled economic-calendar handling only using FMP `FREE`. The proof point is that the system ingests known calendar events, activates deterministic guard windows, and returns auditable news-driven decisions for affected symbols.

For `v2`, move to FMP `BASIC` and extend that foundation to live breaking-news handling with incident creation, pause and exit-only semantics, and broader strategy-aware policy controls.

This split is safer, easier to validate, and better aligned with the current LLD boundaries than trying to solve scheduled events and live news in one release.
