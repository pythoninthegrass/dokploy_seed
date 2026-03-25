---
id: TASK-017
title: Reconcile mounts/volumes on apply/redeploy
status: Done
assignee: []
created_date: '2026-03-23 18:04'
updated_date: '2026-03-23 20:14'
labels:
  - gap-analysis
  - reconciliation
milestone: m-0
dependencies: []
references:
  - main.py
priority: high
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Mounts created during setup are never removed or updated. If a volume is removed from `dokploy.yml`, it persists in Dokploy. Implement mount reconciliation similar to domain reconciliation.

The Terraform provider handles full CRUD for mounts (bind, volume, file types).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Mounts removed from dokploy.yml are deleted from Dokploy on apply/redeploy
- [x] #2 Mounts added to dokploy.yml are created on apply/redeploy
- [x] #3 Mount changes are shown in `plan` output
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented mount/volume reconciliation on apply/redeploy, mirroring the existing domain and schedule reconciliation patterns.

**Changes in `main.py`:**
- `reconcile_mounts()` — core function that diffs existing vs desired mounts by `mountPath`, calling `mounts.update`, `mounts.create`, and `mounts.remove` API endpoints as needed
- `reconcile_app_mounts()` — wrapper that iterates all non-compose apps and calls `reconcile_mounts` for each, saving state
- Wired `reconcile_app_mounts` into `cmd_apply` during redeploy phase
- Added mount diffing to `_plan_redeploy` so `plan` command shows mount additions, removals, and updates

**Tests in `tests/test_unit.py`:**
- `TestMountReconciliation` — 4 tests covering create/update/delete, no-op, all-removed, and bind mount update
- `TestPlanMountChanges` — 1 test verifying `_plan_redeploy` detects mount additions, removals, and updates
<!-- SECTION:FINAL_SUMMARY:END -->
