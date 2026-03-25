---
id: TASK-022
title: Add basic auth / security support
status: Done
assignee: []
created_date: '2026-03-23 18:05'
updated_date: '2026-03-25 18:08'
labels:
  - gap-analysis
  - new-resource
milestone: m-0
dependencies: []
references:
  - main.py
  - schemas/dokploy.schema.json
priority: medium
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider can configure basic authentication (username/password) on applications. Icarus cannot. Add `security` config to app definitions for basic auth protection. Useful for staging environments and admin panels.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Apps can declare basic auth in dokploy.yml (username, password)
- [x] #2 Security config is applied during setup
- [x] #3 Security config is reconciled on apply/redeploy
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All three acceptance criteria were already implemented prior to this task being picked up. Security support includes: schema definition (security_entry with username/password), payload builder, setup-time creation, full reconciliation (create/update/delete by username), plan output, test fixture, and 16 passing unit tests.
<!-- SECTION:FINAL_SUMMARY:END -->
