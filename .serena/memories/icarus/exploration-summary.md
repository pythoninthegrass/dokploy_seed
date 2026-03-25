# Main.py Exploration Summary

## EXPLORATION COMPLETED
Date: 2026-03-23
File Analyzed: `/Users/lance/git/icarus/main.py` (2180 lines)
Scope: Complete architecture for app management, state handling, and API patterns

---

## DOCUMENTS CREATED

1. **icarus/main-py-patterns** - High-level architectural patterns
   - App creation flow (setup)
   - App destruction flow (destroy)
   - App status query (status)
   - State file structure and loading
   - YAML config parsing and validation
   - API call patterns (DokployClient class)
   - Reconciliation patterns (redeploy)
   - Reference resolution for placeholders
   - Environment variable handling
   - Plan command logic

2. **icarus/database-design-reference** - Detailed implementation guide
   - Design principles observed in codebase
   - Exact reconciliation pattern with code walkthrough
   - Exact app wrapper pattern
   - Exact plan changes pattern
   - State structure options for databases
   - Build payload examples (simple, conditional, hybrid)
   - Error handling patterns
   - Environment config integration
   - Complete minimal implementation skeleton
   - Checklist for implementation
   - Likely Dokploy API endpoints

3. **icarus/code-references-by-line** - Quick lookup reference
   - Line-by-line breakdown of critical patterns
   - Specific code examples with line numbers
   - API client class structure
   - Payload builder functions
   - Env var handling details
   - Reference resolution implementation
   - Config loading sequence
   - Common patterns summary

---

## KEY FINDINGS

### 1. IDEMPOTENT RECONCILIATION MODEL
The codebase uses a **diff-apply** pattern for all sub-resources:
- Fetch existing from remote (indexed by natural key)
- Compare against desired from config (indexed by same key)
- Create new resources
- Update existing if attributes differ
- Delete removed resources
- Return lookup dict for state storage

This pattern is consistent across: domains, ports, mounts, schedules.
**For databases**: Apply same pattern—index by database name, reconcile attributes.

### 2. CASCADING LIFECYCLE
- Create project → creates environment (Dokploy returns both)
- Create app → gets ID and computed appName
- Create sub-resources → need parent app ID (from state)
- Delete project → cascades to all apps and resources
- No explicit per-resource cleanup needed on destroy

**For databases**: Likely project-wide, so delete via cascading project deletion.

### 3. TWO-PHASE SETUP
**Phase 1**: Create project + apps, save state immediately (line 904)
- Allows destroy to clean up if phase 2 fails
- Phase 2: Provider config, domains, mounts, ports, schedules

**For databases**: Create them in phase 1 (with apps), before providers.

### 4. STATE IS SINGLE SOURCE OF TRUTH FOR IDs
- IDs come from API responses during setup
- Stored in `.dokploy-state/{env_name}.json`
- Never re-queried from remote except for status/planning
- Update operations use stored ID + changed fields only

**For databases**: Store databaseId in state after create.

### 5. PLAN COMMAND REQUIRES TWO PATHS
- **Initial setup**: What would setup create (fresh state)
- **Redeploy**: Diff what's on server against desired config

Both paths live in separate functions (_plan_initial_setup, _plan_redeploy).

**For databases**: Need both paths in plan.

### 6. RECONCILIATION CALLED ON REDEPLOY ONLY
When `cmd_apply` detects state exists and is valid:
1. Run reconciliations (domains, schedules, mounts, ports)
2. Each one fetches remote, diffs, updates state
3. Trigger deploy

Reconciliations happen BEFORE deploy trigger (line 1181-1186).

**For databases**: Call reconcile before deploy trigger.

### 7. WRAPPER FUNCTIONS SAVE STATE ONCE
App-level wrapper functions (reconcile_app_X) iterate apps, accumulate changes, save state once at end.
- Load state (maybe multiple times across different wrappers)
- Modify state dict in place
- Save if anything changed

**For databases**: If top-level, call reconcile_project_databases() once.
If nested per-app, call from app wrapper, save with app state.

### 8. FETCH REMOTE IS CRUCIAL
Reconciliation requires fetching the actual remote state:
- `client.get("application.one", {"applicationId": id})`
- Extract the specific resource list from response
- Handle null responses gracefully

**For databases**: Likely `client.get("database.byProjectId", {"projectId": project_id})`

### 9. PAYLOAD BUILDERS ARE REUSABLE
Build payload happens once, used for:
1. Checking if update is needed (compare to existing)
2. Posting create request (if new)
3. Posting update request (if changed)

Builders should not do I/O, just transform config → API payload.

**For databases**: Build payload from db config once, reuse in reconcile.

### 10. API ERRORS PROPAGATE
DokployClient.post/get calls raise_for_status() automatically.
No try-catch in higher-level code—errors bubble up.
Safe to assume API errors terminate the command.

---

## SPECIFIC IMPLEMENTATION PATTERNS

### Resource Creation Pattern (from cmd_setup)
```
For each resource in config:
  Build payload (adds IDs and defaults)
  POST create API call
  Extract ID from response
  Store in state[parent][key] = {"ID_field": id}
  Print progress message
```

### Reconciliation Pattern (from reconcile_X)
```
Index existing by natural key
Index desired by natural key
For each desired:
  Build payload
  If key in existing:
    Compare payload to existing attributes
    If differs: POST update with ID + changed fields
    Preserve state entry with ID
  Else:
    POST create
    Extract ID from response
    Add to state
For each existing not in desired:
  POST delete with ID
Return state dict mapping key → {ID_field: id}
```

### Wrapper Pattern (from reconcile_app_X)
```
Load state
changed = False
For each app in config:
  Skip if doesn't apply (compose check, config exists check)
  Fetch remote state via app ID
  Extract resource list (handle null)
  Call base reconcile function
  Update state dict with result
  changed = True
If changed:
  Save state once
```

### Plan Change Pattern
For creates:
```
{
  "action": "create",
  "resource_type": "...",
  "name": display_name,
  "parent": parent_name or None,
  "attrs": {full_attributes}
}
```

For updates:
```
{
  "action": "update",
  "resource_type": "...",
  "name": display_name,
  "parent": parent_name or None,
  "attrs": {key: (old_val, new_val), ...}
}
```

For destroys:
```
{
  "action": "destroy",
  "resource_type": "...",
  "name": display_name,
  "parent": parent_name or None,
  "attrs": {minimal_identifying_attrs}
}
```

---

## STATE STRUCTURE OPTIONS FOR DATABASES

### Recommended: Top-Level (Option 1)
```json
{
  "projectId": "proj-123",
  "environmentId": "env-456",
  "apps": {
    "django": {"applicationId": "app-123", "appName": "app-django", ...}
  },
  "databases": {
    "postgres-main": {
      "databaseId": "db-789",
      "engine": "postgres"
    }
  }
}
```

**Why**: 
- Databases are project-wide resource
- Simpler state structure
- Simpler config structure (one `databases:` block, not nested)
- Cleaner plan output (databases at root, not per-app)
- Aligns with project lifecycle

---

## CONFIGURATION ADDITIONS NEEDED

### dokploy.yml.example additions
```yaml
databases:
  - name: postgres-main
    engine: postgres
    version: "15"
    storage: "50Gb"
    password: ${DB_PASSWORD}
  - name: redis-cache
    engine: redis
    version: "7"
```

### schemas/dokploy.schema.json additions
Define database schema with properties:
- name (required, string)
- engine (required, enum: postgres, mysql, mongodb, redis, etc.)
- version (optional, string)
- storage (optional, string)
- password (optional, string)
- Any other engine-specific fields

---

## FUNCTION ADDITION CHECKLIST

- [ ] `build_database_payload(project_id: str, db: dict) -> dict`
- [ ] `reconcile_databases(client, project_id, existing, desired) -> dict`
- [ ] `reconcile_project_databases(client, cfg, state, state_file) -> None`
- [ ] Update `cmd_setup()` to create databases (add after apps created)
- [ ] Update `cmd_apply()` to call reconcile on redeploy
- [ ] Update `_plan_initial_setup()` to add database changes
- [ ] Update `_plan_redeploy()` to diff databases
- [ ] Add `cmd_plan` integration (already calls compute_plan, which uses _plan_redeploy)

---

## API ENDPOINTS LIKELY NEEDED

Based on pattern analysis, database endpoints probably mirror existing patterns:
- `database.create` - POST, requires projectId + name + engine + version
- `database.update` - POST, requires databaseId + changed fields
- `database.delete` - POST, requires databaseId
- `database.byProjectId` - GET, lists databases for a project
- `database.one` - GET, fetches single database (may not be needed)

**Verification**: Check Dokploy OpenAPI schema at `schemas/openapi_*.json`

---

## TESTING STRATEGY

1. **Unit-like**:
   - Test reconcile_databases with mock existing/desired lists
   - Test payload builder with various configs
   - Test plan generation for databases

2. **Integration**:
   - Test full setup with databases
   - Test redeploy with database updates
   - Test plan command shows database changes
   - Test destroy cascades and removes databases

3. **Real Usage**:
   - Create project with databases
   - Modify database version/storage
   - Redeploy and verify reconciliation
   - Delete config entry and verify plan shows destroy
   - Run full plan → apply cycle

---

## RISK AREAS

1. **API Unknown**: Database endpoints may differ from expected names/payloads
   - Mitigation: Check OpenAPI schema first

2. **ID Storage**: If Dokploy returns different response format for databases
   - Mitigation: Adjust response extraction in reconcile_databases

3. **Cascade Delete**: If database delete doesn't cascade or requires manual cleanup
   - Mitigation: Test destroy carefully, add explicit cleanup if needed

4. **State Fetch**: If fetching databases from remote is slow or unreliable
   - Mitigation: Cache in state between reconciliations

---

## NEXT STEPS

1. Check OpenAPI schema for actual database API endpoints
2. Create build_database_payload() function
3. Create reconcile_databases() function (base)
4. Add reconcile_project_databases() wrapper
5. Integrate into cmd_setup (after apps)
6. Integrate into cmd_apply (on redeploy)
7. Add to plan command (both paths)
8. Test with actual Dokploy instance
9. Update configuration examples
10. Update documentation

---

## ARCHITECTURE STRENGTHS TO PRESERVE

1. **Idempotent reconciliation**: Don't break this pattern
2. **Single state file source of truth**: Keep ID storage pattern
3. **Cascading lifecycle**: Leverage project deletion
4. **Early error detection**: Validate config before API calls
5. **Plan command clarity**: Show all changes before apply
6. **Consistent naming**: Use same patterns as existing resources

---

## PATTERNS OBSERVED ACROSS ALL RESOURCES

| Aspect | Pattern |
|--------|---------|
| **Index Method** | Dict comprehension by natural key |
| **Comparison** | Build payload, compare attribute by attribute |
| **State Key** | Resource natural key (host, mountPath, name, etc.) |
| **State Value** | Dict with at least `{ID_field: id_value}` |
| **Create Check** | Check if key exists in indexed existing |
| **Update Check** | Any(payload.get(k) != existing.get(k) for k in attrs) |
| **Update Payload** | Minimal: ID + changed fields only |
| **Delete Check** | Check if key in existing but not desired |
| **Delete Payload** | Just {ID_field: id_value} |
| **Return Value** | Dict mapping key → {ID_field: id_value} |
| **Wrapper Save** | Save state once at end if changed |
| **Plan Create** | Full attributes in attrs dict |
| **Plan Update** | Diffs as (old, new) tuples |
| **Plan Delete** | Minimal identifying attrs |

**For databases**: Follow every pattern exactly as shown.

---

## COMPLETE PATTERN MATCH CHECK

Does the database implementation need to:
- [ ] Load state? Yes (access project_id, environment_id)
- [ ] Save state? Yes (store database IDs)
- [ ] Parse config? Yes (load databases section)
- [ ] Validate config? Yes (check names are unique, engines valid)
- [ ] Build payloads? Yes (transform config to API format)
- [ ] Call API create? Yes (post database.create)
- [ ] Call API update? Yes (post database.update on version/storage change)
- [ ] Call API delete? Yes (post database.delete)
- [ ] Call API list? Yes (get database.byProjectId or similar)
- [ ] Handle reconciliation? Yes (redeploy with config changes)
- [ ] Generate plan changes? Yes (show creates/updates/destroys)
- [ ] Support redeploy? Yes (reconcile on second apply)
- [ ] Support destroy? Yes (cascade via project deletion)
- [ ] Support status? Maybe (show database details?)
- [ ] Support reference resolution? Probably not (databases don't reference each other)
- [ ] Support environment overrides? Maybe (if project can have multiple db clusters)

All checkmarks = **full integration required**.

---

## TIME TO IMPLEMENTATION ESTIMATE

- Read OpenAPI schema: 15 min
- Write build_database_payload: 10 min
- Write reconcile_databases: 30 min
- Write reconcile_project_databases: 20 min
- Integrate cmd_setup: 15 min
- Integrate cmd_apply: 10 min
- Update plan functions: 45 min
- Test + debug: 90 min
- Total: ~4 hours for core implementation

Plus:
- Schema updates: 20 min
- Config examples: 15 min
- Docs: 30 min
- Integration testing: 60 min

---

## KEY CODE LOCATIONS FOR REFERENCE

| Task | File | Lines |
|------|------|-------|
| Understand state | main.py | 85-87, 694-706 |
| See setup flow | main.py | 833-1041 |
| See reconcile base | main.py | 492-531 (ports) |
| See reconcile wrapper | main.py | 534-557 (app ports) |
| See plan changes | main.py | 1221-1676 |
| See API client | main.py | 658-678 |
| See payload builders | main.py | 336-376 |
| See destroy | main.py | 2014-2026 |

All line numbers verified against 2180-line file.

---

## FINAL ASSESSMENT

The codebase is **exceptionally well-designed** for extension:
- Consistent patterns across all resource types
- Clear separation of concerns (build, reconcile, plan)
- Proper state management and lifecycle
- Robust error handling via API wrapper
- Good comments explaining why (not what)
- Testable architecture with clear inputs/outputs

**Database support can be added cleanly** by following existing patterns exactly.
No refactoring needed—just add new functions that fit the established model.
