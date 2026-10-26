#!/usr/bin/env bash
# Retention, the Nextcloud hook, and a staging restore drill. No live Docker.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/env" "$tmp/backups/daily" "$tmp/backups/weekly"
printf '%s\n' prod >"$tmp/env/prod.env"
printf '%s\n' staging >"$tmp/env/staging.env"

cat >"$tmp/bin/docker" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$DOCKER_LOG"
case "$*" in
  *' ps '*)
    if [ "${FAKE_PS:-running}" = empty ]; then
      exit 0
    fi
    printf '%s\n' postgres api app worker
    ;;
  *pg_dump*)
    printf 'PGDMP' 
    ;;
  *information_schema.tables*)
    printf '%s\n' "${FAKE_TABLES:-7}"
    ;;
  *pg_restore*)
    magic=$(head -c 5)
    cat >/dev/null
    [ "$magic" = PGDMP ] || exit 1
    ;;
  *' stop '*|*' start '*)
    ;;
  *)
    echo "unexpected docker: $*" >&2
    exit 1
    ;;
esac
EOF
cat >"$tmp/bin/put" <<'EOF'
#!/bin/sh
cp "$1" "$PUT_COPY"
EOF
chmod 755 "$tmp/bin/docker" "$tmp/bin/put"

fail() {
  echo "FAIL $*" >&2
  exit 1
}

common=(
  env PATH="$tmp/bin:$PATH"
  PORTFOLIA_ENV_DIR="$tmp/env"
  PORTFOLIA_BACKUP_DIR="$tmp/backups"
  DOCKER_LOG="$tmp/docker.log"
)

# Postgres down: do not create it, do not write a dump.
: >"$tmp/docker.log"
set +e
"${common[@]}" FAKE_PS=empty "$root/scripts/backup.sh" >"$tmp/down.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ] || fail "backup created postgres"
grep -q 'refusing to create it' "$tmp/down.out" || fail "missing refusal"
[ -z "$(find "$tmp/backups" -name '*.dump' -print -quit)" ] || fail "dump written without postgres"
grep -q ' up ' "$tmp/docker.log" && fail "backup ran up" || true

# One daily dump, a weekly copy, and a Nextcloud put.
: >"$tmp/docker.log"
"${common[@]}" BACKUP_DATE=20261026 BACKUP_WEEK=2026-W44 \
  PORTFOLIA_NEXTCLOUD_PUT="$tmp/bin/put" PUT_COPY="$tmp/uploaded.dump" \
  "$root/scripts/backup.sh"
daily=$tmp/backups/daily/prod-20261026.dump
[ -s "$daily" ] || fail "daily dump missing"
[ "$(head -c 5 "$daily")" = PGDMP ] || fail "dump magic"
[ "$(stat -c %a "$daily")" = 600 ] || fail "dump mode"
[ "$(cat "$tmp/backups/daily/prod-20261026.tables")" = 7 ] || fail "table sidecar"
[ -f "$tmp/backups/weekly/prod-2026-W44.dump" ] || fail "weekly copy"
[ -s "$tmp/uploaded.dump" ] || fail "nextcloud put was not called"
grep -q 'compose.staging.yaml' "$tmp/docker.log" && fail "prod backup used staging" || true
grep -q ' up ' "$tmp/docker.log" && fail "backup ran up" || true

# Same week does not replace the weekly file.
printf 'OLD\n' >"$tmp/backups/weekly/prod-2026-W44.dump"
"${common[@]}" BACKUP_DATE=20261027 BACKUP_WEEK=2026-W44 "$root/scripts/backup.sh" >/dev/null
[ "$(cat "$tmp/backups/weekly/prod-2026-W44.dump")" = OLD ] || fail "weekly overwritten"

# 14 daily and 8 weekly kept. Deploy-style files in the root stay.
i=1
while [ "$i" -le 20 ]; do
  printf 'PGDMP' >"$(printf '%s/backups/daily/prod-202609%02d.dump' "$tmp" "$i")"
  i=$((i + 1))
done
i=1
while [ "$i" -le 10 ]; do
  printf 'PGDMP' >"$(printf '%s/backups/weekly/prod-2025-W%02d.dump' "$tmp" "$i")"
  i=$((i + 1))
done
printf 'PGDMP' >"$tmp/backups/prod-0.1.0-deploy.dump"
"${common[@]}" BACKUP_DATE=20261028 BACKUP_WEEK=2026-W44 "$root/scripts/backup.sh" >/dev/null
daily_n=$(find "$tmp/backups/daily" -name 'prod-*.dump' | wc -l)
weekly_n=$(find "$tmp/backups/weekly" -name 'prod-*.dump' | wc -l)
[ "$daily_n" -eq 14 ] || fail "daily retention $daily_n"
[ "$weekly_n" -eq 8 ] || fail "weekly retention $weekly_n"
[ -f "$tmp/backups/prod-0.1.0-deploy.dump" ] || fail "deploy dump pruned"
[ ! -f "$tmp/backups/daily/prod-20260901.dump" ] || fail "oldest daily kept"

# Prod restore is refused before Docker. Staging restore uses the overlay.
: >"$tmp/docker.log"
set +e
"${common[@]}" "$root/scripts/restore.sh" prod "$daily" >"$tmp/prod-restore.out" 2>&1
status=$?
set -e
[ "$status" -eq 2 ] || fail "prod restore was accepted"
grep -q 'refusing to restore over prod' "$tmp/prod-restore.out" || fail "missing prod refusal"
[ ! -s "$tmp/docker.log" ] || fail "prod restore called docker"

: >"$tmp/docker.log"
"${common[@]}" "$root/scripts/restore.sh" staging "$daily" >"$tmp/restore.out"
grep -q 'compose.staging.yaml' "$tmp/docker.log" || fail "staging restore project"
grep -q 'pg_restore' "$tmp/docker.log" || fail "pg_restore not run"
grep -q ' stop ' "$tmp/docker.log" || fail "apps not stopped"
grep -q ' start ' "$tmp/docker.log" || fail "apps not started"
grep -q ' down ' "$tmp/docker.log" && fail "restore ran down" || true
grep -q 'restored staging' "$tmp/restore.out" || fail "restore message"

# Drill restores that dump into staging and records success.
: >"$tmp/docker.log"
rm -f "$tmp/env/restore-drill.ok"
"${common[@]}" "$root/scripts/restore-drill.sh" >"$tmp/drill.out"
[ -s "$tmp/env/restore-drill.ok" ] || fail "drill marker"
grep -q 'compose.staging.yaml' "$tmp/docker.log" || fail "drill used prod project"
grep -q 'restore drill ok' "$tmp/drill.out" || fail "drill message"

# A mismatched count fails and does not record success.
rm -f "$tmp/env/restore-drill.ok"
set +e
"${common[@]}" FAKE_TABLES=1 "$root/scripts/restore-drill.sh" >"$tmp/mismatch.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ] || fail "mismatched drill passed"
[ ! -f "$tmp/env/restore-drill.ok" ] || fail "failed drill recorded success"
echo "backup checks passed"
