---
id: TASK-013
title: Support e2e compose deployments with env var substitution
status: To Do
assignee: []
created_date: '2026-03-18 22:28'
updated_date: '2026-03-18 22:46'
labels:
  - enhancement
  - compose
  - security
dependencies: []
references:
  - schemas/src/openapi_0.26.0.json (compose API schema)
  - docs/api-notes.md
  - examples/docker-compose/docker-compose.yml
  - examples/docker-compose/.env.example
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Icarus currently manages only individual application resources (source: docker/github). It should also support deploying Docker Compose workloads end-to-end — creating compose projects, pushing env vars, updating compose files, and triggering deployments via the Dokploy compose API.

A key part of this is env var substitution: compose files often hardcode credentials across multiple services. Icarus should let users define secrets once (in `dokploy.yml` env config) and reference them as `${VAR}` in the compose file, matching native Docker Compose variable substitution behavior that Dokploy already supports.

**Proof of concept (kestra-kestra-mb4nhz):**
- Uploaded randomized creds as env vars via `compose.update` API (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `KESTRA_ADMIN_EMAIL`, `KESTRA_ADMIN_PASSWORD`)
- Replaced all hardcoded values in the compose file with `${VAR}` references
- Deployed successfully via `compose.deploy` — both `postgres` and `kestra` services running

**Relevant Dokploy API endpoints:**
- `compose.create` — create a compose resource in a project/environment
- `compose.update` — set `env` (newline-delimited KEY=VALUE), `composeFile`, and other fields
- `compose.deploy` — trigger deployment
- `compose.one` — read current state
- `compose.loadServices` — list running services
- `deployment.allByCompose` — check deployment status
- `domain.byComposeId` — manage domains
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 dokploy.yml supports a `source: compose` app type with `composeFile` (inline block scalar or relative file path) and `composeType` (docker-compose or stack)
- [ ] #2 Inline compose: `composeFile` accepts a YAML block scalar (literal `|` or folded `>`) with the full compose content
- [ ] #3 File reference compose: `composeFile` accepts a relative path (e.g. `compose.yml`, `docker-compose.yml`, `kestra/docker-compose.yml`) resolved relative to dokploy.yml location
- [ ] #4 ic setup creates compose resources via compose.create API for compose-type apps
- [ ] #5 ic env pushes env vars to compose resources via compose.update API (same filtering/prefix logic as application env)
- [ ] #6 ic deploy/trigger deploys compose resources via compose.deploy API, respecting deploy_order waves
- [ ] #7 ic status reports compose deployment status (idle/running/done/error) and lists running services
- [ ] #8 ic destroy tears down compose resources via compose.delete API
- [ ] #9 Compose files support ${VAR} references resolved by Dokploy at deploy time from the compose resource env vars
- [ ] #10 Existing non-compose workflows are unaffected
- [ ] #11 Documentation updated: dokploy.yml.example, configuration.md, schema, and a compose example in examples/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
**POC results (2026-03-18):**
- Target: `kestra-kestra-mb4nhz` (composeId: `bCTfFNmglQ-IlqDEK9Tup`)
- Env vars and compose file updated in single `compose.update` call
- `${VAR}` substitution in compose `environment:` blocks works natively — Dokploy resolves them at deploy time
- `$${VAR}` escaping (for healthcheck shell commands) also works correctly
- Deployment took ~3min (kestra image pull), status transitioned: idle -> running -> done
- Both services (`postgres`, `kestra`) loaded successfully via `compose.loadServices`
- Domain assigned: `kestra-kestra-43b6d8-67-200-233-200.traefik.me` (port 8080, serviceName: kestra)
<!-- SECTION:NOTES:END -->
