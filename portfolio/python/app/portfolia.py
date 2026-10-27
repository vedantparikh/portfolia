"""Management commands. Run `python -m portfolia recalc` inside the API container."""

import argparse
import asyncio
import logging

from sqlalchemy.orm import Session

from core.database.connection import SessionLocal
from core.database.models import Portfolio, Transaction
from modules.portfolios.service import PortfolioService

logger = logging.getLogger("portfolia")


async def recalc(db: Session) -> int:
    """Rebuild each active holding from its transactions. Returns how many ran."""
    service = PortfolioService(db)
    portfolios = db.query(Portfolio).filter(Portfolio.is_active.is_(True)).all()
    done = 0
    for portfolio in portfolios:
        asset_ids = [
            row[0]
            for row in db.query(Transaction.asset_id)
            .filter(Transaction.portfolio_id == portfolio.id)
            .distinct()
            .all()
        ]
        for asset_id in asset_ids:
            await service.recalculate_asset_state(db, portfolio.id, asset_id)
            done += 1
    logger.info("recalculated %s holdings", done)
    return done


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="portfolia")
    parser.add_argument("command", choices=["recalc"])
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        if args.command == "recalc":
            asyncio.run(recalc(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
