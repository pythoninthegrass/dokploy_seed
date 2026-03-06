---
id: TASK-002
title: Analyze prod Dokploy projects for reproducibility via dokploy.py
status: Done
assignee: []
created_date: '2026-03-06 08:11'
updated_date: '2026-03-06 15:16'
labels:
  - analysis
  - prod
dependencies: []
documentation:
  - 'backlog://document/doc-001'
  - 'backlog://document/doc-002'
  - 'backlog://document/doc-003'
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Audit the two projects currently running on the production Dokploy server (configured in `.env`) and determine whether each can be fully recreated using `dokploy.py` and a `dokploy.yml` config.

**Steps:**

1. **Inventory existing projects** — Use the Dokploy API (`project.all`, `application.one`, `domain.byApplicationId`, etc.) to enumerate all projects, apps, domains, env vars, source providers, and deploy settings on the prod server.
2. **Map each project to `dokploy.yml` constructs** — For every app, check whether its configuration (source type, Docker image or GitHub repo, domains, command overrides, env vars, deploy order) can be expressed in the current `dokploy.yml` schema.
3. **Identify gaps** — Document any settings, resources, or API features used by the live projects that `dokploy.py` does not yet support (e.g., compose apps, databases/Redis/other services, volumes, mounts, redirects, advanced domain config, security settings, build args, etc.).
4. **Produce a gap report** — For each gap, outline what changes to `dokploy.py` and `dokploy.schema.json` would be needed to support it.
5. **Draft `dokploy.yml` configs** — Write candidate `dokploy.yml` files that reproduce the two projects as closely as the current script allows, noting any manual steps still required.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Full inventory of both prod projects (apps, domains, env targets, source providers, commands, deploy order) is documented
- [x] #2 Each app setting is mapped to the corresponding dokploy.yml field or flagged as unsupported
- [x] #3 Gap report lists every unsupported feature with a proposed plan to add support in dokploy.py / schema
- [x] #4 Draft dokploy.yml configs exist for both projects that cover all currently-supported settings
- [x] #5 Any manual steps required beyond dokploy.py are explicitly listed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Work Done

### Worktree
Branch: `task-002/analyze-prod-projects`
Path: `~/git/dokploy_seed.task-002-analyze-prod-projects`

### Backlog Documents
All deliverables stored in backlog docs (not repo files):
- **DOC-001** — Prod Analysis: full inventory, settings mapping, 7-item gap report, reproducibility summary, manual steps
- **DOC-002** — Draft dokploy.yml for popurls (fully reproducible with caveats)
- **DOC-003** — Draft dokploy.yml for fuck47 (blocked by buildType: static)

### Key Findings
- **2 projects** on prod, each with 1 GitHub-sourced app, 1 domain, no databases/compose
- **popurls**: Fully reproducible via dokploy.py (watchPaths and autoDeploy require manual steps)
- **fuck47**: NOT reproducible — uses `buildType: static` which dokploy.py hardcodes as `dockerfile`

### Critical Gaps
1. `buildType` not configurable (blocks fuck47)
2. `domain.path` not in schema (fuck47 uses `/docs`)
3. `autoDeploy`, `watchPaths`, `replicas` not configurable

### Security Note
Deleted `inventory.py` and `inventory.json` as they contained exposed secrets from the popurls app env vars.
<!-- SECTION:NOTES:END -->
