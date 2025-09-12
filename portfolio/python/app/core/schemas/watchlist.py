from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field, Field


class WatchlistBase(BaseModel):
    """Base watchlist schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Watchlist name")
    description: Optional[str] = Field(
        None, max_length=500, description="Watchlist description"
    )
    is_public: bool = Field(False, description="Whether the watchlist is public")
    color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code"
    )


class WatchlistCreate(WatchlistBase):
    """Schema for creating a new watchlist."""

    pass


class WatchlistUpdate(BaseModel):
    """Schema for updating a watchlist."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: Optional[int] = Field(None, ge=0)


class WatchlistResponse(WatchlistBase):
    """Schema for watchlist response."""

    id: int
    user_id: int
    is_default: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    # Calculated fields (not in database)
    item_count: Optional[int] = Field(None, description="Number of items in watchlist")
    total_gain_loss: Optional[Decimal] = Field(
        None, description="Total gain/loss across all items"
    )
    total_gain_loss_percent: Optional[Decimal] = Field(
        None, description="Total gain/loss percentage"
    )

    class Config:
        from_attributes = True


class WatchlistItemBase(BaseModel):
    """Base watchlist item schema."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    company_name: Optional[str] = Field(
        None, max_length=255, description="Company name"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="User notes")
    personal_rating: Optional[int] = Field(
        None, ge=1, le=5, description="1-5 star rating"
    )
    investment_thesis: Optional[str] = Field(
        None, max_length=2000, description="Investment thesis"
    )
    tags: Optional[List[str]] = Field(
        None, max_items=10, description="User-defined tags"
    )


class WatchlistItemCreate(WatchlistItemBase):
    """Schema for creating a new watchlist item."""

    pass


class WatchlistItemUpdate(BaseModel):
    """Schema for updating a watchlist item."""

    company_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)
    personal_rating: Optional[int] = Field(None, ge=1, le=5)
    investment_thesis: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None, max_items=10)
    sort_order: Optional[int] = Field(None, ge=0)


class WatchlistItemResponse(WatchlistItemBase):
    """Schema for watchlist item response."""

    id: int
    watchlist_id: int
    sort_order: int
    added_date: datetime
    updated_at: datetime

    # Performance data (from database)
    added_price: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    price_change_since_added: Optional[Decimal] = None
    price_change_percent_since_added: Optional[Decimal] = None

    # Alert settings (from database)
    alerts_enabled: bool
    alert_price_high: Optional[Decimal] = None
    alert_price_low: Optional[Decimal] = None
    alert_price_change_percent: Optional[Decimal] = None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def days_since_added(self) -> Optional[int]:
        """Calculates the number of days since the item was added."""
        if not self.added_date:
            return None

        # Ensure timezone-aware comparison to prevent potential TypeErrors
        now_utc = datetime.now(timezone.utc)
        added_date_utc = self.added_date

        # If the added_date is naive, assume it's UTC
        if added_date_utc.tzinfo is None:
            added_date_utc = added_date_utc.replace(tzinfo=timezone.utc)

        time_difference = now_utc - added_date_utc
        return time_difference.days


class WatchlistWithItemsResponse(WatchlistResponse):
    """Schema for watchlist with items response."""

    items: List[WatchlistItemResponse] = []
    performance_summary: Optional[Dict[str, Any]] = None


class WatchlistAlertBase(BaseModel):
    """Base watchlist alert schema."""

    alert_type: str = Field(
        ..., description="Type of alert: price_high, price_low, percent_change"
    )
    threshold_value: Decimal = Field(..., description="Value that triggers the alert")
    condition: str = Field(..., description="Condition: above, below, equals")
    notify_email: bool = Field(True, description="Send email notification")
    notify_push: bool = Field(False, description="Send push notification")
    notify_sms: bool = Field(False, description="Send SMS notification")


class WatchlistAlertCreate(WatchlistAlertBase):
    """Schema for creating a new alert."""

    pass


class WatchlistAlertUpdate(BaseModel):
    """Schema for updating an alert."""

    threshold_value: Optional[Decimal] = None
    condition: Optional[str] = None
    is_active: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_push: Optional[bool] = None
    notify_sms: Optional[bool] = None


class WatchlistAlertResponse(WatchlistAlertBase):
    """Schema for alert response."""

    id: int
    watchlist_item_id: int
    user_id: int
    is_active: bool
    is_triggered: bool
    triggered_at: Optional[datetime] = None
    triggered_value: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WatchlistPerformanceResponse(BaseModel):
    """Schema for performance data response."""

    date: datetime
    price: Decimal
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    price_change_since_added: Optional[Decimal] = None
    price_change_percent_since_added: Optional[Decimal] = None
    days_since_added: Optional[int] = None


class WatchlistReorderRequest(BaseModel):
    """Schema for reordering watchlist items."""

    item_ids: List[int] = Field(
        ..., min_items=1, description="Ordered list of item IDs"
    )


class WatchlistBulkAddRequest(BaseModel):
    """Schema for adding multiple symbols to a watchlist."""

    symbols: List[str] = Field(
        ..., min_items=1, max_items=100, description="List of stock symbols"
    )


class WatchlistStatsResponse(BaseModel):
    """Schema for watchlist statistics."""

    total_watchlists: int
    total_items: int
    public_watchlists: int
    total_gain_loss: Decimal
    total_gain_loss_percent: Decimal
    best_performing_symbol: Optional[Dict[str, Any]] = None
    worst_performing_symbol: Optional[Dict[str, Any]] = None
    most_watched_symbols: List[Dict[str, Any]]
    recent_additions: List[WatchlistItemResponse]
    active_alerts: int


class WatchlistPerformanceSummary(BaseModel):
    """Schema for watchlist performance summary."""

    total_items: int
    items_with_gains: int
    items_with_losses: int
    total_gain_loss: Decimal
    total_gain_loss_percent: Decimal
    average_gain_loss: Decimal
    best_performer: Optional[WatchlistItemResponse] = None
    worst_performer: Optional[WatchlistItemResponse] = None
    performance_by_tag: Optional[Dict[str, Dict[str, Any]]] = None
