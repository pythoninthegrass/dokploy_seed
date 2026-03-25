---
id: TASK-014
title: Add `plan` subcommand with terraform-style diff view
status: Done
assignee: []
created_date: '2026-03-19 19:20'
updated_date: '2026-03-19 19:25'
labels:
  - feature
  - cli
dependencies: []
references:
  - 'main.py:cmd_apply (line 868)'
  - 'main.py:cmd_setup (line 567)'
  - 'main.py:cmd_env (line 761)'
  - 'main.py:reconcile_schedules (line 320)'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a `plan` subcommand to icarus that shows a diff of what `apply` would change in the Dokploy API, similar to `terraform plan`. Uses `+` create, `~` update, `-` destroy symbols.

Scope mirrors what `apply` actually does:
- **Initial setup (no state)**: all resources shown as creates (project, apps, providers, domains, env, mounts, schedules, settings, commands)
- **Redeploy (state exists)**: only diffs env vars, schedules, and compose files (what apply actually touches on redeploy)
- **Orphaned state**: treated as initial setup

Env var diffs show key-level changes only (added/removed/unchanged keys), not values.

Makes read-only API calls (`application.one`, `compose.one`, `schedule.list`) to fetch current remote state for comparison.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 No state file: all resources shown as `+ create`
- [x] #2 State exists, no changes: prints 'up to date' with no diff
- [x] #3 State exists, env keys changed: shows `~ update` with added/removed keys
- [x] #4 State exists, schedules changed: shows create/update/destroy per schedule
- [x] #5 Orphaned state (project gone): falls back to full creates
- [x] #6 Summary line: 'Plan: X to create, Y to update, Z to destroy.'
- [x] #7 No write API calls are made (read-only)
- [x] #8 Subcommand registered in CLI argparse as `plan`
- [x] #9 Tests added to test_unit.py
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `plan` subcommand with terraform-style diff output.

**Functions added to `main.py`:**
- `_env_keys()` — extracts variable names from KEY=value env blobs
- `_plan_initial_setup()` — builds create changes for all resources when no state exists
- `_plan_redeploy()` — diffs env vars and schedules against live API (mirrors what `apply` actually does on redeploy)
- `compute_plan()` — orchestrates initial vs redeploy plan, handles orphaned state
- `print_plan()` — terraform-style output with `+`/`~`/`-` symbols and summary line
- `cmd_plan()` — thin wrapper wiring compute + print

**CLI:** `plan` subcommand registered in argparse and match statement.

**Tests:** 21 new tests in `test_unit.py` covering initial setup creates, no-changes detection, env key diffs, schedule CRUD diffs, orphaned state fallback, print formatting, and the cmd_plan integration path.
<!-- SECTION:FINAL_SUMMARY:END -->
