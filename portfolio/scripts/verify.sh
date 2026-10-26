#!/usr/bin/env bash
# Pre-push gate mirroring CI. Needs only Docker (the Jetson host has no py3.12/node).
#   scripts/verify.sh          compose config + lint + backend tests + migrations + frontend build
#   scripts/verify.sh --stack  also rebuild/restart the local stack and smoke-test it
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
# Dev file and project, so this gate never selects compose.yaml and never
# attaches to the live `portfolio` project (production data).
export COMPOSE_FILE="${COMPOSE_FILE:-compose.dev.yaml}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-portfolio-dev}"
PROJECT=$COMPOSE_PROJECT_NAME

step() { printf '\n== %s\n' "$*"; }

step "deploy rollback"
"$ROOT/scripts/test-deploy.sh"
"$ROOT/scripts/test-staging-sync.sh"

step "release image tags"
tags=$(IMAGE_PREFIX=ghcr.io/example "$ROOT/scripts/release-tags.sh" api version abcdef1 0.1.10)
[ "$tags" = "ghcr.io/example/portfolia-api:0.1.10
ghcr.io/example/portfolia-api:0.1
ghcr.io/example/portfolia-api:sha-abcdef1" ]
tags=$(IMAGE_PREFIX=ghcr.io/example "$ROOT/scripts/release-tags.sh" web edge abcdef1234567)
[ "$tags" = "ghcr.io/example/portfolia-web:edge
ghcr.io/example/portfolia-web:sha-abcdef1" ]
if IMAGE_PREFIX=ghcr.io/example "$ROOT/scripts/release-tags.sh" api version abcdef1 v0.1.0 >/dev/null 2>&1; then
  echo "FAIL release-tags accepted a v prefix"
  exit 1
fi

# CI has no secrets. Prod and staging env files live outside the repo.
step "compose env files"
env_dir="$ROOT/../env"
mkdir -p "$env_dir"
chmod 700 "$env_dir"
if [ ! -f "$env_dir/prod.env" ]; then
  cp "$ROOT/python/app/.env.example" "$env_dir/prod.env"
  chmod 600 "$env_dir/prod.env"
fi
if [ ! -f "$env_dir/staging.env" ]; then
  sed 's/^POSTGRES_DB=portfolio$/POSTGRES_DB=portfolio_staging/' \
    "$ROOT/python/app/.env.example" > "$env_dir/staging.env"
  chmod 600 "$env_dir/staging.env"
fi

step "compose config"
docker compose -f compose.dev.yaml config -q
docker compose -f compose.yaml config -q
docker compose -f compose.yaml -f compose.staging.yaml config -q
python3 - <<'PY'
import json, os, subprocess, sys

def rendered(files):
    # The dev project name is exported for the rest of this script. It must
    # not override the name: field in the prod and staging files.
    env = os.environ.copy()
    env.pop("COMPOSE_PROJECT_NAME", None)
    env.pop("COMPOSE_FILE", None)
    cmd = ["docker", "compose"]
    for f in files:
        cmd += ["-f", f]
    cmd += ["config", "--format", "json"]
    return json.loads(subprocess.check_output(cmd, text=True, env=env))

# Postgres and Redis keep the build definitions of the live containers so a
# later `up` does not recreate them. Every other service is images only.
DATA_SERVICES = {"postgres", "redis"}

def binds_or_builds(data):
    bad = []
    for name, svc in data.get("services", {}).items():
        if svc.get("build") and name not in DATA_SERVICES:
            bad.append(f"{name}: build")
        for vol in svc.get("volumes") or []:
            if isinstance(vol, dict) and vol.get("type") == "bind":
                bad.append(f"{name}: bind {vol.get('target')}")
    return bad

def service_hash(files, service):
    env = os.environ.copy()
    env.pop("COMPOSE_PROJECT_NAME", None)
    env.pop("COMPOSE_FILE", None)
    cmd = ["docker", "compose"]
    for f in files:
        cmd += ["-f", f]
    cmd += ["config", "--hash", service]
    line = subprocess.check_output(cmd, text=True, env=env).strip().split()
    return line[-1]

prod = rendered(["compose.yaml"])
bad = binds_or_builds(prod)
if bad:
    print("FAIL compose.yaml has build or bind mounts")
    print("\n".join(bad))
    sys.exit(1)
for svc in ("postgres", "redis"):
    live = service_hash(["docker-compose.yml"], svc)
    new = service_hash(["compose.yaml"], svc)
    if live != new:
        sys.exit(f"FAIL {svc} config hash would recreate the live container")
if prod.get("name") != "portfolio":
    sys.exit("FAIL compose.yaml project name")
staging = rendered(["compose.yaml", "compose.staging.yaml"])
bad = binds_or_builds(staging)
if bad:
    print("FAIL staging compose has build or bind mounts")
    print("\n".join(bad))
    sys.exit(1)
if staging.get("name") != "portfolio-staging":
    sys.exit("FAIL staging project name")
prod_db = (prod["services"]["postgres"].get("environment") or {}).get("POSTGRES_DB")
stg_db = (staging["services"]["postgres"].get("environment") or {}).get("POSTGRES_DB")
if not prod_db or not stg_db:
    sys.exit("FAIL postgres env file did not load")
if prod_db == stg_db:
    sys.exit("FAIL staging database name matches production")
prod_vol = prod["services"]["postgres"]["volumes"][0]["source"]
stg_vol = staging["services"]["postgres"]["volumes"][0]["source"]
if prod_vol == stg_vol:
    sys.exit("FAIL staging postgres volume matches production")
print("prod compose: app services have no bind mounts; database hashes match")
PY

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
  for url in "http://localhost:${PORTFOLIO_UI_PORT:-3200}/" \
             "http://localhost:${PORTFOLIO_UI_PORT:-3200}/api/v1/health" \
             "http://127.0.0.1:${PORTFOLIO_API_PORT:-8200}/health/"; do
    for attempt in 1 2 3 4 5 6; do
      curl -fsS -o /dev/null --max-time 10 "$url" && break
      [[ $attempt == 6 ]] && { echo "FAIL $url"; exit 1; }
      sleep 5
    done
    echo "ok  $url"
  done
fi

step "all checks passed"
