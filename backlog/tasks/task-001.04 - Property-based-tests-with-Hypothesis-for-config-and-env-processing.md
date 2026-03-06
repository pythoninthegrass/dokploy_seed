---
id: TASK-001.04
title: Property-based tests with Hypothesis for config and env processing
status: In Progress
assignee: []
created_date: '2026-03-06 08:13'
updated_date: '2026-03-06 08:16'
labels:
  - testing
  - property-based
  - hypothesis
dependencies: []
references:
  - 'dokploy.py:78-164'
  - schemas/dokploy.schema.json
documentation:
  - 'https://hypothesis.readthedocs.io/en/latest/'
  - 'https://github.com/python-jsonschema/hypothesis-jsonschema'
parent_task_id: TASK-001
priority: medium
ordinal: 875
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write property-based tests using Hypothesis to fuzz the config processing, environment variable filtering, and reference resolution logic in `dokploy.py`. These tests should discover edge cases that hand-written unit tests miss.

**Functions to fuzz and their properties:**

1. **`filter_env(content, exclude_prefixes)`** (line 153)
   - **Property: idempotent** — `filter_env(filter_env(x, p), p) == filter_env(x, p)`
   - **Property: no excluded keys survive** — output never contains a line starting with any excluded prefix
   - **Property: no comments or blanks** — output contains no lines starting with `#` and no empty lines
   - **Property: subset** — every line in output appears in input
   - **Strategy:** Generate env-file content as `st.text()` with newlines, or structured as lists of `KEY=value` lines interspersed with comments and blanks

2. **`resolve_refs(template, state)`** (line 132)
   - **Property: no unresolved known refs** — if all `{name}` refs exist in state, output contains no `{...}` patterns for known names
   - **Property: unknown refs preserved** — refs not in state remain unchanged
   - **Property: no refs means no change** — template without `{...}` returns unchanged
   - **Strategy:** Generate state dicts with `st.dictionaries(st.from_regex(r'[a-z][a-z0-9_]{0,10}'), ...)` and templates containing `{ref}` placeholders

3. **`merge_env_overrides(cfg, env_name)`** (line 111)
   - **Property: deep copy** — original config is never mutated
   - **Property: override wins** — for any key present in both base and override, the override value appears in result
   - **Property: base preserved** — keys not in override retain base values
   - **Property: missing env = identity** — merging a nonexistent env returns base config (minus `environments` key)
   - **Strategy:** Generate config dicts matching the JSON schema structure using `st.fixed_dictionaries` with the required keys (`project`, `apps`, `environments`)

4. **`validate_config(cfg)` / `validate_env_references(cfg)`** (lines 78, 99)
   - **Property: valid configs don't crash** — configs where all references are consistent should not raise SystemExit
   - **Property: invalid refs always caught** — configs with dangling references always raise SystemExit
   - **Strategy:** Generate configs with known-valid app names and deploy_order/env_targets drawn from those names (valid case) or from a superset including invalid names (invalid case)

5. **`load_config` → `merge_env_overrides` → `validate_config` pipeline**
   - **Property: round-trip stability** — YAML dump + load of a valid config produces an equivalent config
   - **Property: schema conformance** — generated configs that match the JSON schema always pass validation

**Hypothesis strategies to build:**
- `env_content()` — generates realistic `.env` file content (KEY=value lines, comments, blanks)
- `app_name()` — `st.from_regex(r'[a-z][a-z0-9-]{0,15}', fullmatch=True)`
- `app_config()` — valid app dict with name, source, optional dockerImage/command/env
- `dokploy_config()` — full valid config dict matching the JSON schema
- `state_dict()` — state with projectId, environmentId, apps mapping

Consider using `hypothesis-jsonschema` to generate configs from `schemas/dokploy.schema.json` directly if it supports draft 2020-12.

**Test infrastructure:**
- Place tests in `tests/test_property.py`
- Share Hypothesis strategies in `tests/strategies.py` for reuse
- Set `max_examples` appropriately (100 for CI, higher for local exploration)
- Use `@settings(suppress_health_check=[HealthCheck.too_slow])` if needed for complex strategies
- Add `hypothesis` profiles in conftest.py: `ci` (fewer examples, deterministic) and `dev` (more examples)

**Dependencies:** pytest, hypothesis, hypothesis-jsonschema (optional)

**Key files:**
- `dokploy.py:111-164` — merge_env_overrides, resolve_refs, filter_env
- `dokploy.py:78-109` — validate_config, validate_env_references
- `schemas/dokploy.schema.json` — for generating valid configs
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Hypothesis strategies exist for env content, app configs, state dicts, and full dokploy configs
- [ ] #2 filter_env tested for idempotency, prefix exclusion, and subset properties
- [ ] #3 resolve_refs tested for known-ref resolution and unknown-ref preservation
- [ ] #4 merge_env_overrides tested for immutability of original config and override-wins semantics
- [ ] #5 validate_config tested with both valid and intentionally invalid generated configs
- [ ] #6 All property tests pass with at least 100 examples each
- [ ] #7 Hypothesis profiles configured for CI (deterministic, fewer examples) and dev (more examples)
<!-- AC:END -->
