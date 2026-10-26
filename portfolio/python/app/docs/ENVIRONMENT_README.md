# Environment variables

Source of truth for what the API reads: `python/app/config.py`. The compose template is `python/app/.env.example`. The UI template is `js/.env.example`.

Generate a secret:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

## API (`python/app/.env.docker`)

| Key | Role |
|---|---|
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database. In compose the host is `postgres`. |
| `POOL_SIZE`, `MAX_OVERFLOW`, `POOL_TIMEOUT`, `POOL_RECYCLE` | SQLAlchemy pool. Defaults 20 / 30 / 30 / 3600. |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | Cache and reset tokens. Empty password is refused when `ENVIRONMENT` is production. |
| `WORKER_INTERVAL_SECONDS` | Watchlist refresh period. Default 900. |
| `API_HOST`, `API_PORT`, `API_URL` | Bind address and the URL the seed script calls. Compose uses port 8000. |
| `DEBUG`, `LOG_LEVEL`, `ENVIRONMENT` | `ENVIRONMENT` other than development/dev/local/test turns on the secret check. |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Required outside local development. At least 32 characters, not a placeholder. |
| `JWT_ALGORITHM` | Default HS256. `config.py` also accepts `ALGORITHM`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 15. |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Default 30. This is the key `config.py` reads. `.env.example` still lists `REFRESH_TOKEN_EXPIRE_DAYS`, which the code ignores. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_FROM` | Verification and password-reset mail. Default host `smtp-relay.brevo.com`, port 587. |
| `ALLOWED_ORIGINS` or `FRONTEND_URL` | CORS. `*` is rejected outside local development. Default `http://localhost:3000`. |
| `YAHOO_FINANCE_API_KEY`, `ALPHA_VANTAGE_API_KEY` | Present in the template. Yahoo is called without a key. `ALPHA_VANTAGE_API_KEY` in `config.py` is a constant empty string, not read from the environment. |
| `STATIC_DIR` | Default `STATICS`. |
| `LOG_FILE`, `LOG_DIR`, `LOG_JSON` | Read by `main.py`, not by `config.py`. See [LOGGING_CONFIGURATION.md](LOGGING_CONFIGURATION.md). |

`TESTING=true` and `TEST_DATABASE_URL` switch pytest onto SQLite. Do not set them on the running stack.

## UI (`js/.env.docker`)

| Key | Role |
|---|---|
| `FRONTEND_PORT` | Documented in the template. The dev server port in compose is 3000, overridable with `PORTFOLIO_UI_PORT` on the host. |
| `API_HOST`, `API_PORT` | Used with `DOCKER_API_URL` (`http://api:8000` in compose) so the Vite dev server can proxy `/api`. |

## Host overrides

`PORTFOLIO_UI_PORT` and `PORTFOLIO_API_PORT` are compose interpolations. They are not read by Python.
