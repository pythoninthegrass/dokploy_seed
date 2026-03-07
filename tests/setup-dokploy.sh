#!/usr/bin/env bash
set -euo pipefail

# Reusable Dokploy bootstrap for E2E tests.
# Works on any Linux with Docker installed (GHA ubuntu-latest, OrbStack VM, etc.).
#
# Outputs DOKPLOY_URL and DOKPLOY_API_KEY to stdout.
# If $GITHUB_OUTPUT is set, also writes them as step outputs.

DOKPLOY_PORT="${DOKPLOY_PORT:-3000}"
DOKPLOY_URL="http://localhost:${DOKPLOY_PORT}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@e2e.test}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-E2eTestPass123!}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-e2e-pg-pass}"

log() { printf '[setup-dokploy] %s\n' "$*"; }

log "Initializing Docker Swarm..."
docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || true

log "Creating overlay network..."
docker network create --driver overlay --attachable dokploy-network 2>/dev/null || true

log "Creating Docker secret for postgres password..."
echo "$POSTGRES_PASSWORD" | docker secret create dokploy_postgres_password - 2>/dev/null || true

log "Creating /etc/dokploy directory..."
mkdir -p /etc/dokploy

log "Waiting for DNS..."
elapsed=0
until getent hosts registry-1.docker.io >/dev/null 2>&1; do
  if [ "$elapsed" -ge 30 ]; then
    log "ERROR: DNS not available after 30s"
    exit 1
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done

log "Pulling images in parallel..."
docker pull postgres:16 &
pid1=$!
docker pull redis:7 &
pid2=$!
docker pull dokploy/dokploy:latest &
pid3=$!
wait "$pid1" "$pid2" "$pid3"

if [ "${PREPARE_ONLY:-}" = "1" ]; then
  log "Prepare-only mode: stopping after image pull"
  exit 0
fi

log "Starting postgres service..."
docker service create \
  --name dokploy-postgres \
  --network dokploy-network \
  --secret dokploy_postgres_password \
  --env POSTGRES_PASSWORD_FILE=/run/secrets/dokploy_postgres_password \
  --env POSTGRES_USER=dokploy \
  --env POSTGRES_DB=dokploy \
  --replicas 1 \
  --detach \
  --no-resolve-image \
  postgres:16 2>/dev/null || log "postgres service already exists"

log "Starting redis service..."
docker service create \
  --name dokploy-redis \
  --network dokploy-network \
  --replicas 1 \
  --detach \
  --no-resolve-image \
  redis:7 2>/dev/null || log "redis service already exists"

log "Starting dokploy service..."
docker service create \
  --name dokploy \
  --network dokploy-network \
  --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
  --mount type=bind,source=/etc/dokploy,target=/etc/dokploy \
  --mount type=volume,source=dokploy,target=/root/.docker \
  --secret source=dokploy_postgres_password,target=/run/secrets/postgres_password \
  --publish published="${DOKPLOY_PORT}",target=3000,mode=host \
  --replicas 1 \
  --detach \
  --no-resolve-image \
  --env RELEASE_TAG=latest \
  --env DOCKER_CLEANUP_ENABLED=false \
  --env ADVERTISE_ADDR=127.0.0.1 \
  --env POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password \
  dokploy/dokploy:latest 2>/dev/null || log "dokploy service already exists"

log "Waiting for Dokploy health check (timeout: ${HEALTH_TIMEOUT}s)..."
elapsed=0
until curl -sf "${DOKPLOY_URL}/api/trpc/settings.health" >/dev/null 2>&1; do
  if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
    log "ERROR: Health check timed out after ${HEALTH_TIMEOUT}s"
    docker service logs dokploy --tail 50 2>/dev/null || true
    exit 1
  fi
  sleep 2
  elapsed=$((elapsed + 2))
  if [ $((elapsed % 10)) -eq 0 ]; then
    log "  ...waiting (${elapsed}s)"
  fi
done
log "Dokploy is healthy (${elapsed}s)"

log "Registering admin user..."
SIGNUP_RESPONSE=$(curl -sf -X POST "${DOKPLOY_URL}/api/auth/sign-up/email" \
  -H "Content-Type: application/json" \
  -H "Origin: ${DOKPLOY_URL}" \
  -c /tmp/dokploy-cookies.txt \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\",\"name\":\"E2E\",\"lastName\":\"Admin\"}")

if [ -z "$SIGNUP_RESPONSE" ]; then
  log "ERROR: Admin registration returned empty response"
  exit 1
fi
log "Admin registered"

log "Creating API key..."
API_KEY_RESPONSE=$(curl -sf -X POST "${DOKPLOY_URL}/api/auth/api-key/create" \
  -H "Content-Type: application/json" \
  -H "Origin: ${DOKPLOY_URL}" \
  -b /tmp/dokploy-cookies.txt \
  -d '{"name":"e2e-test-key"}')

DOKPLOY_API_KEY=$(echo "$API_KEY_RESPONSE" | jq -r '.key // empty')
API_KEY_ID=$(echo "$API_KEY_RESPONSE" | jq -r '.id // empty')
if [ -z "$DOKPLOY_API_KEY" ]; then
  log "ERROR: Failed to extract API key from response: ${API_KEY_RESPONSE}"
  exit 1
fi
log "API key created (id: ${API_KEY_ID})"

# Dokploy's validateRequest reads organizationId from API key metadata.
# The better-auth api-key/create endpoint does not support metadata, so we
# patch the apikey row in postgres directly.
log "Patching API key metadata with organizationId..."
PG_CONTAINER=$(docker ps -q -f name=dokploy-postgres)
ORG_ID=$(docker exec "$PG_CONTAINER" psql -U dokploy -d dokploy -t -A \
  -c "SELECT organization_id FROM member WHERE role = 'owner' LIMIT 1;")
if [ -z "$ORG_ID" ]; then
  log "ERROR: Could not find owner organization_id in member table"
  exit 1
fi
docker exec "$PG_CONTAINER" psql -U dokploy -d dokploy -c \
  "UPDATE apikey SET metadata = '{\"organizationId\": \"${ORG_ID}\"}', rate_limit_enabled = false WHERE id = '${API_KEY_ID}';" >/dev/null
log "API key patched (organizationId: ${ORG_ID}, rate_limit disabled)"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "DOKPLOY_URL=${DOKPLOY_URL}" >> "$GITHUB_OUTPUT"
  echo "DOKPLOY_API_KEY=${DOKPLOY_API_KEY}" >> "$GITHUB_OUTPUT"
fi

log "Setup complete"
echo "DOKPLOY_URL=${DOKPLOY_URL}"
echo "DOKPLOY_API_KEY=${DOKPLOY_API_KEY}"
