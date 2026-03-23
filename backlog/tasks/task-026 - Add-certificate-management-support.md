---
id: TASK-026
title: Add certificate management support
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
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider can upload custom SSL certificates with auto-renewal. Icarus only sets `certificateType` on domains (letsencrypt/none) but can't manage custom certificates. Add certificate config for uploading custom certs and associating them with domains.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Can declare certificates in dokploy.yml (name, cert data path, key path, auto_renew)
- [ ] #2 Certificates are uploaded during setup
- [ ] #3 Domains can reference custom certificates by name
<!-- AC:END -->
