#!/usr/bin/env bash
# Restore the newest prod daily dump into staging and compare table counts.
#   scripts/restore-drill.sh
# Never targets project portfolio. Postgres for staging must already be running.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
ENV_DIR=${PORTFOLIA_ENV_DIR:-$(cd "$ROOT/.." && pwd)/env}
BACKUP_DIR=${PORTFOLIA_BACKUP_DIR:-/mnt/samsung_ufs/backups/portfolio}
RESTORE_BIN=${RESTORE_BIN:-$ROOT/scripts/restore.sh}
unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES

dump=$(find "$BACKUP_DIR/daily" -maxdepth 1 -name 'prod-*.dump' -printf '%f\n' 2>/dev/null | sort | tail -n 1)
[ -n "$dump" ] || {
  echo "no prod dump to drill" >&2
  exit 1
}
dump="$BACKUP_DIR/daily/$dump"
sidecar="${dump%.dump}.tables"
[ -f "$sidecar" ] || {
  echo "missing table count for $(basename "$dump")" >&2
  exit 1
}
expected=$(tr -d '[:space:]' <"$sidecar")
printf '%s' "$expected" | grep -Eq '^[0-9]+$' || {
  echo "table count sidecar is not a number" >&2
  exit 1
}

"$RESTORE_BIN" staging "$dump"

count=$(
  docker compose -f "$ROOT/compose.yaml" -f "$ROOT/compose.staging.yaml" exec -T postgres sh -c \
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '"'"'public'"'"'"' \
    | tr -d '[:space:]'
)
[ "$count" = "$expected" ] || {
  echo "restored table count $count, dump recorded $expected" >&2
  exit 1
}

umask 077
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ) $dump" >"$ENV_DIR/restore-drill.ok"
chmod 600 "$ENV_DIR/restore-drill.ok"
echo "restore drill ok ($count tables)"
