from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database.models.base import Base


class Watchlist(Base):
    """User watchlist model - supports multiple watchlists per user."""

    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    color = Column(String(7), nullable=True)  # Hex color code for UI
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="watchlists")
    items = relationship(
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

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(
        Integer, ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String(20), nullable=False)  # Stock symbol (e.g., AAPL, GOOGL)
    company_name = Column(String(255), nullable=True)

    # Performance tracking
    added_price = Column(Numeric(10, 2), nullable=True)  # Price when added to watchlist
    added_date = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    current_price = Column(Numeric(10, 2), nullable=True)  # Latest known price
    price_change_since_added = Column(Numeric(10, 2), nullable=True)  # Absolute change
    price_change_percent_since_added = Column(
        Numeric(5, 2), nullable=True
    )  # Percentage change

    # User notes and preferences
    notes = Column(Text, nullable=True)  # User notes about this stock
    personal_rating = Column(Integer, nullable=True)  # 1-5 star rating
    investment_thesis = Column(Text, nullable=True)  # Why user is watching this stock

    # Price alerts
    alert_price_high = Column(Numeric(10, 2), nullable=True)  # High price alert
    alert_price_low = Column(Numeric(10, 2), nullable=True)  # Low price alert
    alert_price_change_percent = Column(Numeric(5, 2), nullable=True)  # % change alert
    alerts_enabled = Column(Boolean, default=True, nullable=False)

    # Organization
    sort_order = Column(Integer, default=0, nullable=False)
    tags = Column(JSON, nullable=True)  # User-defined tags for categorization

    # Timestamps
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    watchlist = relationship("Watchlist", back_populates="items")
    alerts = relationship(
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

    id = Column(Integer, primary_key=True, index=True)
    watchlist_item_id = Column(
        Integer, ForeignKey("watchlist_items.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Alert configuration
    alert_type = Column(
        String(50), nullable=False
    )  # 'price_high', 'price_low', 'percent_change'
    threshold_value = Column(
        Numeric(10, 2), nullable=False
    )  # The value that triggers the alert
    condition = Column(String(20), nullable=False)  # 'above', 'below', 'equals'

    # Alert status
    is_active = Column(Boolean, default=True, nullable=False)
    is_triggered = Column(Boolean, default=False, nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    triggered_value = Column(
        Numeric(10, 2), nullable=True
    )  # Value when alert was triggered

    # Notification settings
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_push = Column(Boolean, default=False, nullable=False)
    notify_sms = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    watchlist_item = relationship("WatchlistItem", back_populates="alerts")
    user = relationship("User", back_populates="watchlist_alerts")

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

    id = Column(Integer, primary_key=True, index=True)
    watchlist_item_id = Column(
        Integer, ForeignKey("watchlist_items.id", ondelete="CASCADE"), nullable=False
    )

    # Performance data
    date = Column(DateTime(timezone=True), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    volume = Column(Integer, nullable=True)
    market_cap = Column(Numeric(20, 2), nullable=True)

    # Calculated metrics
    price_change_since_added = Column(Numeric(10, 2), nullable=True)
    price_change_percent_since_added = Column(Numeric(5, 2), nullable=True)
    days_since_added = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    watchlist_item = relationship("WatchlistItem")

    # Constraints
    __table_args__ = (
        Index("idx_watchlist_performance_item_id", "watchlist_item_id"),
        Index("idx_watchlist_performance_date", "date"),
        Index("idx_watchlist_performance_price", "price"),
    )
