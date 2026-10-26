from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.models.base import Base

if TYPE_CHECKING:
    from core.database.models.analysis_configuration import AnalysisConfiguration
    from core.database.models.asset import Asset
    from core.database.models.portfolio import Portfolio
    from core.database.models.transaction import ManualEntry
    from core.database.models.watchlist import Watchlist, WatchlistAlert


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    profile: Mapped[UserProfile] = relationship(
        "UserProfile", back_populates="user", uselist=False
    )
    sessions: Mapped[list[UserSession]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    portfolios: Mapped[list[Portfolio]] = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    assets: Mapped[list[Asset]] = relationship(
        "Asset", back_populates="user", cascade="all, delete-orphan"
    )
    manual_entries: Mapped[list[ManualEntry]] = relationship(
        "ManualEntry", back_populates="user", cascade="all, delete-orphan"
    )
    watchlists: Mapped[list[Watchlist]] = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_alerts: Mapped[list[WatchlistAlert]] = relationship(
        "WatchlistAlert", back_populates="user", cascade="all, delete-orphan"
    )
    analysis_configurations: Mapped[list[AnalysisConfiguration]] = relationship(
        "AnalysisConfiguration", back_populates="user", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        Index("idx_users_active", "is_active"),
    )


class UserProfile(Base):
    """Extended user profile information."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    currency_preference: Mapped[str] = mapped_column(
        String(3), default="USD", nullable=False
    )
    language_preference: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False
    )
    notification_preferences: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string
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
    user: Mapped[User] = relationship("User", back_populates="profile")

    # Indexes
    __table_args__ = (
        Index("idx_user_profiles_user_id", "user_id"),
        Index("idx_user_profiles_country", "country"),
        Index("idx_user_profiles_currency", "currency_preference"),
    )


class UserSession(Base):
    """User session management for authentication."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token: Mapped[str] = mapped_column(String(500), nullable=False)
    device_info: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string with device details
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )  # IPv6 compatible
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("idx_user_sessions_session_id", "session_id"),
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_expires_at", "expires_at"),
        Index("idx_user_sessions_active", "is_active"),
    )

    @classmethod
    def generate_session_id(cls) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(32)

    @classmethod
    def generate_refresh_token(cls) -> str:
        """Generate a unique refresh token."""
        return secrets.token_urlsafe(64)

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def extend_session(self, hours: int = 24) -> None:
        """Extend session expiration time."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.last_used = datetime.now(timezone.utc)
