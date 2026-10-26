# Database

Postgres 16 in the `postgres` compose service. Data is the named volume `postgres_data` (on this host, under the Docker data-root on `/mnt/samsung_ufs`). No host port. Connect with:

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

The URL the API uses is built in `config.py` from `POSTGRES_*`. Tests use SQLite via `TEST_DATABASE_URL` and never this server.

## Tables

Models are in `core/database/models/`. `core/database/models/auth.py` duplicates the user tables and is unused; the live ones are in `user.py`.

| Model | Table role |
|---|---|
| `User`, `UserProfile`, `UserSession` | Accounts, profile, refresh sessions |
| `Portfolio`, `PortfolioAsset` | Books, and the position cache rebuilt from transactions |
| `Transaction` | Buys, sells, dividends, and the other stored types. `source_key` makes a re-import skip the row |
| `Asset`, `MarketIndex` | Symbols the user tracks. Unique on user + symbol |
| `PortfolioPerformanceHistory` | Old snapshot rows. New charts do not read these |
| `PortfolioAllocation`, `RebalancingEvent`, `PortfolioBenchmark` | Targets, stored rebalance events, benchmark names |
| `Watchlist`, `WatchlistItem`, `WatchlistAlert`, `WatchlistPerformance` | Lists, items, fired alerts, one price row per item per day |
| `AnalysisConfiguration` | Saved indicator sets |

Prices are not stored as a history table. Yahoo history is cached in Redis (see [MARKET_DATA_SERVICE.md](MARKET_DATA_SERVICE.md)).

## Migrations

[development/MIGRATION_GUIDE.md](development/MIGRATION_GUIDE.md). Short version: Alembic on API startup, baseline `e97c82868ff5`, and the gate fails if models drift from the migrations.

## Pool

`POOL_SIZE` 20, `MAX_OVERFLOW` 30, `POOL_TIMEOUT` 30, `POOL_RECYCLE` 3600, all overridable. That pool is sized for a single personal user on a shared host, not for a public deployment.

## Backups

`scripts/backup.sh` writes a custom-format `pg_dump` of the running database to `/mnt/samsung_ufs/backups/portfolio/` (14 daily, 8 weekly). `scripts/restore.sh` loads a dump into staging. Copying the volume of a running Postgres is not a backup. The nightly timer is `deploy/portfolia-backup.timer`; installing it is a host step.
