---
id: TASK-013
title: Support e2e compose deployments with env var substitution
status: Done
assignee: []
created_date: '2026-03-18 22:28'
updated_date: '2026-03-19 18:43'
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
- [x] #1 dokploy.yml supports a `source: compose` app type with `composeFile` (inline block scalar or relative file path) and `composeType` (docker-compose or stack)
- [x] #2 Inline compose: `composeFile` accepts a YAML block scalar (literal `|` or folded `>`) with the full compose content
- [x] #3 File reference compose: `composeFile` accepts a relative path (e.g. `compose.yml`, `docker-compose.yml`, `kestra/docker-compose.yml`) resolved relative to dokploy.yml location
- [x] #4 ic setup creates compose resources via compose.create API for compose-type apps
- [x] #5 ic env pushes env vars to compose resources via compose.update API (same filtering/prefix logic as application env)
- [x] #6 ic apply/trigger deploys compose resources via compose.deploy API, respecting deploy_order waves
- [x] #7 ic status reports compose deployment status (idle/running/done/error) and lists running services
- [x] #8 ic destroy tears down compose resources via compose.delete API
- [x] #9 Compose files support ${VAR} references resolved by Dokploy at deploy time from the compose resource env vars
- [x] #10 Existing non-compose workflows are unaffected
- [x] #11 Documentation updated: dokploy.yml.example, configuration.md, schema, and a compose example in examples/
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

**API comparison — ic vs manual template (2026-03-19):**

| | `kestra-temp` (manual template) | `kestra` (ic) |
|---|---|---|
| Resource type | compose | application |
| `sourceType` | `raw` | `github` |
| `buildType` | n/a | `nixpacks` |
| `composeFile` | full docker-compose YAML | `null` |
| API used | `compose.create` | `application.create` |
| Status | idle (deployable) | error (no repo to build) |

ic currently only uses `application.create` — it has no code path for `compose.create`. For `source: compose` apps, ic must use the `compose.*` API family instead of `application.*`.

Dokploy server is running v0.25.6 (schema pulled from live server, not available on GitHub). The compose API surface (`compose.create`, `compose.update`, `compose.deploy`, etc.) is identical between v0.25.6 and v0.28.8.

**E2E deployment verified (2026-03-19):**
- Kestra compose stack deployed via `ic --env prod apply` from `examples/docker-compose/`
- `compose.create` with `sourceType: raw` via `compose.update`
- Env vars pushed from `.env` via `env_targets` + `compose.update`
- Compose file pushed on both initial setup and redeploy
- Domain routing via Traefik Docker labels (auto-injected by Dokploy on deploy)
- Compose services need explicit `networks: [dokploy-network, default]` for inter-service DNS + Traefik routing
- `depends_on: condition: service_healthy` required for ordered startup
- All 203 existing tests pass, no regressions
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented end-to-end Docker Compose deployment support in icarus.\n\n**main.py changes:**\n- Added `is_compose()` and `resolve_compose_file()` helpers\n- `cmd_setup`: creates compose resources via `compose.create`, pushes compose file via `compose.update` with `sourceType: raw`\n- `cmd_env`: pushes env vars and compose file to compose resources via `compose.update` (on every deploy, not just setup)\n- `cmd_trigger`: deploys/redeploys compose resources via `compose.deploy`/`compose.redeploy`\n- `cmd_status`: reads compose status via `compose.one`\n- `build_domain_payload`: supports `composeId`, `domainType: compose`, and `serviceName`\n- All application-only steps (providers, commands, settings, volumes, schedules) skip compose apps\n\n**docs/configuration.md:** Added Compose Apps section, `composeFile`/`composeType` fields, `serviceName` for domains, Host Tuning section for inotify limits.\n\n**examples/docker-compose/:** Working kestra example with `docker-compose.yml`, `dokploy.yml.example`, `.env.example`.\n\n**Key learnings:**\n- Dokploy defaults `sourceType` to `github` — must explicitly set `raw` for inline/file compose\n- Compose domains use Traefik Docker labels (not file-based configs like applications)\n- Services needing both Traefik routing and inter-service DNS must be on both `dokploy-network` and `default`\n- `compose.redeploy` may not recreate containers if compose hash unchanged — use `compose.stop` + `compose.deploy` for forced restart
<!-- SECTION:FINAL_SUMMARY:END -->
