---
id: TASK-001.03
title: E2E tests against real Dokploy instance (Docker-in-Docker)
status: In Progress
assignee: []
created_date: '2026-03-06 08:13'
updated_date: '2026-03-06 15:34'
labels:
  - testing
  - e2e
  - docker
  - infrastructure
dependencies: []
references:
  - dokploy.py
  - examples/docker-only/dokploy.yml
  - examples/minimal/dokploy.yml
documentation:
  - 'https://dokploy.com/install.sh'
  - 'https://github.com/Dokploy/dokploy/releases'
  - 'https://docs.dokploy.com'
parent_task_id: TASK-001
priority: medium
ordinal: 1875
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Design and implement end-to-end tests that run `dokploy.py` commands against a real Dokploy instance. This requires a containerized Dokploy environment that can be spun up in CI or on a Linux development host.

**Dokploy runtime requirements** (from the official install script at `https://dokploy.com/install.sh`):

| Service | Image | Purpose |
|---------|-------|---------|
| dokploy | `dokploy/dokploy:<version>` | Main app (port 3000, host mode) |
| postgres | `postgres:16` | Database |
| redis | `redis:7` | Cache/queue |
| traefik | `traefik:v3.6.7` | Reverse proxy (ports 80, 443) |

- Runs as **Docker Swarm** services (not plain containers)
- Needs Docker socket mounted (`/var/run/docker.sock`)
- Health check: `GET http://localhost:3000/api/trpc/settings.health`
- Needs `--privileged` for Docker-in-Docker
- **Linux-only** — Docker Swarm inside Docker doesn't work on macOS Docker Desktop

**Approach: Docker-in-Docker (DinD)**

Create a `tests/e2e/` directory with:

1. **`docker-compose.e2e.yml`** — Compose file that stands up a DinD environment:
   - `dind` service: `docker:dind` with `--privileged`, runs a nested Docker daemon
   - Inside the DinD container, initialize Swarm and deploy Dokploy stack (postgres, redis, traefik, dokploy)
   - Expose port 3000 for API access from the test runner
   - Consider a setup script (`tests/e2e/setup-dokploy.sh`) that:
     - Initializes Docker Swarm (`docker swarm init`)
     - Creates the `dokploy-network` overlay network
     - Starts postgres, redis, traefik as containers/services
     - Starts the dokploy service
     - Waits for health check to pass
     - Creates an initial API key (may need to hit the setup endpoint or use the DB directly)

2. **`conftest.py`** (e2e-specific) — pytest fixtures:
   - `dokploy_url` — `http://localhost:3000` (or from env var for remote instances)
   - `api_key` — Generated during setup or from env var
   - `e2e_config` — A minimal `dokploy.yml` with Docker-only apps (no GitHub provider needed)
   - `skip_if_no_dokploy` — `pytest.mark.skipif` decorator that skips e2e tests when Dokploy isn't available

3. **`test_e2e.py`** — End-to-end test scenarios:
   - **Full lifecycle**: `check → setup → env → deploy → status → destroy`
   - Verify project appears in `project.all` after setup
   - Verify apps have correct status after deploy
   - Verify environment variables are set on apps
   - Verify destroy removes the project
   - Verify state file created and cleaned up

**Test isolation:** Each test run should use a unique project name (e.g., `e2e-test-{uuid}`) to avoid collisions.

**CI considerations:**
- Mark all e2e tests with `@pytest.mark.e2e` 
- Configure pytest to skip e2e by default: `addopts = -m "not e2e"` in pyproject.toml
- CI workflow runs e2e via: `pytest -m e2e`
- GitHub Actions: use a Linux runner, start DinD as a service container
- Timeout: e2e tests need longer timeout (Dokploy startup can take 30-60s)

**Alternative to DinD:** If DinD proves too complex, consider:
- A dedicated test VM/VPS with Dokploy pre-installed
- GitHub Actions self-hosted runner with Docker Swarm
- Testcontainers-python for managing the DinD lifecycle

**Open questions to investigate:**
- How to obtain an API key programmatically (Dokploy initial setup flow)
- Whether a stripped-down Dokploy (without Traefik/nixpacks) is viable for faster startup
- Minimum Docker API version required for Swarm mode in DinD

**Dependencies:** pytest, pytest-timeout, docker (optional, for programmatic container management)

**Key files:**
- `dokploy.py` — script under test
- `examples/docker-only/dokploy.yml` — good base config for e2e (no GitHub dependency)
- `examples/minimal/dokploy.yml` — simplest possible config
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docker-compose.e2e.yml (or equivalent) can stand up a working Dokploy instance with DinD
- [ ] #2 Setup script initializes Swarm, deploys Dokploy stack, and waits for health check
- [ ] #3 At least one e2e test runs the full lifecycle: setup → env → deploy → status → destroy
- [ ] #4 E2E tests are marked with @pytest.mark.e2e and skipped by default
- [ ] #5 E2E tests use unique project names to avoid collisions
- [ ] #6 README or doc section explains how to run e2e tests locally and in CI
- [ ] #7 Tests clean up (destroy) even on failure (use pytest fixtures with finalizers)
<!-- AC:END -->
