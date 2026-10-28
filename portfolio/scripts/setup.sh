#!/usr/bin/env bash
# First-time setup on a new host. Creates the env files with generated secrets
# and the shared Docker network. Never overwrites an existing file.
#   scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
ENV_DIR="$ROOT/../env"

command -v docker >/dev/null || { echo "docker is not installed"; exit 1; }
docker compose version >/dev/null || { echo "docker compose v2 is not installed"; exit 1; }

secret() { python3 -c 'import secrets; print(secrets.token_urlsafe(48))'; }

# $1 target, $2 environment, $3 database name, $4 database password
write_api_env() {
  local target=$1 environment=$2 database=$3 db_password=$4
  if [[ -e "$target" ]]; then
    echo "keep    $target"
    return
  fi
  local debug=false
  [[ "$environment" == development ]] && debug=true
  sed -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$db_password|" \
      -e "s|^POSTGRES_DB=.*|POSTGRES_DB=$database|" \
      -e "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$(secret)|" \
      -e "s|^SECRET_KEY=.*|SECRET_KEY=$(secret)|" \
      -e "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(secret)|" \
      -e "s|^ENVIRONMENT=.*|ENVIRONMENT=$environment|" \
      -e "s|^DEBUG=.*|DEBUG=$debug|" \
      "$ROOT/python/app/.env.example" > "$target"
  chmod 600 "$target"
  echo "created $target"
}

mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR"
write_api_env "$ROOT/python/app/.env.docker" development portfolio "$(secret)"
# Production Postgres reads python/app/.env.docker (its live container was
# created that way), so the production API must use the same password.
db_password=$(sed -n 's/^POSTGRES_PASSWORD=//p' "$ROOT/python/app/.env.docker")
write_api_env "$ENV_DIR/prod.env" production portfolio "$db_password"
write_api_env "$ENV_DIR/staging.env" production portfolio_staging "$(secret)"

if [[ ! -e "$ROOT/js/.env.docker" ]]; then
  cp "$ROOT/js/.env.example" "$ROOT/js/.env.docker"
  chmod 600 "$ROOT/js/.env.docker"
  echo "created $ROOT/js/.env.docker"
fi

if ! docker network inspect homepage_proxy-network >/dev/null 2>&1; then
  docker network create homepage_proxy-network >/dev/null
  echo "created network homepage_proxy-network"
fi

cat <<EOF

Next:
  fill EMAIL_* in the env files for verification and password-reset mail
  docker compose -f compose.dev.yaml up -d --wait    # dev: UI :3200, API :8200
EOF
