# Configuration Reference

`dokploy.yml` is validated by `schemas/dokploy.schema.json`. Add this directive at the top for IDE autocomplete:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/pythoninthegrass/icarus/main/schemas/dokploy.schema.json
```

## Top-Level Keys

| Key | Required | Description |
|-----|----------|-------------|
| `project` | yes | Project metadata, env targets, deploy order |
| `github` | if github apps | GitHub defaults for all github-sourced apps |
| `environments` | no | Per-environment overrides |
| `apps` | yes | List of app definitions |

## `project`

| Key | Required | Description |
|-----|----------|-------------|
| `project.name` | yes | Dokploy project name (suffixed with `-<env>` at runtime) |
| `project.description` | yes | Project description |
| `project.env_targets` | no | App names that receive the filtered `.env` file |
| `project.deploy_order` | no | Deploy waves — outer list is sequential, inner lists are parallel |

## `github`

Omit this entire section for Docker-only projects.

| Key | Required | Description |
|-----|----------|-------------|
| `github.owner` | yes | GitHub org or user |
| `github.repository` | yes | Repo name (not `owner/repo` — Dokploy prepends owner) |
| `github.branch` | yes | Branch to deploy from |

## `environments`

Per-environment overrides merged into the base config before any command runs.

| Key | Required | Description |
|-----|----------|-------------|
| `environments.<env>.github` | no | Override `github` settings for this environment |
| `environments.<env>.apps.<name>` | no | Override app properties (see below) |

### Overridable App Properties

All per-app fields can be overridden per environment: `command`, `env`, `dockerImage`, `domain`, `buildType`, `dockerfile`, `dockerContextPath`, `dockerBuildStage`, `publishDirectory`, `autoDeploy`, `replicas`, `buildPath`, `triggerType`, `watchPaths`, `create_env_file`, `schedules`.

### Merging Semantics

- `github` overrides: shallow merge into base `github` section
- `apps.<name>` overrides: shallow merge into the matching base app definition
- Structural properties (`name`, `source`) cannot be overridden — they define the app's identity

## `apps`

| Key | Required | Description |
|-----|----------|-------------|
| `apps[].name` | yes | Unique app name within the project |
| `apps[].source` | yes | `docker`, `github`, or `compose` |
| `apps[].dockerImage` | if docker | Docker image reference |
| `apps[].command` | no | Command override, supports `{app_name}` refs |
| `apps[].env` | no | Per-app env vars (not the project `.env`), supports `{app_name}` refs |
| `apps[].domain` | no | Single domain object or list of domain objects |
| `apps[].buildType` | no | Build type: `dockerfile` (default), `nixpacks`, `static`, `heroku_buildpacks`, `paketo_buildpacks`, `railpack` |
| `apps[].dockerfile` | no | Dockerfile path (default: `Dockerfile`, for `buildType: dockerfile`) |
| `apps[].dockerContextPath` | no | Docker build context path (for `buildType: dockerfile`) |
| `apps[].dockerBuildStage` | no | Docker build target stage (for `buildType: dockerfile`) |
| `apps[].publishDirectory` | no | Publish directory (for `buildType: static`) |
| `apps[].isStaticSpa` | no | Single Page Application mode (for `buildType: static`) |
| `apps[].autoDeploy` | no | Enable auto-deploy on push (`true`/`false`) |
| `apps[].replicas` | no | Number of app replicas (integer, minimum 1) |
| `apps[].buildPath` | no | Build path for GitHub provider (default: `/`) |
| `apps[].triggerType` | no | GitHub trigger type: `push` (default) or `manual` |
| `apps[].watchPaths` | no | File paths to watch for auto-deploy triggers (list of strings) |
| `apps[].create_env_file` | no | Write env vars to a `.env` file in the container working directory (default: `false`) |
| `apps[].volumes` | no | List of volume mount objects for persistent storage |
| `apps[].schedules` | no | List of cron job objects that run commands inside the app container |
| `apps[].composeFile` | if compose | Compose file — inline YAML block scalar (`\|`) or relative file path (e.g. `docker-compose.yml`) resolved from `dokploy.yml` location |
| `apps[].composeType` | no | Compose type: `docker-compose` (default) or `stack` |

### Volume Mount Object

| Key | Required | Description |
|-----|----------|-------------|
| `volume.source` | yes | Volume name (for `type: volume`) or host path (for `type: bind`) |
| `volume.target` | yes | Mount path inside the container |
| `volume.type` | yes | `volume` (Docker-managed) or `bind` (host path) |

### Schedule Object

| Key | Required | Description |
|-----|----------|-------------|
| `schedule.name` | yes | Job name (used to match during reconciliation on redeploy) |
| `schedule.cronExpression` | yes | Standard 5-field cron: `minute hour day month weekday` |
| `schedule.command` | yes | Command to run inside the app container via `docker exec` |
| `schedule.shellType` | no | `bash` (default) or `sh` |
| `schedule.timezone` | no | IANA timezone (e.g. `America/Chicago`) |
| `schedule.enabled` | no | Whether the schedule is active (default: `true`) |

On first `setup`, schedules are created via the Dokploy `schedule.create` API. On subsequent `apply` (redeploy), schedules are reconciled by name: existing schedules are updated, new ones are created, and removed ones are deleted.

### Domain Object

| Key | Required | Description |
|-----|----------|-------------|
| `domain.host` | yes | Domain hostname |
| `domain.port` | yes | Container port to expose |
| `domain.https` | yes | Enable HTTPS |
| `domain.certificateType` | yes | `none` or `letsencrypt` |
| `domain.path` | no | URL path (default: `/`) |
| `domain.internalPath` | no | Internal routing path (default: `/`) |
| `domain.stripPath` | no | Strip path prefix before forwarding (default: `false`) |
| `domain.serviceName` | if compose | Target service name within a compose stack for Traefik routing |

## Compose Apps

Apps with `source: compose` deploy a full Docker Compose stack as a single Dokploy resource. The compose file can be provided inline or as a relative file path:

```yaml
apps:
  # Inline compose file
  - name: my-stack
    source: compose
    composeFile: |
      services:
        web:
          image: nginx
          ports:
            - "80"
    composeType: docker-compose

  # External compose file
  - name: my-stack
    source: compose
    composeFile: docker-compose.yml
    composeType: docker-compose
```

Compose env vars (defined in per-app `env:` or pushed from the project `.env` via `env_targets`) are available in the compose file using standard `${VAR}` syntax. Dokploy resolves these at deploy time. Use `$${VAR}` to escape literal `$` in shell contexts (e.g. healthcheck commands).

Domains for compose apps require `serviceName` to identify which service in the stack receives traffic:

```yaml
environments:
  prod:
    apps:
      my-stack:
        domain:
          host: app.example.com
          port: 8080
          https: true
          certificateType: letsencrypt
          serviceName: web
```

See `examples/docker-compose/` for a complete working example.

## `{app_name}` Resolution

In `command` and `env` fields, `{app_name}` placeholders are replaced with the Dokploy-assigned `appName` from the state file. This allows apps to reference each other's internal Docker network hostnames.

Example: `redis://{redis}:6379/0` resolves to `redis://redis-abcdef:6379/0` (where `redis-abcdef` is the Dokploy appName).

Resolution happens during `setup` (for commands) and `env` (for environment variables).

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOKPLOY_URL` | yes | — | Dokploy server URL |
| `DOKPLOY_API_KEY` | yes | — | API key for authentication |
| `DOKPLOY_ENV` | no | `dev` | Target environment (alternative to `--env` flag) |
| `ENV_EXCLUDE_PREFIXES` | no | — | Extra env var prefixes to exclude when pushing `.env` |
| `DOKPLOY_SSH_HOST` | for logs/exec | — | SSH host for Docker access (IP or hostname) |
| `DOKPLOY_SSH_USER` | no | `root` | SSH user for Docker access |
| `DOKPLOY_SSH_PORT` | no | `22` | SSH port for Docker access |

Resolution order: `--env` flag > `DOKPLOY_ENV` (from `.env` or environment) > `dev`.

The `DOKPLOY_SSH_*` variables are only required for the `logs` and `exec` commands, which connect to the Docker daemon on the Dokploy host via SSH.

## Schema Directive

The `# yaml-language-server` directive at the top of `dokploy.yml` enables IDE features:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/pythoninthegrass/icarus/main/schemas/dokploy.schema.json
```

This works in VS Code (with the YAML extension), JetBrains IDEs, and other editors that support the yaml-language-server protocol. You can also use a local relative path (`$schema=schemas/dokploy.schema.json`) if you have a copy of the schema in your repo.

## Host Tuning

Dokploy hosts running many containers (especially compose stacks) can exhaust default Linux inotify limits, causing `tail: inotify cannot be used, reverting to polling: Too many open files` during deployments.

Apply these sysctl settings on the Dokploy host:

```bash
echo "fs.inotify.max_user_instances=512" | sudo tee -a /etc/sysctl.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

| Setting | Default | Recommended | Purpose |
|---------|---------|-------------|---------|
| `fs.inotify.max_user_instances` | 128 | 512 | Max inotify instances per user (each container watcher uses one) |
| `fs.inotify.max_user_watches` | ~250,000 | 524,288 | Max files watched across all instances |
