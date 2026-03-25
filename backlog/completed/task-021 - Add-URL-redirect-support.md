---
id: TASK-021
title: Add URL redirect support
status: Done
assignee: []
created_date: '2026-03-23 18:05'
updated_date: '2026-03-24 20:32'
labels:
  - gap-analysis
  - new-resource
milestone: m-0
dependencies: []
references:
  - main.py
  - schemas/dokploy.schema.json
priority: medium
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider supports regex-based URL redirects (301/302) attached to applications. Useful for www-to-naked redirects, path rewrites, vanity URLs. Add `redirects` config to app definitions with regex, replacement, and permanent flag. Include reconciliation on apply.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Apps can declare redirects in dokploy.yml (regex, replacement, permanent)
- [x] #2 Redirects are created during setup
- [x] #3 Redirects are reconciled on apply/redeploy
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Add URL redirect support (regex-based 301/302) for applications.

Files modified:
- `schemas/dokploy.schema.json` -- added `redirect` $def and `redirects` array property to app definitions and environment overrides
- `src/icarus/payloads.py` -- added `build_redirect_payload()`
- `src/icarus/reconcile.py` -- added `reconcile_redirects()` and `reconcile_app_redirects()`
- `src/icarus/commands.py` -- added redirect creation in `cmd_setup`, reconciliation call in `cmd_apply`
- `src/icarus/plan.py` -- added redirect diffing in `_plan_initial_setup` and `_plan_redeploy`
- `src/icarus/__init__.py` -- exported new functions
- `tests/test_unit.py` -- 15 new tests covering payload, reconcile, setup, apply, and plan
- `examples/web-app/dokploy.yml` -- added redirect examples
- `tests/fixtures/web_app_config.yml` -- added redirect fixture

API endpoints used: `redirects.create`, `redirects.update`, `redirects.delete`. Existing redirects fetched via `application.one` response. Unique key: `regex` field.
<!-- SECTION:FINAL_SUMMARY:END -->
