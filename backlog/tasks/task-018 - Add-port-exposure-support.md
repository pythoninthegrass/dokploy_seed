---
id: TASK-018
title: Add port exposure support
status: Done
assignee: []
created_date: '2026-03-23 18:04'
updated_date: '2026-03-23 20:53'
labels:
  - gap-analysis
  - new-resource
milestone: m-0
dependencies: []
references:
  - main.py
  - schemas/dokploy.schema.json
priority: high
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Icarus has no way to expose additional ports beyond domain routing. The TF provider supports TCP/UDP port mappings with ingress/host publish modes. Many services need non-HTTP ports (databases, gRPC, custom protocols).

Add `ports` configuration to app definitions in `dokploy.yml` and call the `port.create` API. Include reconciliation (create/delete) on apply.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Apps can declare ports in dokploy.yml (published_port, target_port, protocol, publish_mode)
- [x] #2 Ports are created during setup
- [x] #3 Ports are reconciled on apply/redeploy
- [x] #4 Port changes shown in `plan` output
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added port exposure support to icarus. Apps can now declare `ports` in `dokploy.yml` with `publishedPort`, `targetPort`, `protocol` (tcp/udp), and `publishMode` (ingress/host).

Implementation follows the existing reconciliation pattern (domains, mounts, schedules):

- `build_port_payload()` builds API payloads for `port.create`
- `reconcile_ports()` diffs existing vs desired ports by `publishedPort`, creates/updates/deletes as needed
- `reconcile_app_ports()` orchestrates per-app reconciliation on redeploy
- Ports created during `cmd_setup` (step 9), reconciled during `cmd_apply` redeploy
- `_plan_initial_setup` and `_plan_redeploy` show port create/update/destroy changes
- JSON schema updated with `port` definition and `ports` array on app and environment override
- Documentation and example config updated

11 new tests covering: build_port_payload, reconcile_ports (CRUD, no-op, delete-all), reconcile_app_ports (application.one fetch, compose skip), plan drift detection (redeploy + initial setup), cmd_apply integration (redeploy calls reconcile, fresh deploy does not).
<!-- SECTION:FINAL_SUMMARY:END -->
