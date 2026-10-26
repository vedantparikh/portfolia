from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database.models.base import Base

if TYPE_CHECKING:
    from core.database.models.user import User


class Watchlist(Base):
    """User watchlist model - supports multiple watchlists per user."""

    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    color: Mapped[str | None] = mapped_column(
        String(7), nullable=True
    )  # Hex color code for UI
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="watchlists")
    items: Mapped[list[WatchlistItem]] = relationship(
        "WatchlistItem",
        back_populates="watchlist",
        cascade="all, delete-orphan",
        order_by="WatchlistItem.sort_order",
    )

    # Constraints
    __table_args__ = (
        Index("idx_watchlists_user_id", "user_id"),
        Index("idx_watchlists_name", "name"),
        Index("idx_watchlists_default", "is_default"),
        Index("idx_watchlists_public", "is_public"),
        UniqueConstraint("user_id", "name", name="uq_watchlist_user_name"),
    )


class WatchlistItem(Base):
    """Individual stock/symbol in a watchlist with performance tracking."""

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    watchlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # Stock symbol (e.g., AAPL, GOOGL)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Performance tracking
    added_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Price when added to watchlist
    added_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Latest known price
    price_change_since_added: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Absolute change
    price_change_percent_since_added: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Percentage change

    # User notes and preferences
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # User notes about this stock
    personal_rating: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 1-5 star rating
    investment_thesis: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Why user is watching this stock

    # Price alerts
    alert_price_high: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # High price alert
    alert_price_low: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Low price alert
    alert_price_change_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # % change alert
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Organization
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags: Mapped[Any | None] = mapped_column(
        JSON, nullable=True
    )  # User-defined tags for categorization

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    watchlist: Mapped[Watchlist] = relationship("Watchlist", back_populates="items")
    alerts: Mapped[list[WatchlistAlert]] = relationship(
        "WatchlistAlert", back_populates="watchlist_item", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        Index("idx_watchlist_items_watchlist_id", "watchlist_id"),
        Index("idx_watchlist_items_symbol", "symbol"),
        Index("idx_watchlist_items_sort_order", "sort_order"),
        Index("idx_watchlist_items_added_date", "added_date"),
        Index("idx_watchlist_items_alerts_enabled", "alerts_enabled"),
        UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_item_symbol"),
    )


class WatchlistAlert(Base):
    """Price and performance alerts for watchlist items."""

    __tablename__ = "watchlist_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    watchlist_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("watchlist_items.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Alert configuration
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'price_high', 'price_low', 'percent_change'
    threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # The value that triggers the alert
    condition: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'above', 'below', 'equals'

    # Alert status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_value: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )  # Value when alert was triggered

    # Notification settings
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_push: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    watchlist_item: Mapped[WatchlistItem] = relationship(
        "WatchlistItem", back_populates="alerts"
    )
    user: Mapped[User] = relationship("User", back_populates="watchlist_alerts")

    # Constraints
    __table_args__ = (
        Index("idx_watchlist_alerts_item_id", "watchlist_item_id"),
        Index("idx_watchlist_alerts_user_id", "user_id"),
        Index("idx_watchlist_alerts_type", "alert_type"),
        Index("idx_watchlist_alerts_active", "is_active"),
        Index("idx_watchlist_alerts_triggered", "is_triggered"),
    )


class WatchlistPerformance(Base):
    """Historical performance tracking for watchlist items."""

    __tablename__ = "watchlist_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    watchlist_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("watchlist_items.id", ondelete="CASCADE"), nullable=False
    )

    # Performance data
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    # Calculated metrics
    price_change_since_added: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    price_change_percent_since_added: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    days_since_added: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    watchlist_item: Mapped[WatchlistItem] = relationship("WatchlistItem")

    # Constraints
    __table_args__ = (
        Index("idx_watchlist_performance_item_id", "watchlist_item_id"),
        Index("idx_watchlist_performance_date", "date"),
        Index("idx_watchlist_performance_price", "price"),
    )
