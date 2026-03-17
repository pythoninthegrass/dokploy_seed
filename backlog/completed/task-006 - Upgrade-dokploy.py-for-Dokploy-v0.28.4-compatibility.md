---
id: TASK-006
title: Upgrade dokploy.py for Dokploy v0.28.4 compatibility
status: Done
assignee: []
created_date: '2026-03-07 03:42'
updated_date: '2026-03-07 06:20'
labels:
  - api-compat
  - parent
dependencies: []
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Track all work needed to make dokploy.py compatible with Dokploy v0.28.4 (upgrading from v0.25.6, spanning 20 releases).

Approach: upgrade-then-diff. Capture OpenAPI specs before and after the Dokploy instance upgrade, diff the 13 endpoints used by dokploy.py, and fix any breaking or behavioral changes.

Scope: Script, tests, docs, and schema only. Dokploy instance upgrade is out of scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All 13 API endpoints used by dokploy.py work against Dokploy v0.28.4
- [ ] #2 Unit and integration tests pass
- [ ] #3 End-to-end validation (check, setup, env, deploy, status) succeeds against live v0.28.4 instance
- [ ] #4 docs/api-notes.md updated with any new quirks
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
### Summary

All subtasks complete. dokploy.py is compatible with Dokploy v0.28.4.

### Breaking Changes Fixed

1. `application.saveEnvironment` — `createEnvFile` (boolean) now required. Added per-app `create_env_file` config option (default: false).
2. `application.saveBuildType` — `herokuVersion` and `railpackVersion` now required by Zod (not reflected in OpenAPI spec). Sending null for both.
3. `buildType` enum — `docker` and `heroku` replaced with `heroku_buildpacks`, `paketo_buildpacks`, `railpack`.

### Files Changed

- `dokploy.py` — cmd_env (createEnvFile), build_build_type_payload (herokuVersion, railpackVersion)
- `tests/test_integration.py` — createEnvFile assertions + new test
- `tests/test_unit.py` — updated build type payload expected values
- `schemas/dokploy.schema.json` — create_env_file field, updated buildType enum
- `docs/api-notes.md` — documented all new quirks
- `docs/configuration.md` — added create_env_file, updated buildType enum
- `dokploy.yml.example` — updated buildType comment, added create_env_file

### New Files

- `scripts/fetch_openapi.sh` — fetch OpenAPI spec from GitHub for any Dokploy release tag
- `schemas/src/openapi_0.26.0.json` — baseline spec
- `schemas/src/openapi_0.28.4.json` — target spec

### Key Finding

Dokploy's OpenAPI spec diverges from its Zod validation. The OpenAPI diff missed two breaking changes (herokuVersion/railpackVersion required, buildType enum change) that were caught only by live E2E testing.
<!-- SECTION:NOTES:END -->
