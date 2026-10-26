#!/usr/bin/env bash
# Nightly custom-format dump of Postgres.
#   scripts/backup.sh [prod|staging]
#
# Writes $PORTFOLIA_BACKUP_DIR/daily/<env>-YYYYMMDD.dump (14 kept) and
# weekly/<env>-YYYY-Www.dump (8 kept). Deploy dumps in the directory root
# are left alone. Postgres must already be running; this does not create it.
# If env/backup.env sets NEXTCLOUD_URL, NEXTCLOUD_USER and
# NEXTCLOUD_APP_PASSWORD, the new daily file is uploaded. A missing file
# skips that copy.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
ENV_DIR=${PORTFOLIA_ENV_DIR:-$(cd "$ROOT/.." && pwd)/env}
BACKUP_DIR=${PORTFOLIA_BACKUP_DIR:-/mnt/samsung_ufs/backups/portfolio}
unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES

usage() {
  echo "usage: scripts/backup.sh [prod|staging]" >&2
  exit 2
}

env_name=${1:-prod}
case "$env_name" in
  prod | staging) ;;
  *) usage ;;
esac
[ "$#" -le 1 ] || usage

case "$env_name" in
  prod) env_file=$ENV_DIR/prod.env ;;
  staging) env_file=$ENV_DIR/staging.env ;;
esac
[ -f "$env_file" ] || {
  echo "missing $env_file" >&2
  exit 1
}

day=${BACKUP_DATE:-$(date -u +%Y%m%d)}
week=${BACKUP_WEEK:-$(date -u +%G-W%V)}
printf '%s' "$day" | grep -Eq '^[0-9]{8}$' || usage
printf '%s' "$week" | grep -Eq '^[0-9]{4}-W[0-9]{2}$' || usage

compose() {
  local -a files=(-f "$ROOT/compose.yaml")
  if [ "$env_name" = staging ]; then
    files+=(-f "$ROOT/compose.staging.yaml")
  fi
  docker compose "${files[@]}" "$@"
}

postgres_running() {
  compose ps --status running --services | grep -qx postgres
}

table_count() {
  compose exec -T postgres sh -c \
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '"'"'public'"'"'"'
}

prune_keep() {
  local dir=$1 keep=$2 prefix=$3
  local -a files=()
  local f drop i
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    files+=("$f")
  done < <(find "$dir" -maxdepth 1 -name "${prefix}-*.dump" -printf '%f\n' | sort)
  drop=$((${#files[@]} - keep))
  i=0
  while [ "$i" -lt "$drop" ]; do
    rm -f "$dir/${files[$i]}" "$dir/${files[$i]%.dump}.tables"
    i=$((i + 1))
  done
}

upload_nextcloud() {
  local file=$1
  if [ -n "${PORTFOLIA_NEXTCLOUD_PUT:-}" ]; then
    "$PORTFOLIA_NEXTCLOUD_PUT" "$file"
    echo "nextcloud copy $(basename "$file")"
    return 0
  fi
  local cfg=$ENV_DIR/backup.env
  if [ ! -f "$cfg" ]; then
    echo "nextcloud copy not configured"
    return 0
  fi
  local url user pass
  url=$(awk -F= '$1=="NEXTCLOUD_URL"{print substr($0, index($0,"=")+1); exit}' "$cfg")
  user=$(awk -F= '$1=="NEXTCLOUD_USER"{print substr($0, index($0,"=")+1); exit}' "$cfg")
  pass=$(awk -F= '$1=="NEXTCLOUD_APP_PASSWORD"{print substr($0, index($0,"=")+1); exit}' "$cfg")
  url=${url%$'\r'}
  user=${user%$'\r'}
  pass=${pass%$'\r'}
  url=${url#\"}
  url=${url%\"}
  user=${user#\"}
  user=${user%\"}
  pass=${pass#\"}
  pass=${pass%\"}
  if [ -z "$url" ] || [ -z "$user" ] || [ -z "$pass" ]; then
    echo "backup.env is incomplete; local dump kept" >&2
    return 1
  fi
  curl -fsS --retry 2 --user "${user}:${pass}" -T "$file" "${url%/}/$(basename "$file")" >/dev/null
  echo "nextcloud copy $(basename "$file")"
}

postgres_running || {
  echo "postgres is not running; refusing to create it" >&2
  exit 1
}

umask 077
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"
daily="$BACKUP_DIR/daily/${env_name}-${day}.dump"
compose exec -T postgres sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >"$daily"
if [ ! -s "$daily" ] || [ "$(head -c 5 "$daily")" != PGDMP ]; then
  rm -f "$daily"
  echo "backup is empty or not a custom-format dump" >&2
  exit 1
fi
chmod 600 "$daily"
count=$(table_count | tr -d '[:space:]')
printf '%s' "$count" | grep -Eq '^[0-9]+$' || {
  echo "table count missing" >&2
  exit 1
}
printf '%s\n' "$count" >"${daily%.dump}.tables"
chmod 600 "${daily%.dump}.tables"
echo "backup $daily ($count tables)"

weekly="$BACKUP_DIR/weekly/${env_name}-${week}.dump"
if [ ! -f "$weekly" ]; then
  cp -p "$daily" "$weekly"
  chmod 600 "$weekly"
  echo "weekly $weekly"
fi

prune_keep "$BACKUP_DIR/daily" 14 "$env_name"
prune_keep "$BACKUP_DIR/weekly" 8 "$env_name"
upload_nextcloud "$daily"
