# AI Trading System UI Design Specification

Version: 1.0
Last updated: 2026-05-20
Status: Draft design blueprint for implementation

## Contents
- [1. Purpose](#1-purpose)
- [2. Design Goals](#2-design-goals)
- [3. Product Surfaces](#3-product-surfaces)
- [4. Information Architecture](#4-information-architecture)
- [5. Visual Design System](#5-visual-design-system)
- [6. Typography and Spacing](#6-typography-and-spacing)
- [7. Color Tokens and Themes](#7-color-tokens-and-themes)
- [8. Layout Patterns](#8-layout-patterns)
- [9. Core Components](#9-core-components)
- [9.1 Component Hierarchy and Composition](#91-component-hierarchy-and-composition)
- [9.2 Component Behavioral Contract](#92-component-behavioral-contract)
- [9.3 State Model: Active and Inactive](#93-state-model-active-and-inactive)
- [9.4 Component Do and Do Not Rules](#94-component-do-and-do-not-rules)
- [9.5 Data Freshness and Update Behavior](#95-data-freshness-and-update-behavior)
- [10. View-by-View Design](#10-view-by-view-design)
- [11. Data Visualization Standards](#11-data-visualization-standards)
- [12. Interaction and Motion](#12-interaction-and-motion)
- [13. Accessibility and UX Safety](#13-accessibility-and-ux-safety)
- [14. State, Routing, and Frontend Architecture](#14-state-routing-and-frontend-architecture)
- [14.1 Data Contract Ownership](#141-data-contract-ownership)
- [15. Responsive Behavior](#15-responsive-behavior)
- [16. Content and Terminology](#16-content-and-terminology)
- [17. Non-Functional UI Requirements](#17-non-functional-ui-requirements)
- [18. Build Plan for UI](#18-build-plan-for-ui)
- [19. Design QA Checklist](#19-design-qa-checklist)

## 1. Purpose
Define the operator dashboard UI for the trading platform using Vue 3 and Tailwind CSS with mandatory light and dark mode support.
Mobile responsiveness is mandatory, not optional.

This document focuses on:
- Operations visibility
- Risk-first workflows
- Reliable decision monitoring
- Fast operator interpretation during normal and stressed market conditions

## 2. Design Goals
1. Make risk state obvious within 3 seconds of opening the app.
2. Put system health and kill-switch state above all trading performance visuals.
3. Keep controls operator-safe by reducing accidental actions.
4. Ensure every view is usable in both light and dark modes.
5. Preserve visual consistency with design tokens and reusable components.
6. Ensure all critical workflows are fully usable on mobile devices.

## 3. Product Surfaces
Primary surface:
- Web dashboard for operations, monitoring, and decision audit

Secondary surfaces:
- Read-only wallboard mode for always-on status display
- Mobile responsive condensed dashboard for on-call checks

Out of scope:
- Trade execution UI that bypasses risk engine safeguards

## 4. Information Architecture
Top-level navigation:
1. Overview
2. Portfolio
3. Trades and Signals
4. AI and Models
5. Risk and Safety
6. System Health
7. Incidents and Runbooks
8. Settings

Utility areas:
- Global environment selector (demo, pilot, live)
- Strategy selector
- Date/time range filter
- Theme toggle (light/dark)

News provider visibility requirement:
- System Health and Risk and Safety views must display configured news provider and tier (`FMP`, `FREE` for `v1.x`, `BASIC` for `v2+`) with freshness state.

## 5. Visual Design System
Design direction:
- Data-dense operations console with calm neutral base and strong semantic accents
- Emphasis on legibility over decoration
- High-contrast critical states for risk events and outages

Core principles:
- Consistent card and panel structure
- Semantic color usage only for meaning, not decoration
- Dense but scannable hierarchy with strong headings and compact body text

## 6. Typography and Spacing
Typography stack:
- Primary UI font: Source Sans 3
- Numeric/data font: IBM Plex Mono

Type scale:
- Display: 30/36
- H1: 24/32
- H2: 20/28
- H3: 16/24
- Body: 14/20
- Caption: 12/16

Spacing scale:
- Base unit: 4px
- Primary layout gaps: 8, 12, 16, 24, 32

## 7. Color Tokens and Themes
Use CSS variables mapped through Tailwind theme extensions.

Light theme tokens:
- bg-base: #F7F9FC
- bg-surface: #FFFFFF
- bg-elevated: #EEF2F8
- text-primary: #101828
- text-secondary: #344054
- border-subtle: #D0D5DD
- accent-info: #1570EF
- accent-success: #039855
- accent-warning: #DC6803
- accent-danger: #D92D20

Dark theme tokens:
- bg-base: #0B1220
- bg-surface: #111B2E
- bg-elevated: #18253D
- text-primary: #E4E7EC
- text-secondary: #98A2B3
- border-subtle: #344054
- accent-info: #53B1FD
- accent-success: #32D583
- accent-warning: #FDB022
- accent-danger: #F97066

Theme behavior:
- Default to system preference on first load
- Persist explicit user choice in local storage
- No component may hardcode colors outside token system

## 8. Layout Patterns
Global shell:
- Left nav rail (collapsible)
- Top command/status bar
- Main content region with responsive grid

Standard page grid:
- Desktop: 12 columns
- Tablet: 8 columns
- Mobile: 4 columns

Panel sizing presets:
- KPI card: 3 cols desktop
- Mid chart: 6 cols desktop
- Wide table/chart: 12 cols desktop

## 9. Core Components
Required components:
- StatusBadge
- MetricCard
- DeltaPill
- KillSwitchBanner
- HealthTile
- RiskEventTimeline
- SignalDecisionTable
- TradeLedgerTable
- ModelVersionBadge
- DriftIndicator
- ThemeToggle
- DateRangePicker
- StrategyFilter
- EnvironmentSwitcher

Component rules:
- All components support light and dark mode tokens
- All components have loading, empty, and error states
- Any status component must support severity variants (info, warning, critical)

## 9.1 Component Hierarchy and Composition
App composition tree:
1. AppShell
2. GlobalStatusBar
3. ContextControls
4. RoutePageContainer
5. PageSection
6. DataPanel
7. Atomic components (badges, pills, icons, labels)

Composition rules:
- AppShell owns nav, top bar, and persistent alert strip.
- GlobalStatusBar always renders kill-switch and connectivity summary.
- ContextControls renders environment, strategy, date range, and theme controls.
- RoutePageContainer owns route-level loading and error boundaries.
- DataPanel owns per-widget loading/empty/error states and polling cadence.
- Tables and charts never fetch directly from global app root; they receive typed props from page-level composables.

Required containers:
- `AppShellLayout` for global structure.
- `RiskFirstHeader` for critical status above fold.
- `PanelGrid` for consistent responsive placement.
- `AlertRail` for prioritized incidents and system alerts.

## 9.2 Component Behavioral Contract
Every interactive component must define:
- Input props (typed, validated, defaults where safe).
- Emitted events (single-purpose, named by user intent).
- Visual states (default, hover, focus, active, disabled, loading, error).
- Data states (fresh, stale, unavailable).

Required contracts by component type:
- Status components (`StatusBadge`, `KillSwitchBanner`, `HealthTile`):
	- Must include severity level, timestamp, and source.
	- Must expose text alternative for icon-only indicators.
	- Must avoid ambiguous color-only signaling.
- Metric components (`MetricCard`, `DeltaPill`, `DriftIndicator`):
	- Must display value, unit, time basis, and directional delta policy.
- Data table components (`SignalDecisionTable`, `TradeLedgerTable`, `RiskEventTimeline`):
	- Must support sorting, filtering, pagination/virtualization.
	- Must persist column visibility preferences.
	- Must show deterministic row keys (`decisionId`, `signalId`, `tradeId`).
- Control components (`ThemeToggle`, `DateRangePicker`, filters):
	- Must support keyboard operation and clear reset behavior.
	- Must emit one event per finalized change to avoid excessive network churn.

## 9.3 State Model: Active and Inactive
State taxonomy:
- `active`: component is relevant, enabled, and data is actionable.
- `inactive`: component is visible but not currently actionable due to context.
- `disabled`: component blocked due to role/permissions or safety lock.
- `loading`: waiting for data resolution.
- `error`: failed data or action state.
- `stale`: data present but freshness threshold exceeded.

Active vs inactive behavior requirements:
- Active:
	- Full contrast text and interactive controls enabled.
	- Hover/focus affordances visible.
	- Primary actions available if risk policy allows.
- Inactive:
	- Retain readability but reduce emphasis (muted border/background token).
	- Show explicit reason message (for example, "No strategy selected" or "Outside selected timeframe").
	- Do not hide component entirely unless layout collapse is required on mobile.

Disabled behavior requirements:
- Disabled controls must include tooltip/message explaining why.
- Disabled must never look identical to inactive.
- Critical disabled states (for example, due to kill-switch) must surface at page header and local control level.

Loading behavior requirements:
- Use skeleton loaders for cards/charts/tables with reserved layout space.
- Never shift panel dimensions during loading-to-loaded transition.
- Show last known timestamp where available.

Error behavior requirements:
- Inline error panel with retry action and short technical code.
- Preserve other page sections when one panel errors.
- Escalate repeated failures to `AlertRail` after threshold breaches.

## 9.4 Component Do and Do Not Rules
Must do:
- Keep kill-switch status visible in global header and relevant risk panels.
- Show provenance metadata (`strategyId`, `modelVersion`, `timeframe`) on decision-heavy views.
- Preserve user context (filters, pagination, theme) across route changes.
- Ensure all controls are accessible by keyboard and screen reader.
- Use design tokens for all colors, spacing, borders, and shadows.

Must not do:
- Must not hide critical risk alerts behind tabs or collapses by default.
- Must not auto-execute or imply trade actions from the dashboard UI.
- Must not use red/green alone to convey success/failure.
- Must not reset filters silently on refresh or route transition.
- Must not show stale data without explicit stale indicator.
- Must not hardcode theme colors in component styles.

## 9.5 Data Freshness and Update Behavior
Polling defaults:
- Health and risk status panels: 5-10s
- Portfolio and positions: 15-30s
- Trades/signals ledger: 15-30s
- Model performance panels: 30-60s

Freshness indicators:
- Each panel shows "Last updated" timestamp in UTC.
- `stale` state appears when no update beyond 2x polling interval.
- If stale persists beyond 3x interval, raise warning badge and optional alert rail entry.

Update rules:
- Incremental updates preferred over full re-render.
- Preserve row selection and scroll position on data refresh.
- Apply optimistic UI only for local preference actions (not risk/system status).

### Missing Data Fallback

For unavailable data:
1. Display `N/A` with a tooltip explaining the reason (e.g., "Data unavailable due to backend timeout").
2. Use a neutral color to avoid misinterpretation as an error.
3. Log the fallback event for operator review.

## 10. View-by-View Design
Overview:
- Global risk snapshot
- Equity and drawdown trend
- Active incidents
- System health summary

Portfolio:
- Exposure by symbol and asset class
- Open risk budget consumption
- Correlation concentration indicators

Trades and Signals:
- Accepted and rejected signals
- Trade lifecycle table with reason codes
- Live open trades (hydrated from backend API `GET /trades/open`, not local EA state)
- Filter by strategy, symbol, timeframe, model version

AI and Models:
- Score distribution by strategy
- Calibration and drift indicators
- Active/staged model versions and promotion history

Risk and Safety:
- Kill-switch status and history
- Daily/weekly loss progress against limits
- Risk veto breakdown by cause

System Health:
- API uptime, DB health, EA connectivity
- Error rate and latency trends
- Dependency health tiles

Incidents and Runbooks:
- Incident timeline
- Linked runbook steps
- Operator notes and acknowledgements

Settings:
- Theme preferences
- Default filters
- Notification settings

## 11. Data Visualization Standards
Charts:
- Equity curve: line chart with drawdown overlay
- Risk exposure: stacked bar
- Signal outcomes: histogram and segmented bars
- Health metrics: sparkline plus threshold bands

Visualization rules:
- Never rely on color alone to convey critical state
- Add labels/tooltips for all threshold lines
- Use consistent time axis formatting in UTC
- Show confidence intervals where applicable for model metrics

## 12. Interaction and Motion
Motion principles:
- Minimal and purposeful
- Fast transitions (120-180ms)
- No decorative animations on critical alert surfaces

Interactions:
- Hover reveals detail, not hidden primary controls
- Critical actions require confirmation modals
- Filter changes preserve context and scroll position

## 13. Accessibility and UX Safety
Accessibility minimums:
- WCAG 2.1 AA contrast
- Keyboard navigation for all controls
- Focus-visible styles in both themes
- Semantic landmarks and ARIA labels for data regions

Safety UX:
- Critical alerts pinned above fold
- Clear separation between informational and actionable elements
- Explicit warning copy for actions affecting risk controls

## 14. State, Routing, and Frontend Architecture
Framework and libraries:
- Vue 3
- Tailwind CSS
- Pinia
- Vue Router
- ECharts

State domains:
- Session and auth state
- Filters and viewport state
- Health and incident state
- Risk and portfolio state
- Model and AI state

Routing strategy:
- Nested route layout under app shell
- URL-persisted filters for shareable investigation links

## 14.1 Data Contract Ownership
The UI must consume backend payloads defined in the LLDs and must not invent its own canonical data shape.

View-to-data ownership map:
- Overview: account snapshots, performance snapshots, risk events, incident events.
- Portfolio: positions, exposure summaries, allocation events, correlation summaries.
- Trades and Signals: signals, rejected signals, trades, and live open trades from `GET /trades/open`.
- AI and Models: model versions, model predictions, training runs, calibration summaries.
- Risk and Safety: risk events, kill-switch state, veto reasons, recent limit breaches.
- System Health: backend health endpoints, database health, EA connectivity, model loader status.
- Incidents and Runbooks: incident events, acknowledgements, linked runbook steps.
- Settings: persisted client preferences such as theme, layout, and default filters.

Contract rules:
- If a field is not defined by the backend contract, it is not a UI source of truth.
- New dashboard fields require an LLD update before implementation.
- Decision-heavy views should always carry `decisionId`, `strategyId`, `modelVersion`, `barCloseTimeUtc`, and `evaluatedAtUtc` when applicable.

## 15. Responsive Behavior
Desktop first with strong mobile fallback:
- Desktop: full grid with detailed tables and charts
- Tablet: simplified layout, condensed nav
- Mobile: stacked cards, critical statuses first, table-to-card transforms

Breakpoint standard (Tailwind-aligned):
- `sm` (>= 640px): compact tablet/mobile landscape behavior
- `md` (>= 768px): tablet behavior
- `lg` (>= 1024px): desktop behavior
- `xl` (>= 1280px): wide desktop behavior

Mandatory responsive requirements:
- No horizontal page scrolling at common device widths (320px, 375px, 390px, 412px).
- All primary actions must remain reachable within thumb-friendly zones on mobile.
- Navigation must collapse to a mobile-safe menu or bottom action rail.
- Tables must provide a readable mobile mode (card transform or horizontal sectioned rows).
- Charts must support compact mode with simplified legends and tappable data points.
- Filter controls must stack and remain usable without precision pointer input.
- Risk-critical banners (kill-switch, incident severity) must remain above fold on mobile.
- Theme toggle and environment selector must be accessible on all breakpoints.

Component-level responsive rules:
- `MetricCard`: two-column max on small screens, single-column on very narrow screens.
- `SignalDecisionTable` and `TradeLedgerTable`: switch to card/list mode below `md`.
- `RiskEventTimeline`: collapse secondary metadata behind expand/collapse rows on mobile.
- `DateRangePicker`: use full-width modal/sheet pattern on mobile.
- `ThemeToggle`: always visible in mobile command bar or settings shortcut.

Mobile safety behavior:
- Keep kill-switch status always visible at top
- Collapse low-priority visuals behind expandable sections

Mobile performance targets:
- Initial interactive render under 3.0s on mid-tier mobile devices.
- Interaction response under 150ms for filter toggles and tab switches.

## 16. Content and Terminology
Copy style:
- Concise, operational, and unambiguous
- Prefer explicit reason codes over vague prose

Terminology standards:
- Use one canonical label per concept (for example, risk veto, not reject block)
- Include strategy id and model version in decision contexts

## 17. Non-Functional UI Requirements
Performance:
- First meaningful paint under 2.5s on standard VM network
- Table interactions under 100ms perceived latency

Reliability:
- Graceful empty and degraded states when APIs are unavailable
- Retry and stale-data indicators for delayed services

Security:
- Role-aware route protection
- No sensitive secrets rendered in frontend payloads

## 18. Build Plan for UI
Phase A:
- App shell, navigation, theme system, base tokens

Phase B:
- Overview and system health screens

Phase C:
- Trades/signals/risk views

Phase D:
- AI/model and incidents/runbooks views

Phase E:
- Accessibility hardening and visual QA in both themes

## 19. Design QA Checklist
1. Theme toggle works and persists preference.
2. All screens pass contrast checks in light and dark mode.
3. Risk critical states are visible without scrolling on desktop and mobile.
4. Every table has loading, empty, and error states.
5. Strategy/model filters are consistent across views.
6. Health and risk surfaces degrade gracefully during backend failures.
7. No horizontal overflow on supported mobile widths.
8. All critical actions and alerts are reachable and readable on mobile.
9. Tables and charts provide a validated compact mobile presentation.
