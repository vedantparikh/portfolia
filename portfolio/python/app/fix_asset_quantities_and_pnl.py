import asyncio

from core.database.connection import SessionLocal
from core.database.models import Portfolio, Transaction
from core.services.portfolio_service import PortfolioService


async def main():
    """
    Main asynchronous function to run the recalculation process.
    """
    print("Starting P&L recalculation script for all portfolios and assets...")
    db = SessionLocal()
    try:
        portfolio_service = PortfolioService(db)

        # 1. Get all active portfolios to process
        portfolios = db.query(Portfolio).filter(Portfolio.is_active == True).all()
        if not portfolios:
            print("No active portfolios found. Exiting.")
            return

        print(f"Found {len(portfolios)} active portfolio(s) to process.")

        # 2. Iterate through each portfolio
        for portfolio in portfolios:
            print(f"\n--- Processing Portfolio: '{portfolio.name}' (ID: {portfolio.id}) ---")

            # 3. Find all unique assets that have transactions in this portfolio
            # This ensures we process assets that were fully sold and might not have a
            # PortfolioAsset entry anymore.
            asset_ids_tuples = (
                db.query(Transaction.asset_id)
                .filter(Transaction.portfolio_id == portfolio.id)
                .distinct()
                .all()
            )

            if not asset_ids_tuples:
                print("No transactions found for this portfolio. Skipping.")
                continue

            print(f"Found {len(asset_ids_tuples)} unique asset(s) with transaction history.")

            # 4. For each asset, trigger the recalculation
            for (asset_id,) in asset_ids_tuples:
                try:
                    print(f"  -> Recalculating state for Asset ID: {asset_id}...")

                    # This single method handles everything:
                    # - Recalculates current quantity and cost basis from all transactions.
                    # - Calculates realized P&L using FIFO based on sell history.
                    # - Fetches the current price for unrealized P&L calculation.
                    # - Updates or creates the PortfolioAsset record in the database.
                    await portfolio_service.recalculate_asset_state(
                        portfolio_id=portfolio.id, asset_id=asset_id
                    )
                    print(f"  ✅ Successfully recalculated Asset ID: {asset_id}.")

                except Exception as e:
                    # Log the error but continue with the next asset
                    print(f"  ❌ ERROR processing Asset ID {asset_id} in Portfolio ID {portfolio.id}: {e}")
                    # You might want to add more sophisticated logging here

            print(f"--- Finished processing Portfolio '{portfolio.name}' ---")

        print("\n🎉 Recalculation script completed successfully for all portfolios.")

    finally:
        db.close()
        print("Database session closed.")


if __name__ == "__main__":
    # The script is executed from the command line
    asyncio.run(main())