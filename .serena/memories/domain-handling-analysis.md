# Icarus Domain Handling Analysis

## 1. Domain Creation During Setup

**Location:** `main.py:742-757` in `cmd_setup()`

**Flow:**
- Only called during initial `setup`
- Iterates through `cfg["apps"]`
- For each app with a `domain` config:
  - Supports single domain dict OR list of dicts
  - Calls `build_domain_payload()` to construct request
  - Posts to `domain.create` API endpoint

**Code Pattern:**
```python
domain_cfg = app_def.get("domain")
if not domain_cfg:
    continue

domains = domain_cfg if isinstance(domain_cfg, list) else [domain_cfg]
resource_id = state["apps"][name]["composeId"] if compose else state["apps"][name]["applicationId"]

for dom in domains:
    domain_payload = build_domain_payload(resource_id, dom, compose=compose)
    client.post("domain.create", domain_payload)
```

**Issue:** No state tracking of domain IDs. Domains created but not recorded in state file.

## 2. Domain Payload Construction

**Function:** `build_domain_payload()` at lines 298-322

**Payload Structure:**
- For compose apps: `composeId`, `domainType: "compose"`, `serviceName`
- For regular apps: `applicationId`
- Common fields: `host`, `port`, `https`, `certificateType`
- Optional fields: `path`, `internalPath`, `stripPath` (added only if present in config)

## 3. Apply Command Flow

**Location:** `cmd_apply()` at lines 919-952

**Current Phases:**
1. check - validates config/env
2. setup - creates infrastructure (if needed) or skips if state exists
3. env - pushes environment variables
4. trigger - deploys apps

**Redeploy Path (when state exists):**
- If state valid: skips setup, is_redeploy=True
- Calls `cleanup_stale_routes()` - cleans Traefik configs
- Calls `reconcile_app_schedules()` - reconciles schedules
- Triggers deploy

**Missing:** Domain reconciliation on redeploy

## 4. Plan Command

**Location:** `cmd_plan()` at lines 1322-1331

**Current Behavior:**
- `compute_plan()` returns list of changes
- For initial setup: shows all resources to create
- For redeploy: shows only env changes and schedule changes
- Uses `_plan_initial_setup()` and `_plan_redeploy()`

**Domain Planning:**
- Initial setup (lines 1019-1036): Shows domain creation
- Redeploy (lines 1117-1247): Does NOT analyze domains at all

## 5. Dokploy API Endpoints for Domains

From OpenAPI schema 0.28.4:

**Available Endpoints:**
- `POST /domain.create` - Create domain (takes applicationId or composeId)
- `GET /domain.byApplicationId` - List domains for app (param: applicationId)
- `GET /domain.byComposeId` - List domains for compose (param: composeId)
- `GET /domain.one` - Get single domain (param: domainId)
- `POST /domain.update` - Update domain
- `POST /domain.delete` - Delete domain (param: domainId)
- `POST /domain.validateDomain` - Validate domain
- `POST /domain.generateDomain` - Generate domain
- `GET /domain.canGenerateTraefikMeDomains` - Check TLS-ME availability

**Key Operations:**
- To list domains: Use `domain.byApplicationId` or `domain.byComposeId`
- To delete: Use `domain.delete` with domainId
- Response from list includes domainId needed for delete

## 6. Configuration Structure

**Domain Config in dokploy.yml:**

Single domain:
```yaml
apps:
  - name: web
    domain:
      host: app.example.com
      port: 8000
      https: true
      certificateType: letsencrypt
      path: /api          # optional
      internalPath: /api  # optional
      stripPath: false    # optional
      serviceName: web    # required for compose only
```

Multiple domains:
```yaml
apps:
  - name: web
    domain:
      - host: app.example.com
        port: 8000
        https: true
        certificateType: letsencrypt
      - host: api.example.com
        port: 8001
        https: true
        certificateType: letsencrypt
```

Environment-specific overrides:
```yaml
environments:
  prod:
    apps:
      web:
        domain:
          host: app.example.com
          port: 8000
          https: true
          certificateType: letsencrypt
```

## 7. Existing Reconciliation Patterns

**Schedule Reconciliation** (lines 367-436) - Model to follow:

```python
def reconcile_schedules(client, app_id, existing, desired):
    """Reconcile: update existing by name, create new, delete removed."""
    existing_by_name = {s["name"]: s for s in existing}
    desired_by_name = {s["name"]: s for s in desired}
    
    # Create new / update existing
    for name, sched in desired_by_name.items():
        payload = build_schedule_payload(app_id, sched)
        if name in existing_by_name:
            # Check if needs update, then client.post("schedule.update", ...)
            pass
        else:
            # Create new: client.post("schedule.create", payload)
            pass
    
    # Delete removed
    for name, ex in existing_by_name.items():
        if name not in desired_by_name:
            client.post("schedule.delete", {"scheduleId": ex["scheduleId"]})
```

For domains: Use `host` as the matching key (domains don't have a "name" field).

## 8. State File Structure

Current state file (`.dokploy-state/{env}.json`):
```json
{
  "projectId": "proj-123",
  "environmentId": "env-456",
  "apps": {
    "web": {
      "applicationId": "app-789",
      "appName": "web-abcdef",
      "schedules": {
        "job-name": {"scheduleId": "sched-123"}
      }
    }
  }
}
```

**Missing:** No domain tracking. Need to store domainId for each domain.

## 9. Implementation Strategy for Domain Reconciliation

**State Storage:** Add to each app in state:
```json
"apps": {
  "web": {
    "applicationId": "app-789",
    "appName": "web-abcdef",
    "domains": {
      "app.example.com": {"domainId": "domain-123"},
      "api.example.com": {"domainId": "domain-456"}
    }
  }
}
```

**Reconciliation Logic:**
1. During setup: Create domains, store domainIds in state
2. During redeploy:
   - Fetch existing domains via `domain.byApplicationId`
   - Build desired domain set from config
   - Match by host (primary key)
   - Create new, delete removed, update changed (if needed)
3. In plan: Show domain creation/deletion alongside other changes

**Matching Key:** Domain `host` field (unique identifier for domain within app)

## 10. Cleanup Considerations

**Stale Traefik Routes:** Already handled by `cleanup_stale_routes()` which:
- Collects all configured domain hostnames
- Finds orphaned app names with Traefik configs routing to those domains
- Deletes stale `.yml` files from `/etc/dokploy/traefik/dynamic/`

Domain reconciliation should complement this by deleting domains via API.
