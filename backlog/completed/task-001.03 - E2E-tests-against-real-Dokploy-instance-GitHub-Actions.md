---
id: TASK-001.03
title: E2E tests against real Dokploy instance (GitHub Actions)
status: Done
assignee: []
created_date: '2026-03-06 08:13'
updated_date: '2026-03-06 23:03'
labels:
  - testing
  - e2e
  - github-actions
  - infrastructure
dependencies: []
references:
  - dokploy.py
  - examples/docker-only/dokploy.yml
  - examples/minimal/dokploy.yml
  - 'https://docs.dokploy.com/docs/core/manual-installation'
  - 'https://github.com/Dokploy/dokploy'
documentation:
  - 'https://dokploy.com/install.sh'
  - 'https://github.com/Dokploy/dokploy/releases'
  - 'https://docs.dokploy.com'
  - 'https://github.com/Dokploy/dokploy/blob/main/packages/server/src/lib/auth.ts'
  - >-
    https://github.com/Dokploy/dokploy/blob/main/packages/server/src/services/user.ts
  - 'https://github.com/Dokploy/dokploy/blob/main/apps/dokploy/server/server.ts'
parent_task_id: TASK-001
priority: medium
ordinal: 1875
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Design and implement end-to-end tests that run `dokploy.py` commands against a real Dokploy instance. Uses GitHub Actions Ubuntu runners with native Docker — no DinD needed.

**Dokploy runtime requirements** (from the official install script at `https://docs.dokploy.com/docs/core/manual-installation`):

| Service | Image | Mode | Purpose |
|---------|-------|------|---------|
| dokploy | `dokploy/dokploy:latest` | Swarm service | Main app (port 3000) |
| postgres | `postgres:16` | Swarm service | Database |
| redis | `redis:7` | Swarm service | Cache/queue |

- Runs as **Docker Swarm** services
- Needs Docker socket mounted (`/var/run/docker.sock`)
- Health check: `GET http://localhost:3000/api/trpc/settings.health` (just runs `SELECT 1`)
- **Linux-only** — Docker Swarm doesn't work on macOS Docker Desktop
- Uses Docker secrets for postgres password
- Traefik and nixpacks are **not needed** — E2E tests hit port 3000 directly and use `sourceType: "docker"` apps

**Why not DinD?**

The official install script explicitly rejects running inside a container:
```bash
if [ -f /.dockerenv ]; then
    echo "This script must be run on Linux" >&2
    exit 1
fi
```
While you could bypass this by replicating the `docker service create` commands manually, GitHub Actions Ubuntu runners provide native Docker without any of these complications.

**Why not testcontainers-python?**

Testcontainers manages plain Docker containers. The Dokploy services are Swarm services on an overlay network — testcontainers can't model this. It would reduce to a thin wrapper around a single DinD container, adding a dependency without simplifying anything.

**Approach: GitHub Actions with native Docker**

1. **`.github/workflows/e2e.yml`** — GHA workflow that:
   - Runs on `ubuntu-latest` (Docker pre-installed, no `/.dockerenv`)
   - Initializes Docker Swarm (`docker swarm init --advertise-addr 127.0.0.1`)
   - Creates `dokploy-network` overlay network
   - Creates Docker secret for postgres password
   - Starts postgres, redis, dokploy as Swarm services
   - Waits for health check (`/api/trpc/settings.health`)
   - Registers first admin (`POST /api/auth/sign-up/email`) and creates API key (`POST /api/auth/api-key/create` with `organizationId` metadata)
   - Runs `pytest -m e2e`

2. **`tests/e2e/setup-dokploy.sh`** — Reusable setup script (also usable on a local Linux box):
   - Initializes Swarm, creates network, creates secret
   - Starts postgres, redis, dokploy services (commands taken from official install script)
   - Polls health check endpoint until ready
   - Registers admin and creates API key
   - Outputs connection details (URL, API key)

3. **`tests/e2e/conftest.py`** — pytest fixtures:
   - `dokploy_url` — `http://localhost:3000` (or from env var)
   - `api_key` — From env var (set by setup script or GHA workflow)
   - `e2e_config` — Minimal `dokploy.yml` with Docker-only apps (no GitHub provider)
   - `skip_if_no_dokploy` — `pytest.mark.skipif` that skips when Dokploy isn't reachable

4. **`tests/e2e/test_e2e.py`** — End-to-end test scenarios:
   - **Full lifecycle**: `check → setup → env → deploy → status → destroy`
   - Verify project appears in `project.all` after setup
   - Verify apps have correct status after deploy
   - Verify environment variables are set on apps
   - Verify destroy removes the project
   - Verify state file created and cleaned up

**Test isolation:** Each test run uses a unique project name (e.g., `e2e-test-{uuid}`).

**CI configuration:**
- Mark all e2e tests with `@pytest.mark.e2e`
- Default pytest config skips e2e: `addopts = -m "not e2e"`
- GHA workflow runs: `pytest -m e2e`
- Timeout: e2e tests need longer timeout (Dokploy startup can take 30-60s)

**Local development:**
- Linux users can run `tests/e2e/setup-dokploy.sh` then `pytest -m e2e`
- macOS users skip e2e tests (handled by skip marker + health check fixture)

**Dependencies:** pytest, pytest-timeout

**Key files:**
- `dokploy.py` — script under test
- `examples/docker-only/dokploy.yml` — good base config for e2e (no GitHub dependency)
- `examples/minimal/dokploy.yml` — simplest possible config
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GHA workflow starts Dokploy (swarm init, overlay network, postgres/redis/dokploy services — no Traefik)
- [x] #2 Setup script (`tests/e2e/setup-dokploy.sh`) is reusable for local Linux and CI
- [x] #3 Setup script registers admin and creates API key programmatically (better-auth endpoints)
- [x] #4 At least one e2e test runs the full lifecycle: setup → env → deploy → status → destroy
- [x] #5 E2E tests are marked with @pytest.mark.e2e and skipped by default
- [x] #6 E2E tests use unique project names to avoid collisions
- [x] #7 Docs explain how to run e2e tests locally (Linux) and in CI
- [x] #8 Tests clean up (destroy) even on failure (pytest fixtures with finalizers)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Research Notes (2026-03-06)

### Install script analysis
- Official install script at `https://docs.dokploy.com/docs/core/manual-installation` blocks running inside Docker (`/.dockerenv` check) — DinD can't use it directly
- Services: postgres + redis + dokploy are Swarm services; traefik is a plain `docker run` container
- Uses `docker secret create` for postgres password
- Swarm init requires `--advertise-addr` (uses public IP by default, use `127.0.0.1` for CI)

### DinD ruled out
- `/.dockerenv` check blocks the install script inside containers
- Could bypass by replicating commands manually, but adds unnecessary complexity
- GHA Ubuntu runners have native Docker — simpler and more reliable

### Testcontainers-python ruled out
- Manages plain Docker containers, can't model Swarm services on overlay networks
- Built-in PostgresContainer/RedisContainer are unusable (services must be on `dokploy-network` overlay)
- Would collapse to a thin wrapper around DinD, adding a dependency without simplifying anything

### Traefik not needed
- Only serves HTTP on ports 80/443 for domain routing
- E2E tests hit Dokploy API directly on port 3000
- Skipping Traefik reduces startup time and port conflicts

## Open Questions Resolved (2026-03-06)

Source: Dokploy source code at https://github.com/Dokploy/dokploy

### Q1: How to obtain an API key programmatically

Dokploy uses **better-auth** with the `apiKey` plugin. The programmatic setup sequence is:

1. **Wait for health**: `GET http://localhost:3000/api/trpc/settings.health` — returns `{"status":"ok"}` once PostgreSQL is reachable (just runs `SELECT 1`)

2. **Register first admin**: `POST /api/auth/sign-up/email` with `{"email", "password", "name", "lastName"}`. Guard logic in `packages/server/src/lib/auth.ts` allows registration when no member with `role: "owner"` exists yet. With `autoSignIn: true` (self-hosted default), the response includes session cookies.

3. **Create API key**: Using session cookies from step 2, call `POST /api/auth/api-key/create` (better-auth plugin endpoint). The `createApiKey` wrapper in `packages/server/src/services/user.ts` stores `organizationId` in the API key metadata — this is important because `validateRequest` reads it back to set `activeOrganizationId`. Without it, organization-scoped operations fail.

4. **Use API key**: All subsequent calls use `x-api-key: <key>` header against tRPC endpoints at `/api/trpc/<router>.<procedure>`.

Key source files:
- `packages/server/src/lib/auth.ts` — auth config, `validateRequest`, `databaseHooks`
- `packages/server/src/services/user.ts` — `createApiKey` wrapper
- `apps/dokploy/lib/auth-client.ts` — client config with `apiKeyClient()` plugin
- `packages/server/src/db/schema/account.ts` — `apikey` table schema

### Q2: Stripped-down Dokploy (without Traefik/nixpacks) is fully viable

**Hard dependencies** (API won't start without these):
- PostgreSQL — health check is `SELECT 1`
- Redis — BullMQ deployment queue
- Docker daemon with Swarm initialized
- `dokploy-network` overlay network

**NOT required for API startup:**
- Nixpacks — build-time only, invoked when `buildType: "nixpacks"`. Never checked at startup or in health check
- Traefik — runs as a separate container for HTTP routing on 80/443. API writes config files to disk but doesn't communicate with Traefik process
- Buildpacks, Railpack, RClone — all build/backup tools, never checked at startup

The `server-validate.ts` checks for nixpacks/buildpacks are **informational only** — they report status in a UI dashboard panel but do NOT block any functionality.

For E2E tests using `sourceType: "docker"` or `buildType: "dockerfile"` apps, nixpacks is never invoked. Traefik is never needed since tests hit port 3000 directly.

**Minimum E2E stack**: PostgreSQL + Redis + Dokploy (3 Swarm services). No Traefik, no nixpacks.

## Implementation Complete (2026-03-06)

### Files Created
- `tests/setup-dokploy.sh` — Reusable Dokploy bootstrap script
- `tests/test_e2e.py` — 5 E2E lifecycle tests
- `tests/cloud-init.yml` — Cloud-init config for OrbStack VM provisioning
- `.github/workflows/e2e.yml` — GHA workflow

### Files Modified
- `tests/conftest.py` — Added e2e fixtures (dokploy_url, api_key, skip_if_no_dokploy, e2e_client, e2e_config, e2e_project)
- `pyproject.toml` — Added addopts="-m 'not e2e'", pytest-timeout dep
- `docs/testing.md` — Added E2E Tests section with cloud-init instructions

### Key Discoveries During Implementation
1. **Docker secret mount needed**: The dokploy service must mount `dokploy_postgres_password` secret and set `POSTGRES_PASSWORD_FILE` env var
2. **Origin header required**: better-auth CSRF protection requires `Origin` header on auth endpoints
3. **API key metadata patch**: better-auth's api-key/create endpoint doesn't support metadata. Dokploy's validateRequest requires organizationId in API key metadata. Setup script patches the apikey row in postgres directly.
4. **Rate limiting disabled**: Default API keys have rateLimitMax=10/day. Setup script disables rate limiting.

### Verification Results
- `uv run pytest tests/ -v` — 111 passed, 5 deselected (e2e skipped by addopts)
- `uv run pytest tests/ -m e2e -o "addopts=" -v --timeout=120` — 5 passed against live Dokploy in OrbStack VM
- Flat convention followed: test_e2e.py in tests/, fixtures in tests/conftest.py, script in tests/setup-dokploy.sh
<!-- SECTION:NOTES:END -->
