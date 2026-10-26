#!/usr/bin/env bash
# Restore a custom-format dump into staging, or into prod with --allow-prod.
#   scripts/restore.sh staging /path/to/prod-YYYYMMDD.dump
#   scripts/restore.sh prod /path/to/prod-YYYYMMDD.dump --allow-prod
#
# Stops api, app, and worker, then pg_restore --clean. Does not delete
# volumes, does not create Postgres, and does not start apps again if the
# restore fails.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
ENV_DIR=${PORTFOLIA_ENV_DIR:-$(cd "$ROOT/.." && pwd)/env}
unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES

usage() {
  echo "usage: scripts/restore.sh <prod|staging> <dump> [--allow-prod]" >&2
  exit 2
}

env_name=${1:-}
dump=${2:-}
[ -n "$env_name" ] && [ -n "$dump" ] || usage
shift 2
allow_prod=0
for arg in "$@"; do
  case "$arg" in
    --allow-prod) allow_prod=1 ;;
    *) usage ;;
  esac
done

case "$env_name" in
  prod | staging) ;;
  *) usage ;;
esac

if [ "$env_name" = prod ] && [ "$allow_prod" -ne 1 ]; then
  echo "refusing to restore over prod; pass --allow-prod" >&2
  exit 2
fi

[ -f "$dump" ] && [ -s "$dump" ] || {
  echo "dump is missing or empty" >&2
  exit 1
}
[ "$(head -c 5 "$dump")" = PGDMP ] || {
  echo "dump is not custom format" >&2
  exit 1
}

case "$env_name" in
  prod) env_file=$ENV_DIR/prod.env ;;
  staging) env_file=$ENV_DIR/staging.env ;;
esac
[ -f "$env_file" ] || {
  echo "missing $env_file" >&2
  exit 1
}

compose() {
  local -a files=(-f "$ROOT/compose.yaml")
  if [ "$env_name" = staging ]; then
    files+=(-f "$ROOT/compose.staging.yaml")
  fi
  docker compose "${files[@]}" "$@"
}

compose ps --status running --services | grep -qx postgres || {
  echo "postgres is not running; refusing to create it" >&2
  exit 1
}

running=$(compose ps --status running --services)
stopped=
for svc in api app worker; do
  if printf '%s\n' "$running" | grep -qx "$svc"; then
    compose stop "$svc"
    stopped="$stopped $svc"
  fi
done

set +e
compose exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl --exit-on-error' \
  <"$dump"
status=$?
set -e
if [ "$status" -ne 0 ]; then
  echo "restore failed; api, app, and worker left stopped" >&2
  exit 1
fi

if [ -n "$stopped" ]; then
  # shellcheck disable=SC2086
  compose start $stopped
fi
echo "restored $env_name from $dump"
