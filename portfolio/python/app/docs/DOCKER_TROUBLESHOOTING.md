# Docker troubleshooting

Dev project: `portfolio-dev`, file `portfolio/compose.dev.yaml`. Production project: `portfolio`, file `portfolio/compose.yaml`. Services: `app`, `api`, `worker`, `postgres`, `redis`. Commands below are the dev stack. Prefix production with `-f compose.yaml` and do not recreate its Postgres or Redis.

```bash
docker compose -f compose.dev.yaml ps
docker compose -f compose.dev.yaml logs --tail 100 api
docker compose -f compose.dev.yaml logs --tail 100 worker
```

## The UI loads and /api returns 404

The Vite dev server proxies `/api` using `js/vite.config.js`, which is bind-mounted. If that file was missing when the image was built and the mount is absent, the proxy is gone. The compose file mounts it read-only for this reason. Recreate `app` after changing the proxy.

## Code changes do not appear in the API

`main.py`, `config.py`, `start_api.py`, and `start_api.sh` are single-file mounts. A tool that writes a temp file and renames it leaves the container on the old inode. `docker compose -f compose.dev.yaml restart api`. Edits under `core/` and `api/` are directory mounts and do not have this problem. Production images have no bind mounts; a code change needs a rebuilt image.

## API container exits on start

`start_api.sh` waits for Postgres and Redis, then runs `alembic upgrade head`. A migration error is fatal on purpose. Read `docker compose -f compose.dev.yaml logs api` before restarting in a loop. Production does not migrate on startup; run `docker compose -f compose.yaml --profile migrate run --rm migrate`.

## `network homepage_proxy-network not found`

The UI joins that external network. Create it once:

```bash
docker network create homepage_proxy-network
```

## Port already in use

Dev UI defaults to 3200, API to `127.0.0.1:8200`. Production stays on 3000 and `127.0.0.1:8000`. Override with `PORTFOLIO_UI_PORT` and `PORTFOLIO_API_PORT`. Do not publish Postgres to free a port.

## Healthcheck flapping

- API: `GET http://localhost:8000/health/` from inside the container.
- Worker: `/tmp/worker-heartbeat` must be newer than two intervals. A worker that crashes before the first pass stays unhealthy for the start period (120s) and then fails.
- Dev UI: `curl http://localhost:3000` inside `app`. Production `app` is nginx on 8080 and has no curl.

## Out of memory

Limits are 1 GB UI, 2 GB API, 384 MB worker, 1 GB Postgres, 256 MB Redis. The API is the one that pulls Yahoo history into pandas. Raising its limit on this host takes memory from the rest of the machine. Prefer a shorter request over a higher limit.

## Do not

`docker compose down -v` deletes the database volume of the selected project. Never run it against production `portfolio`. Prefer `docker compose -f compose.dev.yaml up -d --wait` for the dev stack, and a single service name when you changed one.
