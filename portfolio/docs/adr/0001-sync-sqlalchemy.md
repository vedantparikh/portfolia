# 0001 Sync SQLAlchemy with `def` routes

**Context.** Every endpoint was `async def` but used a synchronous SQLAlchemy session, so each query blocked the event loop. The workload is one user on a shared Jetson; the slow parts are Yahoo calls, not the database.

**Decision.** Keep SQLAlchemy 2 in sync mode. Database routes are plain `def`, which FastAPI runs in its threadpool. A route stays `async def` only when it awaits I/O (market data); blocking calls inside it go through `run_in_threadpool`. `get_db` is one unit of work: commit on success, rollback on error.

**Consequences.** No asyncpg/AsyncSession migration. Models use `Mapped[]` and timezone-aware datetimes. If concurrency ever matters, the threadpool size is the knob before an async rewrite.
