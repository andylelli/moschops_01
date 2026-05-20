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

## Notes
- All environments must use separate credentials and secrets.
- Deployment pipelines must enforce promotion gates.