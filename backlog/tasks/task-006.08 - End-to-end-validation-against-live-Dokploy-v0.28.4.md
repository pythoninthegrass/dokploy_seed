---
id: TASK-006.08
title: End-to-end validation against live Dokploy v0.28.4
status: Done
assignee: []
created_date: '2026-03-07 03:43'
updated_date: '2026-03-07 06:39'
labels:
  - api-compat
dependencies:
  - TASK-006.06
  - TASK-006.07
parent_task_id: TASK-006
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run the full command suite against a live Dokploy v0.28.4 instance to validate everything works:

```bash
uv run pytest tests/ -v                      # all tests pass
uv run --script dokploy.py --env prod check   # pre-flight succeeds
uv run --script dokploy.py --env prod setup   # project + apps created
uv run --script dokploy.py --env prod env     # env vars pushed
uv run --script dokploy.py --env prod deploy  # deploys triggered
uv run --script dokploy.py --env prod status  # status readable
uv run --script dokploy.py --env prod destroy # cleanup works
```

This is the final validation gate before closing the parent task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 uv run pytest tests/ -v passes with 0 failures
- [x] #2 check, setup, env, deploy, status, destroy all succeed against live v0.28.4
- [x] #3 No regressions in existing functionality
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
### E2E Results Against Live Dokploy v0.28.4

#### Unit/Integration Tests

132 passed, 5 deselected (e2e markers)

#### Live E2E (all passed)

- `check` — pre-flight 5/5
- `setup` — project + app created, GitHub provider configured, buildType set, domain created
- `env` — env vars pushed with createEnvFile=false
- `trigger` — deploy triggered (async, returns immediately)
- `status` — app status: done
- `destroy` — project deleted, state file removed

#### Additional Fixes Required During E2E

1. `application.saveBuildType`: `herokuVersion` and `railpackVersion` are now required fields (even if null). OpenAPI spec marks them as nullable but Zod validates them as non-optional. Fixed by adding both fields with `None` default to `build_build_type_payload()`.
2. `buildType` enum updated: `docker` and `heroku` replaced with `heroku_buildpacks`, `paketo_buildpacks`, `railpack` in schema, docs, and example.

#### Production Re-deployed

Project re-created and deployed after validation.
<!-- SECTION:NOTES:END -->
