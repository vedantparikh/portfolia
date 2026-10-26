#!/usr/bin/env bash
# Deploy a published image to prod or staging.
#   scripts/deploy.sh prod 0.1.0
#   scripts/deploy.sh staging edge
#
# Prod only restarts api, app, and worker (--no-deps). Postgres and Redis
# must already be running; this script will not create or recreate them.
# A failed start or smoke check redeploys the version in env/<env>.deployed.
# Rollback does not run migrations: the previous image must tolerate the
# schema (expand, then migrate, then contract).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
ENV_DIR=${PORTFOLIA_ENV_DIR:-$(cd "$ROOT/.." && pwd)/env}
BACKUP_DIR=${PORTFOLIA_BACKUP_DIR:-/mnt/samsung_ufs/backups/portfolio}
REGISTRY=${PORTFOLIA_REGISTRY:-ghcr.io/vedantparikh}
unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES

usage() {
  echo "usage: scripts/deploy.sh <prod|staging> <X.Y.Z|edge|sha-...> [--allow-irreversible]" >&2
  exit 2
}

env_name=${1:-}
version=${2:-}
[ -n "$env_name" ] && [ -n "$version" ] || usage
shift 2 || usage
allow_irreversible=0
for arg in "$@"; do
  case "$arg" in
    --allow-irreversible) allow_irreversible=1 ;;
    *) usage ;;
  esac
done

case "$env_name" in
  prod | staging) ;;
  *) usage ;;
esac

if [ "${version#v}" != "$version" ]; then
  rest=${version#v}
  if printf '%s' "$rest" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    version=$rest
  fi
fi
case "$version" in
  edge)
    [ "$env_name" = staging ] || {
      echo "prod deploys a version (X.Y.Z), not edge" >&2
      exit 2
    }
    ;;
  sha-*)
    printf '%s' "${version#sha-}" | grep -Eq '^[0-9a-fA-F]{7,}$' || usage
    ;;
  *)
    printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || usage
    ;;
esac

case "$env_name" in
  prod)
    env_file=$ENV_DIR/prod.env
    export PORTFOLIO_UI_PORT=${PORTFOLIO_UI_PORT:-3000}
    export PORTFOLIO_API_PORT=${PORTFOLIO_API_PORT:-8000}
    ;;
  staging)
    env_file=$ENV_DIR/staging.env
    export PORTFOLIO_UI_PORT=${PORTFOLIO_STAGING_UI_PORT:-3100}
    export PORTFOLIO_API_PORT=${PORTFOLIO_STAGING_API_PORT:-8100}
    ;;
esac
[ -f "$env_file" ] || {
  echo "missing $env_file" >&2
  exit 1
}

state_file=$ENV_DIR/${env_name}.deployed
history_file=$ENV_DIR/${env_name}.history
phase=init
ROLLBACK=${ROLLBACK:-}

set_images() {
  export PORTFOLIO_API_IMAGE="${REGISTRY}/portfolia-api:${version}"
  export PORTFOLIO_WEB_IMAGE="${REGISTRY}/portfolia-web:${version}"
}

compose() {
  local -a files=(-f "$ROOT/compose.yaml")
  if [ "$env_name" = staging ]; then
    files+=(-f "$ROOT/compose.staging.yaml")
  fi
  docker compose "${files[@]}" "$@"
}

backup() {
  mkdir -p "$BACKUP_DIR"
  local out="$BACKUP_DIR/${env_name}-${version}-$(date -u +%Y%m%dT%H%M%SZ).dump"
  compose exec -T postgres sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >"$out"
  if [ ! -s "$out" ]; then
    rm -f "$out"
    echo "backup is empty" >&2
    return 1
  fi
  chmod 600 "$out"
  echo "backup $out"
}

postgres_running() {
  compose ps --status running --services | grep -qx postgres
}

up_services() {
  if [ "$env_name" = prod ]; then
    local running
    running=$(compose ps --status running --services)
    printf '%s\n' "$running" | grep -qx postgres || {
      echo "prod postgres is not running; refusing to create it" >&2
      return 1
    }
    printf '%s\n' "$running" | grep -qx redis || {
      echo "prod redis is not running; refusing to create it" >&2
      return 1
    }
    # --no-deps: do not let Compose recreate postgres or redis.
    compose up -d --wait --wait-timeout 180 --no-deps api app || return 1
    compose up -d --no-deps worker || return 1
  else
    compose up -d --wait --wait-timeout 180 postgres redis api app || return 1
    compose up -d --no-deps worker || return 1
  fi
}

smoke() {
  local url attempt
  local -a urls=(
    "http://127.0.0.1:${PORTFOLIO_UI_PORT}/"
    "http://127.0.0.1:${PORTFOLIO_UI_PORT}/api/v1/"
    "http://127.0.0.1:${PORTFOLIO_API_PORT}/health/live"
    "http://127.0.0.1:${PORTFOLIO_API_PORT}/health/ready"
  )
  for url in "${urls[@]}"; do
    attempt=1
    while [ "$attempt" -le "${SMOKE_ATTEMPTS:-6}" ]; do
      if curl -fsS -o /dev/null --max-time 10 "$url"; then
        echo "ok  $url"
        break
      fi
      if [ "$attempt" -eq "${SMOKE_ATTEMPTS:-6}" ]; then
        echo "FAIL $url" >&2
        return 1
      fi
      sleep "${SMOKE_SLEEP:-5}"
      attempt=$((attempt + 1))
    done
  done
}

record() {
  local tmp
  tmp=$(mktemp "$ENV_DIR/.deployed.XXXXXX")
  printf '%s\n' "$version" >"$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$state_file"
  {
    printf '%s\n' "$version"
    if [ -f "$history_file" ]; then
      grep -vx "$version" "$history_file" || true
    fi
  } | head -n 3 >"$history_file.new"
  chmod 600 "$history_file.new"
  mv "$history_file.new" "$history_file"
  echo "deployed $env_name $version"
  if [ "$allow_irreversible" -eq 1 ]; then
    echo "allow-irreversible set"
  fi
}

prune() {
  [ -f "$history_file" ] || return 0
  local keep line repo tag
  keep=$(head -n 3 "$history_file")
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    repo=${line%:*}
    tag=${line##*:}
    case "$repo" in
      "$REGISTRY/portfolia-api" | "$REGISTRY/portfolia-web") ;;
      *) continue ;;
    esac
    case "$tag" in
      [0-9]*.[0-9]*.[0-9]*) ;;
      *) continue ;;
    esac
    if printf '%s\n' "$keep" | grep -qx "$tag"; then
      continue
    fi
    docker rmi "$repo:$tag" || true
  done < <(docker image ls --format '{{.Repository}}:{{.Tag}}')
}

deploy_version() {
  set_images
  phase=pull
  echo "pull $PORTFOLIO_API_IMAGE"
  compose pull api app worker || return 1
  compose --profile migrate pull migrate || return 1
  phase=backup
  if postgres_running; then
    backup || return 1
  elif [ "$env_name" = prod ]; then
    echo "prod postgres is not running; refusing to create it" >&2
    return 1
  else
    echo "no staging database yet; skipping backup"
    compose up -d --wait --wait-timeout 180 postgres redis || return 1
  fi
  if [ "${ROLLBACK:-}" != 1 ]; then
    phase=migrate
    compose --profile migrate run --rm --no-deps migrate || return 1
  else
    echo "rollback skips migrate"
  fi
  phase=up
  up_services || return 1
  phase=smoke
  smoke || return 1
  phase=record
  record || return 1
  phase=prune
  prune || true
  phase=done
}

failed_version=$version
if ! deploy_version; then
  if [ "${ROLLBACK:-}" = 1 ]; then
    echo "rollback of $version failed during $phase" >&2
    exit 1
  fi
  prev=$(tr -d '[:space:]' <"$state_file" 2>/dev/null || true)
  if [ -n "$prev" ] && [ "$prev" != "$failed_version" ] && { [ "$phase" = up ] || [ "$phase" = smoke ]; }; then
    echo "rolling back to $prev" >&2
    ROLLBACK=1
    version=$prev
    if ! deploy_version; then
      echo "rollback of $prev failed during $phase" >&2
      exit 1
    fi
    docker rmi "$REGISTRY/portfolia-api:$failed_version" "$REGISTRY/portfolia-web:$failed_version" || true
    exit 1
  fi
  echo "deploy of $failed_version failed during $phase" >&2
  exit 1
fi
