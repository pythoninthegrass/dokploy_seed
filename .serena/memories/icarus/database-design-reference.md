# Database Support Implementation Reference

Based on thorough analysis of main.py (2180 lines), this document captures the exact patterns needed to add database resource management consistently with existing code.

---

## DESIGN PRINCIPLES OBSERVED IN CODEBASE

### 1. Single Responsibility per Resource Type
- Each resource (app, domain, mount, port, schedule) has dedicated helpers:
  - **build_X_payload()** - construct API payload
  - **reconcile_X()** - diff and update one resource
  - **reconcile_app_X()** - wrapper that iterates apps, calls base reconcile, saves state
  - **_plan_X()** - generate changes for plan command

### 2. State Structure Consistency
- Root: `state["projectId"]`, `state["environmentId"]`, `state["apps"]`
- Per-app: `state["apps"][name]` contains IDs + resource lookup dicts
- Resource dicts indexed by **natural key** (e.g., host for domains, mountPath for mounts)
- Each entry stores at minimum the resource ID (e.g., `{"domainId": "d-123"}`)

### 3. Idempotent Reconciliation
- Existing resources keyed by identity (host, mountPath, name, etc.)
- Compare desired vs existing by key, not by ID
- Update only if attributes differ (check each relevant field)
- Delete only resources in existing but not in desired
- Create resources in desired but not in existing

### 4. Cascading Deletion
- Delete project → cascades to all apps
- Delete app → cascades to all its resources (domains, mounts, etc.)
- No per-resource pre-deletion required (Dokploy handles cascade)
- Only delete state file at end

### 5. Plan Command Integration
- **_plan_initial_setup()**: Assume clean state, list all creates
- **_plan_redeploy()**: Fetch each app from remote, diff attributes, return list of changes
- Change object format: `{action, resource_type, name, parent, attrs}`
- Parent = app name for child resources
- Attrs = create attrs OR diffs tuple dict OR deleted attr dict

---

## EXACT RECONCILIATION PATTERN

### Model: reconcile_ports() (lines 492-531)

```python
def reconcile_ports(
    client: DokployClient,
    app_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    # 1. INDEX EXISTING AND DESIRED BY NATURAL KEY
    existing_by_port = {p["publishedPort"]: p for p in existing}
    desired_by_port = {p["publishedPort"]: p for p in desired}
    
    result_state = {}
    
    # 2. ITERATE DESIRED, CREATE OR UPDATE
    for pub_port, port in desired_by_port.items():
        payload = build_port_payload(app_id, port)
        if pub_port in existing_by_port:
            ex = existing_by_port[pub_port]
            port_id = ex["portId"]
            # CHECK IF UPDATE NEEDED
            needs_update = any(
                payload.get(key) != ex.get(key) 
                for key in ("targetPort", "protocol", "publishMode")
            )
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
            # CREATE NEW
            resp = client.post("port.create", payload)
            result_state[pub_port] = {"portId": resp["portId"]}
    
    # 3. DELETE REMOVED
    for pub_port, ex in existing_by_port.items():
        if pub_port not in desired_by_port:
            client.post("port.delete", {"portId": ex["portId"]})
    
    return result_state
```

### Key Implementation Details:
1. **Payload construction** happens before existence check (used in both create and update)
2. **Update check** compares specific keys (not whole payload)
3. **Update payload** is minimal: only ID + fields that changed (portId, not applicationId)
4. **Response handling**: Extract ID from response, store in result_state
5. **Return value**: Dict mapping natural-key → {"id": ...} for state storage

### For Databases, Apply This:
- Natural key = database name (or name+type if multiple types)
- Attributes to compare: engine, version, storage, backups, etc.
- Index by: `{db["name"]: db for db in existing}`
- Build payload before checking existence
- Update endpoint likely: `database.update` with databaseId + changed fields
- Return: `{name: {"databaseId": ...}}`

---

## EXACT APP WRAPPER PATTERN

### Model: reconcile_app_ports() (lines 534-557)

```python
def reconcile_app_ports(
    client: DokployClient,
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    changed = False
    for app_def in cfg.get("apps", []):
        if is_compose(app_def):
            continue
        ports = app_def.get("ports")
        name = app_def["name"]
        # SKIP IF NO CONFIG AND NO PRIOR STATE
        if ports is None and "ports" not in state["apps"].get(name, {}):
            continue
        # GET APP ID FROM STATE
        app_id = state["apps"][name]["applicationId"]
        # FETCH REMOTE
        remote = client.get("application.one", {"applicationId": app_id})
        existing = remote.get("ports") or []
        desired = ports or []
        # RECONCILE
        new_state = reconcile_ports(client, app_id, existing, desired)
        # UPDATE STATE
        state["apps"][name]["ports"] = new_state
        changed = True
    # SAVE ONCE IF ANYTHING CHANGED
    if changed:
        save_state(state, state_file)
```

### Key Implementation Details:
1. **Iterate over apps** in config (source of truth)
2. **Skip if**: No config AND no prior state (resource was never defined)
3. **Get app ID** from state (assumes app exists)
4. **Fetch remote**: Use client.get() to fetch app details, extract resource list
5. **Extract lists**: `existing = remote.get("ports") or []` handles null
6. **Call base reconcile** with both lists
7. **Update state dict** with returned mapping
8. **Save state once** at end if anything changed (not per-app)

### For Databases, Apply This:
- Iterate: `for db_def in cfg.get("databases", [])`
- No source type check (not compose-specific)
- Skip if: No config AND "databases" not in state
- Get ID: `db_id = state["databases"][name]["databaseId"]` (if top-level)
- Fetch remote: Likely `client.get("database.byProjectId", {"projectId": project_id})`
  - Filter to specific database in response
- Call base reconcile: `reconcile_databases(...)`
- Update state: `state["databases"][name] = new_state`
- Save once at end

---

## EXACT PLAN CHANGES PATTERN

### Model: Ports in _plan_redeploy() (lines 1553-1608)

```python
ports_cfg = app_def.get("ports")
if ports_cfg is not None or "ports" in state["apps"].get(name, {}):
    remote_ports = remote.get("ports") or []
    
    desired_ports = ports_cfg or []
    existing_by_pub = {p["publishedPort"]: p for p in remote_ports}
    desired_by_pub = {p["publishedPort"]: p for p in desired_ports}
    
    # CREATE OR UPDATE
    for pub_port, port in desired_by_pub.items():
        payload = build_port_payload(app_info["applicationId"], port)
        display_name = f"{pub_port} -> {port['targetPort']}"
        if pub_port in existing_by_pub:
            ex = existing_by_pub[pub_port]
            diffs: dict = {}
            # COMPARE ATTRIBUTES
            for key in ("targetPort", "protocol", "publishMode"):
                old_val = ex.get(key)
                new_val = payload.get(key)
                if old_val != new_val:
                    diffs[key] = (old_val, new_val)
            if diffs:
                changes.append({
                    "action": "update",
                    "resource_type": "port",
                    "name": display_name,
                    "parent": name,
                    "attrs": diffs,  # {key: (old, new)}
                })
        else:
            changes.append({
                "action": "create",
                "resource_type": "port",
                "name": display_name,
                "parent": name,
                "attrs": {
                    "publishedPort": pub_port,
                    "targetPort": port.get("targetPort"),
                    "protocol": port.get("protocol", "tcp"),
                    "publishMode": port.get("publishMode", "ingress"),
                },
            })
    
    # DELETE
    for pub_port, ex in existing_by_pub.items():
        if pub_port not in desired_by_pub:
            changes.append({
                "action": "destroy",
                "resource_type": "port",
                "name": f"{pub_port} -> {ex.get('targetPort', '?')}",
                "parent": name,
                "attrs": {"publishedPort": pub_port},
            })
```

### Key Implementation Details:
1. **Conditional block**: `if cfg is not None or prior state exists`
2. **Index both**: existing_by_key and desired_by_key
3. **For creates**: Include all desired attributes in attrs dict
4. **For updates**: Build payload, compare each relevant key, store (old, new) tuples
5. **For deletes**: Just name/key + minimal identifying attrs
6. **Display names**: Descriptive (e.g., "80 -> 8080" not just "80")
7. **Parent**: Always set to app_name for child resources

### For Databases in _plan_redeploy():
```python
databases_cfg = cfg.get("databases", [])
if databases_cfg or "databases" in state:
    remote_databases = ... # fetch from remote
    desired_by_name = {d["name"]: d for d in databases_cfg}
    existing_by_name = {d["name"]: d for d in remote_databases}
    
    # Similar create/update/delete loop
    # Attrs: engine, version, storage, backups, etc.
    # Parent: project (or root if top-level)
```

---

## EXACT STATE STRUCTURE FOR NEW RESOURCE

### Example: Current Ports State (from setup, line 1016)
```python
state["apps"][name]["ports"] = {}
for port in ports:
    resp = client.post("port.create", port_payload)
    state["apps"][name]["ports"][port["publishedPort"]] = {"portId": resp["portId"]}
```

### Result:
```json
{
  "apps": {
    "django": {
      "applicationId": "app-123",
      "appName": "app-django",
      "ports": {
        "8080": {"portId": "p-456"},
        "9000": {"portId": "p-789"}
      }
    }
  }
}
```

### For Databases, Decide:
**Option 1: Top-level (parallel to apps)**
```json
{
  "projectId": "proj-123",
  "environmentId": "env-456",
  "apps": { ... },
  "databases": {
    "postgres": {"databaseId": "db-789", "engine": "postgres", ...},
    "redis": {"databaseId": "db-101", "engine": "redis", ...}
  }
}
```

**Option 2: Nested in app** (if db is tied to specific app)
```json
{
  "apps": {
    "django": {
      "applicationId": "app-123",
      "databases": {
        "postgres": {"databaseId": "db-789"}
      }
    }
  }
}
```

**Option 3: Nested in app, indexed by name** (hybrid)
```json
{
  "apps": {
    "django": {
      "applicationId": "app-123",
      "databases": {
        "postgres-main": {"databaseId": "db-789", "engine": "postgres"},
        "redis-cache": {"databaseId": "db-101", "engine": "redis"}
      }
    }
  }
}
```

**Recommendation**: Option 1 (top-level) because:
- Databases often project-wide, not per-app
- Simpler state structure
- Simpler config structure (one `databases:` block)
- Easier plan command (one section, not per-app)
- Matches project lifecycle (create with project, delete with project)

---

## BUILD PAYLOAD EXAMPLES FROM CODEBASE

### Example 1: build_port_payload (lines 351-359) - Simple
```python
def build_port_payload(app_id: str, port: dict) -> dict:
    return {
        "applicationId": app_id,
        "publishedPort": port["publishedPort"],
        "targetPort": port["targetPort"],
        "protocol": port.get("protocol", "tcp"),
        "publishMode": port.get("publishMode", "ingress"),
    }
```
- Takes app_id (context), port spec (from config)
- Adds resource owner + defaults
- Returns flat dict ready for API

### Example 2: build_mount_payload (lines 336-348) - Conditional
```python
def build_mount_payload(app_id: str, mount: dict) -> dict:
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
```
- Conditional fields based on mount type
- Maps config keys to API keys (target → mountPath)

### Example 3: build_domain_payload (lines 298-321) - Both Conditional and Optional
```python
def build_domain_payload(resource_id: str, dom: dict, *, compose: bool = False) -> dict:
    if compose:
        payload = {
            "composeId": resource_id,
            "domainType": "compose",
            "serviceName": dom["serviceName"],
        }
    else:
        payload = {"applicationId": resource_id}
    payload.update({
        "host": dom["host"],
        "port": dom["port"],
        "https": dom["https"],
        "certificateType": dom["certificateType"],
    })
    # OPTIONAL FIELDS
    for key in ("path", "internalPath", "stripPath"):
        if key in dom:
            payload[key] = dom[key]
    return payload
```
- Conditional base structure (compose vs app)
- Common fields added to both
- Optional fields only if present

### For Database Payload:
```python
def build_database_payload(project_id: str, db: dict) -> dict:
    payload = {
        "projectId": project_id,
        "name": db["name"],
        "engine": db["engine"],  # postgres, mysql, mongodb, redis, etc.
        "version": db.get("version", "latest"),
    }
    # Optional features
    for key in ("storage", "password", "backupRetention", "replicationEnabled"):
        if key in db:
            payload[key] = db[key]
    return payload
```

---

## ERROR HANDLING PATTERNS

### Silent Handling (from _plan_redeploy, line 1438)
```python
if not isinstance(remote_domains, list):
    remote_domains = []
```
- API returns non-list on error/no data → treat as empty
- No exception, just continue

### Early Exit on Missing State (from cmd_destroy)
```python
state = load_state(state_file)  # Exits if missing
```
- load_state() calls sys.exit(1) if file not found

### Cascading Failure (from cmd_setup)
```python
save_state(state, state_file, quiet=True)  # Line 904 - EARLY SAVE
# ... continue setup ...
save_state(state, state_file)  # Line 1035 - FINAL SAVE
```
- Early save allows destroy to clean up if later steps fail
- destroy only needs projectId, which is saved first

---

## ENVIRONMENT CONFIG INTEGRATION

### How Apps Reference Config
```python
for app_def in cfg["apps"]:
    name = app_def["name"]
    # app_def has: source, name, domain, volumes, ports, schedules, env, etc.
    # Each is optional
    if is_compose(app_def):
        # compose-specific setup
    else:
        # application setup
```

### For Databases
YAML config structure would be:
```yaml
databases:
  - name: postgres-main
    engine: postgres
    version: "15"
    storage: 50Gb
    password: ${DB_PASSWORD}
  - name: redis-cache
    engine: redis
    version: "7"
```

Load: `databases = cfg.get("databases", [])`
Iterate: `for db_def in databases`
Store state after create: `state["databases"][name] = {"databaseId": id, ...}`

---

## COMPLETE MINIMAL IMPLEMENTATION SKELETON

```python
# 1. BUILD PAYLOAD
def build_database_payload(project_id: str, db: dict) -> dict:
    payload = {
        "projectId": project_id,
        "name": db["name"],
        "engine": db["engine"],
        "version": db.get("version", "latest"),
    }
    for key in ("storage", "password"):
        if key in db:
            payload[key] = db[key]
    return payload

# 2. BASE RECONCILE
def reconcile_databases(
    client: DokployClient,
    project_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    existing_by_name = {d["name"]: d for d in existing}
    desired_by_name = {d["name"]: d for d in desired}
    result_state = {}
    
    for name, db in desired_by_name.items():
        payload = build_database_payload(project_id, db)
        if name in existing_by_name:
            ex = existing_by_name[name]
            db_id = ex["databaseId"]
            needs_update = any(
                payload.get(key) != ex.get(key)
                for key in ("version", "storage")
            )
            if needs_update:
                update_payload = {**payload, "databaseId": db_id}
                update_payload.pop("projectId", None)
                client.post("database.update", update_payload)
            result_state[name] = {"databaseId": db_id}
        else:
            resp = client.post("database.create", payload)
            result_state[name] = {"databaseId": resp["databaseId"]}
    
    for name, ex in existing_by_name.items():
        if name not in desired_by_name:
            client.post("database.delete", {"databaseId": ex["databaseId"]})
    
    return result_state

# 3. APP WRAPPER (if nested) OR PROJECT WRAPPER (if top-level)
def reconcile_project_databases(
    client: DokployClient,
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    databases = cfg.get("databases", [])
    project_id = state["projectId"]
    
    if not databases and "databases" not in state:
        return
    
    # Fetch all databases for project
    all_dbs = client.get("database.byProjectId", {"projectId": project_id}) or []
    existing = all_dbs
    desired = databases
    
    new_state = reconcile_databases(client, project_id, existing, desired)
    state["databases"] = new_state
    save_state(state, state_file)

# 4. IN SETUP (after apps created)
def cmd_setup(...):
    # ... existing app setup ...
    
    # DATABASES
    for db_def in cfg.get("databases", []):
        name = db_def["name"]
        print(f"Creating database: {name}...")
        db_payload = build_database_payload(project_id, db_def)
        resp = client.post("database.create", db_payload)
        state["databases"][name] = {"databaseId": resp["databaseId"]}
    
    save_state(state, state_file)

# 5. IN APPLY (redeploy reconciliation)
def cmd_apply(...):
    # ... existing setup + env ...
    if is_redeploy:
        # ... existing reconciliations ...
        reconcile_project_databases(client, cfg, state, state_file)
    # ... trigger ...

# 6. IN PLAN (_plan_initial_setup)
def _plan_initial_setup(cfg, repo_root, changes):
    # ... existing ...
    
    for db_def in cfg.get("databases", []):
        changes.append({
            "action": "create",
            "resource_type": "database",
            "name": db_def["name"],
            "parent": None,
            "attrs": {
                "engine": db_def["engine"],
                "version": db_def.get("version", "latest"),
            },
        })

# 7. IN PLAN (_plan_redeploy)
def _plan_redeploy(client, cfg, state, repo_root, changes):
    # ... existing ...
    
    databases_cfg = cfg.get("databases", [])
    if databases_cfg or "databases" in state:
        remote_dbs = client.get("database.byProjectId", {"projectId": state["projectId"]}) or []
        desired_by_name = {d["name"]: d for d in databases_cfg}
        existing_by_name = {d["name"]: d for d in remote_dbs}
        
        for name, db in desired_by_name.items():
            if name in existing_by_name:
                ex = existing_by_name[name]
                diffs = {}
                for key in ("version", "storage"):
                    if db.get(key) != ex.get(key):
                        diffs[key] = (ex.get(key), db.get(key))
                if diffs:
                    changes.append({
                        "action": "update",
                        "resource_type": "database",
                        "name": name,
                        "parent": None,
                        "attrs": diffs,
                    })
            else:
                changes.append({
                    "action": "create",
                    "resource_type": "database",
                    "name": name,
                    "parent": None,
                    "attrs": {
                        "engine": db["engine"],
                        "version": db.get("version", "latest"),
                    },
                })
        
        for name, ex in existing_by_name.items():
            if name not in desired_by_name:
                changes.append({
                    "action": "destroy",
                    "resource_type": "database",
                    "name": name,
                    "parent": None,
                    "attrs": {"engine": ex.get("engine", "")},
                })
```

---

## CHECKLIST FOR ADDING DATABASE SUPPORT

- [ ] Update `dokploy.yml.example` with `databases:` block
- [ ] Update schema (`schemas/dokploy.schema.json`) with database properties
- [ ] Add `build_database_payload()` function
- [ ] Add `reconcile_databases()` function (base, non-iterating)
- [ ] Add wrapper function (e.g., `reconcile_project_databases()` or nested per-app)
- [ ] Update `cmd_setup()` to create databases and initialize state
- [ ] Update `cmd_apply()` to call wrapper on redeploy
- [ ] Update `_plan_initial_setup()` to include database creates
- [ ] Update `_plan_redeploy()` to diff databases against desired config
- [ ] Test with multiple databases of same and different engines
- [ ] Test reconciliation (update version/storage)
- [ ] Test deletion (remove from config, verify plan shows destroy)
- [ ] Test plan command shows databases
- [ ] Test state file contains database IDs
- [ ] Update docs with database section
- [ ] Update example configs if adding databases as examples

---

## KEY APIS LIKELY NEEDED (from pattern analysis)

Based on port/mount/schedule patterns, database APIs would likely be:
- `database.create` - POST with project_id, name, engine, version, etc.
- `database.update` - POST with databaseId + changed fields
- `database.delete` - POST with databaseId
- `database.byProjectId` - GET to list databases for a project
- `database.one` - GET to fetch single database details

(Verify exact endpoint names against OpenAPI schema)
