---
id: TASK-016
title: Reconcile domains on apply/redeploy
status: Done
assignee: []
created_date: '2026-03-23 18:04'
updated_date: '2026-03-23 18:12'
labels:
  - gap-analysis
  - reconciliation
milestone: m-0
dependencies: []
references:
  - main.py
  - 'https://github.com/TheFrozenFire/terraform-provider-dokploy'
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Icarus creates domains during `setup` but never removes stale ones on `apply`/redeploy. If a domain is removed from `dokploy.yml`, it persists in Dokploy. Implement full domain reconciliation: compare declared domains against server state, create new ones, and delete removed ones.

The Terraform provider handles full CRUD for domains. Icarus should match this for its config-driven model.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Domains removed from dokploy.yml are deleted from Dokploy on apply/redeploy
- [x] #2 Domains added to dokploy.yml are created on apply/redeploy
- [x] #3 Domain changes are shown in `plan` output
- [x] #4 Existing setup-only domain creation still works
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented full domain reconciliation on apply/redeploy, matching the existing schedule reconciliation pattern.

**Changes in `main.py`:**
- Added `reconcile_domains()` — compares existing vs desired domains by host, creates new, updates changed (port/https/certificateType/path/internalPath/stripPath), deletes removed. Returns state dict mapping host -> {domainId}.
- Added `reconcile_app_domains()` — orchestrator that iterates all apps, fetches existing domains via `domain.byApplicationId`/`domain.byComposeId`, calls `reconcile_domains()`, saves state.
- Wired `reconcile_app_domains()` into `cmd_apply()` redeploy path (alongside existing `reconcile_app_schedules`).
- Added domain diffing to `_plan_redeploy()` — shows create/update/destroy changes for domains in `plan` output.

**Tests added to `test_unit.py`:**
- `TestDomainReconciliation` (4 tests): create+delete+update, no-op, all-removed, compose domains
- `TestPlanDomainChanges` (1 test): verifies plan output shows domain additions, removals, and updates

All 244 tests pass. Lint clean.
<!-- SECTION:FINAL_SUMMARY:END -->
