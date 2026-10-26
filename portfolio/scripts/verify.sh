#!/usr/bin/env bash
# Pre-push gate mirroring CI. Needs only Docker (the Jetson host has no py3.12/node).
#   scripts/verify.sh          compose config + lint + backend tests + migrations + frontend build
#   scripts/verify.sh --stack  also rebuild/restart the local stack and smoke-test it
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PROJECT=${COMPOSE_PROJECT_NAME:-portfolio}

step() { printf '\n== %s\n' "$*"; }

step "compose config"
docker compose config -q

step "build images"
docker compose build -q api app postgres worker

step "lint: ruff (backend), eslint (frontend)"
docker run --rm --user "$(id -u):$(id -g)" -v "$ROOT/python/app:/app" -w /app \
  "$PROJECT-api" sh -c 'ruff check --no-cache . && ruff format --check --no-cache .'
docker run --rm --network none \
  -v "$ROOT/js/src:/app/src:ro" -v "$ROOT/js/eslint.config.js:/app/eslint.config.js:ro" \
  -v "$ROOT/js/vite.config.js:/app/vite.config.js:ro" \
  "$PROJECT-app" npx eslint . --report-unused-disable-directives --max-warnings 0

step "backend: app import + pytest (throwaway container, not on the stack network)"
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$ROOT/python/app:/app" -w /app \
  -e HOME=/tmp -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/test.db \
  -e PYTHONPATH=/app:/tmp/extra -e PYTHONDONTWRITEBYTECODE=1 \
  "$PROJECT-api" sh -c '
    pip install -q --disable-pip-version-check --no-deps --target /tmp/extra ta &&
    python -c "import main; assert len(main.app.openapi()[\"paths\"]) >= 85" &&
    python -m pytest tests -q -p no:cacheprovider'

step "migrations: upgrade, drift check, downgrade (throwaway Postgres)"
scripts/check_migrations.sh

step "frontend: production build"
docker run --rm --network none \
  -v "$ROOT/js/src:/app/src:ro" -v "$ROOT/js/vite.config.js:/app/vite.config.js:ro" \
  "$PROJECT-app" npx vite build --outDir /tmp/dist --logLevel warn

step "prod images: build, size, non-root, no bind mounts"
docker build -f "$ROOT/python/app/Dockerfile.prod" -t portfolia-api:prod "$ROOT/python/app"
docker build -f "$ROOT/js/Dockerfile.prod" -t portfolia-web:prod "$ROOT/js"
# The plan's 400 MB API cap is not reachable: polars, pyarrow and pandas
# alone are about 450 MB. The gate holds the measured build, plus slack.
api_max=$((900 * 1024 * 1024))
web_max=$((100 * 1024 * 1024))
api_size=$(docker image inspect -f '{{.Size}}' portfolia-api:prod)
web_size=$(docker image inspect -f '{{.Size}}' portfolia-web:prod)
echo "portfolia-api:prod $((api_size / 1024 / 1024)) MB"
echo "portfolia-web:prod $((web_size / 1024 / 1024)) MB"
[[ "$api_size" -lt "$api_max" ]] || { echo "FAIL API image exceeds 900 MB"; exit 1; }
[[ "$web_size" -lt "$web_max" ]] || { echo "FAIL web image exceeds 100 MB"; exit 1; }
[[ "$(docker run --rm --entrypoint id portfolia-api:prod -u)" != "0" ]]
[[ "$(docker run --rm --entrypoint id portfolia-web:prod -u)" != "0" ]]
docker run --rm --network none -e TESTING=true -e ENVIRONMENT=test \
  --entrypoint python portfolia-api:prod \
  -c 'import main; assert len(main.app.openapi()["paths"]) >= 85'
docker run --rm --network none --entrypoint alembic portfolia-api:prod heads >/dev/null
docker rm -f portfolia-web-smoke >/dev/null 2>&1 || true
docker run -d --name portfolia-web-smoke -p 127.0.0.1:18080:8080 portfolia-web:prod >/dev/null
cleanup_web() { docker rm -f portfolia-web-smoke >/dev/null 2>&1 || true; }
trap cleanup_web EXIT
for attempt in 1 2 3 4 5 6; do
  curl -fsS --max-time 5 http://127.0.0.1:18080/ | grep -q 'id="root"' && break
  [[ $attempt == 6 ]] && { docker logs portfolia-web-smoke; exit 1; }
  sleep 1
done
curl -fsS -o /dev/null --max-time 5 http://127.0.0.1:18080/portfolio
cleanup_web
trap - EXIT

if [[ "${1:-}" == "--stack" ]]; then
  step "stack: up + smoke"
  docker compose up -d --wait --wait-timeout 300
  for url in "http://localhost:${PORTFOLIO_UI_PORT:-3000}/" \
             "http://localhost:${PORTFOLIO_UI_PORT:-3000}/api/v1/health" \
             "http://127.0.0.1:${PORTFOLIO_API_PORT:-8000}/health/"; do
    for attempt in 1 2 3 4 5 6; do
      curl -fsS -o /dev/null --max-time 10 "$url" && break
      [[ $attempt == 6 ]] && { echo "FAIL $url"; exit 1; }
      sleep 5
    done
    echo "ok  $url"
  done
fi

step "all checks passed"
