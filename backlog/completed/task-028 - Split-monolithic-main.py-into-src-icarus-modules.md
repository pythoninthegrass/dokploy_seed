---
id: TASK-028
title: Split monolithic main.py into src/icarus/ modules
status: Done
assignee: []
created_date: '2026-03-23 22:41'
updated_date: '2026-03-23 23:09'
labels:
  - refactor
dependencies: []
references:
  - .sisyphus/drafts/refactor-main-split.md
  - .claude/plans/calm-humming-quasar.md
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refactor the 2326-LOC monolithic `main.py` (PEP 723 script) into logical modules under `src/icarus/`. After the split, `main.py` becomes a ~10-line thin router with imports and `cli.py` holds the argparse + match/case dispatch.

## Module Layout

```
src/icarus/
  __init__.py      Re-exports all public symbols
  cli.py           argparse + match/case dispatch
  config.py        config singleton, find_repo_root
  schema.py        load/validate/merge dokploy.yml, get_state_file
  env.py           env filtering, resolve_refs
  client.py        DokployClient, state load/save
  payloads.py      all payload builders, DB constants, compose helpers
  reconcile.py     all reconcile_* functions
  plan.py          plan/diff logic, cmd_plan
  ssh.py           SSH/Docker/Traefik/container helpers
  commands.py      all cmd_* functions
```

## Key Decisions

- Remove PEP 723 script metadata from main.py
- Remove symlink src/icarus/main.py -> ../../main.py
- __init__.py re-exports everything (including private fns used by tests)
- Tests migrate from importlib hack to `import icarus as dokploy`
- Entry point `ic = "icarus:main"` preserved via __init__.py re-export from cli.py

## Plan File

Full plan at `.claude/plans/calm-humming-quasar.md`
<!-- SECTION:DESCRIPTION:END -->
