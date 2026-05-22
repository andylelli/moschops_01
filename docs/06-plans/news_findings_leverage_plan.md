# News Findings Leverage Plan (Beyond v1.1 Scope)

Version: 1.1
Last updated: 2026-05-21
Status: Draft planning document
Primary audience: Tech Lead, Backend Lead, Quant Lead, Ops Lead

## Contents
- [1. Purpose](#1-purpose)
- [2. Authority and Scope Boundaries](#2-authority-and-scope-boundaries)
- [3. Strategy Context Used for Fit Assessment](#3-strategy-context-used-for-fit-assessment)
- [4. Prioritized Item List](#4-prioritized-item-list)
- [5. Item 1 - Call-Budget Governor and Poll Scheduler](#5-item-1---call-budget-governor-and-poll-scheduler)
- [6. Item 2 - Provider Freshness SLO and Drift Thresholds](#6-item-2---provider-freshness-slo-and-drift-thresholds)
- [7. Item 3 - Historical Backfill and Replay Ingestion](#7-item-3---historical-backfill-and-replay-ingestion)
- [8. Item 4 - Economics Indicators Regime Overlay](#8-item-4---economics-indicators-regime-overlay)
- [9. Item 5 - Headline Incident Candidate Pipeline](#9-item-5---headline-incident-candidate-pipeline)
- [10. Item 6 - Press Release Event Channel](#10-item-6---press-release-event-channel)
- [11. Item 7 - Provider Change Monitoring Automation](#11-item-7---provider-change-monitoring-automation)
- [12. Item 8 - Licensing and Data-Use Compliance Controls](#12-item-8---licensing-and-data-use-compliance-controls)
- [13. Recommended Sequencing by Version](#13-recommended-sequencing-by-version)
- [14. Exit Evidence for This Plan](#14-exit-evidence-for-this-plan)
- [15. Other Strategy Options Using Available Information](#15-other-strategy-options-using-available-information)

## 1. Purpose
Capture actionable opportunities from FMP documentation findings that are useful to the platform but are outside the currently approved v1.1 scheduled-event implementation scope.

This plan is additive and does not replace or weaken any mandatory behavior in the v1.1 news addendum.

## 2. Authority and Scope Boundaries
Authority order applied when producing this plan:
1. `docs/02-architecture/lld_v1.md`
2. `docs/02-architecture/lld_v1_1_news.md`
3. `docs/02-architecture/lld_v2.md`
4. `docs/01-roadmap/coding_plan.md`

In scope for this plan:
- Enhancements that leverage FMP capabilities beyond v1.1 minimum scheduled-calendar controls.
- Operational and governance controls to improve reliability and auditability of news inputs.
- Future-phase recommendations for v2 incident and multi-strategy behavior.

Out of scope for this plan:
- Changing v1.1 acceptance criteria.
- Changing existing v1.1 risk-policy semantics for protective exits.
- Implementing code in this document.

## 3. Strategy Context Used for Fit Assessment
Current primary strategy context:
- v1 runtime is a single-strategy, D1 daily-breakout execution path.
- Risk policy emphasis is deterministic, auditable, fail-closed for new entries, and protective exits always allowed.

Strategy-fit labels used below:
- `Fits current strategy`: directly useful for current v1/v1.1 daily-breakout operation.
- `Better for another strategy`: higher value for event-driven, intraday, or multi-strategy runtime in v2+.

## 4. Prioritized Item List
| Priority | Item | Why now | Fits current strategy | Better for another strategy |
|---|---|---|---|---|
| P0 | Call-budget governor and poll scheduler | Needed to keep `FREE` tier stable and deterministic | Yes | No |
| P0 | Provider freshness SLO and drift thresholds | Needed for reliable fail-closed behavior | Yes | No |
| P1 | Historical backfill and replay ingestion | Needed for stronger validation and evidence quality | Yes | No |
| P1 | Provider change monitoring automation | Prevents silent behavior drift from provider updates | Yes | No |
| P1 | Licensing and data-use compliance controls | Reduces legal and distribution risk | Yes | No |
| P2 | Economics indicators regime overlay | Improves regime awareness beyond event windows | Partial | Yes |
| P2 | Headline incident candidate pipeline | Supports unscheduled-event awareness with operator gating | Partial | Yes |
| P3 | Press release event channel | Most useful for equities/event-driven systems | No | Yes |

## 5. Item 1 - Call-Budget Governor and Poll Scheduler
Why:
- FMP `FREE` tier quota and bandwidth ceilings make unconstrained polling fragile.
- Economic-calendar freshness cadence and endpoint constraints require predictable scheduling.

Benefits:
- Prevents quota exhaustion and unexpected stale periods during active market windows.
- Produces deterministic provider usage, which improves reproducibility and operations planning.
- Supports clean upgrade path from `FREE` to `BASIC` without reworking policy logic.

Strategy fit assessment:
- Fits current strategy: Yes.
- Better for another strategy: No. This is foundational for all strategies.

Plan actions:
1. Add explicit per-endpoint budget policy (daily and per-minute caps).
2. Add priority scheduler for calendar sync versus non-critical reads.
3. Add guardrails for retries, backoff, and budget-aware degradation modes.
4. Emit budget telemetry in provider health surfaces.

Version target:
- v1.1 hardening and v1.2 operations readiness.

## 6. Item 2 - Provider Freshness SLO and Drift Thresholds
Why:
- v1.1 already requires stale-provider fallback, but SLO-quality thresholds and drift alarms are needed for sustained reliability.

Benefits:
- Makes `FRESH`, `DEGRADED`, `STALE`, `DOWN` transitions measurable and testable.
- Reduces false safety triggers while preserving fail-closed safety intent.
- Improves incident triage and post-mortem clarity.

Strategy fit assessment:
- Fits current strategy: Yes.
- Better for another strategy: No. This is a shared platform safety control.

Plan actions:
1. Define freshness SLI windows per endpoint class.
2. Add provider-time drift checks and UTC consistency checks.
3. Add alert thresholds for sync lag, consecutive failures, and stale duration.
4. Extend evidence package templates with freshness timelines.

Version target:
- v1.1 hardening, v1.3 ops maturity.

## 7. Item 3 - Historical Backfill and Replay Ingestion
Why:
- Endpoint range and pagination limits require explicit ingestion planning for full-history test coverage.

Benefits:
- Improves backtest and replay realism for scheduled-event policy validation.
- Enables deterministic comparison of policy revisions on the same historical corpus.
- Strengthens acceptance evidence quality across phases.

Strategy fit assessment:
- Fits current strategy: Yes.
- Better for another strategy: No. Useful for all strategy validation.

Plan actions:
1. Define rolling backfill jobs with bounded range windows.
2. Add dedup and idempotent replay policies for historical loads.
3. Persist provider snapshots required for reproducible replays.
4. Add verification checks for data continuity gaps.

Version target:
- v1.2 validation hardening, v1.3 demo evidence support.

## 8. Item 4 - Economics Indicators Regime Overlay
Why:
- Calendar-event windows handle event-time risk but not broader macro regime context.

Benefits:
- Improves risk posture adaptation across inflation, rates, and growth regimes.
- Can reduce overexposure when macro backdrop is adverse even outside event windows.
- Supports richer portfolio controls in v2 allocator logic.

Strategy fit assessment:
- Fits current strategy: Partial.
- Better for another strategy: Yes, especially multi-strategy allocation and macro-aware swing systems.

Plan actions:
1. Define non-blocking macro regime score from economics indicators.
2. Use regime score only as risk modifier first, not as direct entry trigger.
3. Add calibration and drift monitoring for regime feature behavior.
4. Keep strict separation between scheduled-event veto and macro overlay logic.

Version target:
- v2.0 preferred; optional late v1.3 experiment in read-only mode.

## 9. Item 5 - Headline Incident Candidate Pipeline
Why:
- Unscheduled shocks remain a risk gap if only calendar windows are used.

Benefits:
- Adds early warning channel for operator response without forcing fragile full automation.
- Preserves deterministic policy by requiring acknowledgement before enforcement.
- Provides a clean bridge from v1.1 scheduled controls to v2 incident lifecycle.

Strategy fit assessment:
- Fits current strategy: Partial, as operator-assist only.
- Better for another strategy: Yes, especially intraday and event-driven strategies.

Plan actions:
1. Ingest headline feeds into incident candidates with confidence tags.
2. Require operator `ACKNOWLEDGED` step before incident becomes active.
3. Restrict automated actions to conservative defaults (`PAUSE` or `EXIT_ONLY`) in v2.
4. Add audit trail for candidate -> acknowledgement -> clear transitions.

Version target:
- v2.0+ only.

## 10. Item 6 - Press Release Event Channel
Why:
- Company-specific release flows are a distinct event type not fully represented by macro calendars.

Benefits:
- Improves single-name equity event risk handling.
- Supports finer strategy scoping for symbol-level event controls.

Strategy fit assessment:
- Fits current strategy: No for current FX/metals-first daily-breakout scope.
- Better for another strategy: Yes, equities and event-driven models.

Plan actions:
1. Add separate event taxonomy for corporate releases.
2. Bind event scope to symbol-level exposure maps.
3. Keep default disabled for current v1 instrument set.

Version target:
- v2.x optional extension.

## 11. Item 7 - Provider Change Monitoring Automation
Why:
- Provider route, schema, or cadence changes can silently break deterministic behavior if unmanaged.

Benefits:
- Detects upstream breaking changes early.
- Reduces surprise regressions and emergency hotfix pressure.
- Improves operational confidence before demo and pilot stages.

Strategy fit assessment:
- Fits current strategy: Yes.
- Better for another strategy: No. Platform-wide reliability control.

Plan actions:
1. Poll provider changelog and status references on a controlled schedule.
2. Run schema-diff checks against stored contract expectations.
3. Create runbook triggers for review, rollback, or temporary policy tightening.
4. Add monthly provider-assumption review checkpoint.

Version target:
- Start in v1.2, mandatory by v1.3.

## 12. Item 8 - Licensing and Data-Use Compliance Controls
Why:
- External data use, storage, and display constraints require explicit governance to avoid downstream legal risk.

Benefits:
- Ensures platform usage remains within plan and redistribution rights.
- Reduces risk of compliance debt during dashboard expansion and external reporting.
- Clarifies what can be persisted, displayed, and exported by environment.

Strategy fit assessment:
- Fits current strategy: Yes.
- Better for another strategy: No. This is cross-strategy governance.

Plan actions:
1. Add provider-terms review checklist for each release gate.
2. Tag data artifacts with allowed-usage classification.
3. Add UI guardrails for restricted display/export cases.
4. Add legal-signoff requirement before pilot-level external sharing.

Version target:
- Begin immediately with v1.1 operations, enforce at v1.3 gate.

## 13. Recommended Sequencing by Version
v1.1 hardening:
1. Item 1 - Call-budget governor and scheduler.
2. Item 2 - Freshness SLO and drift thresholds.
3. Item 8 - Licensing and compliance controls.

v1.2 and v1.3 maturity:
1. Item 3 - Historical backfill and replay ingestion.
2. Item 7 - Provider change monitoring automation.

v2+ expansion:
1. Item 5 - Headline incident candidate pipeline.
2. Item 4 - Economics indicators regime overlay.
3. Item 6 - Press release event channel.

## 14. Exit Evidence for This Plan
This planning document is considered complete when:
1. Each item has an owning team and target milestone in implementation tracking.
2. Each item has acceptance checks linked in runbook tasks.
3. Strategy-fit decisions are confirmed by product and quant owners.
4. No item conflicts with v1.1 safety requirements or v2 sequencing rules.

## 15. Other Strategy Options Using Available Information
This section explains additional strategies that can leverage currently available information from:
- Scheduled economic calendar events.
- Economic indicators time series.
- General and stock news headlines.
- Press release channels.
- Provider freshness and status telemetry.

### 15.1 Strategy Candidates and Fit
| Strategy candidate | Data used well | Why it works | Benefits | Fit with current strategy | Better suited to another strategy |
|---|---|---|---|---|---|
| Macro regime risk-overlay trend following | Economic indicators + calendar + provider freshness | Uses indicators to classify macro regime and adjust existing trend risk posture | Better drawdown control and less overexposure in adverse macro phases | Partial fit; can be added as risk modifier to current daily-breakout | No |
| Event-window breakout specialization | Economic calendar + event impact + historical replay | Focuses on pre/post high-impact windows with deterministic behavior | Clear, auditable rules and stronger news-to-action traceability | Strong fit; close to current v1.1 architecture | No |
| Post-release continuation strategy | Calendar events + actual/forecast/previous fields + volatility context | Trades momentum continuation when release surprise aligns with directional impulse | Captures structured post-event directional moves | Weak fit for current D1-only setup; timing granularity may be too coarse | Yes; better for intraday event-driven FX |
| News incident defensive allocator | Headline feeds + status/freshness + incident lifecycle | Converts unscheduled headlines into operator-reviewed risk actions | Faster shock response while preserving governance and auditability | Partial fit as operator-assist in current stack | Yes; best in v2 multi-strategy runtime |
| Equity event and press-release reaction strategy | Press releases + stock news + company-level mapping | Uses company-specific catalysts not represented in macro calendar | Better symbol-level event control and potential alpha in single-name instruments | Low fit for current FX/metals-first scope | Yes; best for equity/event-driven book |
| Cross-asset risk-on/risk-off rotation | Economic indicators + calendar + broad headline flow | Builds top-down risk regime to rotate exposure across strategy buckets | Improved portfolio diversification and macro alignment | Not a direct fit for single-strategy v1 | Yes; best with v2 allocator and multi-strategy orchestration |

### 15.2 Recommended Strategy Path by Version
1. v1.1 to v1.3: prioritize event-window breakout specialization and macro regime risk overlay as non-disruptive extensions.
2. v2.0: add news incident defensive allocator once incident lifecycle support is active.
3. v2.x: add equity event and press-release reaction only when instrument universe expands beyond current scope.
4. v2.x: add cross-asset risk-on/risk-off rotation only after shared allocator telemetry and attribution are stable.

### 15.3 Selection Criteria for First Non-v1.1 Strategy
Choose the first additional strategy that satisfies all conditions below:
1. Deterministic policy outcomes from identical inputs.
2. Clear reason-code lineage in risk and rejection records.
3. No violation of protective-exit safety rule.
4. Data freshness and quota budget remain within configured thresholds.
5. Replay evidence demonstrates improvement versus baseline on drawdown and risk-adjusted return.
