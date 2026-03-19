#!/usr/bin/env bash
# Fetch Dokploy OpenAPI spec from GitHub for a given release tag.
# Usage: ./scripts/fetch_openapi.sh [tag] (e.g., v0.28.4)
# Omit tag to fetch the latest release.
set -euo pipefail

TAG="${1:-$(gh api repos/Dokploy/dokploy/releases/latest --jq '.tag_name')}"
VERSION="${TAG#v}"
OUTDIR="schemas/src"
OUTFILE="${OUTDIR}/openapi_${VERSION}.json"

mkdir -p "$OUTDIR"
gh api "repos/Dokploy/dokploy/contents/openapi.json?ref=${TAG}" \
  --jq '.content' | base64 -d | jq . > "$OUTFILE"

echo "Saved: $OUTFILE ($(wc -c < "$OUTFILE") bytes)"
