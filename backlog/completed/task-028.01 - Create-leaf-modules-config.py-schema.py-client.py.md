---
id: TASK-028.01
title: 'Create leaf modules: config.py, schema.py, client.py'
status: Done
assignee: []
created_date: '2026-03-23 22:42'
updated_date: '2026-03-23 22:44'
labels:
  - refactor
dependencies: []
parent_task_id: TASK-028
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract zero-dependency modules from main.py into src/icarus/.

**config.py** (~45 LOC):
- `_build_config()`, `config` singleton, `find_repo_root()`

**schema.py** (~95 LOC):
- `get_state_file()`, `load_config()`, `validate_config()`, `validate_env_references()`, `merge_env_overrides()`

**client.py** (~65 LOC):
- `DokployClient` class, `validate_state()`, `load_state()`, `save_state()`

These are leaf nodes in the dependency DAG — no imports from other icarus modules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 config.py contains _build_config, config singleton, find_repo_root
- [x] #2 schema.py contains get_state_file, load_config, validate_config, validate_env_references, merge_env_overrides
- [x] #3 client.py contains DokployClient, validate_state, load_state, save_state
- [x] #4 All three modules import successfully: python -c 'from icarus.config import config; from icarus.schema import load_config; from icarus.client import DokployClient'
<!-- AC:END -->
