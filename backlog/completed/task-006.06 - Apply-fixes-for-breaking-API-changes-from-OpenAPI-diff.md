---
id: TASK-006.06
title: Apply fixes for breaking API changes from OpenAPI diff
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
After the OpenAPI diff (TASK-006.02) identifies breaking changes, apply the necessary fixes to dokploy.py.

This is a catch-all task for changes discovered by the diff that aren't covered by the specific audit tasks (TASK-006.03, TASK-006.04, TASK-006.05). Scope will be refined after the diff is complete.

Potential areas based on release notes:
- New required fields in existing endpoints
- Changed field types or validation
- Removed or renamed endpoints
- Changed response formats
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All breaking changes from diff addressed
- [ ] #2 dokploy.py updated with fixes
- [ ] #3 Tests updated to match new API behavior
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Only breaking change from diff: `application.saveEnvironment` requires `createEnvFile`. Fixed in TASK-006.04.

Additive changes in `application.update` (new optional fields: args, bitbucketRepositorySlug, createEnvFile, rollbackRegistryId) — no action needed.
<!-- SECTION:NOTES:END -->
