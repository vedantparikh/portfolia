import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database.models.base import Base


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

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(
        Enum(TransactionStatus), default=TransactionStatus.COMPLETED, nullable=False
    )

    # Transaction details
    quantity = Column(Numeric(20, 8), nullable=False)  # Support for fractional shares
    price = Column(Numeric(20, 4), nullable=False)  # Price per share/unit
    total_amount = Column(Numeric(20, 4), nullable=False)  # Total transaction value
    currency = Column(String(3), default="USD", nullable=False)

    # Transaction metadata
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    settlement_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)  # External reference
    fees = Column(Numeric(20, 4), default=0, nullable=False)  # Transaction fees
    taxes = Column(Numeric(20, 4), default=0, nullable=False)  # Tax implications

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
    portfolio = relationship("Portfolio", back_populates="transactions")
    asset = relationship("Asset", back_populates="transactions")
    manual_entry = relationship(
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
    )

    @property
    def net_amount(self) -> float:
        """Calculate net amount after fees and taxes."""
        return float(self.total_amount) - float(self.fees) - float(self.taxes)

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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    entry_method = Column(Enum(EntryMethod), default=EntryMethod.MANUAL, nullable=False)
    validation_status = Column(
        String(50), default="pending", nullable=False
    )  # pending, validated, flagged
    validation_notes = Column(Text, nullable=True)
    source_file = Column(String(255), nullable=True)  # If imported from file
    import_batch_id = Column(String(100), nullable=True)  # For batch imports
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
    user = relationship("User", back_populates="manual_entries")
    transaction = relationship("Transaction", back_populates="manual_entry")

    # Indexes for performance
    __table_args__ = (
        Index("idx_manual_entries_user_id", "user_id"),
        Index("idx_manual_entries_transaction_id", "transaction_id"),
        Index("idx_manual_entries_method", "entry_method"),
        Index("idx_manual_entries_validation", "validation_status"),
        Index("idx_manual_entries_batch", "import_batch_id"),
    )
