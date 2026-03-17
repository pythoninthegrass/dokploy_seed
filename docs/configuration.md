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
| `apps[].source` | yes | `docker` or `github` |
| `apps[].dockerImage` | if docker | Docker image reference |
| `apps[].command` | no | Command override, supports `{app_name}` refs |
| `apps[].env` | no | Per-app env vars (not the project `.env`), supports `{app_name}` refs |
| `apps[].domain` | no | Single domain object or list of domain objects |
| `apps[].buildType` | no | Build type: `dockerfile` (default), `nixpacks`, `static`, `heroku_buildpacks`, `paketo_buildpacks`, `railpack` |
| `apps[].dockerfile` | no | Dockerfile path (default: `Dockerfile`, for `buildType: dockerfile`) |
| `apps[].dockerContextPath` | no | Docker build context path (for `buildType: dockerfile`) |
| `apps[].dockerBuildStage` | no | Docker build target stage (for `buildType: dockerfile`) |
| `apps[].publishDirectory` | no | Publish directory (for `buildType: static`) |
| `apps[].autoDeploy` | no | Enable auto-deploy on push (`true`/`false`) |
| `apps[].replicas` | no | Number of app replicas (integer, minimum 1) |
| `apps[].buildPath` | no | Build path for GitHub provider (default: `/`) |
| `apps[].triggerType` | no | GitHub trigger type: `push` (default) or `manual` |
| `apps[].watchPaths` | no | File paths to watch for auto-deploy triggers (list of strings) |
| `apps[].create_env_file` | no | Write env vars to a `.env` file in the container working directory (default: `false`) |
| `apps[].volumes` | no | List of volume mount objects for persistent storage |
| `apps[].schedules` | no | List of cron job objects that run commands inside the app container |

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

On first `setup`, schedules are created via the Dokploy `schedule.create` API. On subsequent `deploy` (redeploy), schedules are reconciled by name: existing schedules are updated, new ones are created, and removed ones are deleted.

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
