# Integration Points for Database Support

This document maps exactly where database code needs to be inserted into main.py.

---

## 1. NEW HELPER FUNCTIONS (Add after existing payload builders, before reconciliation)

### Location: After line 375 (after build_schedule_payload)

```python
def build_database_payload(project_id: str, db: dict) -> dict:
    """Build payload for database.create/update."""
    payload = {
        "projectId": project_id,
        "name": db["name"],
        "engine": db["engine"],
        "version": db.get("version", "latest"),
    }
    for key in ("storage", "password", "backupRetention", "replicationEnabled"):
        if key in db:
            payload[key] = db[key]
    return payload
```

---

## 2. BASE RECONCILIATION FUNCTION (Add after line 531, after reconcile_ports)

```python
def reconcile_databases(
    client: DokployClient,
    project_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    """Reconcile databases: update existing by name, create new, delete removed.

    Returns a dict mapping database name -> {"databaseId": ...} for state storage.
    """
    existing_by_name = {d["name"]: d for d in existing}
    desired_by_name = {d["name"]: d for d in desired}

    result_state = {}

    for name, db in desired_by_name.items():
        payload = build_database_payload(project_id, db)
        if name in existing_by_name:
            ex = existing_by_name[name]
            database_id = ex["databaseId"]
            needs_update = any(
                payload.get(key) != ex.get(key)
                for key in ("version", "storage", "password", "backupRetention", "replicationEnabled")
            )
            if needs_update:
                update_payload = {**payload, "databaseId": database_id}
                update_payload.pop("projectId", None)
                client.post("database.update", update_payload)
            result_state[name] = {"databaseId": database_id}
        else:
            resp = client.post("database.create", payload)
            result_state[name] = {"databaseId": resp["databaseId"]}

    for name, ex in existing_by_name.items():
        if name not in desired_by_name:
            client.post("database.delete", {"databaseId": ex["databaseId"]})

    return result_state
```

---

## 3. APP WRAPPER FUNCTION (Add after line 557, after reconcile_app_ports)

```python
def reconcile_project_databases(
    client: DokployClient,
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile databases for the project on redeploy."""
    databases = cfg.get("databases", [])
    if not databases and "databases" not in state:
        return

    project_id = state["projectId"]
    
    # Fetch existing databases for this project
    all_dbs = client.get("database.byProjectId", {"projectId": project_id})
    if not isinstance(all_dbs, list):
        all_dbs = []
    
    desired = databases
    new_state = reconcile_databases(client, project_id, all_dbs, desired)
    state["databases"] = new_state
    save_state(state, state_file)
```

---

## 4. SETUP COMMAND - DATABASE CREATION (Line ~1018-1032)

### Location: After schedules (line 1032), add:

```python
    # 11. Databases (project-level, created after apps)
    databases = cfg.get("databases", [])
    if databases:
        state["databases"] = {}
        for db_def in databases:
            name = db_def["name"]
            print(f"Creating database: {name}...")
            db_payload = build_database_payload(project_id, db_def)
            resp = client.post("database.create", db_payload)
            state["databases"][name] = {"databaseId": resp["databaseId"]}
            print(f"  {name}: id={resp['databaseId']}")
```

### Also update initial state creation (line 864-868):

Change:
```python
state: dict = {
    "projectId": project_id,
    "environmentId": environment_id,
    "apps": {},
}
```

To:
```python
state: dict = {
    "projectId": project_id,
    "environmentId": environment_id,
    "apps": {},
    "databases": {},  # Add this line
}
```

---

## 5. APPLY COMMAND - REDEPLOY RECONCILIATION (Line 1181-1186)

### Location: Change this block:

Current (lines 1181-1186):
```python
    if is_redeploy:
        cleanup_stale_routes(load_state(state_file), cfg)
        reconcile_app_domains(client, cfg, load_state(state_file), state_file)
        reconcile_app_schedules(client, cfg, load_state(state_file), state_file)
        reconcile_app_mounts(client, cfg, load_state(state_file), state_file)
        reconcile_app_ports(client, cfg, load_state(state_file), state_file)
```

To:
```python
    if is_redeploy:
        cleanup_stale_routes(load_state(state_file), cfg)
        reconcile_project_databases(client, cfg, load_state(state_file), state_file)
        reconcile_app_domains(client, cfg, load_state(state_file), state_file)
        reconcile_app_schedules(client, cfg, load_state(state_file), state_file)
        reconcile_app_mounts(client, cfg, load_state(state_file), state_file)
        reconcile_app_ports(client, cfg, load_state(state_file), state_file)
```

**Note**: Databases must be reconciled before apps (in case app needs to connect to them).

---

## 6. PLAN COMMAND - INITIAL SETUP (Line 1336, after schedules)

### Location: In `_plan_initial_setup()`, after schedules section (line 1335), add:

```python
    # Databases
    for db_def in cfg.get("databases", []):
        changes.append(
            {
                "action": "create",
                "resource_type": "database",
                "name": db_def["name"],
                "parent": None,
                "attrs": {
                    "engine": db_def["engine"],
                    "version": db_def.get("version", "latest"),
                },
            }
        )
```

---

## 7. PLAN COMMAND - REDEPLOY (Line 1676, after schedules)

### Location: In `_plan_redeploy()`, after schedules section (line 1676), add:

```python
    # Databases
    databases_cfg = cfg.get("databases", [])
    if databases_cfg or "databases" in state:
        remote_dbs = client.get("database.byProjectId", {"projectId": state["projectId"]})
        if not isinstance(remote_dbs, list):
            remote_dbs = []

        desired_by_name = {d["name"]: d for d in databases_cfg}
        existing_by_name = {d["name"]: d for d in remote_dbs}

        for name, db in desired_by_name.items():
            if name in existing_by_name:
                ex = existing_by_name[name]
                diffs: dict = {}
                for key in ("version", "storage", "password", "backupRetention", "replicationEnabled"):
                    old_val = ex.get(key)
                    new_val = db.get(key)
                    if old_val != new_val:
                        diffs[key] = (old_val, new_val)
                if diffs:
                    changes.append(
                        {
                            "action": "update",
                            "resource_type": "database",
                            "name": name,
                            "parent": None,
                            "attrs": diffs,
                        }
                    )
            else:
                changes.append(
                    {
                        "action": "create",
                        "resource_type": "database",
                        "name": name,
                        "parent": None,
                        "attrs": {
                            "engine": db["engine"],
                            "version": db.get("version", "latest"),
                        },
                    }
                )

        for name, ex in existing_by_name.items():
            if name not in desired_by_name:
                changes.append(
                    {
                        "action": "destroy",
                        "resource_type": "database",
                        "name": name,
                        "parent": None,
                        "attrs": {"engine": ex.get("engine", "")},
                    }
                )
```

---

## 8. STATUS COMMAND (Optional, line 1192-1204)

### Location: In `cmd_status()`, can optionally add database status:

After app status loop, add:
```python
    if "databases" in state:
        print()
        for name, info in state.get("databases", {}).items():
            db = client.get("database.one", {"databaseId": info["databaseId"]})
            status = db.get("databaseStatus", "unknown")
            print(f"  {name:10s}  {status}  (database)")
```

(Only if database.one endpoint exists and databaseStatus field is returned)

---

## SUMMARY OF CHANGES BY COMMAND

| Command | Change | Location | Type |
|---------|--------|----------|------|
| setup | Add database creation | Before final save (line 1032+) | Addition |
| apply | Call reconcile on redeploy | Line 1181-1186 | Modification |
| plan | Add initial setup changes | Line 1336+ | Addition |
| plan | Add redeploy diffs | Line 1676+ | Addition |
| status | Show database status | Line 1204+ | Optional |

---

## INTEGRATION CHECKLIST

- [ ] Add build_database_payload function
- [ ] Add reconcile_databases function
- [ ] Add reconcile_project_databases function
- [ ] Update state initialization to include "databases": {}
- [ ] Add database creation loop in cmd_setup
- [ ] Update reconciliation call in cmd_apply
- [ ] Add databases to _plan_initial_setup
- [ ] Add databases to _plan_redeploy
- [ ] Update cmd_status (optional)
- [ ] Test full workflow: setup → apply → plan → destroy
- [ ] Update dokploy.yml.example
- [ ] Update JSON schema
- [ ] Update documentation

---

## FUNCTION SIGNATURES FOR REFERENCE

```python
def build_database_payload(project_id: str, db: dict) -> dict:
    """Transform database config to API payload."""

def reconcile_databases(
    client: DokployClient,
    project_id: str,
    existing: list[dict],
    desired: list[dict],
) -> dict:
    """Reconcile project databases: create/update/delete as needed."""

def reconcile_project_databases(
    client: DokployClient,
    cfg: dict,
    state: dict,
    state_file: Path,
) -> None:
    """Reconcile all project databases on redeploy."""
```

---

## EXACT API CALL PATTERNS

Based on existing code:

**Create**:
```python
resp = client.post("database.create", build_database_payload(project_id, db_def))
db_id = resp["databaseId"]
```

**Update**:
```python
update_payload = {**payload, "databaseId": database_id}
update_payload.pop("projectId", None)  # Remove context fields
client.post("database.update", update_payload)
```

**Delete**:
```python
client.post("database.delete", {"databaseId": database_id})
```

**List**:
```python
all_dbs = client.get("database.byProjectId", {"projectId": project_id})
```

**Fetch One** (optional):
```python
db = client.get("database.one", {"databaseId": database_id})
```

---

## STATE STRUCTURE AFTER SETUP

```json
{
  "projectId": "proj-abc123",
  "environmentId": "env-def456",
  "apps": {
    "django": {
      "applicationId": "app-ghi789",
      "appName": "app-django"
    }
  },
  "databases": {
    "postgres-main": {
      "databaseId": "db-jkl012"
    },
    "redis-cache": {
      "databaseId": "db-mno345"
    }
  }
}
```

---

## VALIDATION & ERROR HANDLING

Inherited from existing patterns:
1. Config validation happens in cmd_setup before any API calls
2. API errors (via raise_for_status) terminate the command
3. State is saved early (after project create) to enable partial cleanup
4. Reconciliation handles non-list responses gracefully
5. Missing database section in config is handled (defaults to empty list)

No new error handling needed—use existing patterns.

---

## DOKPLOY.YML.EXAMPLE UPDATE

Add to dokploy.yml.example (new section after apps):

```yaml
# Optional: Project-wide databases
databases:
  - name: postgres-main
    engine: postgres
    version: "15"
    storage: "50Gb"
    password: ${DB_PASSWORD}  # Can use env var references
    
  - name: redis-cache
    engine: redis
    version: "7"
```

---

## SCHEMA UPDATE (schemas/dokploy.schema.json)

Add to properties:

```json
{
  "databases": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "engine": {
          "type": "string",
          "enum": ["postgres", "mysql", "mongodb", "redis"]
        },
        "version": {"type": "string"},
        "storage": {"type": "string"},
        "password": {"type": "string"},
        "backupRetention": {"type": "integer"},
        "replicationEnabled": {"type": "boolean"}
      },
      "required": ["name", "engine"]
    }
  }
}
```

---

## TESTING ADDITIONS

Add tests in `tests/test_integration.py` or similar:

```python
def test_database_setup():
    """Test database creation in setup."""
    
def test_database_reconcile_update():
    """Test database version update on redeploy."""
    
def test_database_reconcile_delete():
    """Test database deletion when removed from config."""
    
def test_plan_shows_databases():
    """Test plan command includes database changes."""
```

---

## DEPLOYMENT ORDER QUESTION

Current order in cmd_apply:
1. cleanup_stale_routes
2. (proposed) reconcile_project_databases ← NEW
3. reconcile_app_domains
4. reconcile_app_schedules
5. reconcile_app_mounts
6. reconcile_app_ports

This order makes sense:
- Databases should exist BEFORE apps connect to them
- Domains can be reconciled after
- Everything else follows

---

## OPTIONAL ENHANCEMENTS (Not Required)

1. **Database password rotation**: Add separate command to update DB passwords
2. **Backup management**: Add schedule-style backup configs
3. **Database restore**: Add separate command to restore from backup
4. **Connection pooling**: Add pool size configuration
5. **Read replicas**: Extend engine to support read-only instances

These are nice-to-have but not needed for initial implementation.

---

## FINAL VALIDATION

Before submitting PR:
- [ ] Code follows existing patterns exactly
- [ ] No new error handling added (rely on existing)
- [ ] State structure matches other resources
- [ ] API calls use correct endpoint names (verify against OpenAPI)
- [ ] Plan command shows databases correctly
- [ ] Full workflow works: setup → apply → plan → destroy
- [ ] No breaking changes to existing functionality
- [ ] Documentation updated
- [ ] Example configs provided
