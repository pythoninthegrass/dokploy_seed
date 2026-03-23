---
id: TASK-021
title: Add URL redirect support
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
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The TF provider supports regex-based URL redirects (301/302) attached to applications. Useful for www-to-naked redirects, path rewrites, vanity URLs. Add `redirects` config to app definitions with regex, replacement, and permanent flag. Include reconciliation on apply.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Apps can declare redirects in dokploy.yml (regex, replacement, permanent)
- [ ] #2 Redirects are created during setup
- [ ] #3 Redirects are reconciled on apply/redeploy
<!-- AC:END -->
