# Starting Portfolia

The supported runtime is Docker Compose, from this directory. Do not install a host virtualenv or run `npm run dev` on the home server: the system Python is 3.8 and there is no host Node.

## First time

```bash
cd portfolio
cp python/app/.env.example python/app/.env.docker
cp js/.env.example js/.env.docker
```

Edit `.env.docker` (mode 600). Generate secrets with:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Set `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET_KEY`, and `REDIS_PASSWORD`. Leave Yahoo keys blank; market data does not use them. Email uses Brevo (`EMAIL_HOST=smtp-relay.brevo.com`, port 587) if you want verification and password-reset mail.

The compose file joins the external network `homepage_proxy-network`. Create it once if it is missing:

```bash
docker network create homepage_proxy-network
```

## Start

```bash
docker compose -f compose.dev.yaml up -d --wait
```

That is project `portfolio-dev`. `compose.yaml` is production (project `portfolio`, UI :3000). A bare `docker compose up` selects that file. Use `compose.dev.yaml` when you want the dev stack.

| Check | Expected |
|---|---|
| UI | <http://localhost:3200> returns the sign-in page |
| API | `curl -f http://127.0.0.1:8200/health/` |
| API docs | <http://127.0.0.1:8200/docs> |
| Worker | `docker compose -f compose.dev.yaml ps` shows `worker` healthy |

The API runs `alembic upgrade head` on startup and exits if the migration fails. Postgres and Redis have no host port.

Logs:

```bash
docker compose -f compose.dev.yaml logs -f api
docker compose -f compose.dev.yaml logs -f worker
```

Dev defaults are UI 3200 and API 8200. Override with `PORTFOLIO_UI_PORT` and `PORTFOLIO_API_PORT`.

## Demo login

Username `demo`, password `DemoApp!234`. What that account contains, and how not to destroy it, is in [../docs/USER_GUIDE.md](../docs/USER_GUIDE.md).

## Stop

```bash
docker compose -f compose.dev.yaml stop
```

`docker compose down -v` deletes the database volume of whichever file Compose selects. Do not use it on the production project `portfolio`.

## When something fails

[python/app/docs/DOCKER_TROUBLESHOOTING.md](python/app/docs/DOCKER_TROUBLESHOOTING.md).
