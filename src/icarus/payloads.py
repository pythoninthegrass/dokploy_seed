from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from icarus.client import DokployClient

DATABASE_TYPES = {"postgres", "mysql", "mariadb", "mongo", "redis"}

DATABASE_DEFAULTS = {
    "postgres": "postgres:16",
    "mysql": "mysql:8",
    "mariadb": "mariadb:11",
    "mongo": "mongo:7",
    "redis": "redis:7",
}


def database_endpoint(db_type: str, action: str) -> str:
    """Return the Dokploy API endpoint for a database operation."""
    return f"{db_type}.{action}"


def database_id_key(db_type: str) -> str:
    """Return the ID field name for a database type."""
    return f"{db_type}Id"


def build_database_create_payload(name: str, db_def: dict, environment_id: str) -> dict:
    """Build the API payload for creating a database resource."""
    db_type = db_def["type"]
    payload: dict = {
        "name": name,
        "environmentId": environment_id,
        "dockerImage": db_def.get("dockerImage", DATABASE_DEFAULTS[db_type]),
        "databasePassword": db_def["databasePassword"],
    }

    if db_def.get("description"):
        payload["description"] = db_def["description"]

    if db_type in ("postgres", "mysql", "mariadb"):
        payload["databaseName"] = db_def["databaseName"]
        payload["databaseUser"] = db_def["databaseUser"]

    if db_type in ("mysql", "mariadb"):
        payload["databaseRootPassword"] = db_def["databaseRootPassword"]

    if db_type == "mongo":
        payload["databaseUser"] = db_def["databaseUser"]

    return payload


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


def resolve_github_provider(client: DokployClient, providers: list[dict], owner: str) -> str:
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


def build_port_payload(app_id: str, port: dict) -> dict:
    """Build payload for port.create."""
    return {
        "applicationId": app_id,
        "publishedPort": port["publishedPort"],
        "targetPort": port["targetPort"],
        "protocol": port.get("protocol", "tcp"),
        "publishMode": port.get("publishMode", "ingress"),
    }


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
