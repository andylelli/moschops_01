# Requirements Traceability Matrix

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Map the major platform requirements to their delivery phase, authoritative design source, and verification status.

## Traceability Matrix
| Req ID | Requirement | Delivery phase/version | Authoritative source | Verification evidence | Status |
|---|---|---|---|---|---|
| RTM-01 | Deterministic daily-breakout execution on completed bars only | Phase 1 / v1.0 | [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | EA backtest and unit tests | Not verified |
| RTM-02 | Strategy API returns signal, risk, and health decisions with idempotent correlation | Phase 2 / v1.0 | [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | API contract tests | Not verified |
| RTM-03 | Persist signals, rejections, trades, features, model metadata, and snapshots | Phase 3 / v1.0 | [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | Migration and persistence tests | Not verified |
| RTM-04 | Risk engine vetoes unsafe trades and enforces capital caps | Phase 4 / v1.0 | [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | Risk rule simulation | Not verified |
| RTM-05 | Backtesting uses realistic costs and avoids look-ahead bias | Phase 5 / v1.0 | [../01-roadmap/coding_plan.md](../01-roadmap/coding_plan.md), [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | Validation report | Not verified |
| RTM-06 | AI model training uses walk-forward validation and calibrated promotion gates | Phase 6-7 / v1.1 | [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | Model validation artifacts | Not verified |
| RTM-07 | Portfolio runtime respects correlation and exposure controls | Phase 8 / v1.2 | [../01-roadmap/coding_plan.md](../01-roadmap/coding_plan.md), [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | Portfolio simulation | Not verified |
| RTM-08 | Operations dashboard shows risk, health, AI, and live trade status | Phase 9 / v1.3 | [../05-ui/ui_design.md](../05-ui/ui_design.md), [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | UI acceptance tests | Not verified |
| RTM-09 | Demo and micro-live controls require safety gating and incident tracking | Phase 10 / v1.3 | [../01-roadmap/coding_plan.md](../01-roadmap/coding_plan.md), [../02-architecture/lld_v1.md](../02-architecture/lld_v1.md) | Runbook rehearsal | Not verified |
| RTM-10 | Multi-strategy and managed-cloud expansion preserve v1 safeguards | Phase 11-13 / v2.0-v2.1 | [../02-architecture/lld_v2.md](../02-architecture/lld_v2.md) | Integration and migration tests | Not verified |
| RTM-11 | News provider is Financial Modeling Prep with version-tier policy (`FREE` for v1.x, `BASIC` for v2+) | Phase v1.1-v2.x | [../02-architecture/lld_v1_1_news.md](../02-architecture/lld_v1_1_news.md), [../02-architecture/lld_v2.md](../02-architecture/lld_v2.md), [../06-plans/news_integration_plan.md](../06-plans/news_integration_plan.md) | Config and health telemetry evidence (`/health`, `/news/providers`) | Not verified |

## Notes
- Treat this matrix as the cross-reference layer for planning and review.
- Add verification evidence links as implementation and testing complete.
