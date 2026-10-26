from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.database.models.transaction import TransactionType
from core.schemas.portfolio import check_transaction_numbers


class SupportedFormat(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"


class AccountStatementProvider(BaseModel):
    """Account statement provider information."""

    id: str = Field(..., description="Unique provider identifier")
    name: str = Field(..., description="Provider display name")
    description: str = Field(..., description="Provider description")
    supported_formats: List[SupportedFormat] = Field(
        ..., description="Supported file formats"
    )
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
    transaction_date: str = Field(
        ..., description="Transaction date in YYYY-MM-DD format"
    )
    transaction_type: TransactionType = Field(..., description="Transaction type")
    name: str = Field(..., description="Asset name")
    symbol: Optional[str] = Field(None, description="Asset symbol")
    total_amount: Decimal = Field(..., description="Total transaction amount")
    quantity: Decimal = Field(..., description="Transaction quantity")
    price: Optional[Decimal] = Field(None, description="Price per share")
    fees: Decimal = Field(default=Decimal("0"), description="Transaction fees")
    taxes: Decimal = Field(default=Decimal("0"), description="Taxes withheld")
    currency: Optional[str] = Field(None, description="ISO currency of the amounts")
    source_key: Optional[str] = Field(
        None, description="Stable id of the statement row, used to skip re-imports"
    )


class SkippedRow(BaseModel):
    """A statement row that is read but not imported."""

    transaction_date: str = Field(..., description="Date in YYYY-MM-DD format")
    kind: str = Field(..., description="Row type as printed on the statement")
    description: str = Field(..., description="Row description")
    amount: Decimal = Field(..., description="Amount as printed")
    currency: Optional[str] = Field(None, description="ISO currency of the amount")
    reason: str = Field(..., description="Why the row is not imported")


class Fill(BaseModel):
    """An executed trade price, used to identify the listing it was traded on."""

    date: str = Field(..., description="Trade date in YYYY-MM-DD format")
    price: Decimal = Field(..., description="Price per share before fees and taxes")


class ParsedInstrument(BaseModel):
    """One security (by ISIN) in a statement."""

    isin: str = Field(..., description="ISIN")
    name: str = Field(..., description="Name as printed in the statement")
    transaction_count: int = Field(..., description="Importable rows for this ISIN")
    fills: List[Fill] = Field(default_factory=list, description="Buy/sell prices")


class ParsingMetadata(BaseModel):
    """Metadata about the parsing process."""

    total_transactions: int = Field(
        ..., description="Total number of transactions parsed"
    )
    total_skipped: int = Field(default=0, description="Rows read but not imported")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")


class ParsedData(BaseModel):
    """Parsed data from account statement."""

    provider: str = Field(..., description="Provider that generated the statement")
    statement_period: StatementPeriod = Field(..., description="Statement period")
    transactions: List[ParsedTransaction] = Field(
        ..., description="Parsed transactions"
    )
    skipped: List[SkippedRow] = Field(
        default_factory=list, description="Rows read but not imported"
    )
    instruments: List[ParsedInstrument] = Field(
        default_factory=list, description="Securities to map to assets, by ISIN"
    )
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
    asset_id: Optional[int] = Field(
        None, description="Existing asset; otherwise `symbol` is looked up or created"
    )
    symbol: Optional[str] = Field(
        None, description="Yahoo ticker when asset_id is unset"
    )
    isin: Optional[str] = Field(None, description="ISIN, remembered on the asset")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    quantity: Decimal = Field(..., description="Transaction quantity")
    price: Decimal = Field(..., description="Price per share")
    total_amount: Decimal = Field(..., description="Total transaction amount")
    fees: Decimal = Field(default=Decimal("0"), description="Transaction fees")
    taxes: Decimal = Field(default=Decimal("0"), description="Taxes withheld")
    currency: Optional[str] = Field(
        None, description="ISO currency; defaults to the portfolio currency"
    )
    notes: Optional[str] = Field(None, description="Transaction notes")
    source_key: Optional[str] = Field(
        None,
        max_length=64,
        description="Statement row id from /parse; a row already in the portfolio is skipped",
    )

    @model_validator(mode="after")
    def _numbers(self):
        check_transaction_numbers(self.transaction_type, self.quantity, self.price)
        return self


class BulkTransactionCreate(BaseModel):
    """Request for bulk transaction creation."""

    portfolio_id: int = Field(..., description="Target portfolio ID")
    transactions: List[BulkTransactionItem] = Field(
        ..., description="Transactions to create"
    )


class CreatedTransaction(BaseModel):
    """Created transaction response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Transaction ID")
    transaction_date: datetime = Field(..., description="Transaction date")
    asset_id: int = Field(..., description="Asset ID")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    quantity: Decimal = Field(..., description="Transaction quantity")
    price: Decimal = Field(..., description="Price per share")
    fees: Decimal = Field(..., description="Transaction fees")
    taxes: Decimal = Field(..., description="Taxes withheld")
    total_amount: Decimal = Field(..., description="Total transaction amount")
    currency: str = Field(..., description="ISO currency")
    portfolio_id: int = Field(..., description="Portfolio ID")
    notes: Optional[str] = Field(None, description="Transaction notes")
    created_at: datetime = Field(..., description="Creation timestamp")


class BulkCreateSummary(BaseModel):
    """Summary of bulk transaction creation."""

    total_created: int = Field(..., description="Number of transactions created")
    total_failed: int = Field(..., description="Number of transactions that failed")
    total_skipped: int = Field(
        default=0, description="Rows skipped because they were already imported"
    )
    errors: List[str] = Field(default_factory=list, description="Error messages")


class BulkCreateResponse(BaseModel):
    """Response for bulk transaction creation."""

    created_transactions: List[CreatedTransaction] = Field(
        ..., description="Successfully created transactions"
    )
    summary: BulkCreateSummary = Field(..., description="Creation summary")


class ImportedCheckRow(BaseModel):
    """A parsed row to look up in a portfolio."""

    source_key: str = Field(..., max_length=64)
    transaction_date: str = Field(..., description="Date in YYYY-MM-DD format")
    transaction_type: TransactionType
    isin: Optional[str] = None
    quantity: Decimal
    total_amount: Decimal


class ImportedCheckRequest(BaseModel):
    portfolio_id: int
    transactions: List[ImportedCheckRow]


class ImportedCheckResponse(BaseModel):
    imported_keys: List[str] = Field(
        ..., description="source_keys of the rows already in the portfolio"
    )


class ResolveInstrumentsRequest(BaseModel):
    """Securities to match to Yahoo listings."""

    instruments: List[ParsedInstrument] = Field(..., min_length=1, max_length=10)


class ListingCandidate(BaseModel):
    """A Yahoo listing and how well it contains the statement's fills."""

    symbol: str
    exchange: Optional[str] = None
    currency: Optional[str] = None
    match_percent: Optional[float] = Field(
        None, description="Share of checked fills inside that day's low-high range"
    )
    fills_checked: int = 0


class InstrumentResolution(BaseModel):
    """Suggested listing for one ISIN."""

    isin: str
    status: str = Field(
        ...,
        description="existing | matched (≥90% in the account currency) | uncertain (≥50%) | unmatched",
    )
    suggested_symbol: Optional[str] = None
    asset_id: Optional[int] = Field(None, description="Your asset already mapped to it")
    candidates: List[ListingCandidate] = Field(default_factory=list)


class ResolveInstrumentsResponse(BaseModel):
    results: List[InstrumentResolution]
