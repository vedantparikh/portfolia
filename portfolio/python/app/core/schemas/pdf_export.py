"""
PDF Export schemas for transaction reports.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from core.database.models.transaction import TransactionType


class TransactionExportFilters(BaseModel):
    """Filters for transaction export."""

    portfolio_ids: Optional[List[int]] = Field(
        None, description="Portfolio IDs to include"
    )
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    transaction_types: Optional[List[TransactionType]] = Field(
        None, description="Transaction types to include"
    )
    asset_symbols: Optional[List[str]] = Field(
        None, description="Asset symbols to include"
    )
    min_amount: Optional[Decimal] = Field(
        None, description="Minimum transaction amount"
    )
    max_amount: Optional[Decimal] = Field(
        None, description="Maximum transaction amount"
    )


class PDFExportOptions(BaseModel):
    """Options for PDF export configuration."""

    include_summary: bool = Field(True, description="Include summary statistics")
    include_charts: bool = Field(False, description="Include charts (future feature)")
    include_portfolio_details: bool = Field(
        True, description="Include portfolio information"
    )
    include_asset_details: bool = Field(True, description="Include asset details")
    group_by_portfolio: bool = Field(
        False, description="Group transactions by portfolio"
    )
    group_by_asset: bool = Field(False, description="Group transactions by asset")
    sort_by: str = Field("transaction_date", description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


class TransactionExportRequest(BaseModel):
    """Request model for transaction PDF export."""

    filters: TransactionExportFilters = Field(default_factory=TransactionExportFilters)
    options: PDFExportOptions = Field(default_factory=PDFExportOptions)
    custom_filename: Optional[str] = Field(
        None, description="Custom filename (without extension)"
    )


class TransactionSummaryStats(BaseModel):
    """Summary statistics for transactions."""

    total_transactions: int
    total_buy_volume: Decimal
    total_sell_volume: Decimal
    net_flow: Decimal
    total_fees: Decimal
    total_taxes: Decimal
    unique_assets: int
    date_range: str
    portfolios_included: List[str]


class ExportedTransactionData(BaseModel):
    """Transaction data for export."""

    id: int
    portfolio_name: str
    asset_symbol: str
    asset_name: str
    transaction_type: TransactionType
    quantity: Decimal
    price: Decimal
    total_amount: Decimal
    fees: Decimal
    taxes: Decimal
    transaction_date: datetime
    settlement_date: Optional[datetime]
    notes: Optional[str]
    reference_number: Optional[str]
    currency: str


class PDFExportResponse(BaseModel):
    """Response model for PDF export."""

    filename: str
    file_size: int
    transaction_count: int
    summary_stats: TransactionSummaryStats
    generated_at: datetime
    export_id: str
