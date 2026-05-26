# AI Trading System UI Design Specification

Version: 1.2
Last updated: 2026-05-22
Status: Active design blueprint for implementation

## UI Implementation Progress Tracker

Last verified: 2026-05-22

Status legend:
- Not started
- In progress
- Blocked
- Complete

### Overall Snapshot

| Metric | Value | Notes |
|---|---|---|
| Estimated overall implementation completion | 54% | Based on tracker rows below and current dashboard evidence |
| Active blockers | 1 | Provider entitlement constraints may limit some data-rich UI validation flows |
| Highest-priority open areas | Full API contract binding, training/admin diagnostic depth, visualization stack completion | Needed to satisfy sections 10-12, 14.1, and 19 |

### Section-by-Section Tracker

| Track ID | Spec section(s) | Scope | Status | Completion | Evidence / Notes |
|---|---|---|---|---:|---|
| UI-01 | 1, 2, 3, 4 | Product intent, IA, and top-level navigation model | In progress | 82 | Full top-level route set is wired; shell now exposes role chip, environment/strategy/date/profile context controls, and global risk-first header surfaces |
| UI-02 | 5, 5.1 | Visual system, iconography, and polish standards | In progress | 45 | Tokenized theme base exists; Font Awesome integration and icon registry rollout still pending |
| UI-03 | 6, 7 | Typography, spacing, and light/dark token behavior | In progress | 70 | Typography and token variables are implemented; full quality-pass spacing conformance pending |
| UI-04 | 8 | Layout patterns and grid behavior | In progress | 74 | Global shell, responsive nav, alert rail, and persistent kill-switch banner patterns are now implemented; panel preset consistency still pending |
| UI-05 | 9, 9.1, 9.2, 9.3, 9.4, 9.5 | Core component library and behavior contracts | In progress | 46 | `DataPanel`, `MetricCard`, `StatusBadge`, `KillSwitchBanner`, `AlertRail`, `RoleGuard`, and `TradeLedgerTable` are implemented; additional component contract coverage remains |
| UI-06 | 10 | View-by-view design coverage | In progress | 52 | All top-level views are implemented; training/admin/risk/trades pages now include stronger interaction and control scaffolding, but several panels still use placeholder datasets |
| UI-07 | 11, 11.1 | Visualization standards and graph tooling | Not started | 10 | Required chart stack and rich model/admin visual diagnostics are not yet integrated |
| UI-08 | 12, 12.1 | Interaction and micro-interaction quality | In progress | 50 | Admin privileged actions now use explicit two-step confirmation with reason capture; deterministic motion and advanced training interaction quality pass still pending |
| UI-09 | 13 | Accessibility and UX safety | In progress | 48 | Focus-visible styling, role-aware action gating, and text-labeled status badges are present; full WCAG validation and complete keyboard pass remain |
| UI-10 | 14, 14.1 | Frontend architecture and data contract ownership | In progress | 50 | Vue/Pinia/router baseline exists; full route/state domain coverage and contract checks pending |
| UI-11 | 15 | Responsive behavior and mobile safety | In progress | 62 | Mobile navigation plus table-to-card transform is now implemented in trade ledger surfaces; compact chart/diagnostic modes still pending |
| UI-12 | 16 | Content and terminology consistency | In progress | 45 | Reason-code oriented copy is present in some views; full canonical terminology pass pending |
| UI-13 | 17 | Non-functional UI requirements | Not started | 15 | Performance and reliability targets defined but not yet formally measured |
| UI-14 | 18 | Build plan execution | In progress | 42 | Phase A-C are substantially implemented and parts of Phase E/F have started via training/admin action flows and accessibility hardening |
| UI-15 | 19 | Design QA checklist completion | In progress | 18 | Items covering theme persistence, risk visibility, icon semantics, and part of mobile table behavior now have implementation evidence; formal QA evidence is still open |

## Contents
- [UI Implementation Progress Tracker](#ui-implementation-progress-tracker)
- [1. Purpose](#1-purpose)
- [2. Design Goals](#2-design-goals)
- [3. Product Surfaces](#3-product-surfaces)
- [4. Information Architecture](#4-information-architecture)
- [5. Visual Design System](#5-visual-design-system)
- [5.1 Iconography and Visual Polish](#51-iconography-and-visual-polish)
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
- [11.1 Training and Admin Visualization Profiles](#111-training-and-admin-visualization-profiles)
- [12. Interaction and Motion](#12-interaction-and-motion)
- [12.1 Interaction Quality Pass](#121-interaction-quality-pass)
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
- Admin-safe system control and auditing workflows
- AI training workflows that are easy for first-time operators and powerful for advanced users

## 2. Design Goals
1. Make risk state obvious within 3 seconds of opening the app.
2. Put system health and kill-switch state above all trading performance visuals.
3. Keep controls operator-safe by reducing accidental actions.
4. Ensure every view is usable in both light and dark modes.
5. Preserve visual consistency with design tokens and reusable components.
6. Ensure all critical workflows are fully usable on mobile devices.
7. Make AI training setup runnable in under 2 minutes for default presets.
8. Provide rich visual diagnostics so model quality and risk can be interpreted at a glance.

## 3. Product Surfaces
Primary surface:
- Web dashboard for operations, monitoring, and decision audit
- Web control center for admin governance and AI training lifecycle

Secondary surfaces:
- Read-only wallboard mode for always-on status display
- Mobile responsive condensed dashboard for on-call checks
- Guided training wizard mode for rapid and safe model iteration

Out of scope:
- Trade execution UI that bypasses risk engine safeguards

## 4. Information Architecture
Top-level navigation:
1. Overview
2. Portfolio
3. Trades and Signals
4. AI and Models
5. Training Studio
6. Risk and Safety
7. System Health
8. Incidents and Runbooks
9. Admin
10. Settings

Utility areas:
- Global environment selector (demo, pilot, live)
- Strategy selector
- Date/time range filter
- Theme toggle (light/dark)
- Dataset/profile selector (training surfaces)
- Operator role chip (viewer, analyst, admin)

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
- Strong icon and label pairing for rapid scanning in high-pressure workflows

## 5.1 Iconography and Visual Polish
Icon system standard:
- Use Font Awesome as the default icon library across navigation, status badges, and action controls.
- Use SVG component rendering through Vue, not icon fonts.
- Use one visual family baseline (`solid` for navigation/status, `regular` for secondary/detail actions).

Recommended frontend package installs:
1. `npm install @fortawesome/fontawesome-svg-core @fortawesome/free-solid-svg-icons @fortawesome/free-regular-svg-icons @fortawesome/vue-fontawesome`
2. Optional licensed tier: `@fortawesome/pro-solid-svg-icons` and `@fortawesome/pro-regular-svg-icons` only when a valid license is available.

Icon usage rules:
- Every icon that conveys state must include an adjacent text label in critical workflows.
- Icon-only buttons must include accessible name attributes and visible focus style.
- Keep icon sizes consistent by role: 14px for inline metadata, 16px for table/status rows, 20px for section headers, 24px for primary KPI/status tiles.
- Do not mix more than two icon visual weights on the same surface.
- Do not use decorative icons in kill-switch, risk veto, or incident-critical banners.

Navigation and status icon mapping baseline:
- Overview: `faGaugeHigh`
- Portfolio: `faBriefcase`
- Trades and Signals: `faArrowRightArrowLeft`
- AI and Models: `faMicrochip`
- Training Studio: `faFlask`
- Risk and Safety: `faShieldHalved`
- System Health: `faHeartbeat`
- Incidents and Runbooks: `faTriangleExclamation`
- Admin: `faUserShield`
- Settings: `faGear`
- Success state: `faCircleCheck`
- Warning state: `faTriangleExclamation`
- Critical state: `faCircleXmark`

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

Quality pass typography and spacing rules:
- Header rows and section intros must maintain a minimum 12px vertical rhythm.
- Dense operational tables must preserve at least 40px row height for readability and tap comfort.
- Label-value pairs in KPI and status cards must align to a consistent baseline grid.

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
- TrainingWizard
- TrainingPresetSelector
- HyperparameterEditor
- DatasetCoverageHeatmap
- TrainingRunTimeline
- MetricsComparisonChart
- FeatureImportancePanel
- ConfusionMatrixCard
- RocPrPanel
- ArtifactRegistryTable
- RunPromotionDrawer
- JobQueueBoard
- AuditLogTable
- RoleGuard
- IconActionButton
- IconLabel

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
- Training components (`TrainingWizard`, `HyperparameterEditor`, `TrainingRunTimeline`):
	- Must support Easy mode (preset-first) and Advanced mode (full option panel).
	- Must provide safe defaults and show estimated run cost/time before launch.
	- Must persist draft configuration and allow clone-from-previous-run.
- Admin components (`RoleGuard`, `AuditLogTable`, `RunPromotionDrawer`):
	- Must enforce role-aware visibility and action gating.
	- Must require explicit confirmation for high-impact actions (promotion, rollback, disable).
	- Must record actor, timestamp, and reason for every privileged action.
- Icon components (`IconActionButton`, `IconLabel`):
	- Must render Font Awesome icons via Vue component wrappers.
	- Must include an accessible text name and preserve minimum contrast in both themes.
	- Must avoid icon-only signaling for critical state changes.

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
- Keep training status, queue state, and last successful model promotion visible above fold in Training Studio.
- Keep admin action audit trail visible and filterable by actor, action type, and time range.

Must not do:
- Must not hide critical risk alerts behind tabs or collapses by default.
- Must not auto-execute or imply trade actions from the dashboard UI.
- Must not use red/green alone to convey success/failure.
- Must not reset filters silently on refresh or route transition.
- Must not show stale data without explicit stale indicator.
- Must not hardcode theme colors in component styles.
- Must not allow model promotion, rollback, or policy override without role and confirmation checks.
- Must not hide failed training diagnostics; root-cause context must always be reachable in one click.

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

Training Studio:
- Guided training wizard (6-step) that covers workflow selection, data/validation parameters, feature toggles, AI runtime policy, launch review, and completion actions
- Easy mode path with recommended presets by strategy and timeframe
- Advanced mode with expandable options for feature set, label policy, split policy, CV, calibration, and thresholds
- One-click launch from preset with editable guardrails
- Training run timeline with queue state, duration estimate, and resource profile
- Outcome snapshot cards must include percentage-based quality interpretation (for example: estimated success likelihood, accuracy, capture rate, coverage, calibration alignment, and robustness).
- Outcome area must include a prominent overall effectiveness percentage in large typography for fast operator triage, with supporting metric percentages below it.
- Visual diagnostics: confusion matrix, ROC/PR, feature importance, calibration curve, reliability bins, and drift deltas
- Wizard completion state must provide direct navigation shortcuts to diagnostics and training timeline evidence.
- Run comparison workspace with side-by-side metrics and threshold simulations
- Artifact panel with ONNX, metadata, and reproducibility hash visibility
- Promotion readiness checklist with explicit risk gate status

Admin:
- Role and access overview (viewer, analyst, admin)
- System toggles with scoped blast-radius descriptions
- Approval queue for model promotion and rollback
- Audit log explorer with actor, action, reason, and affected scope
- Configuration snapshots and rollback controls
- Provider entitlement and quota status board

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

Second-pass quality expectations for all views:
- Each page header must include one primary icon + title + short operational subtitle.
- Each critical panel must expose state, source, and timestamp in a single visual scan row.
- Empty and degraded states must provide next-step guidance, not just status text.

## 11. Data Visualization Standards
Charts:
- Equity curve: line chart with drawdown overlay
- Risk exposure: stacked bar
- Signal outcomes: histogram and segmented bars
- Health metrics: sparkline plus threshold bands
- Training loss and validation curves: dual-axis line with confidence bands
- Confusion matrix: annotated heatmap
- ROC and Precision-Recall: interactive line charts with threshold markers
- Feature importance: ranked horizontal bars with cohort filter
- Calibration reliability: bucketed line + residual bars
- Run comparison: radar summary + sortable metric table
- Pipeline topology and dependency views for admin/training lineage

Visualization rules:
- Never rely on color alone to convey critical state
- Add labels/tooltips for all threshold lines
- Use consistent time axis formatting in UTC
- Show confidence intervals where applicable for model metrics

## 11.1 Training and Admin Visualization Profiles
Graphing and charting stack:
- Baseline: ECharts with vue-echarts for operational and performance charts
- High-interaction diagnostics: Plotly.js for zoomable model-quality visuals
- Relationship and dependency views: Cytoscape for pipeline lineage and dependency graphs
- Optional custom rendering: D3 for bespoke visuals not covered by existing libraries

Recommended frontend package installs:
1. `npm install echarts vue-echarts`
2. `npm install plotly.js-dist-min vue-plotly`
3. `npm install cytoscape`
4. `npm install d3`

Visualization implementation policy:
- Use route-level code splitting and dynamic imports for heavy graph libraries.
- Prefer pre-aggregated backend series for large datasets to keep UI responsive.
- Provide static fallback summaries when interactive graphs fail to load.
- Keep chart legends and icon indicators consistent with Font Awesome status semantics.

## 12. Interaction and Motion
Motion principles:
- Minimal and purposeful
- Fast transitions (120-180ms)
- No decorative animations on critical alert surfaces

Interactions:
- Hover reveals detail, not hidden primary controls
- Critical actions require confirmation modals
- Filter changes preserve context and scroll position

## 12.1 Interaction Quality Pass
Required micro-interaction standards:
- Use deterministic transition durations (120ms, 160ms, 180ms only).
- Keep skeleton-to-content transitions visually stable with no panel jump.
- Use icon-assisted confirmations for high-impact actions, including explicit consequence copy.
- Require two-step confirmation for model promotion, rollback, and global disable actions.

Training ease-of-use standards:
- Easy mode launches must expose a recommended preset first and hide advanced fields by default.
- Advanced mode must be searchable and grouped by category (data, labels, CV, thresholds, calibration, export).
- Every advanced setting must include inline help text and safe default value.
- Guided wizard flow must provide ordered step navigation with per-step validation before launch.
- Guided wizard modal must support keyboard-safe dismissal (Escape key) and preserve operator-entered values across steps.
- Training launch summary must show expected runtime, resource profile, and rollback plan before submit.

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
- Plotly.js (training diagnostics)
- Cytoscape (admin/training dependency graphs)
- Font Awesome (`@fortawesome/vue-fontawesome` and icon packs)

State domains:
- Session and auth state
- Filters and viewport state
- Health and incident state
- Risk and portfolio state
- Model and AI state
- Training configuration, jobs, and run artifacts state
- Admin approvals, role scopes, and audit state

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
- Training Studio: training profiles, run requests, job statuses, run metrics, artifact metadata, promotion candidate assessments.
- Risk and Safety: risk events, kill-switch state, veto reasons, recent limit breaches.
- System Health: backend health endpoints, database health, EA connectivity, model loader status.
- Incidents and Runbooks: incident events, acknowledgements, linked runbook steps.
- Admin: role assignments, approval records, config versions, operational toggles, and audit events.
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
- Mandatory action-level authorization checks for admin and model promotion workflows
- Privileged action audit trail retention and exportable review views

## 18. Build Plan for UI
Phase A:
- App shell, navigation, theme system, base tokens
- Font Awesome integration with centralized icon registry and navigation/status icon mapping

Phase B:
- Overview and system health screens

Phase C:
- Trades/signals/risk views

Phase D:
- AI/model and incidents/runbooks views

Phase E:
- Training Studio easy mode and advanced mode with diagnostics visuals
- Admin control center with approvals, audit logs, and rollback surfaces

Phase F:
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
10. Training Studio supports both one-click preset launch and advanced configuration editing.
11. Training diagnostics charts (loss, ROC/PR, confusion matrix, calibration, feature importance) render with fallback states.
12. Admin actions are role-gated, confirmed, and auditable with actor and reason.
13. Font Awesome icons are consistently applied across navigation, statuses, and action controls.
14. Icon semantics match state semantics (success, warning, critical) and include text where critical.
15. Easy training mode is usable end-to-end without touching advanced settings.
16. Advanced training mode remains discoverable, grouped, and fully keyboard accessible.
17. Guided training wizard covers all runtime and training parameters with step-level validation and launch review.
18. Wizard post-launch completion step exposes quick navigation to diagnostics and training-session timeline.
19. Training outcome cards present percentage-based model quality interpretation and explicitly label estimated-success metrics as non-guaranteed live outcomes.
