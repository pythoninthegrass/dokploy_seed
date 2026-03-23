#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#     "docker[ssh]>=7.0",
#     "httpx>=0.28.1,<1",
#     "python-decouple>=3.8",
#     "pyyaml>=6.0",
# ]
# [tool.uv]
# exclude-newer = "2026-03-31T00:00:00Z"
# ///

# pyright: reportMissingImports=false
# type: ignore[import-untyped]

"""
Dokploy deployment script — config-driven via dokploy.yml.

Usage:
    ic check
    ic --env <environment> <setup|env|apply|status|clean|destroy>
    ic --env <environment> logs [app] [-f] [-n TAIL] [--exited]
    ic --env <environment> exec [app] [--exited] [-- command...]

Environment can also be set via DOKPLOY_ENV env var.
SSH commands (logs, exec) require DOKPLOY_SSH_HOST in .env.
"""

import argparse
import copy
import docker
import httpx
import json
import os
import paramiko
import re
import sys
import yaml
from decouple import Config, RepositoryEmpty, RepositoryEnv
from pathlib import Path


def _build_config() -> Config:
    """Build a decouple Config from the resolved .env path.

    Honors the ``DOTENV_FILE`` environment variable to override the default
    path, following the python-decouple convention.
    """
    env_file = Path(os.environ.get("DOTENV_FILE", str(Path.cwd() / ".env")))
    if env_file.is_file():
        return Config(RepositoryEnv(str(env_file)))
    return Config(RepositoryEmpty())


config = _build_config()


def find_repo_root() -> Path:
    """Walk up from cwd looking for dokploy.yml."""
    current = Path.cwd()
    while True:
        if (current / "dokploy.yml").exists():
            return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root without finding config
            print("ERROR: Could not find dokploy.yml in any parent directory.")
            sys.exit(1)
        current = parent


DEFAULT_ENV_EXCLUDES = [
    "COMPOSE_",
    "CONTAINER_NAME",
    "DOKPLOY_",
    "DOPPLER_",
    "PGDATA",
    "POSTGRES_VERSION",
    "TASK_X_",
]


def get_state_file(repo_root: Path, env_name: str) -> Path:
    """Return path to the state file for the given environment."""
    return repo_root / ".dokploy-state" / f"{env_name}.json"


def load_config(repo_root: Path) -> dict:
    """Read and return dokploy.yml from the repo root."""
    config_file = repo_root / "dokploy.yml"
    if not config_file.exists():
        print(f"ERROR: Config file not found: {config_file}")
        sys.exit(1)
    with config_file.open() as f:
        return yaml.safe_load(f)


def validate_config(cfg: dict) -> None:
    """Fail fast on invalid config references."""
    app_names = {a["name"] for a in cfg["apps"]}

    for target in cfg["project"].get("env_targets", []):
        if target not in app_names:
            print(f"ERROR: env_targets references unknown app '{target}'")
            sys.exit(1)

    for wave in cfg["project"].get("deploy_order", []):
        for name in wave:
            if name not in app_names:
                print(f"ERROR: deploy_order references unknown app '{name}'")
                sys.exit(1)

    github_apps = [a for a in cfg["apps"] if a.get("source") == "github"]
    if github_apps and "github" not in cfg:
        print("ERROR: GitHub-sourced apps exist but no [github] config found")
        sys.exit(1)


def validate_env_references(cfg: dict) -> None:
    """Check that environment app overrides reference apps that exist in the base config."""
    app_names = {a["name"] for a in cfg["apps"]}
    environments = cfg.get("environments", {})

    for env_name, env_cfg in environments.items():
        for app_name in env_cfg.get("apps", {}):
            if app_name not in app_names:
                print(f"ERROR: environments.{env_name}.apps references unknown app '{app_name}'")
                sys.exit(1)


def merge_env_overrides(cfg: dict, env_name: str) -> dict:
    """Deep-copy config and merge environment-specific overrides into it."""
    merged = copy.deepcopy(cfg)
    environments = merged.pop("environments", {})

    env_overrides = environments.get(env_name, {})

    # Merge github overrides
    if "github" in env_overrides and "github" in merged:
        merged["github"].update(env_overrides["github"])

    # Merge per-app overrides
    app_overrides = env_overrides.get("apps", {})
    for app_def in merged["apps"]:
        name = app_def["name"]
        if name in app_overrides:
            app_def.update(app_overrides[name])

    return merged


def resolve_refs(template: str, state: dict) -> str:
    """Replace {app_name} placeholders with Dokploy appName from state."""

    def replacer(match: re.Match) -> str:
        ref = match.group(1)
        if ref in state["apps"]:
            return state["apps"][ref]["appName"]
        return match.group(0)  # leave unresolved refs as-is

    return re.sub(r"\{(\w+)\}", replacer, template)


def get_env_excludes() -> list[str]:
    """Merge default exclusion patterns with optional extras from .env.

    Reads ``ENV_EXCLUDE_PREFIXES`` for backward compatibility and the new
    ``ENV_EXCLUDES`` key.  Patterns ending with ``_`` or ``*`` are treated as
    prefix matches; all other patterns are exact matches.
    """
    patterns = list(DEFAULT_ENV_EXCLUDES)
    for env_key in ("ENV_EXCLUDES", "ENV_EXCLUDE_PREFIXES"):
        extras: str = config(env_key, default="")  # type: ignore[assignment]
        if extras:
            patterns.extend(p.strip() for p in extras.split(",") if p.strip())
    return patterns


def _is_env_excluded(key: str, patterns: list[str]) -> bool:
    """Check if an env var key matches any exclusion pattern.

    Patterns ending with ``_`` or ``*`` are prefix matches (the ``*`` is
    stripped before comparison).  All other patterns are exact matches.
    """
    for pattern in patterns:
        if pattern.endswith("*"):
            if key.startswith(pattern[:-1]):
                return True
        elif pattern.endswith("_"):
            if key.startswith(pattern):
                return True
        else:
            if key == pattern:
                return True
    return False


def filter_env(content: str, exclude_patterns: list[str]) -> str:
    """Strip comments, blank lines, and lines whose key matches an exclusion pattern."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key = stripped.split("=", 1)[0].strip()
        if _is_env_excluded(key, exclude_patterns):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n" if lines else ""


def resolve_env_for_push(env_file: Path, exclude_patterns: list[str]) -> str:
    """Read env file and resolve values, preferring os.environ over file values.

    Uses python-decouple's Config resolution (os.environ > file > default)
    so that ``doppler run -- ic env`` injects secrets without modifying the file.
    """
    repo = RepositoryEnv(str(env_file))
    push_config = Config(repo)
    lines = []
    for key in repo.data:
        if _is_env_excluded(key, exclude_patterns):
            continue
        lines.append(f"{key}={push_config(key)}")
    return "\n".join(lines) + "\n" if lines else ""


def build_github_provider_payload(app_id: str, app_def: dict, github_cfg: dict, github_id: str) -> dict:
    """Build payload for application.saveGithubProvider."""
    return {
        "applicationId": app_id,
        "repository": github_cfg["repository"],
        "branch": github_cfg["branch"],
        "owner": github_cfg["owner"],
        "buildPath": app_def.get("buildPath", "/"),
        "githubId": github_id,
        "enableSubmodules": False,
        "triggerType": app_def.get("triggerType", "push"),
        "watchPaths": app_def.get("watchPaths"),
    }


def resolve_github_provider(client: "DokployClient", providers: list[dict], owner: str) -> str:
    """Find the GitHub provider that has access to repos owned by `owner`."""
    for p in providers:
        gid = p["githubId"]
        repos = client.get("github.getGithubRepositories", params={"githubId": gid})
        owners = {r["owner"]["login"] for r in repos}
        if owner in owners:
            return gid
    available = [p["githubId"] for p in providers]
    raise SystemExit(
        f"ERROR: No GitHub provider has access to owner '{owner}'.\n"
        f"  Available providers: {available}\n"
        f"  Configure access in Dokploy UI."
    )


def build_build_type_payload(app_id: str, app_def: dict) -> dict:
    """Build payload for application.saveBuildType."""
    build_type = app_def.get("buildType", "dockerfile")
    payload: dict = {
        "applicationId": app_id,
        "buildType": build_type,
        "dockerfile": app_def.get("dockerfile", "Dockerfile") if build_type == "dockerfile" else None,
        "dockerContextPath": app_def.get("dockerContextPath", ""),
        "dockerBuildStage": app_def.get("dockerBuildStage", ""),
        "herokuVersion": None,
        "railpackVersion": None,
    }
    if build_type == "static":
        payload["publishDirectory"] = app_def.get("publishDirectory", "")
        payload["isStaticSpa"] = app_def.get("isStaticSpa", False)
    return payload


def is_compose(app_def: dict) -> bool:
    """Check if an app definition uses compose source type."""
    return app_def.get("source") == "compose"


def resolve_compose_file(app_def: dict, repo_root: Path) -> str:
    """Resolve compose file content from inline block scalar or relative path."""
    compose_file = app_def["composeFile"]
    # Multi-line string = inline block scalar
    if "\n" in compose_file:
        return compose_file
    # Single-line = relative file path
    path = repo_root / compose_file
    if not path.exists():
        print(f"ERROR: Compose file not found: {path}")
        sys.exit(1)
    return path.read_text()


def build_domain_payload(resource_id: str, dom: dict, *, compose: bool = False) -> dict:
    """Build payload for domain.create."""
    if compose:
        payload = {
            "composeId": resource_id,
            "domainType": "compose",
            "serviceName": dom["serviceName"],
        }
    else:
        payload = {
            "applicationId": resource_id,
        }
    payload.update(
        {
            "host": dom["host"],
            "port": dom["port"],
            "https": dom["https"],
            "certificateType": dom["certificateType"],
        }
    )
    for key in ("path", "internalPath", "stripPath"):
        if key in dom:
            payload[key] = dom[key]
    return payload


def build_app_settings_payload(app_id: str, app_def: dict) -> dict | None:
    """Build payload for application.update (autoDeploy, replicas).

    Returns None if no settings need updating.
    """
    payload: dict = {"applicationId": app_id}
    for key in ("autoDeploy", "replicas"):
        if key in app_def:
            payload[key] = app_def[key]
    return payload if len(payload) > 1 else None


def build_mount_payload(app_id: str, mount: dict) -> dict:
    """Build payload for mounts.create."""
    payload = {
        "serviceId": app_id,
        "type": mount["type"],
        "mountPath": mount["target"],
        "serviceType": "application",
    }
    if mount["type"] == "volume":
        payload["volumeName"] = mount["source"]
    elif mount["type"] == "bind":
        payload["hostPath"] = mount["source"]
    return payload


def build_schedule_payload(app_id: str, sched: dict) -> dict:
    """Build payload for schedule.create."""
    payload = {
        "name": sched["name"],
        "cronExpression": sched["cronExpression"],
        "command": sched["command"],
        "scheduleType": "application",
        "applicationId": app_id,
        "shellType": sched.get("shellType", "bash"),
        "enabled": sched.get("enabled", True),
    }
    if "timezone" in sched:
        payload["timezone"] = sched["timezone"]
    return payload


def reconcile_schedules(
    client: "DokployClient",
    app_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    """Reconcile schedules: update existing by name, create new, delete removed.

    Returns a dict mapping schedule name -> {"scheduleId": ...} for state storage.
    """
    existing_by_name = {s["name"]: s for s in existing}
    desired_by_name = {s["name"]: s for s in desired}

    result_state = {}

    for name, sched in desired_by_name.items():
        payload = build_schedule_payload(app_id, sched)
        if name in existing_by_name:
            ex = existing_by_name[name]
            schedule_id = ex["scheduleId"]
            needs_update = (
                payload.get("cronExpression") != ex.get("cronExpression")
                or payload.get("command") != ex.get("command")
                or payload.get("shellType") != ex.get("shellType")
                or payload.get("enabled") != ex.get("enabled")
                or payload.get("timezone") != ex.get("timezone")
            )
            if needs_update:
                update_payload = {**payload, "scheduleId": schedule_id}
                update_payload.pop("applicationId", None)
                update_payload.pop("scheduleType", None)
                client.post("schedule.update", update_payload)
            result_state[name] = {"scheduleId": schedule_id}
        else:
            resp = client.post("schedule.create", payload)
            result_state[name] = {"scheduleId": resp["scheduleId"]}

    for name, ex in existing_by_name.items():
        if name not in desired_by_name:
            client.post("schedule.delete", {"scheduleId": ex["scheduleId"]})

    return result_state


def reconcile_app_schedules(
    client: "DokployClient",
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile schedules for all apps on redeploy."""
    changed = False
    for app_def in cfg.get("apps", []):
        schedules = app_def.get("schedules")
        if schedules is None and "schedules" not in state["apps"].get(app_def["name"], {}):
            continue
        name = app_def["name"]
        app_id = state["apps"][name]["applicationId"]
        existing = client.get(
            "schedule.list",
            {"id": app_id, "scheduleType": "application"},
        )
        if not isinstance(existing, list):
            existing = []
        desired = schedules or []
        new_state = reconcile_schedules(client, app_id, existing, desired)
        state["apps"][name]["schedules"] = new_state
        changed = True
    if changed:
        save_state(state, state_file)


def reconcile_mounts(
    client: "DokployClient",
    app_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    """Reconcile mounts: update existing by mountPath, create new, delete removed.

    Returns a dict mapping mountPath -> {"mountId": ...} for state storage.
    """
    existing_by_path = {m["mountPath"]: m for m in existing}
    desired_by_path = {m["target"]: m for m in desired}

    result_state = {}

    for path, mount in desired_by_path.items():
        payload = build_mount_payload(app_id, mount)
        if path in existing_by_path:
            ex = existing_by_path[path]
            mount_id = ex["mountId"]
            needs_update = (
                payload.get("type") != ex.get("type")
                or payload.get("volumeName") != ex.get("volumeName")
                or payload.get("hostPath") != ex.get("hostPath")
            )
            if needs_update:
                update_payload = {**payload, "mountId": mount_id}
                update_payload.pop("serviceId", None)
                update_payload.pop("serviceType", None)
                client.post("mounts.update", update_payload)
            result_state[path] = {"mountId": mount_id}
        else:
            resp = client.post("mounts.create", payload)
            result_state[path] = {"mountId": resp["mountId"]}

    for path, ex in existing_by_path.items():
        if path not in desired_by_path:
            client.post("mounts.remove", {"mountId": ex["mountId"]})

    return result_state


def reconcile_app_mounts(
    client: "DokployClient",
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile mounts for all apps on redeploy."""
    changed = False
    for app_def in cfg.get("apps", []):
        if is_compose(app_def):
            continue
        volumes = app_def.get("volumes")
        name = app_def["name"]
        if volumes is None and "mounts" not in state["apps"].get(name, {}):
            continue
        app_id = state["apps"][name]["applicationId"]
        remote = client.get("application.one", {"applicationId": app_id})
        existing = remote.get("mounts") or []
        desired = volumes or []
        new_state = reconcile_mounts(client, app_id, existing, desired)
        state["apps"][name]["mounts"] = new_state
        changed = True
    if changed:
        save_state(state, state_file)


def reconcile_domains(
    client: "DokployClient",
    resource_id: str,
    existing: list[dict],
    desired: list[dict],
    *,
    compose: bool = False,
) -> dict:
    """Reconcile domains: update existing by host, create new, delete removed.

    Returns a dict mapping host -> {"domainId": ...} for state storage.
    """
    existing_by_host = {d["host"]: d for d in existing}
    desired_by_host = {d["host"]: d for d in desired}

    result_state = {}

    for host, dom in desired_by_host.items():
        payload = build_domain_payload(resource_id, dom, compose=compose)
        if host in existing_by_host:
            ex = existing_by_host[host]
            domain_id = ex["domainId"]
            needs_update = any(
                payload.get(key) != ex.get(key)
                for key in ("port", "https", "certificateType", "path", "internalPath", "stripPath")
            )
            if needs_update:
                update_payload = {k: v for k, v in payload.items() if k not in ("applicationId", "composeId", "domainType")}
                update_payload["domainId"] = domain_id
                client.post("domain.update", update_payload)
            result_state[host] = {"domainId": domain_id}
        else:
            resp = client.post("domain.create", payload)
            result_state[host] = {"domainId": resp["domainId"]}

    for host, ex in existing_by_host.items():
        if host not in desired_by_host:
            client.post("domain.delete", {"domainId": ex["domainId"]})

    return result_state


def reconcile_app_domains(
    client: "DokployClient",
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile domains for all apps on redeploy."""
    changed = False
    for app_def in cfg.get("apps", []):
        domain_cfg = app_def.get("domain")
        name = app_def["name"]
        if domain_cfg is None and "domains" not in state["apps"].get(name, {}):
            continue
        compose = is_compose(app_def)
        if compose:
            resource_id = state["apps"][name]["composeId"]
            existing = client.get("domain.byComposeId", {"composeId": resource_id})
        else:
            resource_id = state["apps"][name]["applicationId"]
            existing = client.get("domain.byApplicationId", {"applicationId": resource_id})
        if not isinstance(existing, list):
            existing = []
        desired = domain_cfg if isinstance(domain_cfg, list) else [domain_cfg] if domain_cfg else []
        new_state = reconcile_domains(client, resource_id, existing, desired, compose=compose)
        state["apps"][name]["domains"] = new_state
        changed = True
    if changed:
        save_state(state, state_file)


class DokployClient:
    """Thin httpx wrapper for Dokploy API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key},
            timeout=60.0,
        )

    def get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self.client.get(f"/api/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, payload: dict | None = None) -> dict:
        resp = self.client.post(f"/api/{path}", json=payload or {})
        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()


def validate_state(client: DokployClient, state: dict) -> bool:
    """Check if the project in state still exists on the server.

    Returns True if valid or if the server can't be reached (assume valid).
    Returns False if the project is confirmed gone.
    """
    try:
        projects = client.get("project.all")
    except httpx.HTTPStatusError:
        return True
    return any(p["projectId"] == state["projectId"] for p in projects)


def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        print(f"ERROR: State file not found: {state_file}")
        print("Run 'setup' first.")
        sys.exit(1)
    return json.loads(state_file.read_text())


def save_state(state: dict, state_file: Path, *, quiet: bool = False) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2) + "\n")
    if not quiet:
        print(f"State saved to {state_file}")


def cmd_check(repo_root: Path) -> None:
    """Pre-flight checks: env vars, server reachability, API auth, config."""
    passed = 0
    failed = 0

    def _pass(label: str, detail: str = "") -> None:
        nonlocal passed
        passed += 1
        msg = f"  PASS  {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)

    def _fail(label: str, detail: str = "") -> None:
        nonlocal failed
        failed += 1
        msg = f"  FAIL  {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)

    def _warn(label: str, detail: str = "") -> None:
        msg = f"  WARN  {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)

    def _skip(label: str, detail: str = "") -> None:
        msg = f"  SKIP  {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)

    print("Running pre-flight checks...\n")

    # 1. Env vars
    api_key = None
    try:
        api_key = config("DOKPLOY_API_KEY")
        _pass("DOKPLOY_API_KEY is set")
    except Exception:
        _fail("DOKPLOY_API_KEY is not set")

    base_url = None
    try:
        base_url = config("DOKPLOY_URL", default="https://dokploy.example.com")
        if base_url == "https://dokploy.example.com":
            _warn(
                "DOKPLOY_URL",
                "using default placeholder (https://dokploy.example.com)",
            )
        else:
            _pass("DOKPLOY_URL", base_url)
    except Exception:
        _fail("DOKPLOY_URL is not set")

    # 2. URL reachability
    if base_url and base_url != "https://dokploy.example.com":
        try:
            resp = httpx.get(base_url, timeout=10.0, follow_redirects=True)
            _pass("Server reachable", f"HTTP {resp.status_code}")
        except httpx.ConnectError:
            _fail("Server unreachable", f"cannot connect to {base_url}")
        except httpx.TimeoutException:
            _fail("Server unreachable", f"timeout connecting to {base_url}")
        except Exception as exc:
            _fail("Server reachable", str(exc))
    else:
        _skip(
            "Server reachability",
            "no valid DOKPLOY_URL configured",
        )

    # 3. API key validity
    if api_key and base_url and base_url != "https://dokploy.example.com":
        try:
            resp = httpx.get(
                f"{base_url.rstrip('/')}/api/project.all",
                headers={"x-api-key": api_key},
                timeout=10.0,
            )
            if resp.status_code == 200:
                _pass("API key valid", "authenticated successfully")
            else:
                _fail(
                    "API key invalid",
                    f"HTTP {resp.status_code}",
                )
        except Exception as exc:
            _fail("API key check", str(exc))
    else:
        _skip(
            "API key validation",
            "missing DOKPLOY_API_KEY or DOKPLOY_URL",
        )

    # 4. Config file
    config_path = repo_root / "dokploy.yml"
    if config_path.exists():
        try:
            with config_path.open() as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                _fail("dokploy.yml", "file does not contain a YAML mapping")
            else:
                missing = [k for k in ("project", "apps") if k not in data]
                if missing:
                    _fail(
                        "dokploy.yml",
                        f"missing required keys: {', '.join(missing)}",
                    )
                else:
                    _pass("dokploy.yml", "valid with project and apps keys")
        except yaml.YAMLError as exc:
            _fail("dokploy.yml", f"YAML parse error: {exc}")
    else:
        _fail("dokploy.yml", f"not found at {config_path}")

    # Summary
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


def cmd_setup(client: DokployClient, cfg: dict, state_file: Path, repo_root: Path | None = None) -> None:
    if state_file.exists():
        print(f"ERROR: State file already exists: {state_file}")
        print("Run 'destroy' first or delete the state file manually.")
        sys.exit(1)

    project_cfg = cfg["project"]
    github_cfg = cfg.get("github")

    # 1. Create project
    print("Creating project...")
    project = client.post(
        "project.create",
        {"name": project_cfg["name"], "description": project_cfg["description"]},
    )
    project_id = project["project"]["projectId"]
    environment_id = project["environment"]["environmentId"]
    print(f"  Project created: {project_id}")
    print(f"  Environment ID: {environment_id}")

    # 2. Get githubId (only if there are GitHub-sourced apps)
    github_id = None
    if github_cfg:
        print("Fetching GitHub provider ID...")
        providers = client.get("github.githubProviders")
        if not providers:
            print("ERROR: No GitHub provider found. Configure one in Dokploy UI first.")
            sys.exit(1)
        github_id = resolve_github_provider(client, providers, github_cfg["owner"])
        print(f"  GitHub ID: {github_id}")

    state: dict = {
        "projectId": project_id,
        "environmentId": environment_id,
        "apps": {},
    }

    # 3. Create apps
    for app_def in cfg["apps"]:
        name = app_def["name"]
        if is_compose(app_def):
            print(f"Creating compose: {name}...")
            compose_type = app_def.get("composeType", "docker-compose")
            result = client.post(
                "compose.create",
                {
                    "name": name,
                    "environmentId": environment_id,
                    "composeType": compose_type,
                },
            )
            compose_id = result["composeId"]
            app_name = result["appName"]
            state["apps"][name] = {
                "composeId": compose_id,
                "appName": app_name,
                "source": "compose",
            }
            print(f"  {name}: id={compose_id} appName={app_name}")
        else:
            print(f"Creating app: {name}...")
            result = client.post(
                "application.create",
                {"name": name, "environmentId": environment_id},
            )
            app_id = result["applicationId"]
            app_name = result["appName"]
            state["apps"][name] = {"applicationId": app_id, "appName": app_name}
            print(f"  {name}: id={app_id} appName={app_name}")

    # Save state early so destroy can clean up if later steps fail
    save_state(state, state_file, quiet=True)

    # 4. Configure providers
    for app_def in cfg["apps"]:
        name = app_def["name"]

        if is_compose(app_def):
            compose_id = state["apps"][name]["composeId"]
            compose_content = resolve_compose_file(app_def, repo_root or state_file.parent.parent)
            print(f"Pushing compose file for {name}...")
            client.post(
                "compose.update",
                {"composeId": compose_id, "composeFile": compose_content, "sourceType": "raw"},
            )
            continue

        app_id = state["apps"][name]["applicationId"]

        if app_def["source"] == "docker":
            print(f"Configuring Docker provider for {name}...")
            client.post(
                "application.saveDockerProvider",
                {
                    "applicationId": app_id,
                    "dockerImage": app_def["dockerImage"],
                    "username": None,
                    "password": None,
                    "registryUrl": None,
                },
            )
        elif app_def["source"] == "github":
            assert github_cfg is not None
            print(f"Configuring GitHub provider for {name}...")
            provider_payload = build_github_provider_payload(app_id, app_def, github_cfg, github_id)
            client.post("application.saveGithubProvider", provider_payload)

            build_type = app_def.get("buildType", "dockerfile")
            print(f"  Setting buildType={build_type} for {name}...")
            build_payload = build_build_type_payload(app_id, app_def)
            client.post("application.saveBuildType", build_payload)

    # 5. Command overrides (resolve {ref} placeholders)
    for app_def in cfg["apps"]:
        name = app_def["name"]
        if is_compose(app_def):
            continue
        command = app_def.get("command")
        if not command:
            continue
        resolved = resolve_refs(command, state)
        app_id = state["apps"][name]["applicationId"]
        print(f"Setting command override for {name}...")
        client.post(
            "application.update",
            {"applicationId": app_id, "command": resolved},
        )

    # 6. Domains
    for app_def in cfg["apps"]:
        name = app_def["name"]
        domain_cfg = app_def.get("domain")
        if not domain_cfg:
            continue

        # Support single dict or list of dicts
        domains = domain_cfg if isinstance(domain_cfg, list) else [domain_cfg]
        compose = is_compose(app_def)
        resource_id = state["apps"][name]["composeId"] if compose else state["apps"][name]["applicationId"]
        for dom in domains:
            print(f"Creating domain for {name}: {dom['host']}...")
            domain_payload = build_domain_payload(resource_id, dom, compose=compose)
            client.post("domain.create", domain_payload)

    # 7. Application settings (autoDeploy, replicas)
    for app_def in cfg["apps"]:
        if is_compose(app_def):
            continue
        name = app_def["name"]
        app_id = state["apps"][name]["applicationId"]
        settings_payload = build_app_settings_payload(app_id, app_def)
        if settings_payload:
            print(f"Updating app settings for {name}...")
            client.post("application.update", settings_payload)

    # 8. Volume mounts
    for app_def in cfg["apps"]:
        if is_compose(app_def):
            continue
        volumes = app_def.get("volumes")
        if not volumes:
            continue
        name = app_def["name"]
        app_id = state["apps"][name]["applicationId"]
        for vol in volumes:
            print(f"Creating mount for {name}: {vol['source']} -> {vol['target']}...")
            mount_payload = build_mount_payload(app_id, vol)
            client.post("mounts.create", mount_payload)

    # 9. Schedules
    for app_def in cfg["apps"]:
        if is_compose(app_def):
            continue
        schedules = app_def.get("schedules")
        if not schedules:
            continue
        name = app_def["name"]
        app_id = state["apps"][name]["applicationId"]
        state["apps"][name]["schedules"] = {}
        for sched in schedules:
            print(f"Creating schedule for {name}: {sched['name']}...")
            sched_payload = build_schedule_payload(app_id, sched)
            resp = client.post("schedule.create", sched_payload)
            state["apps"][name]["schedules"][sched["name"]] = {"scheduleId": resp["scheduleId"]}

    # 10. Save state
    save_state(state, state_file)
    print("\nSetup complete!")
    print(f"  Project: {project_id}")
    for name, info in state["apps"].items():
        rid = info.get("composeId") or info.get("applicationId")
        print(f"  {name}: {rid}")


def cmd_env(
    client: DokployClient,
    cfg: dict,
    state_file: Path,
    repo_root: Path,
    env_file_override: Path | None = None,
) -> None:
    state = load_state(state_file)
    env_targets = cfg["project"].get("env_targets", [])
    env_file = env_file_override or Path(os.environ.get("DOTENV_FILE", str(repo_root / ".env")))
    apps_by_name = {a["name"]: a for a in cfg["apps"]}

    if env_targets:
        if not env_file.exists():
            print(f"ERROR: {env_file} not found.")
            sys.exit(1)

        exclude_patterns = get_env_excludes()
        filtered = resolve_env_for_push(env_file, exclude_patterns)
        total = len(filtered.strip().splitlines()) if filtered.strip() else 0
        print(f"Filtered .env: {total} vars")

        for name in env_targets:
            app_info = state["apps"][name]
            resolved = resolve_refs(filtered, state)
            if app_info.get("source") == "compose":
                compose_id = app_info["composeId"]
                app_def = apps_by_name[name]
                compose_content = resolve_compose_file(app_def, repo_root)
                print(f"Pushing env + compose file to {name}...")
                client.post(
                    "compose.update",
                    {
                        "composeId": compose_id,
                        "env": resolved,
                        "composeFile": compose_content,
                        "sourceType": "raw",
                    },
                )
            else:
                app_id = app_info["applicationId"]
                create_env_file = apps_by_name[name].get("create_env_file", False)
                print(f"Pushing env vars to {name}...")
                client.post(
                    "application.saveEnvironment",
                    {
                        "applicationId": app_id,
                        "env": resolved,
                        "buildArgs": None,
                        "buildSecrets": None,
                        "createEnvFile": create_env_file,
                    },
                )

    # Push per-app custom env (with {ref} resolution)
    for app_def in cfg["apps"]:
        custom_env = app_def.get("env")
        if not custom_env:
            continue
        name = app_def["name"]
        resolved = resolve_refs(custom_env, state)
        app_info = state["apps"][name]
        if is_compose(app_def):
            compose_id = app_info["composeId"]
            print(f"Pushing custom env to compose {name}...")
            existing = client.get("compose.one", {"composeId": compose_id})
            prev_env = existing.get("env", "")
            merged = (prev_env.rstrip("\n") + "\n" + resolved).lstrip("\n")
            client.post(
                "compose.update",
                {"composeId": compose_id, "env": merged},
            )
        else:
            app_id = app_info["applicationId"]
            create_env_file = app_def.get("create_env_file", False)
            print(f"Pushing custom env to {name}...")
            client.post(
                "application.saveEnvironment",
                {
                    "applicationId": app_id,
                    "env": resolved,
                    "buildArgs": None,
                    "buildSecrets": None,
                    "createEnvFile": create_env_file,
                },
            )

    print("\nEnvironment variables pushed.")


def cmd_trigger(client: DokployClient, cfg: dict, state_file: Path, *, redeploy: bool = False) -> None:
    state = load_state(state_file)
    deploy_order = cfg["project"].get("deploy_order", [])
    endpoint = "application.redeploy" if redeploy else "application.deploy"
    action = "Redeploying" if redeploy else "Deploying"

    for i, wave in enumerate(deploy_order, 1):
        print(f"Wave {i}: {', '.join(wave)}")
        for name in wave:
            app_info = state["apps"][name]
            print(f"  {action} {name}...")
            if app_info.get("source") == "compose":
                compose_endpoint = "compose.redeploy" if redeploy else "compose.deploy"
                client.post(compose_endpoint, {"composeId": app_info["composeId"]})
            else:
                client.post(endpoint, {"applicationId": app_info["applicationId"]})
            print(f"    {name} deploy triggered.")

    print("\nAll deploys triggered.")


def cmd_apply(
    repo_root: Path,
    client: DokployClient,
    cfg: dict,
    state_file: Path,
    env_file_override: Path | None = None,
) -> None:
    print("\n==> Phase 1/4: check")
    cmd_check(repo_root)

    is_redeploy = False
    if state_file.exists():
        state = load_state(state_file)
        if validate_state(client, state):
            print("\n==> Phase 2/4: setup (skipped, state file exists)")
            is_redeploy = True
        else:
            print("\n==> Phase 2/4: setup (state orphaned, recreating)")
            state_file.unlink()
            cmd_setup(client, cfg, state_file, repo_root)
    else:
        print("\n==> Phase 2/4: setup")
        cmd_setup(client, cfg, state_file, repo_root)

    print("\n==> Phase 3/4: env")
    cmd_env(client, cfg, state_file, repo_root, env_file_override=env_file_override)

    if is_redeploy:
        cleanup_stale_routes(load_state(state_file), cfg)
        reconcile_app_domains(client, cfg, load_state(state_file), state_file)
        reconcile_app_schedules(client, cfg, load_state(state_file), state_file)
        reconcile_app_mounts(client, cfg, load_state(state_file), state_file)

    print("\n==> Phase 4/4: trigger")
    cmd_trigger(client, cfg, state_file, redeploy=is_redeploy)


def cmd_status(client: DokployClient, state_file: Path) -> None:
    state = load_state(state_file)

    print(f"Project: {state['projectId']}")
    print()
    for name, info in state["apps"].items():
        if info.get("source") == "compose":
            comp: dict = client.get("compose.one", {"composeId": info["composeId"]})  # type: ignore[assignment]
            status = comp.get("composeStatus", "unknown")
        else:
            app: dict = client.get("application.one", {"applicationId": info["applicationId"]})  # type: ignore[assignment]
            status = app.get("applicationStatus", "unknown")
        print(f"  {name:10s}  {status}")


def _env_keys(env_blob: str | None) -> set[str]:
    """Extract variable names from a KEY=value env blob."""
    if not env_blob:
        return set()
    keys = set()
    for line in env_blob.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            keys.add(stripped.split("=", 1)[0].strip())
    return keys


def _plan_initial_setup(cfg: dict, repo_root: Path, changes: list[dict]) -> None:
    """Populate changes list for a fresh setup (no state exists)."""
    project_cfg = cfg["project"]
    changes.append(
        {
            "action": "create",
            "resource_type": "project",
            "name": project_cfg["name"],
            "parent": None,
            "attrs": {
                "name": project_cfg["name"],
                "description": project_cfg.get("description", ""),
            },
        }
    )

    for app_def in cfg["apps"]:
        name = app_def["name"]
        compose = is_compose(app_def)
        rtype = "compose" if compose else "application"
        attrs: dict = {"source": app_def.get("source", "compose")}
        if not compose:
            if app_def.get("source") == "docker":
                attrs["dockerImage"] = app_def.get("dockerImage", "")
            elif app_def.get("source") == "github":
                attrs["buildType"] = app_def.get("buildType", "dockerfile")
        changes.append(
            {
                "action": "create",
                "resource_type": rtype,
                "name": name,
                "parent": None,
                "attrs": attrs,
            }
        )

        domain_cfg = app_def.get("domain")
        if domain_cfg:
            domains = domain_cfg if isinstance(domain_cfg, list) else [domain_cfg]
            for dom in domains:
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "domain",
                        "name": dom["host"],
                        "parent": name,
                        "attrs": {
                            "host": dom["host"],
                            "port": dom["port"],
                            "https": dom.get("https", False),
                            "certificateType": dom.get("certificateType", "none"),
                        },
                    }
                )

        if not compose:
            settings_keys = {}
            for key in ("autoDeploy", "replicas"):
                if key in app_def:
                    settings_keys[key] = app_def[key]
            if settings_keys:
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "settings",
                        "name": name,
                        "parent": None,
                        "attrs": settings_keys,
                    }
                )

            for vol in app_def.get("volumes", []):
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "mount",
                        "name": f"{vol['source']} -> {vol['target']}",
                        "parent": name,
                        "attrs": {
                            "type": vol["type"],
                            "source": vol["source"],
                            "target": vol["target"],
                        },
                    }
                )

            for sched in app_def.get("schedules", []):
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "schedule",
                        "name": sched["name"],
                        "parent": name,
                        "attrs": {
                            "cronExpression": sched["cronExpression"],
                            "command": sched["command"],
                        },
                    }
                )

    env_targets = cfg["project"].get("env_targets", [])
    if env_targets:
        env_file = repo_root / ".env"
        if env_file.exists():
            raw_env = env_file.read_text()
            exclude_prefixes = get_env_excludes()
            filtered = filter_env(raw_env, exclude_prefixes)
            keys = _env_keys(filtered)
            for target_name in env_targets:
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "environment",
                        "name": target_name,
                        "parent": None,
                        "attrs": {"keys": sorted(keys)},
                    }
                )

    for app_def in cfg["apps"]:
        custom_env = app_def.get("env")
        if custom_env:
            keys = _env_keys(custom_env)
            changes.append(
                {
                    "action": "create",
                    "resource_type": "environment",
                    "name": app_def["name"],
                    "parent": None,
                    "attrs": {"keys": sorted(keys)},
                }
            )


def _plan_redeploy(
    client: "DokployClient",
    cfg: dict,
    state: dict,
    repo_root: Path,
    changes: list[dict],
) -> None:
    """Populate changes list by diffing remote state against desired config."""
    apps_by_name = {a["name"]: a for a in cfg["apps"]}
    env_targets = cfg["project"].get("env_targets", [])

    env_file = repo_root / ".env"
    filtered_env: str | None = None
    if env_targets and env_file.exists():
        raw_env = env_file.read_text()
        exclude_prefixes = get_env_excludes()
        filtered_env = filter_env(raw_env, exclude_prefixes)

    for name, app_info in state["apps"].items():
        app_def = apps_by_name.get(name)
        if app_def is None:
            continue
        compose = app_info.get("source") == "compose"

        if compose:
            remote = client.get("compose.one", {"composeId": app_info["composeId"]})
        else:
            remote = client.get(
                "application.one",
                {"applicationId": app_info["applicationId"]},
            )

        remote_env = remote.get("env") or ""

        desired_parts: list[str] = []
        if name in env_targets and filtered_env:
            resolved = resolve_refs(filtered_env, state)
            desired_parts.append(resolved)
        custom_env = apps_by_name.get(name, {}).get("env")
        if custom_env:
            resolved_custom = resolve_refs(custom_env, state)
            desired_parts.append(resolved_custom)

        desired_env = "\n".join(p.rstrip("\n") for p in desired_parts) + "\n" if desired_parts else ""

        remote_keys = _env_keys(remote_env)
        desired_keys = _env_keys(desired_env)

        if remote_keys != desired_keys:
            added = sorted(desired_keys - remote_keys)
            removed = sorted(remote_keys - desired_keys)
            changes.append(
                {
                    "action": "update",
                    "resource_type": "environment",
                    "name": name,
                    "parent": None,
                    "attrs": {"added": added, "removed": removed},
                }
            )

        domain_cfg = app_def.get("domain")
        if domain_cfg is not None or "domains" in state["apps"].get(name, {}):
            if compose:
                remote_domains = client.get("domain.byComposeId", {"composeId": app_info["composeId"]})
            else:
                remote_domains = client.get("domain.byApplicationId", {"applicationId": app_info["applicationId"]})
            if not isinstance(remote_domains, list):
                remote_domains = []

            desired_domains = domain_cfg if isinstance(domain_cfg, list) else [domain_cfg] if domain_cfg else []
            existing_by_host = {d["host"]: d for d in remote_domains}
            desired_by_host = {d["host"]: d for d in desired_domains}

            for host, dom in desired_by_host.items():
                if host in existing_by_host:
                    ex = existing_by_host[host]
                    diffs: dict = {}
                    for key in ("port", "https", "certificateType", "path", "internalPath", "stripPath"):
                        old_val = ex.get(key)
                        new_val = dom.get(key)
                        if old_val != new_val:
                            diffs[key] = (old_val, new_val)
                    if diffs:
                        changes.append(
                            {
                                "action": "update",
                                "resource_type": "domain",
                                "name": host,
                                "parent": name,
                                "attrs": diffs,
                            }
                        )
                else:
                    changes.append(
                        {
                            "action": "create",
                            "resource_type": "domain",
                            "name": host,
                            "parent": name,
                            "attrs": {
                                "host": host,
                                "port": dom.get("port"),
                                "https": dom.get("https", False),
                                "certificateType": dom.get("certificateType", "none"),
                            },
                        }
                    )

            for host in existing_by_host:
                if host not in desired_by_host:
                    changes.append(
                        {
                            "action": "destroy",
                            "resource_type": "domain",
                            "name": host,
                            "parent": name,
                            "attrs": {"host": host},
                        }
                    )

        if compose or app_def is None:
            continue

        volumes = app_def.get("volumes")
        if volumes is not None or "mounts" in state["apps"].get(name, {}):
            remote_mounts = remote.get("mounts") or []

            desired_mounts = volumes or []
            existing_by_path = {m["mountPath"]: m for m in remote_mounts}
            desired_by_path = {m["target"]: m for m in desired_mounts}

            for target, mount in desired_by_path.items():
                source = mount["source"]
                display_name = f"{source} -> {target}"
                if target in existing_by_path:
                    ex = existing_by_path[target]
                    payload = build_mount_payload(app_info["applicationId"], mount)
                    diffs: dict = {}
                    for key in ("type", "volumeName", "hostPath"):
                        old_val = ex.get(key)
                        new_val = payload.get(key)
                        if old_val != new_val:
                            diffs[key] = (old_val, new_val)
                    if diffs:
                        changes.append(
                            {
                                "action": "update",
                                "resource_type": "mount",
                                "name": display_name,
                                "parent": name,
                                "attrs": diffs,
                            }
                        )
                else:
                    changes.append(
                        {
                            "action": "create",
                            "resource_type": "mount",
                            "name": display_name,
                            "parent": name,
                            "attrs": {
                                "type": mount["type"],
                                "source": source,
                                "target": target,
                            },
                        }
                    )

            for target, ex in existing_by_path.items():
                if target not in desired_by_path:
                    ex_source = ex.get("hostPath") or ex.get("volumeName") or ""
                    changes.append(
                        {
                            "action": "destroy",
                            "resource_type": "mount",
                            "name": f"{ex_source} -> {target}",
                            "parent": name,
                            "attrs": {"mountPath": target},
                        }
                    )

        schedules = app_def.get("schedules")
        if schedules is None and "schedules" not in state["apps"].get(name, {}):
            continue

        app_id = app_info["applicationId"]
        existing = client.get(
            "schedule.list",
            {"id": app_id, "scheduleType": "application"},
        )
        if not isinstance(existing, list):
            existing = []
        desired = schedules or []

        existing_by_name = {s["name"]: s for s in existing}
        desired_by_name = {s["name"]: s for s in desired}

        for sname, sched in desired_by_name.items():
            payload = build_schedule_payload(app_id, sched)
            if sname in existing_by_name:
                ex = existing_by_name[sname]
                diffs: dict = {}
                for key in (
                    "cronExpression",
                    "command",
                    "shellType",
                    "enabled",
                    "timezone",
                ):
                    old_val = ex.get(key)
                    new_val = payload.get(key)
                    if old_val != new_val:
                        diffs[key] = (old_val, new_val)
                if diffs:
                    changes.append(
                        {
                            "action": "update",
                            "resource_type": "schedule",
                            "name": sname,
                            "parent": name,
                            "attrs": diffs,
                        }
                    )
            else:
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "schedule",
                        "name": sname,
                        "parent": name,
                        "attrs": {
                            "cronExpression": sched["cronExpression"],
                            "command": sched["command"],
                        },
                    }
                )

        for sname, ex in existing_by_name.items():
            if sname not in desired_by_name:
                changes.append(
                    {
                        "action": "destroy",
                        "resource_type": "schedule",
                        "name": sname,
                        "parent": name,
                        "attrs": {"command": ex.get("command", "")},
                    }
                )


def compute_plan(
    client: "DokployClient",
    cfg: dict,
    state_file: Path,
    repo_root: Path,
) -> list[dict]:
    """Compute the list of changes that apply would make, without executing them."""
    changes: list[dict] = []

    if not state_file.exists():
        _plan_initial_setup(cfg, repo_root, changes)
        return changes

    state = load_state(state_file)
    if not validate_state(client, state):
        _plan_initial_setup(cfg, repo_root, changes)
        return changes

    _plan_redeploy(client, cfg, state, repo_root, changes)
    return changes


def print_plan(changes: list[dict]) -> None:
    """Print a terraform-style plan output."""
    if not changes:
        print("\nNo changes. Infrastructure is up to date.")
        return

    symbols = {"create": "+", "update": "~", "destroy": "-"}

    print("\nic will perform the following actions:\n")
    print("Resource actions are indicated with the following symbols:")
    print("  + create")
    print("  ~ update")
    print("  - destroy\n")

    for change in changes:
        action = change["action"]
        sym = symbols[action]
        rtype = change["resource_type"]
        name = change["name"]
        parent = change.get("parent")
        attrs = change.get("attrs", {})

        header = f'{rtype} "{name}" ({parent})' if parent else f'{rtype} "{name}"'

        print(f"  {sym} {header} {{")

        if action == "create":
            for k, v in attrs.items():
                print(f"      + {k:20s} = {v}")
        elif action == "update":
            if rtype == "environment":
                for k in attrs.get("added", []):
                    print(f"      + {k}")
                for k in attrs.get("removed", []):
                    print(f"      - {k}")
            else:
                for k, (old, new) in attrs.items():
                    print(f"      ~ {k:20s} = {old!r} -> {new!r}")
        elif action == "destroy":
            for k, v in attrs.items():
                print(f"      - {k:20s} = {v}")

        print("    }")
        print()

    creates = sum(1 for c in changes if c["action"] == "create")
    updates = sum(1 for c in changes if c["action"] == "update")
    destroys = sum(1 for c in changes if c["action"] == "destroy")
    print(f"Plan: {creates} to create, {updates} to update, {destroys} to destroy.")


def cmd_plan(
    client: "DokployClient",
    cfg: dict,
    state_file: Path,
    repo_root: Path,
) -> None:
    """Show what changes apply would make without executing them."""
    changes = compute_plan(client, cfg, state_file, repo_root)
    print_plan(changes)


def get_ssh_config() -> dict:
    """Read SSH connection settings from environment."""
    host: str = config("DOKPLOY_SSH_HOST", default="")  # type: ignore[assignment]
    if not host:
        print("ERROR: DOKPLOY_SSH_HOST is required for exec/logs commands.")
        print("  Set it in .env or as an environment variable.")
        sys.exit(1)
    user: str = config("DOKPLOY_SSH_USER", default="root")  # type: ignore[assignment]
    port: str = config("DOKPLOY_SSH_PORT", default="22")  # type: ignore[assignment]
    return {"host": host, "user": user, "port": int(port)}


def build_docker_url(ssh_cfg: dict) -> str:
    """Build an ssh:// URL for docker-py from SSH config."""
    user = ssh_cfg.get("user", "root")
    host = ssh_cfg["host"]
    port = ssh_cfg.get("port", 22)
    if port != 22:
        return f"ssh://{user}@{host}:{port}"
    return f"ssh://{user}@{host}"


def get_docker_client(ssh_cfg: dict) -> docker.DockerClient:
    """Create a Docker client connected via SSH."""
    url = build_docker_url(ssh_cfg)
    return docker.DockerClient(base_url=url, use_ssh_client=True)


TRAEFIK_DYNAMIC_DIR = "/etc/dokploy/traefik/dynamic"


def collect_domains(cfg: dict) -> set[str]:
    """Extract all configured domain hostnames from app definitions."""
    domains: set[str] = set()
    for app_def in cfg.get("apps", []):
        domain_cfg = app_def.get("domain")
        if not domain_cfg:
            continue
        domain_list = domain_cfg if isinstance(domain_cfg, list) else [domain_cfg]
        for dom in domain_list:
            domains.add(dom["host"])
    return domains


def find_stale_app_names(current_app_names: set[str], domains: set[str], traefik_files: dict[str, str]) -> set[str]:
    """Identify app names with traefik configs routing to our domains but not in current state.

    Args:
        current_app_names: appNames from the current deployment state.
        domains: hostnames this deployment owns.
        traefik_files: mapping of appName -> content/Host rules from traefik config files.

    Returns:
        Set of stale app names to clean up.
    """
    if not domains:
        return set()
    stale: set[str] = set()
    for app_name, content in traefik_files.items():
        if app_name in current_app_names:
            continue
        if not app_name.startswith("app-"):
            continue
        for domain in domains:
            if f"Host(`{domain}`)" in content:
                stale.add(app_name)
                break
    return stale


def _ssh_exec(ssh: paramiko.SSHClient, cmd: str) -> str:
    """Run a command over SSH and return stdout."""
    _, stdout, _ = ssh.exec_command(cmd)
    return stdout.read().decode().strip()


def cleanup_stale_routes(state: dict, cfg: dict) -> None:
    """Remove traefik configs and docker services for orphaned deployments.

    Skips gracefully if all three DOKPLOY_SSH_ env vars are missing.
    """
    host: str = config("DOKPLOY_SSH_HOST", default="")  # type: ignore[assignment]
    user: str = config("DOKPLOY_SSH_USER", default="")  # type: ignore[assignment]
    port: str = config("DOKPLOY_SSH_PORT", default="")  # type: ignore[assignment]
    if not host and not user and not port:
        print("  Cleanup: skipping (DOKPLOY_SSH_* env vars not set)")
        return
    if not host:
        print("  Cleanup: skipping (DOKPLOY_SSH_HOST is required)")
        return

    domains = collect_domains(cfg)
    if not domains:
        return

    current_app_names = {info["appName"] for info in state["apps"].values()}
    ssh_user = user or "root"
    ssh_port = int(port) if port else 22

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=ssh_port, username=ssh_user)

        traefik_files: dict[str, str] = {}
        file_list = _ssh_exec(ssh, f"ls {TRAEFIK_DYNAMIC_DIR}/*.yml 2>/dev/null")
        for filepath in file_list.splitlines():
            app_name = filepath.rsplit("/", 1)[-1].removesuffix(".yml")
            content = _ssh_exec(ssh, f"cat {filepath}")
            traefik_files[app_name] = content

        stale = find_stale_app_names(current_app_names, domains, traefik_files)
        if not stale:
            return

        print(f"  Cleaning up {len(stale)} stale route(s)...")
        for app_name in sorted(stale):
            config_path = f"{TRAEFIK_DYNAMIC_DIR}/{app_name}.yml"
            _ssh_exec(ssh, f"rm -f {config_path}")
            _ssh_exec(ssh, f"docker service rm {app_name} 2>/dev/null")
            print(f"    Removed: {app_name}")
    finally:
        ssh.close()


def get_containers(client: DokployClient, app_name: str) -> list[dict]:
    """Fetch containers for an app via the Dokploy API."""
    return client.get(
        "docker.getContainersByAppNameMatch",
        params={"appName": app_name},
    )


def resolve_app_for_exec(state: dict, app_name: str | None) -> str:
    """Resolve an app name argument to a Dokploy appName from state.

    If app_name is None and only one app exists, auto-selects it.
    """
    apps = state["apps"]
    if app_name is None:
        if len(apps) == 1:
            return next(iter(apps.values()))["appName"]
        names = ", ".join(sorted(apps.keys()))
        print(f"ERROR: Multiple apps found — specify an app: {names}")
        sys.exit(1)
    if app_name not in apps:
        names = ", ".join(sorted(apps.keys()))
        print(f"ERROR: Unknown app '{app_name}'. Available: {names}")
        sys.exit(1)
    return apps[app_name]["appName"]


def select_container(containers: list[dict], exited: bool, for_exec: bool = False) -> dict:
    """Pick a container from the list.

    Default: return the most recent active container (for logs) or running container (for exec).
    With exited=True: show a numbered list and prompt for selection.
    """
    if not containers:
        print("ERROR: No containers found for this app.")
        sys.exit(1)

    if exited:
        for i, c in enumerate(containers, 1):
            print(f"  {i}) {c['name']}  ({c['containerId'][:12]})  [{c['state']}]")
        while True:
            try:
                choice = int(input("Select container: "))
                if 1 <= choice <= len(containers):
                    return containers[choice - 1]
            except (ValueError, EOFError):
                pass
            print(f"  Enter a number between 1 and {len(containers)}.")
    elif for_exec:
        running = [c for c in containers if c["state"] == "running"]
        if not running:
            print("ERROR: No running container found. Use --exited to pick from exited containers.")
            sys.exit(1)
        return running[0]
    else:
        return containers[0]


def cmd_logs(client: DokployClient, state_file: Path, app: str | None, follow: bool, tail: int, exited: bool) -> None:
    """Fetch container logs via docker-py over SSH."""
    state = load_state(state_file)
    dokploy_name = resolve_app_for_exec(state, app)
    ssh_cfg = get_ssh_config()

    containers = get_containers(client, dokploy_name)
    container_info = select_container(containers, exited=exited)
    print(
        f"Container: {container_info['name']} ({container_info['containerId'][:12]}) [{container_info['state']}]",
        file=sys.stderr,
    )

    docker_client = get_docker_client(ssh_cfg)
    try:
        container = docker_client.containers.get(container_info["containerId"])
        tail_arg = tail if tail > 0 else "all"
        if follow:
            for chunk in container.logs(stream=True, follow=True, tail=tail_arg):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
        else:
            output = container.logs(tail=tail_arg)
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
    except KeyboardInterrupt:
        pass
    finally:
        docker_client.close()


def cmd_exec(client: DokployClient, state_file: Path, app: str | None, exited: bool, command: list[str] | None) -> None:
    """Execute a command in a container via docker-py over SSH."""
    state = load_state(state_file)
    dokploy_name = resolve_app_for_exec(state, app)
    ssh_cfg = get_ssh_config()

    containers = get_containers(client, dokploy_name)
    container_info = select_container(containers, exited=exited, for_exec=True)
    print(
        f"Container: {container_info['name']} ({container_info['containerId'][:12]}) [{container_info['state']}]",
        file=sys.stderr,
    )

    docker_client = get_docker_client(ssh_cfg)
    try:
        container = docker_client.containers.get(container_info["containerId"])
        cmd = command if command else ["sh"]
        exit_code, output = container.exec_run(cmd, stdin=True, tty=True, demux=True)
        if output:
            stdout_data, stderr_data = output
            if stdout_data:
                sys.stdout.buffer.write(stdout_data)
            if stderr_data:
                sys.stderr.buffer.write(stderr_data)
        sys.exit(exit_code)
    finally:
        docker_client.close()


def cmd_clean(cfg: dict, state_file: Path) -> None:
    """Remove stale Traefik configs and orphaned Docker services."""
    state = load_state(state_file)
    print("Cleaning stale routes...")
    cleanup_stale_routes(state, cfg)
    print("Clean complete.")


def cmd_destroy(client: DokployClient, cfg: dict, state_file: Path) -> None:
    state = load_state(state_file)

    cleanup_stale_routes(state, cfg)

    project_id = state["projectId"]
    print(f"Deleting project {project_id} (cascades to all apps)...")
    client.post("project.remove", {"projectId": project_id})
    print("  Project deleted.")

    state_file.unlink(missing_ok=True)
    print("  State file removed.")
    print("\nDestroy complete.")


def cmd_import(client: DokployClient, cfg: dict, state_file: Path) -> None:
    if state_file.exists():
        print(f"ERROR: State file already exists: {state_file}")
        print("Delete the state file first if you want to re-import.")
        sys.exit(1)

    project_name = cfg["project"]["name"]
    print("Fetching projects from server...")
    projects = client.get("project.all")

    matching = [p for p in projects if p["name"] == project_name]
    if not matching:
        print(f"ERROR: No project named '{project_name}' found on the server.")
        sys.exit(1)

    project = matching[0]
    project_id = project["projectId"]
    print(f"  Found project: {project_id}")

    environments = project.get("environments", [])
    if not environments:
        print("ERROR: Project has no environments.")
        sys.exit(1)

    environment = environments[0]
    environment_id = environment["environmentId"]
    print(f"  Environment: {environment_id}")

    server_apps = {app["name"]: app for app in environment.get("applications", [])}

    config_app_names = [app_def["name"] for app_def in cfg["apps"]]
    missing = [name for name in config_app_names if name not in server_apps]
    if missing:
        print(f"ERROR: Apps not found on server: {', '.join(missing)}")
        sys.exit(1)

    state: dict = {
        "projectId": project_id,
        "environmentId": environment_id,
        "apps": {},
    }

    for name in config_app_names:
        srv = server_apps[name]
        state["apps"][name] = {
            "applicationId": srv["applicationId"],
            "appName": srv["appName"],
        }
        print(f"  {name}: id={srv['applicationId']} appName={srv['appName']}")

    save_state(state, state_file)
    print("\nImport complete!")
    print(f"  Project: {project_id}")
    for name, info in state["apps"].items():
        rid = info.get("composeId") or info.get("applicationId")
        print(f"  {name}: {rid}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dokploy deployment script — config-driven via dokploy.yml.")
    parser.add_argument(
        "--env",
        default=None,
        help="Target environment (default: DOKPLOY_ENV from .env, or 'dev')",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        type=Path,
        help="Path to .env file for push (default: DOTENV_FILE env var, or <repo>/.env)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Pre-flight checks")
    sub.add_parser("plan", help="Show what apply would change without executing")
    sub.add_parser("setup", help="Create project + apps")
    sub.add_parser("env", help="Push environment variables")
    sub.add_parser("apply", help="Full pipeline: check, setup, env, trigger")
    sub.add_parser("trigger", help="Deploy apps in wave order")
    sub.add_parser("status", help="Show deployment status")
    sub.add_parser("clean", help="Remove stale Traefik configs and orphaned Docker services")
    sub.add_parser("destroy", help="Delete project and state file")
    sub.add_parser("import", help="Import existing project from server")

    logs_parser = sub.add_parser("logs", help="View container logs via SSH")
    logs_parser.add_argument("app", nargs="?", default=None, help="App name (auto-selects if only one)")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    logs_parser.add_argument("-n", "--tail", type=int, default=100, help="Number of lines (default: 100, 0 for all)")
    logs_parser.add_argument("--exited", action="store_true", help="Pick from all containers (including exited)")

    exec_parser = sub.add_parser("exec", help="Execute command in container via SSH")
    exec_parser.add_argument("app", nargs="?", default=None, help="App name (auto-selects if only one)")
    exec_parser.add_argument("--exited", action="store_true", help="Pick from all containers (including exited)")
    exec_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (default: sh)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    if args.command == "check":
        cmd_check(Path.cwd())
        return

    env_name = args.env or config("DOKPLOY_ENV", default="dev")

    api_key: str = config("DOKPLOY_API_KEY")  # type: ignore[assignment]
    base_url: str = config("DOKPLOY_URL", default="https://dokploy.example.com")  # type: ignore[assignment]
    client = DokployClient(base_url, api_key)

    if args.command in ("logs", "exec"):
        state_file = get_state_file(Path.cwd(), env_name)
        if args.command == "logs":
            cmd_logs(client, state_file, args.app, args.follow, args.tail, args.exited)
        else:
            exec_cmd = args.cmd if args.cmd else None
            if exec_cmd and exec_cmd[0] == "--":
                exec_cmd = exec_cmd[1:]
            cmd_exec(client, state_file, args.app, args.exited, exec_cmd or None)
        return

    repo_root = find_repo_root()
    state_file = get_state_file(repo_root, env_name)

    cfg = load_config(repo_root)
    validate_env_references(cfg)
    cfg = merge_env_overrides(cfg, env_name)
    validate_config(cfg)

    match args.command:
        case "plan":
            cmd_plan(client, cfg, state_file, repo_root)
        case "setup":
            cmd_setup(client, cfg, state_file, repo_root)
        case "env":
            cmd_env(client, cfg, state_file, repo_root, env_file_override=args.env_file)
        case "apply":
            cmd_apply(repo_root, client, cfg, state_file, env_file_override=args.env_file)
        case "trigger":
            cmd_trigger(client, cfg, state_file, redeploy=True)
        case "status":
            cmd_status(client, state_file)
        case "clean":
            cmd_clean(cfg, state_file)
        case "destroy":
            cmd_destroy(client, cfg, state_file)
        case "import":
            cmd_import(client, cfg, state_file)


if __name__ == "__main__":
    main()
