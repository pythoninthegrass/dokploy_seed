---
id: TASK-006.02
title: Diff v0.26.0 and v0.28.4 OpenAPI specs for the 13 endpoints we use
status: Done
assignee: []
created_date: '2026-03-07 03:42'
updated_date: '2026-03-07 05:56'
labels:
  - api-compat
dependencies:
  - TASK-006.01
parent_task_id: TASK-006
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Diff `schemas/src/openapi_0.26.0.json` against `schemas/src/openapi_0.28.4.json`, focusing on the 13 endpoints dokploy.py uses:

- project.all, project.create, project.remove
- application.create, application.one, application.update
- application.saveDockerProvider, application.saveGithubProvider
- application.saveBuildType, application.saveEnvironment
- application.deploy
- domain.create
- github.githubProviders

For each endpoint, compare: request schema, response schema, required vs optional fields, validation rules.

Categorize each change as: breaking, behavioral, or additive. Document findings in the parent task (TASK-006) implementation notes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Diff report covers all 13 endpoints
- [ ] #2 Each change categorized as breaking, behavioral, or additive
- [ ] #3 Findings documented in TASK-006 implementation notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
### Diff Results (v0.26.0 vs v0.28.4)

#### BREAKING

- `application.saveEnvironment`: `createEnvFile` (boolean) added as **required** field

#### ADDITIVE (non-breaking)

- `application.update`: new optional fields `args`, `bitbucketRepositorySlug`, `createEnvFile`, `rollbackRegistryId`

#### NO CHANGES (12 endpoints)

- `project.all`, `project.create`, `project.remove`
- `application.create`, `application.one`, `application.saveDockerProvider`
- `application.saveGithubProvider`, `application.saveBuildType`, `application.deploy`
- `domain.create`, `github.githubProviders`, `github.getGithubRepositories`

#### Risk Assessment

- `application.deploy` async behavior (v0.26.2): no schema change, script is fire-and-forget — **no action needed**
- `domain.create` validation (v0.26.6): no schema change — **no action needed**
- `application.saveEnvironment` createEnvFile: **requires fix in dokploy.py**
<!-- SECTION:NOTES:END -->
