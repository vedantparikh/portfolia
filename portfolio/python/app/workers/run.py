"""
Background worker: watchlist alerts, holding prices, FX and performance snapshots.

Runs one pass every WORKER_INTERVAL_SECONDS and touches a heartbeat file after
each pass (the container healthcheck reads it).
"""

import asyncio
import logging
import signal
import time
from pathlib import Path

from workers.book import refresh_book

from config import settings
from core.database.connection import SessionLocal
from core.services.watchlist_service import WatchlistService

HEARTBEAT = Path("/tmp/worker-heartbeat")
logger = logging.getLogger("workers.run")


async def run_once() -> dict:
    db = SessionLocal()
    try:
        result = await WatchlistService(db).refresh_prices_and_alerts()
        try:
            result.update(await refresh_book(db))
        except Exception:
            logger.exception("Holding refresh failed")
        return result
    finally:
        db.close()


async def main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    interval = settings.WORKER_INTERVAL_SECONDS
    logger.info("Worker started; refresh every %ss", interval)
    while not stop.is_set():
        started = time.monotonic()
        try:
            result = await run_once()
            logger.info(
                "Watchlists refreshed in %.1fs: %s", time.monotonic() - started, result
            )
        except Exception:
            logger.exception("Watchlist refresh failed")
        HEARTBEAT.touch()
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass
    logger.info("Worker stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    asyncio.run(main())
