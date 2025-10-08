import base64
from datetime import datetime, timezone
from typing import List, Tuple

from sqlalchemy.orm import Session

from core.database.models import Transaction
from core.schemas.account_statements import (
    AccountStatementProvider,
    BulkCreateSummary,
    BulkTransactionItem,
    CreatedTransaction,
    ParsedData,
    SupportedFormat,
)
from core.services.parsers.portfolia import PortfoliaParser
from core.services.parsers.trade_republic import TradeRepublicParser
from core.services.portfolio_service import PortfolioService


class AccountStatementService:
    """Service for account statement parsing and processing."""

    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self._parsers = {
            "trade_republic": TradeRepublicParser(),
            "portfolia": PortfoliaParser(),
        }

    def get_supported_providers(self) -> List[AccountStatementProvider]:
        """Get list of supported account statement providers."""
        return [
            AccountStatementProvider(
                id="trade_republic",
                name="Trade Republic",
                description="German neobroker",
                supported_formats=[SupportedFormat.PDF],
                logo_url="/logos/trade_republic.png",
            ),
            AccountStatementProvider(
                id="portfolia",
                name="Portfolia",
                description="Portfolia app-generated transaction reports",
                supported_formats=[SupportedFormat.PDF],
                logo_url="/logos/portfolia.png",
            ),
        ]

    def parse_statement(
        self, provider_id: str, file_content: str, filename: str
    ) -> ParsedData:
        """Parse account statement PDF."""
        if provider_id not in self._parsers:
            raise ValueError(f"Unsupported provider: {provider_id}")

        try:
            pdf_content = base64.b64decode(file_content)
        except Exception as e:
            raise ValueError(f"Invalid base64 content: {str(e)}") from e

        parser = self._parsers[provider_id]
        result = parser.parse(pdf_content)

        if filename and result.metadata:
            result.metadata.warnings.insert(0, f"Parsed from file: {filename}")

        return result

    async def create_bulk_transactions(
            self,
            portfolio_id: int,
            transactions_data: List[BulkTransactionItem],
            user_id: int,
    ) -> Tuple[List[CreatedTransaction], BulkCreateSummary]:
        """Create multiple transactions efficiently and robustly from parsed data."""
        # 1. Verify portfolio access once at the start
        portfolio = self.portfolio_service.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise ValueError("Portfolio not found or access denied")

        created_transaction_models = []
        errors = []
        affected_asset_ids = set()

        # 2. Prepare all transaction models and add them to the session
        for i, item in enumerate(transactions_data):
            try:
                if item.transaction_type in [
                    "deposit", "withdrawal", "interest", "tax"
                ]:
                    continue

                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    asset_id=item.asset_id,
                    transaction_type=item.transaction_type,
                    quantity=item.quantity,
                    price=item.price,
                    total_amount=item.total_amount,
                    transaction_date=datetime.strptime(
                        item.transaction_date, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc),
                    fees=item.fees,
                    notes=item.notes,
                )
                self.db.add(transaction)
                affected_asset_ids.add(item.asset_id)
                created_transaction_models.append(transaction)

            except Exception as e:
                errors.append(f"Data item {i + 1} ('{item.notes}'): {str(e)}")

        # 3. Perform a single commit for all valid transactions
        try:
            if created_transaction_models:
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            return [], BulkCreateSummary(
                total_created=0,
                total_failed=len(transactions_data),
                errors=[f"Database commit failed, rolling back all changes: {e}"] + errors,
            )

        # 4. Recalculate the state for each affected asset ONCE
        for asset_id in affected_asset_ids:
            await self.portfolio_service.recalculate_asset_state(portfolio_id, asset_id)

        # 5. Prepare the successful response data
        final_created_list = [
            CreatedTransaction.from_orm(tx) for tx in created_transaction_models
        ]
        summary = BulkCreateSummary(
            total_created=len(final_created_list),
            total_failed=len(errors),
            errors=errors,
        )
        return final_created_list, summary