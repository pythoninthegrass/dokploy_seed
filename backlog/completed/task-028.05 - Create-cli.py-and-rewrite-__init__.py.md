---
id: TASK-028.05
title: Create cli.py and rewrite __init__.py
status: Done
assignee: []
created_date: '2026-03-23 22:43'
updated_date: '2026-03-23 22:50'
labels:
  - refactor
dependencies:
  - TASK-028.04
parent_task_id: TASK-028
priority: high
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**cli.py** (~95 LOC):
- Extract `main()` function: argparse setup + match/case dispatch
- Imports from icarus.config, icarus.schema, icarus.client, icarus.commands

**__init__.py** (~30 LOC):
- Re-export all public symbols from every module (FastAPI-style)
- Include private functions used by tests: `_build_config`, `_plan_redeploy`, `_plan_initial_setup`
- `from icarus.cli import main` for entry point compatibility
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 cli.py contains main() with argparse + match/case
- [x] #2 __init__.py re-exports all public symbols from all modules
- [x] #3 Entry point works: python -c 'from icarus import main; print(main)'
- [x] #4 No circular imports: python -c 'import icarus'
<!-- AC:END -->
