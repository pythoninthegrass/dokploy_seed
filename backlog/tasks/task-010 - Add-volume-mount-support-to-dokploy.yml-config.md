---
id: TASK-010
title: Add volume mount support to dokploy.yml config
status: Done
assignee: []
created_date: '2026-03-16 22:23'
updated_date: '2026-03-16 22:33'
labels:
  - feature
  - gh-issue-7
dependencies: []
references:
  - 'GH issue #7'
  - main.py
  - schemas/dokploy.schema.json
  - dokploy.yml.example
  - docs/configuration.md
priority: high
ordinal: 500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Currently there is no way to configure persistent volume mounts in `dokploy.yml`. This means any data written to the container filesystem is lost on every Dokploy redeploy.

The concrete motivating case is the meetup_bot project, which uses SQLite at `/data/meetup_bot.db`. Every redeploy wipes the database because there is no volume mount keeping it on the host.

The proposed solution is to add a `volumes` key to app definitions in `dokploy.yml`, allowing users to declare mounts that icarus will configure via the Dokploy API. Example:

```yaml
apps:
  meetup_bot:
    volumes:
      - source: meetup_bot_data
        target: /data
        type: volume
```

This requires schema changes, API integration for mount creation during setup/deploy, documentation updates, and tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 dokploy.yml supports a `volumes` list per app with `source`, `target`, and `type` fields
- [x] #2 JSON schema (`schemas/dokploy.schema.json`) updated to validate the new `volumes` key
- [x] #3 Volume mounts are applied via Dokploy API during setup/deploy
- [x] #4 Existing configs without `volumes` continue to work (backward compatible)
- [x] #5 `dokploy.yml.example` and `docs/configuration.md` updated with volume mount documentation
- [x] #6 Tests cover volume mount parsing, API call generation, and missing/empty volumes
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added volume mount support to `dokploy.yml` config.

**Changes:**
- `main.py`: Added `build_mount_payload()` function that maps config `source`/`target`/`type` to Dokploy API fields (`volumeName`/`hostPath`, `mountPath`, `serviceType`). Added step 8 in `cmd_setup` to call `mounts.create` for each volume.
- `schemas/dokploy.schema.json`: Added `volume` definition to `$defs` and `volumes` array property to app items.
- `dokploy.yml.example`: Added volume mount example on the redis app.
- `docs/configuration.md`: Added Volume Mount Object reference table.
- `docs/api-notes.md`: Documented `mounts.create` endpoint fields.
- `tests/fixtures/volumes_config.yml`: New fixture with volume and bind mount types.
- `tests/conftest.py`: Added `volumes_config` fixture.
- `tests/test_unit.py`: Added `TestBuildMountPayload` (4 tests) and `TestCmdSetupVolumes` (3 tests) plus 2 schema/parsing tests.
- `pyproject.toml`: Fixed duplicate `[project.scripts]` and `[build-system]` sections.

**Test results:** 169 passed, 0 failed.
<!-- SECTION:FINAL_SUMMARY:END -->
