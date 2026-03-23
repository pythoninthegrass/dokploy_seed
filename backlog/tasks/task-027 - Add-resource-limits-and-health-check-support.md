---
id: TASK-027
title: Add resource limits and health check support
status: To Do
assignee: []
created_date: '2026-03-23 18:05'
labels:
  - gap-analysis
  - new-resource
milestone: m-0
dependencies: []
references:
  - main.py
  - schemas/dokploy.schema.json
priority: low
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider exposes resource limits (CPU/memory) and health check configuration. Icarus has neither. Add optional `resources` (cpu, memory limits/reservations) and `healthCheck` (command, interval, timeout, retries) config to app definitions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Apps can declare resource limits in dokploy.yml (cpu, memory)
- [ ] #2 Apps can declare health checks in dokploy.yml (command, interval, timeout, retries)
- [ ] #3 Configs are applied via application.update API
<!-- AC:END -->
