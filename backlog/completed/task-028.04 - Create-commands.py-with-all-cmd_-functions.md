---
id: TASK-028.04
title: Create commands.py with all cmd_* functions
status: Done
assignee: []
created_date: '2026-03-23 22:43'
updated_date: '2026-03-23 22:49'
labels:
  - refactor
dependencies:
  - TASK-028.01
  - TASK-028.02
  - TASK-028.03
parent_task_id: TASK-028
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract all command implementations into src/icarus/commands.py (~500 LOC).

**Contents:**
- `cmd_check()`, `cmd_setup()`, `cmd_env()`, `cmd_trigger()`, `cmd_apply()`, `cmd_status()`, `cmd_logs()`, `cmd_exec()`, `cmd_clean()`, `cmd_destroy()`, `cmd_import()`

Top of the dependency tree (below cli.py). Imports from: config, schema, env, client, payloads, reconcile, plan, ssh.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 commands.py contains all 11 cmd_* functions
- [x] #2 All commands import successfully from icarus.commands
<!-- AC:END -->
