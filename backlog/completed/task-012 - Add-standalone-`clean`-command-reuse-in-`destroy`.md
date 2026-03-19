---
id: TASK-012
title: 'Add standalone `clean` command, reuse in `destroy`'
status: Done
assignee: []
created_date: '2026-03-17 15:17'
updated_date: '2026-03-17 15:29'
labels:
  - feat
  - gh-issue-5
dependencies: []
references:
  - 'https://github.com/pythoninthegrass/icarus/issues/5'
  - 'main.py:881'
  - 'main.py:1043'
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**GitHub Issue**: #5 — Clean up stale Traefik configs and orphaned Docker services on destroy

## Problem

When `ic destroy` removes a Dokploy project, stale Traefik dynamic config files and orphaned Docker Swarm services remain on the server. On subsequent `ic deploy`, the old Traefik config routes the same domain to a dead service, causing 502 Bad Gateway errors (Traefik load-balances between old dead and new live backends).

Currently `cleanup_stale_routes()` is only called during `deploy` (main.py:787). The `cmd_destroy()` function (main.py:1043) does not call it at all.

## Requirements

1. **Standalone `clean` command** — new `cmd_clean` subcommand that calls `cleanup_stale_routes()` directly, so users can run `ic --env prod clean` independently
2. **Reuse in `destroy`** — `cmd_destroy` should call the same cleanup logic before or after deleting the project
3. **Skip cleanup when SSH env vars are missing** — if all three mandatory `DOKPLOY_SSH_*` env vars (`DOKPLOY_SSH_HOST`, `DOKPLOY_SSH_USER`, `DOKPLOY_SSH_PORT`) are absent, skip cleanup gracefully with a message instead of erroring out. Currently only `DOKPLOY_SSH_HOST` is checked (main.py:886-889); `DOKPLOY_SSH_USER` and `DOKPLOY_SSH_PORT` have defaults so the skip condition should check whether all three are explicitly unset/empty

## Current Code

- `cleanup_stale_routes()` at main.py:881 — SSH-based cleanup of stale Traefik configs and Docker services
- `cmd_destroy()` at main.py:1043 — deletes project + state file, does NOT call cleanup
- Deploy calls cleanup at main.py:787
- SSH env vars read at main.py:807-813 and main.py:886-897

## Implementation Notes

- Add `clean` to the argparse subparsers (main.py:~1128) and dispatch (main.py:~1187)
- `cmd_clean` needs `state_file` and `cfg` (same as deploy's cleanup call)
- In `cmd_destroy`, call cleanup before project deletion (state file still exists and is needed to resolve app names)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Standalone `ic --env <env> clean` command exists and removes stale Traefik configs + orphaned Docker services via SSH
- [x] #2 `cmd_destroy` calls the same cleanup logic before deleting the Dokploy project
- [x] #3 Cleanup is skipped gracefully (with a message, no error) when all three `DOKPLOY_SSH_HOST`, `DOKPLOY_SSH_USER`, `DOKPLOY_SSH_PORT` env vars are missing/empty
- [x] #4 Tests cover: clean command invocation, destroy-with-cleanup flow, skip behavior when SSH vars are absent
- [x] #5 CLI help output includes the `clean` subcommand
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Changes

### `main.py`
- **`cleanup_stale_routes()`** (line ~881): Now reads all three `DOKPLOY_SSH_HOST`, `DOKPLOY_SSH_USER`, `DOKPLOY_SSH_PORT` up front. Skips with message when all three are empty. Falls back to defaults (`root`/`22`) when only user/port are missing but host is set.
- **`cmd_clean(cfg, state_file)`**: New function that loads state and delegates to `cleanup_stale_routes()`.
- **`cmd_destroy(client, cfg, state_file)`**: Signature changed to accept `cfg`. Calls `cleanup_stale_routes()` before project deletion (while state file still exists).
- **CLI**: Added `clean` subcommand to argparse and dispatch. Updated usage docstring.

### Tests
- `TestCmdClean`: Verifies `cmd_clean` delegates to `cleanup_stale_routes` with correct args
- `TestCmdDestroyCallsCleanup`: Verifies cleanup runs before `project.remove` (ordering test)
- `TestCleanupSkipsWhenAllSshVarsMissing`: Two tests — skips when all three empty, proceeds when only host is set
- Updated all existing `cmd_destroy` callers in `test_integration.py`, `test_e2e.py`, `conftest.py` for new signature
<!-- SECTION:NOTES:END -->
