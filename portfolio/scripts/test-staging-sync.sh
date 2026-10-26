#!/usr/bin/env bash
# edge digest changes deploy staging once. A missing manifest does nothing.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/env"
printf '%s\n' staging >"$tmp/env/staging.env"

cat >"$tmp/bin/curl" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$CURL_LOG"
if [ "${CURL_FAIL:-}" = 1 ]; then
  exit 22
fi
name=api
case "$*" in
  *portfolia-web*) name=web ;;
esac
printf 'docker-content-digest: sha256:%s\n' "$name"
EOF
cat >"$tmp/bin/deploy" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$DEPLOY_LOG"
exit 0
EOF
cat >"$tmp/bin/seed" <<'EOF'
#!/bin/sh
printf '%s\n' seed >> "$SEED_LOG"
exit 0
EOF
chmod 755 "$tmp/bin/curl" "$tmp/bin/deploy" "$tmp/bin/seed"

run() {
  env PATH="$tmp/bin:$PATH" \
    PORTFOLIA_ENV_DIR="$tmp/env" \
    CURL_LOG="$tmp/curl.log" \
    DEPLOY_LOG="$tmp/deploy.log" \
    SEED_LOG="$tmp/seed.log" \
    STAGING_DEPLOY="$tmp/bin/deploy" \
    STAGING_SEED_CMD="$tmp/bin/seed" \
    "$root/scripts/staging-sync.sh"
}

fail() {
  echo "FAIL $*" >&2
  exit 1
}

: >"$tmp/curl.log"
: >"$tmp/deploy.log"
: >"$tmp/seed.log"
run
[ "$(wc -l <"$tmp/deploy.log")" -eq 1 ] || fail "first change did not deploy"
grep -q 'staging edge' "$tmp/deploy.log" || fail "deploy args"
grep -qx 'sha256:api sha256:web' "$tmp/env/staging.digest" || fail "digest not recorded"
[ "$(wc -l <"$tmp/seed.log")" -eq 1 ] || fail "first run did not seed"

run
[ "$(wc -l <"$tmp/deploy.log")" -eq 1 ] || fail "unchanged edge deployed again"
[ "$(wc -l <"$tmp/seed.log")" -eq 2 ] || fail "seed skipped while edge was unchanged"

rm -f "$tmp/env/staging.digest"
: >"$tmp/deploy.log"
CURL_FAIL=1 run
[ ! -s "$tmp/deploy.log" ] || fail "missing manifest still deployed"
echo "staging sync checks passed"
