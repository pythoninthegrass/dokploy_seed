---
id: TASK-024
title: Add registry management support
status: Done
assignee: []
created_date: '2026-03-23 18:05'
updated_date: '2026-03-24 20:31'
labels:
  - gap-analysis
  - new-resource
milestone: m-0
dependencies: []
references:
  - main.py
  - schemas/dokploy.schema.json
priority: medium
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider manages container registry credentials (Docker Hub, GitHub, GitLab, ECR, GCP, Azure, DigitalOcean). Icarus has no equivalent — users must configure registries manually in the Dokploy UI. Add registry config to `dokploy.yml` (top-level or per-app) so private image pulls work without manual setup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Can declare registries in dokploy.yml (name, url, credentials, type)
- [x] #2 Registries are created during setup
- [x] #3 Apps can reference a registry by name for Docker image pulls
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added container registry management support to Icarus.

**Changes:**
- `schemas/dokploy.schema.json`: Added `registry_entry` def, top-level `registries` array, `registry` field on app items and env overrides
- `src/icarus/payloads.py`: Added `build_registry_create_payload`, `build_registry_update_payload`, `resolve_registry_id`
- `src/icarus/schema.py`: Added validation that app `registry` references exist in the `registries` section
- `src/icarus/commands.py`: Registry creation in `cmd_setup` (idempotent, server-scoped), app-registry association via `application.update`, registry import in `cmd_import`, reconciliation wired into `cmd_apply`
- `src/icarus/reconcile.py`: Added `reconcile_registries` and `reconcile_app_registry`
- `src/icarus/plan.py`: Registry create entries in initial plan, registry attr on app creates
- `src/icarus/__init__.py`: Exported new functions
- `tests/fixtures/registry_config.yml`: New test fixture
- `tests/conftest.py`: Added `registry_config` fixture
- `tests/test_unit.py`: 20 new tests covering payloads, validation, setup, reconciliation, and planning

All 271 tests pass (249 unit + 22 property). Linting clean.
<!-- SECTION:FINAL_SUMMARY:END -->
