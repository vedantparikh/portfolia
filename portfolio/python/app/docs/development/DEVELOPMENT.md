# Development

Read [../../../../CLAUDE.md](../../../../CLAUDE.md) before changing code. This page is the short version of the commands.

## Setup

[../../../../STARTUP_GUIDE.md](../../../../STARTUP_GUIDE.md). After it is up:

- UI <http://localhost:3000>
- API <http://127.0.0.1:8000/docs>

The compose file bind-mounts `api/`, `core/`, `alembic/`, and `workers/` as directories, and bind-mounts `main.py`, `config.py`, and `start_api.py` as single files. Replacing a single file (formatters do this) leaves the container on the old inode. Restart the API after editing those files.

## Where code goes

| Change | Where |
|---|---|
| A new HTTP route | `api/v1/<feature>/router.py`, included from `main.py` |
| A query or a write | `core/services/<feature>_service.py` |
| A portfolio number | `core/domain/`, with a golden test first |
| A Yahoo call | `core/services/market_data_service.py` |
| A table | `core/database/models/`, plus an Alembic revision |
| A screen | `js/src/components/<feature>/`, calling `js/src/services/api.js` |

A feature change updates that feature's `CLAUDE.md` in the same commit.

Domain errors use `DomainError` / `NotFoundError`. Routers that catch a broad exception build the HTTP detail with `public_message(e, "fixed text")`. `tests/unit/test_error_messages.py` fails the build if a detail interpolates the exception.

## Tests

From `portfolio/`:

```bash
scripts/verify.sh
```

That is the gate: compose config, ruff, eslint, pytest in the API image, the migration round-trip, and the Vite production build. CI runs it with `--stack` on arm64.

A single file:

```bash
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/python/app:/app" -w /app \
  -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/t.db \
  -e PYTHONDONTWRITEBYTECODE=1 portfolio-api \
  python -m pytest tests/unit/test_domain_engine.py -q -p no:cacheprovider
```

`tests/quarantine.txt` only shrinks. Do not add a line to hide a new failure.

`tests/unit/test_calculation_snapshots.py` pins the numbers the UI shows. If it fails, a displayed number changed. Fix the regression, or regenerate with `UPDATE_SNAPSHOTS=1` only when the change is intentional, and say so in the commit.

There are no frontend unit tests. `npm test` is a placeholder.

## Lint

Ruff (line length is the formatter's, E712 ignored for SQLAlchemy `== True`) and ESLint 9 (flat config, `react/prop-types` off). Both must report zero. Commands are in [../../../../README.md](../../../../README.md).

## Commits

Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`), one logical change, on a branch. `scripts/verify.sh` passes before the commit. Do not push unless asked.

## Dependencies

Do not add, upgrade, or remove a pip, npm, base image, or GitHub Action dependency without asking. The pinned versions are in `python/app/requirements.txt` and `js/package.json`.
