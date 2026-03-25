# Code References by Line Number - Quick Lookup

## CRITICAL PATTERNS - LINE NUMBERS

### 1. STATE STRUCTURE & MANAGEMENT

**State File Path Generation**: Line 85-87
```python
def get_state_file(repo_root: Path, env_name: str) -> Path:
    return repo_root / ".dokploy-state" / f"{env_name}.json"
```

**Load State**: Line 694-699
- Exits if missing (expects setup to run first)
- Returns dict directly from JSON

**Save State**: Line 702-706
- Creates parent dir if needed
- JSON with indent=2
- Optional quiet flag

**State Validation**: Line 681-691
- Checks if project still exists on server
- Returns True if valid OR unreachable (assume valid)
- Only returns False if confirmed gone

**State Structure Example** (lines 864-868):
```python
state: dict = {
    "projectId": project_id,
    "environmentId": environment_id,
    "apps": {},
}
```

### 2. APP CREATION IN SETUP

**Setup Entry Point**: Line 833
- First thing: check state file doesn't exist (line 834)
- Early state save: line 904 (CRITICAL - allows destroy cleanup)
- Final state save: line 1035

**Non-Compose App Creation**: Lines 893-901
```python
result = client.post("application.create", {...})
app_id = result["applicationId"]
app_name = result["appName"]
state["apps"][name] = {"applicationId": app_id, "appName": app_name}
```

**Compose App Creation**: Lines 873-890
- Note: stores `"source": "compose"` marker (line 889)
- Note: stores composeId instead of applicationId (line 887)

**State Save After Apps**: Line 904
```python
save_state(state, state_file, quiet=True)
```
- Before any provider config (allows cleanup on failure)

### 3. RESOURCE SETUP SEQUENCE IN cmd_setup

**Order** (lines 906-1032):
1. **Lines 906-943**: Providers (Docker/GitHub config)
2. **Lines 945-959**: Command overrides (with ref resolution)
3. **Lines 961-975**: Domains (loop over desired domains)
4. **Lines 977-986**: App settings (autoDeploy, replicas)
5. **Lines 988-1000**: Volume mounts
6. **Lines 1002-1016**: Ports (with state initialization)
7. **Lines 1018-1032**: Schedules (with state initialization)

**Ports State Initialization** (lines 1011-1016):
```python
state["apps"][name]["ports"] = {}
for port in ports:
    print(f"Creating port for {name}: ...")
    port_payload = build_port_payload(app_id, port)
    resp = client.post("port.create", port_payload)
    state["apps"][name]["ports"][port["publishedPort"]] = {"portId": resp["portId"]}
```

**Schedules State Initialization** (lines 1027-1032):
- Same pattern as ports
- Key is schedule name, stores scheduleId

### 4. RECONCILIATION BASE FUNCTIONS

**Reconcile Ports** (lines 492-531):
- Pattern: index existing & desired by key
- For each desired: build payload, check if exists, create or update
- For each existing not desired: delete
- Return dict mapping key → {id}
- **Payload reuse**: built once, used for both update check and POST
- **Update check** (line 512): `any(payload.get(key) != ex.get(key) for key in (...))`
- **Update payload** (lines 514-520): minimal, includes ID + fields
- **Delete** (lines 527-529): only needs ID

**Reconcile Domains** (lines 586-625):
- Same index pattern
- Update check compares: port, https, certificateType, path, internalPath, stripPath (line 609)
- Update payload excludes applicationId/composeId/domainType (line 613)
- Handles both compose and non-compose (compose parameter)

**Reconcile Mounts** (lines 450-489):
- Index by mountPath (line 460-461)
- Checks type, volumeName, hostPath (lines 471-473)
- Build payload before checking existence

**Reconcile Schedules** (lines 378-419):
- Index by schedule name
- Checks cronExpression, command, shellType, enabled, timezone (lines 399-403)
- Update payload removes applicationId/scheduleType (lines 406-408)

### 5. RECONCILIATION APP WRAPPER FUNCTIONS

**reconcile_app_ports** (lines 534-557):
- Skip compose: `if is_compose(app_def): continue` (line 543)
- Skip if no config and no prior state (lines 545-548)
- Fetch remote: `client.get("application.one", {"applicationId": app_id})` (line 550)
- Extract list: `remote.get("ports") or []` (line 551)
- Call base: `reconcile_ports(client, app_id, existing, desired)` (line 553)
- Update state: `state["apps"][name]["ports"] = new_state` (line 554)
- Save once if changed: `if changed: save_state(state, state_file)` (lines 556-557)

**reconcile_app_mounts** (lines 560-583):
- Same pattern as ports
- Fetch from `application.one` response (line 576)

**reconcile_app_domains** (lines 628-655):
- **Two fetch paths** based on compose (lines 642-647):
  - Compose: `client.get("domain.byComposeId", {"composeId": resource_id})`
  - App: `client.get("domain.byApplicationId", {"applicationId": resource_id})`
- Handles non-list response: `if not isinstance(existing, list): existing = []` (line 648)
- Passes compose flag to reconcile: `reconcile_domains(..., compose=compose)` (line 651)

**reconcile_app_schedules** (lines 422-447):
- No skip condition (line 432 complex: `if schedules is None and ...`)
- Fetch schedules: `client.get("schedule.list", {"id": app_id, "scheduleType": "application"})` (line 436)
- Note: "id" parameter, "scheduleType" for filtering

### 6. REDEPLOY RECONCILIATION IN cmd_apply

**Redeploy Check** (lines 1164-1176):
```python
is_redeploy = False
if state_file.exists():
    state = load_state(state_file)
    if validate_state(client, state):
        print("\n==> Phase 2/4: setup (skipped, state file exists)")
        is_redeploy = True
```

**Reconciliations Called** (lines 1181-1186):
```python
if is_redeploy:
    cleanup_stale_routes(load_state(state_file), cfg)
    reconcile_app_domains(client, cfg, load_state(state_file), state_file)
    reconcile_app_schedules(client, cfg, load_state(state_file), state_file)
    reconcile_app_mounts(client, cfg, load_state(state_file), state_file)
    reconcile_app_ports(client, cfg, load_state(state_file), state_file)
```
- **Note**: Reloads state multiple times (inefficient but safe)
- Could optimize by loading once, reusing

### 7. DESTROY FLOW

**cmd_destroy** (lines 2014-2026):
```python
state = load_state(state_file)
cleanup_stale_routes(state, cfg)
project_id = state["projectId"]
print(f"Deleting project {project_id} (cascades to all apps)...")
client.post("project.remove", {"projectId": project_id})
print("  Project deleted.")
state_file.unlink(missing_ok=True)
print("  State file removed.")
```
- Only needs projectId
- Cascades to all apps automatically
- No per-app or per-resource deletion

### 8. STATUS COMMAND

**cmd_status** (lines 1192-1204):
```python
state = load_state(state_file)
print(f"Project: {state['projectId']}")
print()
for name, info in state["apps"].items():
    if info.get("source") == "compose":
        comp = client.get("compose.one", {"composeId": info["composeId"]})
        status = comp.get("composeStatus", "unknown")
    else:
        app = client.get("application.one", {"applicationId": info["applicationId"]})
        status = app.get("applicationStatus", "unknown")
    print(f"  {name:10s}  {status}")
```
- Iterate state apps (not config)
- Two fetch paths: compose vs app
- Extract status field with "unknown" default

### 9. PLAN COMMAND

**Entry Point**: Line 1752-1760
```python
def cmd_plan(client, cfg, state_file, repo_root):
    changes = compute_plan(client, cfg, state_file, repo_root)
    print_plan(changes)
```

**compute_plan** (lines 1679-1698):
- If no state: call `_plan_initial_setup(cfg, repo_root, changes)`
- If state but invalid: call `_plan_initial_setup(cfg, repo_root, changes)`
- If state valid: call `_plan_redeploy(client, cfg, state, repo_root, changes)`

**_plan_initial_setup** (lines 1221-1368):
- Lines 1224-1235: Project create change
- Lines 1237-1255: App creates (checks compose type)
- Lines 1257-1274: Domain creates
- Lines 1276-1290: Settings (if present)
- Lines 1292-1305: Mounts
- Lines 1307-1321: Ports
- Lines 1323-1335: Schedules
- Lines 1337-1354: Env vars (filtered + targets)
- Lines 1356-1368: Custom env

**_plan_redeploy** (lines 1371-1676):
- Iterate state apps, fetch remote, diff against config
- **Environment diffs** (lines 1403-1430): Uses `_env_keys()` to compare
- **Domain diffs** (lines 1432-1490): Compares host, port, https, etc.
- **Mount diffs** (lines 1492-1551): Compares type, source, target
- **Port diffs** (lines 1553-1608): Compares targetPort, protocol, publishMode
- **Schedule diffs** (lines 1610-1676): Compares cronExpression, command, shellType, enabled, timezone

**Change Object Format** (lines 1221-1235 example):
```python
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
```

**print_plan** (lines 1701-1749):
- Prints terraform-style diff
- Symbols: + (create), ~ (update), - (destroy)
- For updates, shows (old, new) pairs

### 10. API CLIENT & CALLS

**DokployClient Class** (lines 658-678):
```python
class DokployClient:
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
```

**Example Calls**:
- GET: `client.get("project.all")` (line 688)
- GET with params: `client.get("application.one", {"applicationId": app_id})` (line 550)
- POST: `client.post("project.create", {"name": "...", "description": "..."})` (line 844)
- POST expect response: `resp = client.post("port.create", payload); port_id = resp["portId"]` (line 1015)

### 11. PAYLOAD BUILDERS

**build_port_payload** (lines 351-359):
- Simple: just maps config keys to API keys + adds defaults
- Reused in reconcile (create check AND both create/update calls)

**build_mount_payload** (lines 336-348):
- Conditional: checks mount type
- Maps source → volumeName or hostPath

**build_domain_payload** (lines 298-321):
- Dual-mode: compose vs app base structure
- Optional fields only if present

**build_schedule_payload** (lines 362-375):
- Required + optional fields
- Defaults for shellType, enabled

**build_app_settings_payload** (lines 324-333):
- Returns None if only applicationId (no actual settings)
- Only constructs payload if autoDeploy or replicas present

### 12. ENVIRONMENT VARIABLE HANDLING

**get_env_excludes** (lines 166-178):
- Merges DEFAULT_ENV_EXCLUDES with ENV_EXCLUDES, ENV_EXCLUDE_PREFIXES from .env
- Patterns ending with `_` or `*` are prefix matches

**_is_env_excluded** (lines 181-197):
- Checks if key matches pattern
- Handles prefix (* and _) vs exact match

**filter_env** (lines 200-211):
- Strips comments, blanks, excluded keys
- Returns newline-terminated string

**resolve_env_for_push** (lines 214-227):
- Reads env file via decouple (respects os.environ override)
- Filters excluded patterns
- Used in cmd_env (line 1061)

### 13. REFERENCE RESOLUTION

**resolve_refs** (lines 154-163):
```python
def resolve_refs(template: str, state: dict) -> str:
    def replacer(match: re.Match) -> str:
        ref = match.group(1)
        if ref in state["apps"]:
            return state["apps"][ref]["appName"]
        return match.group(0)
    return re.sub(r"\{(\w+)\}", replacer, template)
```
- Uses regex to find {app_name} patterns
- Replaces with appName from state
- Leaves unresolved refs as-is (doesn't fail)

**Usage**:
- Line 953: Command override
- Line 1067: Filtered env in cmd_env
- Line 1103: Custom env in cmd_env
- Line 1407, 1411: In plan redeploy

### 14. COMPOSE DETECTION

**is_compose** (lines 279-281):
```python
def is_compose(app_def: dict) -> bool:
    return app_def.get("source") == "compose"
```

**Usage**:
- Line 542: Skip compose in reconcile_app_ports
- Line 568: Skip compose in reconcile_app_mounts
- Line 641: Two fetch paths based on compose
- Line 1239: Determine resource type (application vs compose)

### 15. CONFIG LOADING & VALIDATION

**find_repo_root** (lines 60-71):
- Walks up from cwd looking for dokploy.yml
- Exits if not found

**load_config** (lines 90-97):
- Reads dokploy.yml from repo root
- Returns yaml.safe_load result

**validate_config** (lines 100-118):
- Checks env_targets apps exist
- Checks deploy_order apps exist
- Checks GitHub config present if needed

**validate_env_references** (lines 121-130):
- Checks environment overrides reference valid apps

**merge_env_overrides** (lines 133-151):
- Deep copy config
- Pop environments block
- Update github overrides
- Update per-app overrides
- Return merged

**Order in main** (lines 2150-2156):
```python
repo_root = find_repo_root()
cfg = load_config(repo_root)
validate_env_references(cfg)
cfg = merge_env_overrides(cfg, env_name)
validate_config(cfg)
```

---

## COMMON PATTERNS SUMMARY

1. **Index before iterate**: `{resource["key"]: resource for resource in list}`
2. **Build payload early**: Reuse same payload for update-check AND create/update calls
3. **Handle null responses**: `remote.get("field") or []`
4. **State dict structure**: `state["category"][name] = {ID_field: id_value}`
5. **Reconcile return value**: Always returns dict mapping key → {id}
6. **Skip compose when needed**: Check `if is_compose(app_def): continue`
7. **Save state once**: Only save at end of wrapper if anything changed
8. **Cascade delete**: Only need parent ID, rest cascades automatically
9. **Fetch remote once per app**: Not once per resource type
10. **Plan changes format**: Consistent structure with action/resource_type/name/parent/attrs
