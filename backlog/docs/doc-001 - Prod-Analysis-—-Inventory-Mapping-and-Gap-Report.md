---
id: doc-001
title: 'Prod Analysis — Inventory, Mapping, and Gap Report'
type: other
created_date: '2026-03-06 15:11'
---
# Production Dokploy Analysis

Inventory of the two projects running on the production Dokploy server,
mapped against `dokploy.py` capabilities, with gap analysis.

## 1. Project Inventory

### Project: popurls

| Field | Value |
|---|---|
| Project ID | `1xUq6wJfnQ6JBF8qaVLwg` |
| Name | popurls |
| Description | *(empty)* |
| Environment | production (`25Gi7YsehmAN0MMyUmrES`) |
| Databases | None |
| Compose | None |

#### App: app

| Field | Value |
|---|---|
| App Name (Dokploy) | `popurls-app-duzqek` |
| Source | github |
| GitHub Owner | pythoninthegrass |
| GitHub Repo | glance |
| GitHub Branch | main |
| Build Type | dockerfile |
| Dockerfile | `Dockerfile` |
| Docker Context Path | *(empty string)* |
| Docker Build Stage | *(empty string)* |
| Build Path | `/` |
| Trigger Type | push |
| Watch Paths | `config/**`, `assets/**`, `Dockerfile`, `^(?!.*\.md$).*$` |
| Auto Deploy | true |
| Command | *(none)* |
| Env Vars | 6 vars (FQDN, GITHUB_TOKEN, REDDIT_APP_NAME, REDDIT_APP_CLIENT_ID, REDDIT_APP_SECRET, MY_SECRET_TOKEN) |
| Replicas | 1 |
| Status | done |
| Memory/CPU Limits | *(none)* |
| Mounts | *(none)* |
| Ports | *(none)* |
| Volumes | *(none)* |
| Redirects | *(none)* |
| Security | *(none)* |
| Registry | *(none)* |

**Domain:**

| Field | Value |
|---|---|
| Host | popurls.xyz |
| Port | 8080 |
| HTTPS | true |
| Certificate | letsencrypt |
| Path | `/` |
| Internal Path | `/` |
| Strip Path | false |

---

### Project: fuck47

| Field | Value |
|---|---|
| Project ID | `POcX7wpQbxcMBGgQF1HCR` |
| Name | fuck47 |
| Description | *(empty)* |
| Environment | production (`tSKtzpLo92IkDTAiAD_6M`) |
| Databases | None |
| Compose | None |

#### App: app

| Field | Value |
|---|---|
| App Name (Dokploy) | `fuck47-app-pvapgc` |
| Source | github |
| GitHub Owner | pythoninthegrass |
| GitHub Repo | fuck47 |
| GitHub Branch | main |
| Build Type | **static** |
| Dockerfile | *(null)* |
| Docker Context Path | *(null)* |
| Docker Build Stage | *(null)* |
| Build Path | `/` |
| Trigger Type | push |
| Watch Paths | *(empty)* |
| Auto Deploy | true |
| Command | *(none)* |
| Env Vars | *(none)* |
| Replicas | 1 |
| Status | idle |
| Memory/CPU Limits | *(none)* |
| Mounts | *(none)* |
| Ports | *(none)* |
| Volumes | *(none)* |
| Redirects | *(none)* |
| Security | *(none)* |
| Registry | *(none)* |

**Domain:**

| Field | Value |
|---|---|
| Host | dev.fuckfortyseven.org |
| Port | 80 |
| HTTPS | true |
| Certificate | letsencrypt |
| Path | `/docs` |
| Internal Path | `/` |
| Strip Path | false |

---

## 2. Settings Mapping (dokploy.yml coverage)

### Supported

| Prod Setting | dokploy.yml Field | Notes |
|---|---|---|
| project.name | `project.name` | Fully supported |
| project.description | `project.description` | Fully supported |
| app.name | `apps[].name` | Fully supported |
| app.sourceType=github | `apps[].source: github` | Fully supported |
| github.owner | `github.owner` | Fully supported |
| github.repository | `github.repository` | Fully supported |
| github.branch | `github.branch` | Fully supported |
| domain.host | `apps[].domain.host` | Fully supported |
| domain.port | `apps[].domain.port` | Fully supported |
| domain.https | `apps[].domain.https` | Fully supported |
| domain.certificateType | `apps[].domain.certificateType` | Fully supported |
| app.env | `apps[].env` | Fully supported |
| app.command | `apps[].command` | Fully supported |

### Unsupported (Gaps)

| Prod Setting | Current Behavior | Impact |
|---|---|---|
| **buildType** | Hardcoded to `"dockerfile"` in `cmd_setup` | **fuck47 uses `static`** — cannot reproduce |
| **autoDeploy** | Not configurable | Both projects have `true`; currently cannot set |
| **watchPaths** | Not configurable | popurls has 4 watch paths; ignored by script |
| **triggerType** | Hardcoded to `"push"` | Matches prod but not configurable |
| **domain.path** | Not in schema | fuck47 has `/docs` path; popurls has `/` |
| **domain.internalPath** | Not in schema | Both have `/` |
| **domain.stripPath** | Not in schema | Both have `false` |
| **buildPath** | Hardcoded to `"/"` | Matches prod but not configurable |
| **publishDirectory** | Not configurable | Both `null` but relevant for static builds |
| **replicas** | Not configurable | Both `1`; cannot scale |
| **enableSubmodules** | Hardcoded to `false` | Matches prod but not configurable |

---

## 3. Gap Report

### Gap 1: `buildType` — CRITICAL

**Problem:** `dokploy.py` hardcodes `buildType` to `"dockerfile"` in
`cmd_setup` (line 413). The fuck47 project uses `buildType: "static"`,
which is a fundamentally different deployment model (Nixpacks-based static
site serving). Without this, fuck47 cannot be reproduced.

**Proposed fix:**

- Add `buildType` field to `apps[]` in schema (enum: `dockerfile`,
  `static`, `nixpacks`, `heroku`, `docker`)
- Make `dockerfile`, `dockerContextPath`, `dockerBuildStage` conditional on
  `buildType: dockerfile`
- Add `publishDirectory` field (needed for static builds)
- Update `cmd_setup` to call `application.saveBuildType` with the
  configured type

### Gap 2: `autoDeploy`

**Problem:** No config field to set auto-deploy behavior. Both prod apps
use `autoDeploy: true`.

**Proposed fix:**

- Add optional `autoDeploy` boolean to `apps[]` schema
- Call `application.update` with `{"applicationId": ..., "autoDeploy": true/false}`

### Gap 3: `watchPaths`

**Problem:** popurls uses specific watch paths for its GitHub trigger
(`config/**`, `assets/**`, `Dockerfile`, regex exclude for `.md` files).
The script hardcodes `watchPaths: None`.

**Proposed fix:**

- Add optional `watchPaths` array to `apps[]` schema (or under a `github`
  sub-object on each app)
- Pass through to `application.saveGithubProvider`

### Gap 4: Domain `path`

**Problem:** fuck47's domain has `path: "/docs"` which routes traffic from
`dev.fuckfortyseven.org/docs` to the app. The domain schema has no `path`
field.

**Proposed fix:**

- Add optional `path` field to `$defs.domain` schema (default: `"/"`)
- Pass through to `domain.create`

### Gap 5: Domain `internalPath` and `stripPath`

**Problem:** Both are domain-level settings not exposed in the schema.
While both prod projects use the defaults (`/` and `false`), other
deployments may need them.

**Proposed fix:**

- Add optional `internalPath` (string, default `"/"`) and `stripPath`
  (boolean, default `false`) to `$defs.domain`
- Pass through to `domain.create`

### Gap 6: `replicas`

**Problem:** No way to configure replica count. Both projects use 1, but
scaling is a common need.

**Proposed fix:**

- Add optional `replicas` integer to `apps[]` schema (default: 1)
- Call `application.update` with `{"applicationId": ..., "replicas": N}`

### Gap 7: `triggerType` and `buildPath`

**Problem:** Both are hardcoded in `cmd_setup` (`push` and `/`
respectively). These match the prod values but aren't configurable.

**Proposed fix:**

- Add optional `triggerType` (enum: `push`, `manual`) and `buildPath`
  (string, default `"/"`) to the github config or per-app
- Pass through to `application.saveGithubProvider`

---

## 4. Reproducibility Summary

| Project | Reproducible? | Blockers |
|---|---|---|
| **popurls** | **Yes** (with caveats) | watchPaths not configurable, autoDeploy not settable. Core setup (source, domain, env, build) works. |
| **fuck47** | **No** | `buildType: static` not supported. Script will create a dockerfile-type app instead. Domain `path: /docs` not configurable. |

---

## 5. Manual Steps Required

### Both projects

1. **API key and GitHub provider** must be pre-configured in Dokploy UI
2. **autoDeploy** must be toggled manually in the Dokploy UI after setup
3. **watchPaths** (popurls) must be configured manually via API or UI

### fuck47 only

1. **buildType** must be changed from `dockerfile` to `static` manually
   via `application.saveBuildType` API call or Dokploy UI
2. **Domain path** must be set to `/docs` manually in Dokploy UI
3. **publishDirectory** may need to be set depending on the static build
   output
