# Dokploy API Notes

Quirks and gotchas discovered while building the deployment script.

## OpenAPI Schema

The Dokploy OpenAPI schema can be downloaded from the authenticated endpoint:

```text
GET /api/settings.getOpenApiDocument
```

Requires the `x-api-key` header.

## API Quirks

- **`saveGithubProvider`**: `repository` is the repo name only (e.g. `my-repo`), not `owner/repo` — Dokploy prepends the `owner` automatically.

- **`saveBuildType`**: `dockerfile`, `dockerContextPath`, and `dockerBuildStage` must be explicit strings (not `null`) — use `"Dockerfile"`, `""`, `""` respectively. Passing `null` causes Dokploy to use the clone directory name as the Dockerfile path. As of v0.28.4, `herokuVersion` and `railpackVersion` are also required (send `null` when not applicable). The OpenAPI spec marks them as nullable but the Zod validator rejects missing fields. The `buildType` enum values are: `dockerfile`, `nixpacks`, `static`, `heroku_buildpacks`, `paketo_buildpacks`, `railpack`.

- **`github.getGithubRepositories`**: GET with `?githubId=<id>`. Returns list of GitHub
  repo objects. Each repo has `owner.login` — used to auto-select the correct provider
  when multiple GitHub providers are configured.

- **`project.remove`** (not `project.delete`) is the correct endpoint for project deletion.

- **`application.saveBuildType`** is a separate endpoint from `application.update` — build type configuration cannot be set via the general update endpoint.

- **`application.saveEnvironment`**: `createEnvFile` (boolean) became a required field in Dokploy v0.28.4 (added in v0.26.1 as optional, promoted to required later). Controls whether env vars are written to a `.env` file in the container's working directory. Set `false` to preserve pre-v0.26.1 behavior (env vars injected as process environment only).

- **`mounts.create`**: Creates a persistent mount for an application. Required fields: `serviceId` (the application ID), `type` (`volume`, `bind`, or `file`), `mountPath` (container path). Optional: `serviceType` (`application` — the default for standalone apps). For `type: volume`, send `volumeName`; for `type: bind`, send `hostPath`.

- **`application.deploy`** returns an empty response body on success. Since v0.26.2, deployments execute asynchronously in the background — the endpoint returns immediately.

- **`project.create`** returns a nested structure: `{"project": {...}, "environment": {...}}`.

## Known Server-Side Issues

- **Stale Traefik configs after project destroy**: `project.remove` deletes the
  project and its applications from the Dokploy database but does not remove the
  corresponding Traefik dynamic config files from `/etc/dokploy/traefik/dynamic/`.
  Repeated destroy/recreate cycles accumulate orphaned `<appName>.yml` files, all
  with identical routing rules. Traefik round-robins across dead services, causing
  502 errors. **Workaround**: manually delete stale `.yml` files from the dynamic
  config directory. Traefik watches the directory and picks up removals without a
  restart.

## Container & Log Access

The Dokploy REST API does **not** expose a container logs endpoint. The UI uses WebSocket/tRPC subscriptions for real-time log streaming, which is not available via the REST API.

Instead, the `logs` and `exec` commands use `docker-py` with SSH transport (`ssh://user@host`) to connect to the Docker daemon on the Dokploy host directly. Container IDs are resolved via the REST API, then docker-py fetches logs or runs exec against those containers.

### Endpoints Used

- **`docker.getContainersByAppNameMatch`**: GET with `?appName=<appName>`. Returns a list of containers (running + exited) matching the Dokploy-assigned appName. Each entry has `containerId`, `name`, and `state` (`running`, `exited`, `created`).

- **`docker.getContainersByAppLabel`**: GET with `?appName=<appName>&type=standalone|swarm`. Similar to above but filters by deployment type label.

- **`docker.getServiceContainersByAppName`**: GET with `?appName=<appName>&serviceName=<service>`. Returns containers for a specific service within a compose/stack app.

### SSH Transport

`docker-py` with `use_ssh_client=True` spawns `ssh -- <host> docker system dial-stdio` as a subprocess, piping the Docker API through the user's local SSH binary. This uses existing SSH config, keys, and known_hosts.

## Health Check / Pre-flight

The `check` command uses `GET /api/project.all` to validate the API key.
This endpoint is a good choice for pre-flight auth validation because:

- It requires authentication (returns 401/403 with an invalid key)
- It returns 200 with a small JSON payload on success
- It has no side effects (read-only)
