---
id: TASK-003
title: Implement dokploy.py changes to fully support prod project recreation
status: To Do
assignee: []
created_date: '2026-03-06 08:14'
updated_date: '2026-03-06 08:16'
labels:
  - implementation
  - prod
dependencies:
  - TASK-002
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Based on the gap report and findings from TASK-002, implement all necessary changes to `dokploy.py`, `dokploy.schema.json`, and supporting files so that both prod projects can be fully recreated via `dokploy.py` without manual steps.

If TASK-002 concludes that the current script already supports everything needed, this task can be closed immediately with a note confirming no changes are required.

**Likely work (pending TASK-002 findings):**

- Add support for any unsupported resource types (e.g., compose apps, databases, Redis, volumes, mounts, redirects, advanced domain settings, build args)
- Update `dokploy.schema.json` to reflect new config fields
- Update `dokploy.yml.example` and `docs/configuration.md` with new options
- Add or update example configs in `examples/`
- Finalize the draft `dokploy.yml` configs from TASK-002 into working, validated configs for both prod projects
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All gaps identified in TASK-002 are addressed in dokploy.py (or explicitly deferred with justification)
- [ ] #2 dokploy.schema.json validates the new config fields
- [ ] #3 Both prod projects have working dokploy.yml configs that pass `dokploy.py check`
- [ ] #4 Running `setup`, `env`, and `deploy` against a test environment successfully recreates the project structure
- [ ] #5 No manual steps remain — or any remaining ones are documented and tracked as separate tasks
<!-- AC:END -->
