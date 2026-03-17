---
id: TASK-006.01
title: Create fetch-openapi script and download baseline + target specs
status: Done
assignee: []
created_date: '2026-03-07 03:42'
updated_date: '2026-03-07 05:56'
labels:
  - api-compat
dependencies: []
parent_task_id: TASK-006
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `scripts/fetch_openapi.sh` — a shell script using `gh` CLI to fetch Dokploy's `openapi.json` from GitHub at any release tag. Then use it to download two specs:

1. **Baseline**: v0.26.0 (earliest tag with `openapi.json`; v0.25.6 predates its addition)
2. **Target**: v0.28.4

Output goes to `schemas/src/openapi_<version>.json`.

The script:
```bash
#!/usr/bin/env bash
set -euo pipefail
TAG="${1:?Usage: $0 <tag> (e.g., v0.28.4)}"
VERSION="${TAG#v}"
OUTDIR="schemas/src"
OUTFILE="${OUTDIR}/openapi_${VERSION}.json"
mkdir -p "$OUTDIR"
gh api "repos/Dokploy/dokploy/contents/openapi.json?ref=${TAG}" \
  --jq '.content' | base64 -d | jq . > "$OUTFILE"
echo "Saved: $OUTFILE ($(wc -c < "$OUTFILE") bytes)"
```

Then run:
```bash
./scripts/fetch_openapi.sh v0.26.0
./scripts/fetch_openapi.sh v0.28.4
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 scripts/fetch_openapi.sh exists and is executable
- [x] #2 schemas/src/openapi_0.26.0.json fetched and valid JSON
- [x] #3 schemas/src/openapi_0.28.4.json fetched and valid JSON
<!-- AC:END -->
