#!/usr/bin/env bash
# Deploy staging when the GHCR edge digests change. A systemd timer runs this
# every 15 minutes. Prod is never touched.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
ENV_DIR=${PORTFOLIA_ENV_DIR:-$(cd "$ROOT/.." && pwd)/env}
REGISTRY_PATH=${PORTFOLIA_REGISTRY_PATH:-vedantparikh}
state=$ENV_DIR/staging.digest
deploy_cmd=${STAGING_DEPLOY:-$ROOT/scripts/deploy.sh}

edge_digest() {
  local name=$1 headers
  headers=$(curl -fsSL -D - -o /dev/null \
    -H "Accept: application/vnd.oci.image.index.v1+json" \
    -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
    "https://ghcr.io/v2/${REGISTRY_PATH}/portfolia-${name}/manifests/edge") || return 1
  printf '%s\n' "$headers" | awk 'tolower($1)=="docker-content-digest:" {print $2}' | tr -d '\r' | head -n 1
}

seed_if_empty() {
  if [ -n "${STAGING_SEED_CMD:-}" ]; then
    # shellcheck disable=SC2086
    $STAGING_SEED_CMD
    return
  fi
  local count
  count=$(docker compose -f "$ROOT/compose.yaml" -f "$ROOT/compose.staging.yaml" exec -T api \
    python -c 'from core.database.connection import SessionLocal; from core.database.models import User; db=SessionLocal(); print(db.query(User).count()); db.close()')
  count=$(printf '%s' "$count" | tr -d '[:space:]')
  if [ "$count" != 0 ]; then
    echo "staging already has users"
    return 0
  fi
  echo "seeding staging demo data"
  docker compose -f "$ROOT/compose.yaml" -f "$ROOT/compose.staging.yaml" exec -T api \
    python scripts/seed_demo_application.py \
    --base-url http://127.0.0.1:8000 \
    --years 1 \
    --max-trades-daily 30 \
    --max-trades-weekly 12 \
    --max-trades-monthly 8
}

api=$(edge_digest api) || {
  echo "edge manifest not available; skipping"
  exit 0
}
web=$(edge_digest web) || {
  echo "edge manifest not available; skipping"
  exit 0
}
if [ -z "$api" ] || [ -z "$web" ]; then
  echo "edge digest missing; skipping"
  exit 0
fi
want="$api $web"
have=$(cat "$state" 2>/dev/null || true)
if [ "$have" = "$want" ]; then
  echo "edge unchanged"
else
  echo "edge changed; deploying staging"
  "$deploy_cmd" staging edge
  mkdir -p "$ENV_DIR"
  tmp=$(mktemp "$ENV_DIR/.digest.XXXXXX")
  printf '%s\n' "$want" >"$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$state"
fi
seed_if_empty
