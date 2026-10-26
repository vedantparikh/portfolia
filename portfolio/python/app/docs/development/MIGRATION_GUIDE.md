# Schema migrations

Alembic is the only thing that creates or alters tables. The API does not call `create_all` (tests do, on SQLite). `start_api.sh` runs `alembic upgrade head` before serving, and the container exits if that fails.

The baseline revision is `alembic/versions/e97c82868ff5_baseline.py`. Databases that were stamped at that revision already match it.

## Add a migration

1. Change the model in `core/database/models/`.
2. Autogenerate against a throwaway Postgres, not the stack database. `scripts/check_migrations.sh` shows the pattern: a temporary server, `alembic revision --autogenerate`, then review.
3. Read the generated file. Drop any new Postgres enum types in `downgrade()`.
4. Keep it expand/contract. A release may add columns or tables or backfill. Dropping or renaming waits for the next release, so the previous process can still start.
5. `scripts/check_migrations.sh` must pass: upgrade from empty, `alembic check` (no model drift), downgrade to base, upgrade again.

Do not hand-edit the stack database to match a model. Do not delete `postgres_data` to "fix" a migration.

## Commands inside the API container

```bash
docker compose exec api alembic current
docker compose exec api alembic history
```

`alembic downgrade` on the stack database is a data-loss decision. Do not run it because a guide once said to.
