from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from core.database.models.transaction import TransactionType


class SupportedFormat(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"


class AccountStatementProvider(BaseModel):
    """Account statement provider information."""
    id: str = Field(..., description="Unique provider identifier")
    name: str = Field(..., description="Provider display name")
    description: str = Field(..., description="Provider description")
    supported_formats: List[SupportedFormat] = Field(..., description="Supported file formats")
    logo_url: Optional[str] = Field(None, description="Provider logo URL")


class ProvidersResponse(BaseModel):
    """Response for getting supported providers."""
    providers: List[AccountStatementProvider]


class StatementPeriod(BaseModel):
    """Statement period information."""
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")


class ParsedTransaction(BaseModel):
    """Parsed transaction from PDF statement."""
    id: str = Field(..., description="Temporary transaction ID")
    transaction_date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    name: str = Field(..., description="Asset name")
    symbol: Optional[str] = Field(None, description="Asset symbol")
    total_amount: Decimal = Field(..., description="Total transaction amount")
    quantity: Decimal = Field(..., description="Transaction quantity")
    price: Optional[Decimal] = Field(None, description="Price per share")
    fees: Decimal = Field(default=Decimal("0"), description="Transaction fees")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Parsing confidence score")
    needs_review: bool = Field(default=False, description="Whether transaction needs manual review")


class ParsingMetadata(BaseModel):
    """Metadata about the parsing process."""
    total_transactions: int = Field(..., description="Total number of transactions parsed")
    parsing_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall parsing confidence")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")


class ParsedData(BaseModel):
    """Parsed data from account statement."""
    provider: str = Field(..., description="Provider that generated the statement")
    statement_period: StatementPeriod = Field(..., description="Statement period")
    transactions: List[ParsedTransaction] = Field(..., description="Parsed transactions")
    metadata: ParsingMetadata = Field(..., description="Parsing metadata")


class ParseResponse(BaseModel):
    """Response for PDF parsing endpoint."""
    parsed_data: ParsedData


class ParseRequest(BaseModel):
    """Request for PDF parsing endpoint."""
    provider_id: str = Field(..., description="Provider identifier")
    file: str = Field(..., description="Base64 encoded PDF content")
    filename: str = Field(..., description="Original filename")


class BulkTransactionItem(BaseModel):
    """Individual transaction for bulk creation."""
    transaction_date: str = Field(..., description="Transaction datetime")
    asset_id: int = Field(..., description="Asset ID")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    quantity: Decimal = Field(..., description="Transaction quantity")
    price: Decimal = Field(..., description="Price per share")
    total_amount: Decimal = Field(..., description="Total transaction amount")
    fees: Decimal = Field(default=Decimal("0"), description="Transaction fees")
    notes: Optional[str] = Field(None, description="Transaction notes")


class BulkTransactionCreate(BaseModel):
    """Request for bulk transaction creation."""
    portfolio_id: int = Field(..., description="Target portfolio ID")
    transactions: List[BulkTransactionItem] = Field(..., description="Transactions to create")


class CreatedTransaction(BaseModel):
    """Created transaction response."""
    id: int = Field(..., description="Transaction ID")
    transaction_date: str = Field(..., description="Transaction date")
    asset_id: int = Field(..., description="Asset ID")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    quantity: Decimal = Field(..., description="Transaction quantity")
    price: Decimal = Field(..., description="Price per share")
    fees: Decimal = Field(..., description="Transaction fees")
    total_amount: Decimal = Field(..., description="Total transaction amount")
    portfolio_id: int = Field(..., description="Portfolio ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class BulkCreateSummary(BaseModel):
    """Summary of bulk transaction creation."""
    total_created: int = Field(..., description="Number of transactions created")
    total_failed: int = Field(..., description="Number of transactions that failed")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class BulkCreateResponse(BaseModel):
    """Response for bulk transaction creation."""
    created_transactions: List[CreatedTransaction] = Field(..., description="Successfully created transactions")
    summary: BulkCreateSummary = Field(..., description="Creation summary")
