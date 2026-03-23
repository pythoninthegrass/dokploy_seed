---
id: TASK-020
title: Enhance `plan` command with full drift detection
status: Done
assignee: []
created_date: '2026-03-23 18:05'
updated_date: '2026-03-23 21:27'
labels:
  - gap-analysis
  - plan
milestone: m-0
dependencies:
  - TASK-016
  - TASK-017
  - TASK-018
  - TASK-019
references:
  - main.py
priority: high
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The `plan` command currently only shows env and schedule changes. It doesn't detect drift for domains, mounts, app config, ports, or other resources. Should compare local config against server state for all managed resource types and show a comprehensive diff.

Depends on domain/mount/port reconciliation tasks being designed first to understand the server-state query patterns.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Plan shows domain additions/removals
- [x] #2 Plan shows mount additions/removals
- [x] #3 Plan shows port additions/removals
- [x] #4 Plan shows app config changes (command, replicas, autoDeploy, etc.)
- [x] #5 Plan output is accurate compared to what apply actually changes
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added app config drift detection (command, replicas, autoDeploy) to `_plan_redeploy` and created `reconcile_app_settings` function wired into the `cmd_apply` redeploy path. Plan now detects drift for all managed resource types: env, domains, mounts, ports, schedules, and app settings. The plan output accurately reflects what apply will change.

Changes:
- `main.py`: Added settings drift detection in `_plan_redeploy` (compares command/replicas/autoDeploy against remote)
- `main.py`: Added `reconcile_app_settings()` function that updates command/replicas/autoDeploy on redeploy when they differ from remote
- `main.py`: Wired `reconcile_app_settings` into `cmd_apply` redeploy path
- `tests/test_unit.py`: Added `TestPlanAppConfigChanges` (6 tests), `TestCmdApplyReconcileAppSettings` (1 test), `TestReconcileAppSettings` (5 tests)
<!-- SECTION:FINAL_SUMMARY:END -->
