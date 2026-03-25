---
id: TASK-015
title: Redesign env exclusion to support exact match and prefix patterns
status: Done
assignee: []
created_date: '2026-03-23 16:37'
updated_date: '2026-03-23 16:42'
labels:
  - refactor
  - bug
dependencies: []
references:
  - 'https://github.com/pythoninthegrass/icarus/issues/6'
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The `filter_env` function uses `startswith` for all exclusion patterns, making it impossible to exclude a specific short-named variable (e.g. `DEV`) without also excluding unrelated variables that share the prefix (e.g. `DEVICE_TOKEN`, `DEVELOPER_MODE`).

**Problem:** A project had `DEV=True` in its `.env` for local development. This got pushed to production via `ic env`, bypassing auth on all endpoints. Adding `DEV` to `ENV_EXCLUDE_PREFIXES` also excludes any future var starting with `DEV`.

**Current behavior:**
```python
DEFAULT_ENV_EXCLUDE_PREFIXES = ["COMPOSE_", "DOKPLOY_", ...]

if any(key.startswith(prefix) for prefix in exclude_prefixes):
    continue
```

Both `DEFAULT_ENV_EXCLUDE_PREFIXES` and `ENV_EXCLUDE_PREFIXES` are treated as prefixes with no way to exclude an exact key name without risk of over-matching.

**Proposed options (choose one):**

- **Option A (Convention-based, single list):** Entries ending with `_` or `*` are prefix matches; entries without are exact matches. Backward compatible since existing entries like `COMPOSE_` already end with `_`.
- **Option B (Separate config keys):** `ENV_EXCLUDE_KEYS` for exact matches, `ENV_EXCLUDE_PREFIXES` for prefix matches (existing behavior).
- **Option C (Regex support):** Allow regex patterns in exclusion list. Most flexible but higher complexity.

**Files to modify:** `main.py` (`filter_env` function, `DEFAULT_ENV_EXCLUDE_PREFIXES`), `dokploy.yml` schema, docs, and tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Users can exclude exact env var names (e.g. `DEV`) without over-matching vars that share the prefix (e.g. `DEVICE_TOKEN`)
- [x] #2 Existing prefix-based exclusions (e.g. `COMPOSE_`, `DOKPLOY_`) continue to work unchanged (backward compatible)
- [x] #3 Default exclusion list behavior is preserved for current users
- [ ] #4 dokploy.yml schema updated to reflect the chosen pattern syntax
- [x] #5 Documentation updated (configuration.md, dokploy.yml.example)
- [x] #6 Unit tests cover exact match, prefix match, and mixed scenarios
- [x] #7 Edge cases tested: empty patterns, overlapping patterns, case sensitivity
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan: Option A (Convention-based single list)

1. Read current `filter_env` implementation and `DEFAULT_ENV_EXCLUDE_PREFIXES`
2. Write failing tests for exact match vs prefix match behavior
3. Update `filter_env` to distinguish patterns: trailing `_` or `*` = prefix match, otherwise = exact match
4. Rename constant from `DEFAULT_ENV_EXCLUDE_PREFIXES` to `DEFAULT_ENV_EXCLUDES` (since it's no longer all prefixes)
5. Update schema, docs, and example config
6. Run full test suite
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented Option A. Schema update (AC #4) deferred — `ENV_EXCLUDES` is a `.env` variable, not a `dokploy.yml` field, so no JSON schema change needed.
<!-- SECTION:NOTES:END -->
