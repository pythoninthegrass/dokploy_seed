---
id: TASK-006.05
title: Audit domain.create validation changes from v0.26.6
status: Done
assignee: []
created_date: '2026-03-07 03:43'
updated_date: '2026-03-07 05:59'
labels:
  - api-compat
dependencies:
  - TASK-006.02
parent_task_id: TASK-006
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
v0.26.6 tightened Zod validation for domain assignment (#3504). Need to verify:

1. Our `build_domain_payload()` output still passes validation
2. No new required fields were added
3. Field value constraints (e.g., host format, port range) haven't changed incompatibly

Check the OpenAPI diff (TASK-006.02) for schema changes to `domain.create`.

Relevant code: dokploy.py build_domain_payload (lines 199-211), cmd_setup domain loop (lines 479-492).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 domain.create payload validated against v0.28.4 schema
- [ ] #2 build_domain_payload works without changes OR fix applied
- [ ] #3 Any new validation rules documented in docs/api-notes.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
No action needed. OpenAPI diff shows no schema change for domain.create between v0.26.0 and v0.28.4. The Zod validation tightening (v0.26.6) is server-side only and does not affect the OpenAPI schema."
<!-- SECTION:NOTES:END -->
