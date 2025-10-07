"""
Analysis Configuration Database Model
Database model for storing user analysis configurations.
"""

from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class AnalysisConfiguration(Base):
    """Analysis configuration model for storing user indicator configurations."""

    __tablename__ = "analysis_configurations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # JSON field to store indicator configurations
    indicators = Column(JSON, nullable=False, default=list)

    # JSON field to store chart settings
    chart_settings = Column(JSON, nullable=True)

    # Configuration metadata
    is_public = Column(Boolean, default=False, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    user = relationship("User", back_populates="analysis_configurations")

    def __repr__(self):
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
