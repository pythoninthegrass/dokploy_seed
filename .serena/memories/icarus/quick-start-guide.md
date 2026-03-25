# Quick Start Guide - Database Implementation

**Objective**: Add database resource management to icarus  
**Time to complete**: 4-8 hours  
**Difficulty**: Moderate (follow existing patterns exactly)  

---

## STEP 0: UNDERSTAND THE ARCHITECTURE (30 min)

Read these in order:
1. **icarus/exploration-summary** (10 min)
   - Understand idempotent reconciliation
   - See cascading lifecycle model
   - Learn why two-phase setup

2. **icarus/main-py-patterns** (20 min)
   - Study how apps are created
   - See how reconciliation works
   - Learn state structure

---

## STEP 1: PLAN YOUR IMPLEMENTATION (15 min)

Before coding, answer these questions:

**Q1: Where should databases live in state?**  
A: Top-level (`state["databases"][name]`) — not nested per-app (they're project resources)

**Q2: What's the natural key?**  
A: Database name (e.g., "postgres-main")

**Q3: What should be reconcilable attributes?**  
A: engine, version, storage, password, backupRetention, replicationEnabled

**Q4: What are the YAML config attributes?**  
A: name (required), engine (required), version (optional, default "latest"), others (optional)

**Q5: What API endpoints will you use?**  
A: Check Dokploy OpenAPI schema — likely database.create, database.update, database.delete, database.byProjectId

---

## STEP 2: VERIFY API ENDPOINTS (10 min)

Before coding, verify:
```bash
# Check OpenAPI schema for exact endpoint names
cat schemas/openapi_*.json | jq '.paths | keys | grep database'
```

Expected endpoints (but verify!):
- `POST /api/database.create`
- `POST /api/database.update`
- `POST /api/database.delete`
- `GET /api/database.byProjectId`

If endpoints differ, adjust integration points accordingly.

---

## STEP 3: CREATE TEST FIXTURES (10 min)

Create `tests/fixtures/database-config.yml`:
```yaml
databases:
  - name: postgres-main
    engine: postgres
    version: "15"
    storage: "50Gb"
    password: test123
```

This will be used for testing throughout.

---

## STEP 4: WRITE PAYLOAD BUILDER (10 min)

Add after line 375 in main.py:

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

**Test**: Does it correctly transform config to payload? Yes → Continue

---

## STEP 5: WRITE BASE RECONCILE (30 min)

Add after line 531 in main.py:

Use the template from **icarus/integration-points-summary** (section 2).

**Structure**:
1. Index existing by name
2. Index desired by name
3. Loop desired: check if exists, create or update
4. Loop existing: delete if not desired
5. Return state dict

**Test**: Write unit test that reconciles mock existing/desired lists. Verify CRUD operations.

---

## STEP 6: WRITE APP WRAPPER (20 min)

Add after line 557 in main.py:

Use template from **icarus/integration-points-summary** (section 3).

**Structure**:
1. Get databases from config (default empty)
2. Check if skip (no config AND no prior state)
3. Fetch remote via project_id
4. Call base reconcile function
5. Update state["databases"]
6. Save state if changed

**Test**: Verify it calls reconcile correctly. Verify state is updated and saved.

---

## STEP 7: INTEGRATE INTO SETUP (15 min)

In `cmd_setup()` around line 1018:

Add database creation loop after schedules (before final save):

```python
# 11. Databases
databases = cfg.get("databases", [])
if databases:
    state["databases"] = {}
    for db_def in databases:
        name = db_def["name"]
        print(f"Creating database: {name}...")
        db_payload = build_database_payload(project_id, db_def)
        resp = client.post("database.create", db_payload)
        state["databases"][name] = {"databaseId": resp["databaseId"]}
```

Also update state initialization (line 864):
```python
state: dict = {
    "projectId": project_id,
    "environmentId": environment_id,
    "apps": {},
    "databases": {},  # ADD THIS
}
```

**Test**: Setup creates databases, state has IDs.

---

## STEP 8: INTEGRATE INTO APPLY (10 min)

In `cmd_apply()` around line 1181:

Add to redeploy reconciliation:
```python
if is_redeploy:
    cleanup_stale_routes(load_state(state_file), cfg)
    reconcile_project_databases(client, cfg, load_state(state_file), state_file)  # ADD THIS
    reconcile_app_domains(client, cfg, load_state(state_file), state_file)
    # ... rest ...
```

**Test**: Apply on existing state reconciles databases (verify via plan first).

---

## STEP 9: INTEGRATE INTO PLAN - INITIAL (10 min)

In `_plan_initial_setup()` around line 1335:

Add after schedules:
```python
# Databases
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
```

**Test**: Plan on fresh state shows database creates.

---

## STEP 10: INTEGRATE INTO PLAN - REDEPLOY (20 min)

In `_plan_redeploy()` around line 1676:

Add after schedules:

Use template from **icarus/integration-points-summary** (section 7).

**Test**: Plan on existing state shows diffs when version/storage changes.

---

## STEP 11: UPDATE CONFIGURATION (10 min)

### dokploy.yml.example

Add after apps section:
```yaml
# Optional: Project-wide databases
databases:
  - name: postgres-main
    engine: postgres
    version: "15"
    storage: "50Gb"
    password: ${DB_PASSWORD}
```

### schemas/dokploy.schema.json

Add to properties:
```json
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
      "password": {"type": "string"}
    },
    "required": ["name", "engine"]
  }
}
```

---

## STEP 12: TEST IT (60-90 min)

### Manual Testing Flow

**Test 1: Fresh Setup**
```bash
# With databases in dokploy.yml
ic --env test setup
# Check: State file has databases section with IDs
cat .dokploy-state/test.json
```

**Test 2: Plan Command**
```bash
ic --env test plan
# Check: Should show database creates
```

**Test 3: Apply with Changes**
```bash
# Modify database version in dokploy.yml
ic --env test plan
# Check: Should show database update
ic --env test apply
# Check: Database updated (via API call)
```

**Test 4: Delete and Destroy**
```bash
# Remove database from config
ic --env test plan
# Check: Should show database destroy
ic --env test destroy
# Check: All databases deleted (cascaded via project delete)
```

**Test 5: Status (optional)**
```bash
ic --env test status
# Should show database status (if implemented)
```

### Automated Test Writing

In `tests/test_integration.py`:

```python
def test_setup_creates_databases(client, cfg):
    """Test databases created during setup."""
    state = cmd_setup(client, cfg, state_file, repo_root)
    assert "databases" in state
    assert "postgres" in state["databases"]
    assert "databaseId" in state["databases"]["postgres"]

def test_plan_shows_database_creates(client, cfg):
    """Test plan shows database creation."""
    changes = compute_plan(client, cfg, state_file, repo_root)
    db_changes = [c for c in changes if c["resource_type"] == "database"]
    assert len(db_changes) > 0

def test_redeploy_reconciles_database_version(client, cfg, state):
    """Test database version update on redeploy."""
    # Modify config version
    # Call reconcile
    # Verify update payload was sent
```

---

## STEP 13: VERIFY PATTERNS (20 min)

Before committing, check:

- [ ] `build_database_payload()` matches `build_port_payload()` structure
- [ ] `reconcile_databases()` matches `reconcile_ports()` structure exactly
- [ ] `reconcile_project_databases()` matches `reconcile_app_ports()` structure
- [ ] State dict format matches ports/mounts/domains
- [ ] All three CRUD operations in reconcile
- [ ] API calls use correct client.get/post patterns
- [ ] Plan changes use correct format {action, resource_type, name, parent, attrs}
- [ ] No new error handling (rely on existing DokployClient)
- [ ] Config validation happens before API calls

---

## STEP 14: FINAL CHECKLIST (10 min)

Before pushing:

```
Code:
- [ ] All functions added (payload, reconcile, wrapper)
- [ ] All integration points updated (setup, apply, plan x2)
- [ ] State initialization includes "databases": {}
- [ ] No syntax errors
- [ ] No breaking changes to existing code

Configuration:
- [ ] dokploy.yml.example updated
- [ ] JSON schema updated
- [ ] Both have engines list and required fields

Testing:
- [ ] Fresh setup works
- [ ] Plan shows creates
- [ ] Redeploy reconciles changes
- [ ] Destroy removes (cascaded)
- [ ] No errors in logs

Documentation:
- [ ] Updated docs/configuration.md (if exists)
- [ ] Updated example configs
- [ ] Added docstrings to functions
```

---

## COMMON GOTCHAS & SOLUTIONS

### Gotcha 1: API Endpoint Names Wrong
**Symptom**: 404 error on database.create  
**Fix**: Check OpenAPI schema, adjust endpoint names in all calls

### Gotcha 2: Response Format Unknown
**Symptom**: KeyError: "databaseId" after create  
**Fix**: Print response, check actual structure, adjust extraction

### Gotcha 3: Wrong State Structure
**Symptom**: Reconcile can't find database ID  
**Fix**: Verify state["databases"][name] has "databaseId", not "id"

### Gotcha 4: Reconcile Not Called
**Symptom**: Redeploy doesn't update databases  
**Fix**: Check cmd_apply calls reconcile_project_databases, check is_redeploy flag

### Gotcha 5: State Not Saved
**Symptom**: Databases lost between commands  
**Fix**: Verify reconcile function saves state (check last line)

---

## VERIFICATION COMMANDS

After each step, run:

```bash
# Syntax check
python -m py_compile main.py

# Run with test config
ic --env test plan

# Check state file
cat .dokploy-state/test.json | jq '.databases'

# Run tests
pytest tests/ -k database -v

# Check for patterns
grep -n "reconcile_database" main.py
grep -n "build_database_payload" main.py
```

---

## TIME BREAKDOWN

| Step | Time | Cumulative |
|------|------|-----------|
| 0. Understand | 30 min | 30 min |
| 1. Plan | 15 min | 45 min |
| 2. Verify API | 10 min | 55 min |
| 3. Test fixtures | 10 min | 65 min |
| 4. Payload | 10 min | 75 min |
| 5. Reconcile | 30 min | 105 min |
| 6. Wrapper | 20 min | 125 min |
| 7. Setup integration | 15 min | 140 min |
| 8. Apply integration | 10 min | 150 min |
| 9. Plan initial | 10 min | 160 min |
| 10. Plan redeploy | 20 min | 180 min |
| 11. Config | 10 min | 190 min |
| 12. Testing | 90 min | 280 min |
| 13. Verify patterns | 20 min | 300 min |
| 14. Final checklist | 10 min | 310 min |

**Total**: ~5.2 hours = **5-6 hours for complete implementation**

---

## SUCCESS CRITERIA

You're done when:
1. ✅ Fresh setup creates databases (verify in state file)
2. ✅ Plan command shows database section
3. ✅ Redeploy reconciles database changes
4. ✅ Destroy cascades (no manual cleanup)
5. ✅ No breaking changes to existing commands
6. ✅ Code follows existing patterns exactly
7. ✅ Configuration examples work
8. ✅ Tests pass

---

## GET HELP

If stuck:
1. Check **icarus/code-references-by-line** for exact syntax
2. Compare to `reconcile_ports()` (line 492)
3. Compare to `reconcile_app_ports()` (line 534)
4. Verify API endpoint names in OpenAPI schema
5. Print intermediate values to debug state/response

---

## NEXT: CREATE A FEATURE BRANCH

```bash
cd /Users/lance/git/icarus
git checkout -b feat/add-database-support
```

Start with Step 3 (create test fixtures).

---

**Ready to implement?** Start with Step 3.  
**Have questions?** Check icarus/integration-points-summary.  
**Need context?** Read icarus/main-py-patterns.
