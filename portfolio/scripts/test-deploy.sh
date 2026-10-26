#!/usr/bin/env bash
# Proves a failed smoke check redeploys the recorded version and does not
# recreate Postgres. Uses fake docker and curl, never the live stack.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
script=$root/scripts/deploy.sh
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/env" "$tmp/backups"

cat >"$tmp/bin/docker" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$DEPLOY_LOG"
case "$*" in
  *' ps '*)
    printf '%s\n' postgres redis api
    ;;
  image' 'ls*)
    printf '%s\n' \
      'ghcr.io/vedantparikh/portfolia-api:0.1.0' \
      'ghcr.io/vedantparikh/portfolia-api:0.0.9' \
      'ghcr.io/vedantparikh/portfolia-web:0.0.9' \
      'ghcr.io/vedantparikh/portfolia-api:prod' \
      'ghcr.io/vedantparikh/portfolia-api:edge'
    ;;
  *' exec '*)
    printf 'PGDMP'
    ;;
esac
exit 0
EOF

cat >"$tmp/bin/curl" <<'EOF'
#!/bin/sh
case "${PORTFOLIO_API_IMAGE:-}" in
  *:0.2.0) exit 1 ;;
esac
exit 0
EOF
chmod 755 "$tmp/bin/docker" "$tmp/bin/curl"

common=(
  env
  PATH="$tmp/bin:$PATH"
  PORTFOLIA_ENV_DIR="$tmp/env"
  PORTFOLIA_BACKUP_DIR="$tmp/backups"
  SMOKE_ATTEMPTS=1
  SMOKE_SLEEP=0
)

fail() {
  echo "FAIL $*" >&2
  exit 1
}

# Broken release rolls back to the recorded version.
printf '%s\n' 0.1.0 >"$tmp/env/prod.env"
printf '%s\n' 0.1.0 >"$tmp/env/prod.deployed"
log=$tmp/rollback.log
: >"$log"
set +e
"${common[@]}" DEPLOY_LOG="$log" "$script" prod 0.2.0 >"$tmp/rollback.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ] || fail "broken deploy exited 0"
grep -q 'rolling back to 0.1.0' "$tmp/rollback.out" || fail "no rollback message"
grep -qx '0.1.0' "$tmp/env/prod.deployed" || fail "state file changed"
grep -c 'run --rm --no-deps migrate' "$log" | grep -qx 1 || fail "migrate did not run exactly once"
grep -q 'pull api app worker' "$log" || fail "did not pull"
dumps=$(find "$tmp/backups" -name 'prod-*.dump' | wc -l)
[ "$dumps" -ge 1 ] || fail "no backup"
grep -q 'rmi ghcr.io/vedantparikh/portfolia-api:0.2.0' "$log" || fail "failed image kept"
grep -q 'rmi ghcr.io/vedantparikh/portfolia-api:0.0.9' "$log" || fail "old release kept"
if grep 'up ' "$log" | grep -q postgres; then
  fail "prod up included postgres"
fi
if grep -q 'rmi ghcr.io/vedantparikh/portfolia-api:prod' "$log"; then
  fail "pruned the local prod tag"
fi
echo "broken 0.2.0 rolled back to 0.1.0"

# No recorded version: stay failed, do not invent a rollback.
rm -f "$tmp/env/prod.deployed"
log=$tmp/norecord.log
: >"$log"
set +e
"${common[@]}" DEPLOY_LOG="$log" "$script" prod v0.2.0 >"$tmp/norecord.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ] || fail "unrecorded failure exited 0"
if grep -q 'rolling back' "$tmp/norecord.out"; then
  fail "rolled back with no recorded version"
fi
[ ! -f "$tmp/env/prod.deployed" ] || fail "recorded a failed version"

# Successful deploy keeps the last three releases and the local prod tag.
printf '%s\n' 0.1.1 >"$tmp/env/prod.deployed"
printf '%s\n' 0.1.1 0.1.0 >"$tmp/env/prod.history"
log=$tmp/ok.log
: >"$log"
"${common[@]}" DEPLOY_LOG="$log" "$script" prod 0.1.2 >"$tmp/ok.out"
grep -qx '0.1.2' "$tmp/env/prod.deployed" || fail "success did not record"
grep -qx '0.1.2' <(head -n 1 "$tmp/env/prod.history") || fail "history order"
grep -q 'rmi ghcr.io/vedantparikh/portfolia-api:0.0.9' "$log" || fail "did not prune 0.0.9"
if grep -q 'rmi ghcr.io/vedantparikh/portfolia-api:0.1.0' "$log"; then
  fail "pruned a kept release"
fi
echo "0.1.2 recorded and older than the last three pruned"

# Staging may create its own database. Prod may not take edge.
printf '%s\n' staging >"$tmp/env/staging.env"
log=$tmp/staging.log
: >"$log"
"${common[@]}" DEPLOY_LOG="$log" "$script" staging edge >"$tmp/staging.out"
grep -q 'compose.staging.yaml' "$log" || fail "staging file not used"
grep 'up ' "$log" | grep -q postgres || fail "staging did not start postgres"
set +e
"${common[@]}" DEPLOY_LOG="$tmp/edge.log" "$script" prod edge >"$tmp/edge.out" 2>&1
status=$?
set -e
[ "$status" -eq 2 ] || fail "prod edge was accepted"
echo "deploy checks passed"
