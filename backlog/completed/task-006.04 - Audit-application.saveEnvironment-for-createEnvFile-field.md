---
id: TASK-006.04
title: Audit application.saveEnvironment for createEnvFile field
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
v0.26.1 added a `createEnvFile` option to environment settings (#3212). Need to determine:

1. Does `application.saveEnvironment` now require or accept `createEnvFile`?
2. Did the default behavior change? (Previously .env files were always created)
3. Does dokploy.py need to explicitly set `createEnvFile: true` to preserve current behavior?

Check the OpenAPI diff (TASK-006.02) for schema changes to `application.saveEnvironment`.

Relevant code: dokploy.py cmd_env (lines 511-560), payload sends `{applicationId, env, buildArgs: None, buildSecrets: None}`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Determined whether createEnvFile field is needed
- [ ] #2 cmd_env works against v0.28.4 without code changes OR fix applied
- [ ] #3 Behavior documented in docs/api-notes.md if relevant
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed. `createEnvFile` is now required in v0.28.4's `application.saveEnvironment`.

Changes:

- Added `apps_by_name` lookup dict in `cmd_env`
- Both saveEnvironment call sites now include `createEnvFile` from per-app `create_env_file` config (default: `false`)
- Added `test_create_env_file_flag` integration test
- Added `createEnvFile` assertions to existing env tests
<!-- SECTION:NOTES:END -->
