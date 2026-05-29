# Copilot Instructions

Use these repository instructions for every request in this workspace.

## Mission
- Implement the platform in strict alignment with the approved documentation set.
- Prioritize correctness, risk controls, auditability, and deterministic behavior over speed.
- Deliver phase-by-phase in alignment with the roadmap and acceptance criteria.

## Document Authority
Use this order of authority when implementing or resolving conflicts:
1. `docs/02-architecture/lld_v1.md` and `docs/02-architecture/lld_v2.md`
2. `docs/05-ui/ui_design.md`
3. `docs/01-roadmap/coding_plan.md`
4. `docs/00-governance/documentation_checklist.md`
5. `docs/00-governance/implementation_runbook.md`

If a lower-level document conflicts with a higher-level one, follow the higher-level document.

## Efficient Document Reading Workflow
Before coding, perform this lightweight reading pass and extract implementation constraints:

1. Intent and scope pass:
- Read goal, version scope, and in-scope/out-of-scope sections from:
  - `docs/01-roadmap/coding_plan.md`
  - `docs/02-architecture/lld_v1.md` or `docs/02-architecture/lld_v2.md`

2. Contract pass:
- Read API contracts, data model, risk rules, and safety behavior from:
  - `docs/02-architecture/lld_v1.md` or `docs/02-architecture/lld_v2.md`
  - `docs/03-specifications/api_contract_specification.md`
  - `docs/03-specifications/data_dictionary_and_lineage.md`

3. Acceptance pass:
- Read deliverables and exit criteria for the target phase in:
  - `docs/01-roadmap/coding_plan.md`
  - `docs/00-governance/implementation_runbook.md`

4. UI pass (if frontend work):
- Read relevant sections of:
  - `docs/05-ui/ui_design.md`

5. Operations pass (if deployment/ops/risk work):
- Read:
  - `docs/04-operations/security_and_access_control.md`
  - `docs/04-operations/incident_and_operations_runbooks.md`
  - `docs/04-operations/slo_sli_and_alerting_matrix.md`

Always summarize extracted constraints before implementation in your own working notes.

## Implementation Guardrails
- Do not implement behavior that is not traceable to a documented requirement, contract, or phase task.
- Keep changes small, testable, and reversible.
- Maintain strict traceability: code change -> phase task -> acceptance criterion.
- When adding endpoints, fields, or flows, update specs and runbook tracker in the same change.

## Controlled Override Policy
You may override existing documentation only when all conditions are true:
- There is a clear correctness, safety, security, or operability issue.
- The proposed change is objectively better and does not reduce safety guarantees.
- You update all impacted documents in the same change, including:
  - authoritative design/spec file(s)
  - roadmap/runbook/checklist references
  - any cross-links that would otherwise become stale

When overriding docs, add a short rationale section titled "Change Rationale" in the modified document.

## Progress and Quality Requirements
- Update progress checkboxes in `docs/00-governance/implementation_runbook.md` as work advances.
- Keep `docs/00-governance/documentation_checklist.md` statuses synchronized with document reality.
- Validate after doc edits:
  - link integrity
  - `git diff --check`

## Delivery Style
- Be concise and explicit.
- Call out assumptions, risks, and unresolved dependencies.
- Always reference changed file paths in updates.

# IMPORTANT
NEVER CURVE FIT!!!!!!
