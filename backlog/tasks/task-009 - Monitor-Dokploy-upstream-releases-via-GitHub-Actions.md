---
id: TASK-009
title: Monitor Dokploy upstream releases via GitHub Actions
status: Done
assignee: []
created_date: '2026-03-07 06:46'
updated_date: '2026-03-23 15:58'
labels:
  - ci
  - automation
dependencies: []
references:
  - scripts/fetch_openapi.sh
  - schemas/src/
  - .github/workflows/monitor-dokploy.yml
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a GitHub Actions workflow that watches for new Dokploy releases and automatically fetches the updated OpenAPI spec.

**Trigger**: GitHub Actions schedule or `workflow_dispatch` that checks for new releases in `Dokploy/dokploy`.

**On new release**:
1. Run `scripts/fetch_openapi.sh <tag>` to download the OpenAPI spec to `schemas/src/openapi_<version>.json`
2. Open an issue in `icarus` summarizing the new release and flagging any breaking changes to validate

**Why**: Manual tracking of upstream releases is easy to miss. Automating spec fetching and issue creation ensures we stay current and catch API changes early.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GHA workflow triggers on new Dokploy releases (event-based)
- [x] #2 Workflow runs `scripts/fetch_openapi.sh <tag>` and commits the new spec to `schemas/src/`
- [x] #3 Workflow opens a `icarus` issue with the release tag, changelog link, and a checklist for validating breaking changes
- [x] #4 Workflow is idempotent — re-running for an already-fetched version is a no-op
- [x] #5 README or docs updated with workflow description
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `.github/workflows/monitor-dokploy.yml` — a daily cron workflow (8 AM UTC) that:\n1. Resolves the latest Dokploy release tag via `gh api`\n2. Checks if the OpenAPI spec already exists in `schemas/src/` (idempotent)\n3. Runs `scripts/fetch_openapi.sh <tag>` to fetch the spec\n4. Commits the new spec file\n5. Opens a tracking issue with changelog link and validation checklist\n\nAlso supports `workflow_dispatch` with an optional tag input for manual runs.\n\nUpdated README.md with a CI Workflows section documenting all three workflows."
<!-- SECTION:FINAL_SUMMARY:END -->
