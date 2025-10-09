import asyncio
from sqlalchemy import distinct

# Adjust these imports based on your project structure
from core.database.connection import SessionLocal
from core.database.models import Transaction
from core.services.portfolio_service import PortfolioService


async def main():
    """
    This script iterates through every unique portfolio/asset pair that has transactions
    and triggers a recalculation of its state.
    """
    print("Starting the script to fix existing asset quantities...")
    db = SessionLocal()
    portfolio_service = PortfolioService(db)

    try:
        # Get all unique pairs of (portfolio_id, asset_id) from the transaction history.
        # This is the definitive source of truth for which assets need to exist.
        assets_to_recalculate = db.query(
            distinct(Transaction.portfolio_id),
            Transaction.asset_id
        ).all()

        total_assets = len(assets_to_recalculate)
        print(f"Found {total_assets} unique assets across all portfolios to recalculate.")

        for i, (portfolio_id, asset_id) in enumerate(assets_to_recalculate):
            print(f"[{i + 1}/{total_assets}] Recalculating portfolio_id={portfolio_id}, asset_id={asset_id}...")
            await portfolio_service.recalculate_asset_state(portfolio_id, asset_id)

        print("\n✅ All asset quantities and cost bases have been successfully recalculated and fixed.")

    finally:
        db.close()
        print("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(main())