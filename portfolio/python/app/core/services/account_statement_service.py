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
        self.portfolio_service = PortfolioService(db)

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
        """Create multiple transactions from parsed data."""
        created_transactions = []
        errors = []

        portfolio = self.portfolio_service.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise ValueError("Portfolio not found or access denied")

        for i, transaction_data in enumerate(transactions_data):
            try:
                if transaction_data.transaction_type in [
                    "deposit",
                    "withdrawal",
                    "interest",
                    "tax",
                ]:
                    continue

                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    asset_id=transaction_data.asset_id,
                    transaction_type=transaction_data.transaction_type,
                    quantity=transaction_data.quantity,
                    price=transaction_data.price,
                    total_amount=transaction_data.total_amount,
                    transaction_date=datetime.strptime(
                        transaction_data.transaction_date, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc),
                    fees=transaction_data.fees,
                    notes=transaction_data.notes,
                )

                self.db.add(transaction)
                self.db.flush()

                await self.portfolio_service.update_portfolio_asset_from_transaction(
                    portfolio_id, transaction.asset_id, transaction
                )

                created_transaction = CreatedTransaction(
                    id=transaction.id,
                    transaction_date=transaction.transaction_date.strftime("%Y-%m-%d"),
                    asset_id=transaction.asset_id,
                    transaction_type=transaction.transaction_type,
                    quantity=transaction.quantity,
                    price=transaction.price,
                    fees=transaction.fees,
                    total_amount=transaction.total_amount,
                    portfolio_id=portfolio_id,
                    notes=transaction.notes,
                    created_at=transaction.created_at,
                )
                created_transactions.append(created_transaction)

            except Exception as e:
                errors.append(f"Transaction {i+1}: {str(e)}")

        self.db.commit()

        summary = BulkCreateSummary(
            total_created=len(created_transactions),
            total_failed=len(errors),
            errors=errors,
        )

        return created_transactions, summary
