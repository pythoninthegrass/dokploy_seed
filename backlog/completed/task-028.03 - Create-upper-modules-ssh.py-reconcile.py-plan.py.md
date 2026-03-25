---
id: TASK-028.03
title: 'Create upper modules: ssh.py, reconcile.py, plan.py'
status: Done
assignee: []
created_date: '2026-03-23 22:42'
updated_date: '2026-03-23 22:47'
labels:
  - refactor
dependencies:
  - TASK-028.01
  - TASK-028.02
parent_task_id: TASK-028
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract modules that depend on leaf and mid-tier modules.

**ssh.py** (~180 LOC):
- `get_ssh_config()`, `build_docker_url()`, `get_docker_client()`, `TRAEFIK_DYNAMIC_DIR`, `collect_domains()`, `find_stale_app_names()`, `_ssh_exec()`, `cleanup_stale_routes()`, `get_containers()`, `resolve_app_for_exec()`, `select_container()`
- Imports: `icarus.config`, `icarus.client` (type)

**reconcile.py** (~245 LOC):
- `reconcile_schedules()`, `reconcile_app_schedules()`, `reconcile_mounts()`, `reconcile_app_mounts()`, `reconcile_ports()`, `reconcile_app_ports()`, `reconcile_domains()`, `reconcile_app_domains()`, `reconcile_app_settings()`
- Imports: `icarus.payloads`, `icarus.client`, `icarus.env`

**plan.py** (~320 LOC):
- `_env_keys()`, `_plan_initial_setup()`, `_plan_redeploy()`, `compute_plan()`, `print_plan()`, `cmd_plan()`
- Imports: `icarus.env`, `icarus.payloads`, `icarus.client`, `icarus.schema`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ssh.py contains all SSH/Docker/Traefik/container helpers
- [x] #2 reconcile.py contains all reconcile_* and reconcile_app_* functions
- [x] #3 plan.py contains plan/diff logic and cmd_plan
- [x] #4 All three modules import successfully
<!-- AC:END -->
