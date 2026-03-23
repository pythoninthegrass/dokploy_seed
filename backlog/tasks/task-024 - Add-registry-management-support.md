---
id: TASK-024
title: Add registry management support
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
priority: medium
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider manages container registry credentials (Docker Hub, GitHub, GitLab, ECR, GCP, Azure, DigitalOcean). Icarus has no equivalent — users must configure registries manually in the Dokploy UI. Add registry config to `dokploy.yml` (top-level or per-app) so private image pulls work without manual setup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Can declare registries in dokploy.yml (name, url, credentials, type)
- [ ] #2 Registries are created during setup
- [ ] #3 Apps can reference a registry by name for Docker image pulls
<!-- AC:END -->
