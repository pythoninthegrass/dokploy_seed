---
id: TASK-019
title: Add database resource management
status: Done
assignee: []
created_date: '2026-03-23 18:04'
updated_date: '2026-03-23 21:17'
labels:
  - gap-analysis
  - new-resource
milestone: m-0
dependencies: []
references:
  - main.py
  - schemas/dokploy.schema.json
  - dokploy.yml.example
priority: high
ordinal: 4500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Terraform provider manages 5 database types (Postgres, MySQL, MariaDB, MongoDB, Redis) with full lifecycle. Icarus cannot create, configure, or manage any databases — the single biggest feature gap.

Add a `databases` section to `dokploy.yml` (or integrate into `apps` with a new source type). Support create, update, and destroy for all 5 database types. Include docker image selection, credentials, and environment association.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Can declare postgres, mysql, mariadb, mongo, redis databases in dokploy.yml
- [x] #2 Databases are created during setup with configurable image, credentials
- [x] #3 Databases are included in destroy cleanup
- [x] #4 Database IDs stored in state file
- [x] #5 Database status shown in `status` command
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added database resource management to icarus. All 5 Dokploy database types (postgres, mysql, mariadb, mongo, redis) are supported with full lifecycle.

## Changes

### main.py
- Added `DATABASE_TYPES`, `DATABASE_DEFAULTS` constants
- Added `database_endpoint()`, `database_id_key()`, `build_database_create_payload()` helpers
- `cmd_setup`: creates databases after apps, deploys them immediately, stores IDs in state
- `cmd_status`: shows database status with type label
- `_plan_initial_setup`: includes database creates in plan output

### schemas/dokploy.schema.json
- Added optional `database` top-level array property
- Added `$defs/database_entry` with conditional validation per type (mysql/mariadb require rootPassword, mongo requires user, etc.)

### Tests (21 new in test_unit.py)
- `TestDatabaseDefaults`: validates constants
- `TestBuildDatabaseCreatePayload`: payload generation for all 5 types
- `TestDatabaseApiEndpoint`: endpoint/ID key helpers
- `TestCmdSetupDatabases`: creation, deployment, state storage
- `TestCmdStatusDatabases`: status output includes databases
- `TestComputePlanDatabases`: plan shows database creates

### Docs
- `docs/configuration.md`: new `database` section with properties table, type-specific requirements, example
- `dokploy.yml.example`: database section with postgres example and commented alternatives
- `tests/fixtures/database_config.yml`: test fixture with postgres + redis

All 287 tests pass. No regressions.
<!-- SECTION:FINAL_SUMMARY:END -->
