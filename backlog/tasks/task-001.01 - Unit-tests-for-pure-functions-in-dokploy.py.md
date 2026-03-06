---
id: TASK-001.01
title: Unit tests for pure functions in dokploy.py
status: In Progress
assignee: []
created_date: '2026-03-06 08:13'
updated_date: '2026-03-06 08:14'
labels:
  - testing
  - unit-tests
dependencies: []
references:
  - 'dokploy.py:38-201'
  - 'dokploy.py:560-607'
  - examples/web-app/dokploy.yml
  - examples/minimal/dokploy.yml
  - examples/docker-only/dokploy.yml
parent_task_id: TASK-001
priority: high
ordinal: 500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Write pytest unit tests for all pure/near-pure functions in `dokploy.py`. These functions have no external dependencies (no network, no Dokploy server) and can be tested with simple inputs/outputs.

**Functions to test:**

1. **`find_repo_root()`** (line 38) — Walks up from script dir looking for `dokploy.yml`. Test: create temp dirs with/without `dokploy.yml`, verify it finds the right root or exits.

2. **`load_config(repo_root)`** (line 68) — Reads `dokploy.yml` via `yaml.safe_load`. Test: valid YAML, missing file (sys.exit), malformed YAML.

3. **`validate_config(cfg)`** (line 78) — Checks `env_targets` and `deploy_order` reference valid app names, and GitHub config exists if needed. Test: valid config passes, unknown app in env_targets/deploy_order exits, missing github section exits.

4. **`validate_env_references(cfg)`** (line 99) — Checks environment app overrides reference existing apps. Test: valid refs pass, unknown app name in environment overrides exits.

5. **`merge_env_overrides(cfg, env_name)`** (line 111) — Deep-copies config and merges per-env overrides. Test: github overrides merge, per-app overrides merge, missing env returns base config, original config unchanged (deep copy).

6. **`resolve_refs(template, state)`** (line 132) — Replaces `{app_name}` placeholders with Dokploy `appName` from state dict. Test: single ref, multiple refs, unknown ref left as-is, no refs returns unchanged.

7. **`get_env_exclude_prefixes()`** (line 144) — Merges default prefixes with `ENV_EXCLUDE_PREFIXES` from env. Test: defaults only, with extras, empty extras.

8. **`filter_env(content, exclude_prefixes)`** (line 153) — Strips comments, blanks, excluded vars. Test: comments removed, blank lines removed, excluded prefixes filtered, valid lines kept, trailing newline.

9. **`load_state(state_file)` / `save_state(state, state_file)`** (lines 190-201) — JSON round-trip to `.dokploy-state/`. Test: save then load returns same data, load from missing file exits, directory auto-created.

10. **`main()` argparse** (line 560) — Test CLI arg parsing (--env, command choices). Test: valid commands accepted, invalid command rejected, --env flag parsed.

**Test infrastructure:**
- Place tests in `tests/test_unit.py` (or `tests/unit/` directory)
- Use `tmp_path` fixture for filesystem tests
- Use `monkeypatch` for env var tests (`get_env_exclude_prefixes`)
- Use `pytest.raises(SystemExit)` for error-path tests (functions call `sys.exit(1)`)
- Import functions directly from `dokploy` module (may need to handle PEP 723 import — the script can be imported as a module)
- Use example configs from `examples/` directory as realistic fixtures

**Dependencies:** pytest, pytest-cov

**Key files:**
- `dokploy.py` — source under test
- `examples/web-app/dokploy.yml` — realistic valid config
- `examples/minimal/dokploy.yml` — minimal valid config
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every pure function listed above has at least one positive and one negative test case
- [ ] #2 Tests use tmp_path for filesystem isolation (no side effects)
- [ ] #3 Tests for sys.exit paths use pytest.raises(SystemExit)
- [ ] #4 All tests pass with `uv run pytest tests/test_unit.py`
- [ ] #5 conftest.py provides reusable fixtures for sample configs and state dicts
<!-- AC:END -->
