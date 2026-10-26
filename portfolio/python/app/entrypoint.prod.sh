#!/bin/sh
# Production process. Migrations are not run here.
# One-off: docker run --rm <image> alembic upgrade head
set -eu
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec python -m uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}"
