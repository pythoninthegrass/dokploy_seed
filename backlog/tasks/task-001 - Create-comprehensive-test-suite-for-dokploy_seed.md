---
id: TASK-001
title: Create comprehensive test suite for dokploy_seed
status: In Progress
assignee: []
created_date: '2026-03-06 08:11'
updated_date: '2026-03-06 08:16'
labels:
  - testing
  - infrastructure
dependencies:
  - TASK-001.01
  - TASK-001.02
  - TASK-001.03
  - TASK-001.04
references:
  - dokploy.py
  - schemas/dokploy.schema.json
  - examples/
  - dokploy.yml.example
priority: high
ordinal: 250
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish a full test suite for `dokploy.py` covering unit, integration, e2e, and property-based testing. The script is ~600 lines of Python 3.13 with pure utility functions, a thin API client (`DokployClient`), config loading/merging/validation, state management, and 6 CLI commands (check, setup, env, deploy, status, destroy).

Currently there are zero automated tests in the repo.

**Testing layers:**
1. **Unit tests (pytest)** — Pure functions: `find_repo_root`, `load_config`, `validate_config`, `validate_env_references`, `merge_env_overrides`, `resolve_refs`, `get_env_exclude_prefixes`, `filter_env`, `load_state`, `save_state`, argparse in `main()`
2. **Integration tests** — `DokployClient` with `respx` (httpx-native mock), `cmd_*` functions with mocked API calls, state file round-trip, full command pipelines (setup→env→deploy→status→destroy)
3. **E2E tests** — Against a real Dokploy instance running in Docker-in-Docker on a Linux host. Requires `dokploy/dokploy` image + PostgreSQL 16 + Redis 7 + Traefik v3.6.7, Docker Swarm mode, `--privileged` for DinD.
4. **Property-based tests (Hypothesis)** — Fuzz `merge_env_overrides`, `resolve_refs`, `filter_env`, config validation edge cases, YAML round-trip stability

**Test runner:** pytest with pytest-cov. Use PEP 723 inline script metadata or a minimal `pyproject.toml` `[project.optional-dependencies]` for test deps.

**References:**
- `dokploy.py` — the sole script under test
- `schemas/dokploy.schema.json` — config schema (useful for Hypothesis strategies)
- `examples/` — valid config fixtures
- Dokploy install script: `curl -sSL https://dokploy.com/install.sh | sh` (defines required services)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All four testing layers (unit, integration, e2e, property-based) have at least one passing test
- [ ] #2 pytest runs successfully with `uv run pytest` or equivalent
- [ ] #3 Test configuration is defined (pyproject.toml or conftest.py)
- [ ] #4 CI-compatible: tests can be run headlessly on a Linux host
- [ ] #5 Code coverage reporting is configured (pytest-cov)
<!-- AC:END -->
