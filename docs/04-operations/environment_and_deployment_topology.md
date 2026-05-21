# Environment and Deployment Topology

Version: 1.0
Last updated: 2026-05-20

## Purpose
Define the infrastructure topology and promotion gates for the trading platform environments.

## Environments
1. **Development (dev)**:
   - Purpose: Local development and integration testing.
   - Access: Developers only.
   - Infrastructure: Local Docker containers, mock services.
2. **Demo**:
   - Purpose: Internal validation and stakeholder demos.
   - Access: Developers, QA, Product.
   - Infrastructure: Cloud-hosted, limited resources.
3. **Pilot**:
   - Purpose: Controlled live testing with limited capital.
   - Access: Developers, QA, Ops.
   - Infrastructure: Cloud-hosted, production-like.
4. **Live**:
   - Purpose: Full production environment.
   - Access: Ops, limited developer access.
   - Infrastructure: Cloud-hosted, high availability.

## MT5 Placement and Data Flow

- MT5 terminal runs on Windows host (local workstation, VPS, or Windows VM).
- Backend, database, and training services run on Linux host or containerized stack.
- EA sends signal and open-trade snapshots to backend APIs over approved WebRequest endpoints.
- Historical and execution data from MT5 must be exported or streamed into PostgreSQL for training lineage.

## Promotion Gates
- **Dev → Demo**:
  - All unit and integration tests pass.
  - Code review completed.
- **Demo → Pilot**:
  - All demo validation criteria met.
  - No critical bugs in demo.
- **Pilot → Live**:
  - Pilot SLOs met for 8 weeks.
  - Final approval from Product and Ops.

## External News Dependency
- Provider: Financial Modeling Prep (FMP).
- Pricing reference: https://site.financialmodelingprep.com/developer/docs/pricing
- Tier by version: `FREE` for `v1.x`, `BASIC` for `v2+`.
- Environment rule: provider key and tier configuration must be environment-scoped and never shared across env boundaries.

## Notes
- All environments must use separate credentials and secrets.
- Deployment pipelines must enforce promotion gates.
- Demo and higher environments require validated MT5-to-backend connectivity before promotion.