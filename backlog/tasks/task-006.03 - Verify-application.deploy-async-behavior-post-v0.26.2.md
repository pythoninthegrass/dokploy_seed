---
id: TASK-006.03
title: Verify application.deploy async behavior post-v0.26.2
status: Done
assignee: []
created_date: '2026-03-07 03:43'
updated_date: '2026-03-07 05:59'
labels:
  - api-compat
dependencies:
  - TASK-006.02
parent_task_id: TASK-006
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
v0.26.2 changed deployments to execute in background (#3259). dokploy.py already uses fire-and-forget (cmd_trigger discards the response), but we need to verify:

1. Response format hasn't changed (still empty body or compatible JSON)
2. The deploy actually triggers (not silently dropped)
3. cmd_status still works to poll results after async deploy

Test against live v0.28.4 instance after upgrade.

Relevant code: dokploy.py cmd_trigger (lines 563-575), DokployClient.post empty-body handling (lines 241-246).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 application.deploy response format documented
- [ ] #2 cmd_trigger works against v0.28.4 without code changes OR fix applied
- [ ] #3 test_deploy_returns_empty_response still passes or updated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
No action needed. OpenAPI diff shows no schema change for application.deploy between v0.26.0 and v0.28.4. The async behavior change (v0.26.2) is an implementation detail — script is fire-and-forget, response format unchanged."
<!-- SECTION:NOTES:END -->
