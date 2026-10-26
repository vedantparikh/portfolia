# Portfolia API

FastAPI service under `python/app`. The process working directory inside the image is `/app`, and imports are `from core...` / `from api.v1...`. There is no `python/api` package.

How to run it: [../../STARTUP_GUIDE.md](../../STARTUP_GUIDE.md). Product behaviour: [../../../docs/USER_GUIDE.md](../../../docs/USER_GUIDE.md).

## Layout

```
python/app/
  main.py                 # FastAPI app, router includes, DomainError handler
  config.py               # settings from the environment
  start_api.sh            # wait for Postgres and Redis, alembic upgrade head, serve
  alembic/                # the only schema authority
  api/v1/<feature>/       # routers. Read the CLAUDE.md in the feature you change
  core/domain/            # pure portfolio maths
  core/services/          # SQLAlchemy and Yahoo
  core/database/models/   # tables
  workers/run.py          # watchlist price and alert loop
  tests/                  # pytest. See tests/README.md
```

## Useful URLs

With the compose stack up:

- OpenAPI: <http://127.0.0.1:8000/docs>
- Health: `GET /health/`

Routers are mounted at `/api/v1/<feature>`. The map is [docs/ENDPOINT_STRUCTURE.md](docs/ENDPOINT_STRUCTURE.md). Per-feature behaviour, including the gaps, is the `CLAUDE.md` next to each router. Those files are more specific than this README.

## Tests and lint

Use the commands in [../../README.md](../../README.md). Do not pytest inside the running API container.
