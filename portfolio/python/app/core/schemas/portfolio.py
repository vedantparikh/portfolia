from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from core.database.models.asset import AssetType
from core.database.models.transaction import TransactionStatus, TransactionType


class PortfolioBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    currency: str = Field(default="USD", max_length=3)
    is_active: bool = Field(default=True)
    is_public: bool = Field(default=False)


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    currency: Optional[str] = Field(None, max_length=3)
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class Portfolio(PortfolioBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    sync_source: Optional[str] = None
    synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PytrSyncAvailability(BaseModel):
    available: bool = Field(
        ..., description="This user may link a portfolio to the export"
    )
    file_updated_at: Optional[datetime] = None


class PortfolioSyncUpdate(BaseModel):
    source: Optional[Literal["pytr"]] = Field(None, description="null unlinks")


class TradePricedInstrument(BaseModel):
    isin: str
    name: str
    suggested_symbol: Optional[str] = None


class RedeemedInstrument(BaseModel):
    isin: str
    name: str
    date: str
    amount: Decimal


class PortfolioSyncReport(BaseModel):
    file_updated_at: Optional[datetime] = None
    created: int = 0
    already_imported: int = 0
    failed: int = 0
    errors: List[str] = Field(default_factory=list)
    trade_priced: List[TradePricedInstrument] = Field(
        default_factory=list,
        description="No market data: valued at their own last fill until given a ticker",
    )
    redeemed: List[RedeemedInstrument] = Field(
        default_factory=list,
        description="Knock-outs booked as sold at their redemption",
    )
    not_imported: dict[str, int] = Field(
        default_factory=dict, description="Rows the parser skipped, by reason"
    )


class PortfolioSyncStatus(BaseModel):
    source: Optional[str] = None
    synced_at: Optional[datetime] = None
    file_updated_at: Optional[datetime] = None
    report: Optional[PortfolioSyncReport] = None


class InstrumentMapping(BaseModel):
    isin: str = Field(..., min_length=12, max_length=12)
    symbol: str = Field(..., min_length=1, max_length=30)


class PortfolioAssetBase(BaseModel):
    portfolio_id: int
    asset_id: int
    quantity: Decimal = Field(...)
    cost_basis: Decimal = Field(...)
    cost_basis_total: Decimal = Field(...)
    current_value: Optional[Decimal] = Field(None)
    unrealized_pnl: Optional[Decimal] = Field(None)
    unrealized_pnl_percent: Optional[Decimal] = Field(None)
    realized_pnl: Optional[Decimal] = Field(None)
    realized_pnl_percent: Optional[Decimal] = Field(None)


class PortfolioAssetCreate(BaseModel):
    portfolio_id: int
    asset_id: int
    quantity: Decimal = Field(...)
    cost_basis: Decimal = Field(...)


class PortfolioAsset(PortfolioAssetBase):
    id: int
    last_updated: datetime

    class Config:
        from_attributes = True


class PortfolioAssetWithDetails(PortfolioAsset):
    """Portfolio asset with additional asset information"""

    symbol: Optional[str] = None
    asset_name: Optional[str] = None
    market_value: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_return_percent: Optional[Decimal] = None


class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: AssetType
    exchange: Optional[str] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None)
    asset_type: Optional[AssetType] = Field(None)
    currency: Optional[str] = Field(None)
    exchange: Optional[str] = Field(None)
    isin: Optional[str] = Field(None)
    cusip: Optional[str] = Field(None)
    sector: Optional[str] = Field(None)
    industry: Optional[str] = Field(None)
    country: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class AssetDetail(BaseModel):
    open: Optional[Decimal] = Field(None)
    current_price: Optional[Decimal] = Field(None)
    market_cap: Optional[Decimal] = Field(None)
    day_low: Optional[Decimal] = Field(None)
    day_high: Optional[Decimal] = Field(None)
    low_52w: Optional[Decimal] = Field(None)
    high_52w: Optional[Decimal] = Field(None)
    volume_24h: Optional[Decimal] = Field(None)
    price_change_percentage_24h: Optional[Decimal] = Field(None)
    beta: Optional[Decimal] = Field(None)
    trailing_PE: Optional[Decimal] = Field(None)
    forward_PE: Optional[Decimal] = Field(None)
    dividend_yield: Optional[Decimal] = Field(None)
    payout_ratio: Optional[Decimal] = Field(None)
    # Asset Business details
    book_value: Optional[Decimal] = Field(None)
    price_to_book: Optional[Decimal] = Field(None)
    earnings_growth: Optional[Decimal] = Field(None)
    revenue_growth: Optional[Decimal] = Field(None)
    return_on_asset: Optional[Decimal] = Field(None)
    return_on_equity: Optional[Decimal] = Field(None)
    free_cashflow: Optional[Decimal] = Field(None)
    operating_cashflow: Optional[Decimal] = Field(None)
    total_debt: Optional[Decimal] = Field(None)
    total_cash: Optional[Decimal] = Field(None)
    full_time_employees: Optional[Decimal] = Field(None)
    long_business_summary: Optional[str] = Field(None)
    website: Optional[str] = Field(None)


class Asset(AssetBase):
    id: int
    currency: Optional[str] = Field(None, description="Quote currency (from Yahoo)")
    created_at: datetime
    updated_at: Optional[datetime] = None
    detail: Optional[AssetDetail] = None

    class Config:
        from_attributes = True

    @field_validator("detail", mode="before")
    @classmethod
    def validate_detail(cls, v):
        # This validator runs before Pydantic's own validation.
        # If the incoming value 'v' is a dict, it creates an AssetDetail instance from it.
        # If 'v' is already None or an AssetDetail instance, it passes it through unchanged.
        if isinstance(v, dict):
            return AssetDetail(**v)
        return v


class AssetBulkCreateRequest(BaseModel):
    """Schema for bulk asset creation request."""

    symbols: List[str]
    allow_minimal_on_market_data_failure: bool = Field(
        default=False,
        description=(
            "If true, when yfinance cannot return ticker info, create a minimal "
            "Asset (symbol, generic name, default type) so flows like demo seeding still work."
        ),
    )


class FailedAssetInfo(BaseModel):
    """Schema for reporting a failed asset creation."""

    symbol: str
    reason: str


class AssetBulkCreateResponse(BaseModel):
    """Schema for bulk asset creation response."""

    created: List[Asset]
    failed: List[FailedAssetInfo]


class AssetPriceData(BaseModel):
    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    dividends: Decimal
    stock_splits: Decimal


class AssetPrice(BaseModel):
    asset_id: int
    symbol: str
    interval: str
    period: str
    data_points: int
    data: List[AssetPriceData]


# Buys, sells and transfers move shares, so the quantity has to be positive.
# A split's quantity is the ratio. Dividends often arrive as a cash amount with
# quantity 0 (the importer stores the statement total, not shares × rate).
_POSITIVE_QUANTITY = {
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.TRANSFER_IN,
    TransactionType.TRANSFER_OUT,
    TransactionType.SPLIT,
}


def check_transaction_numbers(
    transaction_type: Optional[TransactionType],
    quantity: Optional[Decimal],
    price: Optional[Decimal],
    *,
    quantity_set: bool = True,
    price_set: bool = True,
) -> None:
    """Reject a quantity or price the transaction type cannot mean."""
    if quantity_set and quantity is not None:
        if transaction_type in _POSITIVE_QUANTITY:
            if quantity <= 0:
                raise ValueError(
                    f"{transaction_type.value} quantity must be greater than 0"
                )
        elif quantity < 0:
            raise ValueError("quantity must be zero or greater")
    if price_set and price is not None and price < 0:
        raise ValueError("price must be zero or greater")


class TransactionBase(BaseModel):
    portfolio_id: int
    asset_id: int
    transaction_type: TransactionType
    status: TransactionStatus = Field(default=TransactionStatus.COMPLETED)
    quantity: Decimal = Field(...)
    price: Decimal = Field(...)
    total_amount: Decimal = Field(...)
    currency: str = Field(default="USD")
    transaction_date: datetime
    settlement_date: Optional[datetime] = None
    notes: Optional[str] = None
    reference_number: Optional[str] = None
    fees: Decimal = Field(default=Decimal("0"))
    taxes: Decimal = Field(default=Decimal("0"))


class TransactionCreate(TransactionBase):
    # Computed server-side from quantity, price, fees and taxes; any value sent is ignored
    total_amount: Optional[Decimal] = None

    @model_validator(mode="after")
    def _numbers(self):
        check_transaction_numbers(self.transaction_type, self.quantity, self.price)
        return self


class TransactionUpdate(BaseModel):
    transaction_type: Optional[TransactionType] = None
    quantity: Optional[Decimal] = Field(None)
    price: Optional[Decimal] = Field(None)
    total_amount: Optional[Decimal] = Field(None)
    currency: Optional[str] = None
    transaction_date: Optional[datetime] = None
    settlement_date: Optional[datetime] = None
    notes: Optional[str] = None
    reference_number: Optional[str] = None
    fees: Optional[Decimal] = Field(None)
    taxes: Optional[Decimal] = Field(None)
    status: Optional[TransactionStatus] = None

    @model_validator(mode="after")
    def _numbers(self):
        check_transaction_numbers(
            self.transaction_type,
            self.quantity,
            self.price,
            quantity_set="quantity" in self.model_fields_set,
            price_set="price" in self.model_fields_set,
        )
        return self


class Transaction(TransactionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    portfolio: Portfolio
    asset: Asset

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    """Portfolio summary with performance metrics"""

    portfolio_id: int
    portfolio_name: str
    currency: str
    total_assets: int
    total_cost_basis: float
    total_current_value: float
    today_pnl: float
    today_pnl_percent: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    last_updated: Optional[datetime]
    recent_transactions: int
    is_active: bool
    is_public: bool
    total_realized_pnl: float = Field(
        default=0.0, description="Realized gains and losses on sales, before tax"
    )
    total_dividends: float = Field(default=0.0, description="Dividends before tax")
    taxes_withheld: float = Field(
        default=0.0, description="Tax withheld on sales and dividends"
    )
    tax_adjustments: float = Field(
        default=0.0,
        description="Account-level tax entries: charges positive, refunds negative",
    )
    net_taxes_paid: float = Field(
        default=0.0, description="taxes_withheld + tax_adjustments"
    )
    realized_after_tax: float = Field(
        default=0.0,
        description="total_realized_pnl + total_dividends - net_taxes_paid",
    )
    missing_prices: List[str] = Field(
        default_factory=list,
        description="Open positions without a live price, left out of value and P&L",
    )


class PortfolioHolding(BaseModel):
    """Detailed portfolio holding with current values"""

    asset_id: int
    symbol: str
    name: str
    quantity: float
    cost_basis: float
    cost_basis_total: float
    current_value: Optional[float]
    unrealized_pnl: Optional[float]
    unrealized_pnl_percent: Optional[float]
    realized_pnl: Optional[float]
    realized_pnl_percent: Optional[float]
    today_pnl: Optional[float]
    today_pnl_percent: Optional[float]
    current_price: Optional[float] = None
    weight_percent: Optional[float] = Field(
        None, description="Share of the priced portfolio value (%)"
    )
    last_updated: datetime


class CurrencyTotals(BaseModel):
    """Active portfolios in one currency, summed (values are never mixed across currencies)."""

    currency: str
    portfolios: int
    total_assets: int
    total_value: float
    today_pnl: float = 0.0
    today_pnl_percent: float = 0.0


class PortfolioStatistics(BaseModel):
    """Overall portfolio statistics for a user"""

    total_portfolios: int
    active_portfolios: int
    total_assets: int
    totals: List[CurrencyTotals] = Field(
        default_factory=list, description="One entry per portfolio currency"
    )
    total_value: Optional[float] = Field(
        None, description="Only when every active portfolio has the same currency"
    )
    currency: Optional[str] = None
    today_pnl: Optional[float] = None
    today_pnl_percent: Optional[float] = None
    missing_prices: List[str] = Field(default_factory=list)


# Legacy class for backward compatibility - maps to PortfolioAsset
class PortfolioItem(BaseModel):
    id: int
    currency: str
    portfolio_id: int
    asset_id: int
    quantity: Decimal
    average_price: Decimal  # Maps to cost_basis
    created_at: datetime  # Maps to last_updated
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
