# Documentation Governance Standard

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define how documentation in this repository is authored, reviewed, and kept consistent as the platform evolves.

## Source of Truth
Authoritative documents, in order of behavior specificity:
1. Low-level design documents (`../02-architecture/lld_v1.md`, `../02-architecture/lld_v2.md`)
2. UI design specification (`../05-ui/ui_design.md`)
3. Delivery plan (`../01-roadmap/coding_plan.md`)
4. Checklist and tracking docs (`documentation_checklist.md`)

## Update Rules
- Update the most specific authoritative document first.
- If a change affects implementation behavior, update the relevant LLD before updating summary docs.
- If a change affects operator UI behavior, update `../05-ui/ui_design.md` before downstream task lists.
- Keep the checklist aligned with real document ownership and status.
- Do not leave a planning doc claiming a capability that no authoritative doc defines.

## Review Rules
- Every doc change should preserve consistency with the LLDs.
- New terminology must be canonicalized in one document before being reused elsewhere.
- Cross-references should point to the authoritative source, not a paraphrase.
- Remove or mark historical baseline text when it is no longer relevant to delivery decisions.

## Minimum Acceptance
Documentation is considered maintainable when:
- Source-of-truth order is explicit.
- Planning docs are clearly separated from normative specs.
- Each active implementation area has an authoritative reference.
- The checklist points to a real owning document for each item.