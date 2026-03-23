---
id: TASK-028.06
title: 'Slim root main.py, remove symlink, update tests and docs'
status: Done
assignee: []
created_date: '2026-03-23 22:43'
updated_date: '2026-03-23 23:09'
labels:
  - refactor
dependencies:
  - TASK-028.05
parent_task_id: TASK-028
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Root main.py:**
- Remove PEP 723 script metadata (lines 3-13)
- Keep shebang (uv run or python3, per draft)
- Replace 2300+ lines with: `from icarus.cli import main` + `if __name__ == "__main__": main()`
- Result: ~10 LOC

**Remove symlink:**
- Delete `src/icarus/main.py` (was symlink to `../../main.py`)

**Test imports** — replace importlib hack in all test files:
- conftest.py: `import icarus as _dokploy`
- test_unit.py, test_integration.py, test_e2e.py, test_property.py: `import icarus as dokploy`
- test_property.py strategies.py import stays as-is

**Docs updates:**
- `docs/testing.md` — update "Importing main.py" section
- `CLAUDE.md` — update project structure, remove/update PEP 723 standalone references
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 main.py is ~10 lines with import + if __name__ guard
- [x] #2 src/icarus/main.py symlink is deleted
- [x] #3 All test files use import icarus as dokploy instead of importlib hack
- [x] #4 uv run pytest tests/ -x passes
- [x] #5 docs/testing.md import section updated
- [x] #6 CLAUDE.md project structure updated
- [x] #7 python main.py --help works
- [x] #8 uv tool install . --force && ic --help works
<!-- AC:END -->
