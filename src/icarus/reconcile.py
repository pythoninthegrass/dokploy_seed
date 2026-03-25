from __future__ import annotations

from icarus.client import save_state
from icarus.env import resolve_refs
from icarus.payloads import (
    build_app_settings_payload,
    build_domain_payload,
    build_mount_payload,
    build_port_payload,
    build_redirect_payload,
    build_schedule_payload,
    is_compose,
)
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from icarus.client import DokployClient


def reconcile_schedules(
    client: DokployClient,
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
    client: DokployClient,
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
    client: DokployClient,
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


def reconcile_ports(
    client: DokployClient,
    app_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    """Reconcile ports: update existing by publishedPort, create new, delete removed.

    Returns a dict mapping publishedPort -> {"portId": ...} for state storage.
    """
    existing_by_port = {p["publishedPort"]: p for p in existing}
    desired_by_port = {p["publishedPort"]: p for p in desired}

    result_state = {}

    for pub_port, port in desired_by_port.items():
        payload = build_port_payload(app_id, port)
        if pub_port in existing_by_port:
            ex = existing_by_port[pub_port]
            port_id = ex["portId"]
            needs_update = any(payload.get(key) != ex.get(key) for key in ("targetPort", "protocol", "publishMode"))
            if needs_update:
                update_payload = {
                    "portId": port_id,
                    "publishedPort": payload["publishedPort"],
                    "targetPort": payload["targetPort"],
                    "protocol": payload["protocol"],
                    "publishMode": payload["publishMode"],
                }
                client.post("port.update", update_payload)
            result_state[pub_port] = {"portId": port_id}
        else:
            resp = client.post("port.create", payload)
            result_state[pub_port] = {"portId": resp["portId"]}

    for pub_port, ex in existing_by_port.items():
        if pub_port not in desired_by_port:
            client.post("port.delete", {"portId": ex["portId"]})

    return result_state


def reconcile_app_ports(
    client: DokployClient,
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile ports for all apps on redeploy."""
    changed = False
    for app_def in cfg.get("apps", []):
        if is_compose(app_def):
            continue
        ports = app_def.get("ports")
        name = app_def["name"]
        if ports is None and "ports" not in state["apps"].get(name, {}):
            continue
        app_id = state["apps"][name]["applicationId"]
        remote = client.get("application.one", {"applicationId": app_id})
        existing = remote.get("ports") or []
        desired = ports or []
        new_state = reconcile_ports(client, app_id, existing, desired)
        state["apps"][name]["ports"] = new_state
        changed = True
    if changed:
        save_state(state, state_file)


def reconcile_redirects(
    client: DokployClient,
    app_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    """Reconcile redirects: update existing by regex, create new, delete removed.

    Returns a dict mapping regex -> {"redirectId": ...} for state storage.
    """
    existing_by_regex = {r["regex"]: r for r in existing}
    desired_by_regex = {r["regex"]: r for r in desired}

    result_state = {}

    for regex, redir in desired_by_regex.items():
        payload = build_redirect_payload(app_id, redir)
        if regex in existing_by_regex:
            ex = existing_by_regex[regex]
            redirect_id = ex["redirectId"]
            needs_update = any(payload.get(key) != ex.get(key) for key in ("replacement", "permanent"))
            if needs_update:
                update_payload = {
                    "redirectId": redirect_id,
                    "regex": payload["regex"],
                    "replacement": payload["replacement"],
                    "permanent": payload["permanent"],
                }
                client.post("redirects.update", update_payload)
            result_state[regex] = {"redirectId": redirect_id}
        else:
            resp = client.post("redirects.create", payload)
            result_state[regex] = {"redirectId": resp["redirectId"]}

    for regex, ex in existing_by_regex.items():
        if regex not in desired_by_regex:
            client.post("redirects.delete", {"redirectId": ex["redirectId"]})

    return result_state


def reconcile_app_redirects(
    client: DokployClient,
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile redirects for all apps on redeploy."""
    changed = False
    for app_def in cfg.get("apps", []):
        if is_compose(app_def):
            continue
        redirects = app_def.get("redirects")
        name = app_def["name"]
        if redirects is None and "redirects" not in state["apps"].get(name, {}):
            continue
        app_id = state["apps"][name]["applicationId"]
        remote = client.get("application.one", {"applicationId": app_id})
        existing = remote.get("redirects") or []
        desired = redirects or []
        new_state = reconcile_redirects(client, app_id, existing, desired)
        state["apps"][name]["redirects"] = new_state
        changed = True
    if changed:
        save_state(state, state_file)


def reconcile_app_mounts(
    client: DokployClient,
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
    client: DokployClient,
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
    client: DokployClient,
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


def reconcile_app_settings(
    client: DokployClient,
    cfg: dict,
    state: dict,
) -> None:
    """Reconcile app settings (command, replicas, autoDeploy) on redeploy."""
    for app_def in cfg.get("apps", []):
        if is_compose(app_def):
            continue
        name = app_def["name"]
        app_id = state["apps"][name]["applicationId"]

        settings_payload = build_app_settings_payload(app_id, app_def)
        command = app_def.get("command")
        has_settings = settings_payload is not None or command is not None
        if not has_settings:
            continue

        remote = client.get("application.one", {"applicationId": app_id})

        update_payload: dict = {"applicationId": app_id}
        changed = False

        if command is not None and remote.get("command") != command:
            resolved = resolve_refs(command, state)
            update_payload["command"] = resolved
            changed = True

        for key in ("replicas", "autoDeploy"):
            if key in app_def and remote.get(key) != app_def[key]:
                update_payload[key] = app_def[key]
                changed = True

        if changed:
            client.post("application.update", update_payload)
