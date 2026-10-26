from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database.models.base import Base

if TYPE_CHECKING:
    from core.database.models.asset import Asset
    from core.database.models.portfolio import Portfolio
    from core.database.models.user import User


class TransactionType(enum.Enum):
    """Transaction type enumeration."""

    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    MERGER = "merger"
    SPIN_OFF = "spin_off"
    RIGHTS_ISSUE = "rights_issue"
    STOCK_OPTION_EXERCISE = "stock_option_exercise"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    FEE = "fee"
    OTHER = "other"


class TransactionStatus(enum.Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class EntryMethod(enum.Enum):
    """Transaction entry method enumeration."""

    MANUAL = "manual"
    PDF_IMPORT = "pdf_import"
    API_IMPORT = "api_import"
    CSV_IMPORT = "csv_import"


class Transaction(Base):
    """Portfolio transaction model."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.COMPLETED, nullable=False
    )

    # Transaction details
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # Support for fractional shares
    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # Price per share/unit
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False
    )  # Total transaction value
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Transaction metadata
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    settlement_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # External reference
    source_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # Imported statement row
    fees: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=0, nullable=False
    )  # Transaction fees
    taxes: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=0, nullable=False
    )  # Tax implications

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
    portfolio: Mapped[Portfolio] = relationship(
        "Portfolio", back_populates="transactions"
    )
    asset: Mapped[Asset] = relationship("Asset", back_populates="transactions")
    manual_entry: Mapped[ManualEntry] = relationship(
        "ManualEntry",
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_transactions_portfolio_id", "portfolio_id"),
        Index("idx_transactions_asset_id", "asset_id"),
        Index("idx_transactions_type", "transaction_type"),
        Index("idx_transactions_status", "status"),
        Index("idx_transactions_date", "transaction_date"),
        Index("idx_transactions_portfolio_date", "portfolio_id", "transaction_date"),
        Index("idx_transactions_asset_date", "asset_id", "transaction_date"),
        Index(
            "uq_transactions_portfolio_source_key",
            "portfolio_id",
            "source_key",
            unique=True,
        ),
    )

    @staticmethod
    def compute_total_amount(
        transaction_type: "TransactionType",
        quantity: Decimal,
        price: Decimal,
        fees: Decimal | None = None,
        taxes: Decimal | None = None,
    ) -> Decimal:
        """
        Cash actually moved by a transaction, which is what `total_amount` stores.

        BUY:  quantity * price + fees + taxes  (cash paid; becomes the cost basis)
        SELL: quantity * price - fees - taxes  (net proceeds received)
        Other types: quantity * price
        """
        gross = Decimal(quantity) * Decimal(price)
        costs = Decimal(fees or 0) + Decimal(taxes or 0)
        if transaction_type == TransactionType.BUY:
            return gross + costs
        if transaction_type == TransactionType.SELL:
            return gross - costs
        return gross

    @property
    def is_buy(self) -> bool:
        """Check if transaction is a buy."""
        return self.transaction_type == TransactionType.BUY

    @property
    def is_sell(self) -> bool:
        """Check if transaction is a sell."""
        return self.transaction_type == TransactionType.SELL


class ManualEntry(Base):
    """Manual transaction entry tracking."""

    __tablename__ = "manual_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    transaction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    entry_method: Mapped[EntryMethod] = mapped_column(
        Enum(EntryMethod), default=EntryMethod.MANUAL, nullable=False
    )
    validation_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, validated, flagged
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # If imported from file
    import_batch_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # For batch imports
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
    user: Mapped[User] = relationship("User", back_populates="manual_entries")
    transaction: Mapped[Transaction] = relationship(
        "Transaction", back_populates="manual_entry"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_manual_entries_user_id", "user_id"),
        Index("idx_manual_entries_transaction_id", "transaction_id"),
        Index("idx_manual_entries_method", "entry_method"),
        Index("idx_manual_entries_validation", "validation_status"),
        Index("idx_manual_entries_batch", "import_batch_id"),
    )
