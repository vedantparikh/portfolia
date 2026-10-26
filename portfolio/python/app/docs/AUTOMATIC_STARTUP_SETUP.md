# What happens when the API starts

`python/app/start_api.sh` is the container entrypoint.

1. Wait until Postgres accepts a connection (up to 30 attempts, 2 seconds apart).
2. Wait until Redis answers `PING`, with the same budget.
3. Run `alembic upgrade head`. A failure exits the script. The container does not start serving a half-migrated schema.
4. Start uvicorn.

The process does not create tables itself, does not seed a user, and does not import market data. Demo data is a separate command, documented in [../../../STARTUP_GUIDE.md](../../../STARTUP_GUIDE.md).

`init_db()` on application startup opens the connection pool. It is not a schema installer.

The worker container does not migrate. It waits until the API healthcheck passes, which is after step 3.

Tests are different: pytest sets `TESTING=true` and builds a SQLite schema with `create_all`. That path is not used in the container entrypoint.
