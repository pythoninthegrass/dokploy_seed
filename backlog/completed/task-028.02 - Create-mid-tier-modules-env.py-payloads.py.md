---
id: TASK-028.02
title: 'Create mid-tier modules: env.py, payloads.py'
status: Done
assignee: []
created_date: '2026-03-23 22:42'
updated_date: '2026-03-23 22:45'
labels:
  - refactor
dependencies:
  - TASK-028.01
parent_task_id: TASK-028
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract modules with minimal internal dependencies from main.py.

**env.py** (~75 LOC):
- `DEFAULT_ENV_EXCLUDES`, `get_env_excludes()`, `_is_env_excluded()`, `filter_env()`, `resolve_env_for_push()`, `resolve_refs()`
- Imports: `icarus.config.config`

**payloads.py** (~195 LOC):
- `DATABASE_TYPES`, `DATABASE_DEFAULTS`, `database_endpoint()`, `database_id_key()`, `build_database_create_payload()`
- `build_github_provider_payload()`, `resolve_github_provider()`
- `build_build_type_payload()`, `is_compose()`, `resolve_compose_file()`
- `build_domain_payload()`, `build_app_settings_payload()`, `build_mount_payload()`, `build_port_payload()`, `build_schedule_payload()`
- Imports: `DokployClient` via TYPE_CHECKING only
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 env.py contains DEFAULT_ENV_EXCLUDES, get_env_excludes, _is_env_excluded, filter_env, resolve_env_for_push, resolve_refs
- [x] #2 payloads.py contains all payload builders, DB constants, compose helpers, resolve_github_provider
- [x] #3 Both modules import successfully
<!-- AC:END -->
