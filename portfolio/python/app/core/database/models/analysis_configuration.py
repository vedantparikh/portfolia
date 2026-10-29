"""
Analysis Configuration Database Model
Database model for storing user analysis configurations.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from core.database.models.user import User


class AnalysisConfiguration(Base):
    """Analysis configuration model for storing user indicator configurations."""

    __tablename__ = "analysis_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON field to store indicator configurations
    indicators: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)

    # JSON field to store chart settings
    chart_settings: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    # Configuration metadata
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="analysis_configurations")

    def __repr__(self) -> str:
        return f"<AnalysisConfiguration(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "indicators": self.indicators,
            "chart_settings": self.chart_settings,
            "is_public": self.is_public,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
