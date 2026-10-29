from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database.models.base import Base


class BrokerConnection(Base):
    """A user's login at a broker (Trade Republic via pytr): session encrypted, PIN never stored."""

    __tablename__ = "broker_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    # pending (login waiting for confirmation), connected, expired
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    # idle, running, succeeded, failed
    fetch_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="idle"
    )
    fetch_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetch_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetch_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("uq_broker_connections_user_source", "user_id", "source", unique=True),
    )
