---
id: TASK-011
title: Add schedule/cron job support for applications
status: Done
assignee: []
created_date: '2026-03-17 05:56'
updated_date: '2026-03-17 06:07'
labels:
  - feature
  - schema
  - api
dependencies: []
references:
  - 'schemas/src/openapi_0.28.6.json (lines 33854-33958: schedule.create)'
  - 'schemas/src/openapi_0.28.6.json (lines 33961-34068: schedule.update/delete)'
  - 'https://docs.dokploy.com/docs/core/schedule-jobs'
  - 'https://docs.dokploy.com/docs/api/schedule'
documentation:
  - 'https://docs.dokploy.com/docs/core/schedule-jobs'
  - 'https://docs.dokploy.com/docs/api/schedule'
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add support for Dokploy's `schedule` API as a new property on app definitions in `dokploy.yml`. Schedules are separate resources that attach to an application via `applicationId` and run commands inside the app's container using `docker exec`.

## Dokploy Schedule API

Endpoints: `schedule.create`, `schedule.update`, `schedule.delete`, `schedule.list`, `schedule.one`, `schedule.runManually`

### `schedule.create` payload

**Required:**
- `name` (string) — job name
- `cronExpression` (string) — standard 5-field cron: `minute hour day month weekday`
- `command` (string) — command to run in the container

**Optional (relevant):**
- `applicationId` (string|null) — ties schedule to an app
- `appName` (string) — Dokploy appName
- `scheduleType` (enum) — `"application"` | `"compose"` | `"server"` | `"dokploy-server"`
- `shellType` (enum) — `"bash"` | `"sh"`
- `timezone` (string|null) — e.g. `"America/Chicago"`
- `enabled` (boolean)

### `schedule.list` params
- `scheduleType` query param filters by type

### `schedule.update` payload
- Same as create but `scheduleId` is required

### `schedule.delete` payload
- `scheduleId` (string)

## Target config shape

```yaml
apps:
  - name: web
    source: github
    schedules:
      - name: weekday-run
        cronExpression: "0 9 * * 1-5"
        command: "python run.py"
        shellType: bash
        timezone: America/Chicago
```

## Implementation plan

### 1. Schema (`schemas/dokploy.schema.json`)

Add `schedules` array property to app items and environment app overrides:

```json
"schedules": {
  "type": "array",
  "items": { "$ref": "#/$defs/schedule" }
}
```

Add `$defs/schedule`:
```json
"schedule": {
  "type": "object",
  "required": ["name", "cronExpression", "command"],
  "additionalProperties": false,
  "properties": {
    "name": { "type": "string" },
    "cronExpression": { "type": "string" },
    "command": { "type": "string" },
    "shellType": { "type": "string", "enum": ["bash", "sh"], "default": "bash" },
    "timezone": { "type": "string" },
    "enabled": { "type": "boolean", "default": true }
  }
}
```

### 2. Setup step in `main.py`

After app creation (step 8, volumes), add a new step that iterates `app_def.get("schedules", [])` and calls `schedule.create` with:
```python
{
    "name": sched["name"],
    "cronExpression": sched["cronExpression"],
    "command": sched["command"],
    "scheduleType": "application",
    "applicationId": app_id,
    "shellType": sched.get("shellType", "bash"),
    "timezone": sched.get("timezone"),
    "enabled": sched.get("enabled", True),
}
```

Store returned `scheduleId` values in state under `state["apps"][name]["schedules"]`.

### 3. Redeploy reconciliation

On redeploy, reconcile schedules:
- Fetch existing: `schedule.list` filtered by app
- Match by `name` — update existing (`schedule.update`), create new, delete removed
- This avoids duplicate schedules accumulating across deploys

### 4. State file

Extend app state entries:
```json
{
  "applicationId": "...",
  "appName": "...",
  "schedules": {
    "weekday-run": { "scheduleId": "..." }
  }
}
```

### 5. Destroy

Schedules should cascade-delete when the project is deleted (verify this). If not, delete them explicitly before project deletion.

### 6. Docs and examples

- Update `docs/configuration.md` with schedules reference
- Update `dokploy.yml.example` with a commented schedule example
- Update `examples/` if relevant
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Schema validates `schedules` array on app definitions with name, cronExpression, command (required) and shellType, timezone, enabled (optional)
- [x] #2 Setup creates schedules via `schedule.create` API and stores scheduleIds in state
- [x] #3 Redeploy reconciles schedules: updates existing by name, creates new, deletes removed
- [x] #4 Environment overrides can override schedules per-app
- [x] #5 Tests cover schedule payload building, reconciliation logic, and schema validation
- [x] #6 dokploy.yml.example and docs/configuration.md updated
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Summary

Add schedule/cron job support for Dokploy applications via `dokploy.yml` config.

### Changes

**`main.py`**
- `build_schedule_payload(app_id, sched)` — builds `schedule.create` API payload with defaults (shellType=bash, enabled=True, timezone omitted when unset)
- `reconcile_schedules(client, app_id, existing, desired)` — reconciles schedules by name: updates changed, creates new, deletes removed
- `reconcile_app_schedules(client, cfg, state, state_file)` — iterates apps and reconciles schedules on redeploy
- `cmd_setup` step 9 — creates schedules via `schedule.create` and stores `scheduleId` in state
- `cmd_deploy` — calls `reconcile_app_schedules` on redeploy path

**`schemas/dokploy.schema.json`**
- Added `$defs/schedule` object (name, cronExpression, command required; shellType, timezone, enabled optional)
- Added `schedules` array property to app items and environment app overrides

**`tests/`**
- 14 new unit tests across 5 classes: `TestBuildSchedulePayload` (5), `TestCmdSetupSchedules` (4), `TestScheduleReconciliation` (2), `TestScheduleSchemaValidation` (3)
- New fixture: `tests/fixtures/schedules_config.yml`

**Docs**
- `dokploy.yml.example` — added schedule example on worker app
- `docs/configuration.md` — added Schedule Object reference table and `schedules` to overridable properties

### Tested with
- `~/git/meetup_bot/dokploy.yml` with `cronExpression: "0 9 * * 1-5"` — `ic check` passes, schema validates
- Full test suite: 199 passed, 5 deselected (e2e skipped)
<!-- SECTION:FINAL_SUMMARY:END -->
