---
id: TASK-006.07
title: 'Update docs, schema, and examples for v0.28.4 compatibility'
status: Done
assignee: []
created_date: '2026-03-07 03:43'
updated_date: '2026-03-07 06:01'
labels:
  - api-compat
dependencies:
  - TASK-006.06
parent_task_id: TASK-006
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After all API fixes are applied, update supporting files:

1. `docs/api-notes.md` — Add any new API quirks discovered during the upgrade
2. `schemas/dokploy.schema.json` — Add new config fields if any new API features are worth exposing
3. `dokploy.yml.example` — Update if schema changes affect the example
4. `docs/configuration.md` — Update if new config options are added

Only add fields that are actually useful for the script's use cases. Don't add every new API field.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docs/api-notes.md reflects v0.28.4 behavior
- [ ] #2 Schema validates against updated dokploy.yml.example
- [ ] #3 No stale v0.25.6-specific documentation remains
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Updated:

- `schemas/dokploy.schema.json`: added `create_env_file` boolean (default false) to apps items
- `docs/api-notes.md`: documented `createEnvFile` required field and `application.deploy` async behavior
- `docs/configuration.md`: added `create_env_file` to apps table and overridable properties list
- `dokploy.yml.example`: added commented `create_env_file` example
<!-- SECTION:NOTES:END -->
