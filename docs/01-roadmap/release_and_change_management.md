# Release and Change Management Guide

Version: 1.0
Last updated: 2026-05-20

## Purpose
Define the versioning scheme, release checklist, and rollback procedures for the trading platform.

## Versioning Scheme
- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
  - **MAJOR**: Breaking changes to APIs, data models, or platform behavior.
  - **MINOR**: Backward-compatible feature additions or improvements.
  - **PATCH**: Bug fixes or non-functional changes.

## Release Checklist
1. **Pre-Release Validation**:
   - All P0 requirements in the [requirements traceability matrix](../00-governance/requirements_traceability_matrix.md) are verified.
   - All tests (unit, integration, regression) pass with no critical failures.
   - Documentation is updated and reviewed.
  - News provider configuration is validated against policy: FMP `FREE` for `v1.x`, FMP `BASIC` for `v2+`.
2. **Release Approval**:
   - Obtain sign-off from Product, Tech Lead, and QA.
   - Ensure rollback plan is documented and tested.
3. **Deployment**:
   - Deploy to `demo` environment and validate.
   - Promote to `pilot` and validate.
   - Deploy to `live` after final approval.

## Rollback Procedures
- **Trigger Conditions**:
  - Critical bugs or regressions detected in `demo`, `pilot`, or `live`.
  - Performance degradation beyond SLO thresholds.
- **Rollback Steps**:
  1. Notify stakeholders and freeze new deployments.
  2. Revert to the last stable version using the deployment pipeline.
  3. Validate the rollback and monitor for residual issues.

## Notes
- Rollbacks must be logged in the incident management system.
- Postmortems are mandatory for all rollbacks.