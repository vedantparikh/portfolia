# Contributing

Setup and commands: [README.md](README.md). Rules that also bind coding agents: [CLAUDE.md](CLAUDE.md).

## Workflow

1. Branch from `master` (`feat/…`, `fix/…`, `chore/…`, `docs/…`). Trunk-based; `master` is always deployable.
2. One logical change per commit, Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`, `test:`, `refactor:`). They drive release-please's version bump and changelog.
3. `scripts/verify.sh` passes before every commit; add `--stack` when Docker, compose, env, auth or startup changed. CI runs `verify.sh --stack` on arm64 and is the required check.
4. A change to a feature's behaviour updates that feature's `CLAUDE.md` in the same commit.
5. Never add, upgrade or remove a dependency (pip, npm, base image, GitHub Action) without agreeing it first. Python deps live in `python/app/pyproject.toml` + `uv.lock` (`uv lock` inside the dev API image), npm in `js/package.json` + `package-lock.json`.

## Add a backend feature

```
python/app/
  api/v1/<feature>/router.py     APIRouter(prefix="/<feature>", tags=["<feature>"]); add it to api/v1/router.py
  api/v1/<feature>/CLAUDE.md     purpose, state, endpoints, frontend, workflow, known gaps, planned
  modules/<feature>/service.py   class <Feature>Service: __init__(self, db: Session)
  modules/<feature>/repository.py  SQLAlchemy queries; never commits
  core/schemas/<feature>.py      Pydantic request/response models
  core/database/models/<x>.py    Mapped[] columns + an Alembic revision
  tests/unit/test_<feature>.py
```

- Routers validate, depend on `get_current_active_user` (or `get_owned_portfolio` for a portfolio route) and call one service method. Plain `def` unless the handler awaits I/O; FastAPI runs `def` routes in its threadpool ([ADR 0001](docs/adr/0001-sync-sqlalchemy.md)).
- `get_db` commits when the request succeeds and rolls back when it raises. Services and repositories do not commit.
- Every query is scoped by `user_id`.
- Expected failures raise `DomainError` / `NotFoundError` (`core/errors.py`) with a message written for the user: 400 / 404 in the error envelope. Do not catch `Exception` to return a 500; the global handler logs it and returns `internal_error`.
- A number shown to the user comes from `core/domain` (pure, golden-tested) ([ADR 0002](docs/adr/0002-calculation-engine.md)). Never a second copy of a metric. Percent units are `15.0`.
- Market data only through `core/services/market_data_service.py`; tests mock the provider.
- Literal paths before `/{id}`. A new route changes `tests/unit/api_routes.txt` and `openapi_operations.txt` and the generated frontend types: regenerate them and review the diff.

Regenerate the frontend API types after an API change:

```bash
docker run --rm -v "$PWD/python/app:/app" -w /app -e TESTING=true -e ENVIRONMENT=test \
  -e TEST_DATABASE_URL=sqlite:////tmp/t.db portfolio-dev-api \
  python -c 'import json,main; print(json.dumps(main.app.openapi()))' > /tmp/openapi.json
docker run --rm -v /tmp/openapi.json:/tmp/openapi.json:ro -v "$PWD/js/src/shared/api/generated:/out" \
  portfolio-dev-app npx openapi-typescript /tmp/openapi.json -o /out/schema.ts
```

## Schema migrations

Alembic is the only thing that creates or alters tables.

1. Change the model in `core/database/models/`.
2. Autogenerate against a throwaway Postgres (pattern in `scripts/check_migrations.sh`), never the stack database.
3. Review the file. Drop new Postgres enum types in `downgrade()`.
4. Expand/contract: a release may add columns or tables, or backfill. Dropping or renaming waits for the next release, so the previous image still starts and rollback stays an image swap. A migration that cannot be undone needs `deploy.sh --allow-irreversible`.
5. `scripts/check_migrations.sh` must pass: upgrade from empty, `alembic check` (no drift), downgrade to base, upgrade.

## Add a frontend feature

```
js/src/features/<feature>/
  api.ts          endpoint wrappers on the shared axios client (shared/api/client.ts)
  queries.ts      TanStack Query hooks; mutations invalidate the keys they change
  <Page>.jsx      registered as a lazy route in app/router.jsx, inside ProtectedLayout
  CLAUDE.md       pointer to the backend feature reference
  *.test.jsx      Vitest + Testing Library; HTTP mocked with MSW (src/test/msw)
```

- Dialogs use `shared/ui/Modal` (focus trap, Esc, labelled title). Shared states: `Spinner`, `EmptyState`, `ErrorState`.
- Numbers and money only through `utils/formatters.jsx` / `useMoney()`; ESLint rejects `.toFixed(` and literal `$` amounts.
- Errors: `apiErrorMessage(error, "fallback")` into `react-hot-toast`.
- New files can be TypeScript (`allowJs`, strict for `.ts`); request/response types come from `shared/api/generated/schema.ts`.
- UI changes stay small and reviewable; no redesigns in a refactor.

## Tests

| Layer | Where | Run |
|---|---|---|
| Domain maths | `tests/unit/test_domain_engine.py`, `test_fx.py`, golden values | pytest |
| Displayed numbers | `tests/unit/test_calculation_snapshots.py` + `snapshots/calculations.json` | pytest; `UPDATE_SNAPSHOTS=1` only for an intended change, explained in the commit |
| Services, routes | `tests/unit`, `tests/integration` (SQLite, fake Redis, no network) | pytest |
| Indicators | `test_indicator_reference.py` against `ta` | pytest |
| Frontend | `src/**/*.test.*` | Vitest |
| End to end | `js/e2e/*.spec.ts` | Playwright in `verify.sh --stack` |

`tests/quarantine.txt` is empty and stays empty: never quarantine a new failure.
