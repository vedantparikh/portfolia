"""
PDF Export Service for generating transaction reports.
"""

import io
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.doctemplate import SimpleDocTemplate
from sqlalchemy.orm import Session, joinedload

from core.database.models import Asset, Portfolio, Transaction, User
from core.database.models.transaction import TransactionType
from core.domain.fx import MissingFxError, canonical_currency, convert_amount
from core.errors import DomainError
from core.schemas.pdf_export import (
    CurrencyVolume,
    ExportedTransactionData,
    PDFExportOptions,
    PDFExportResponse,
    TransactionExportFilters,
    TransactionSummaryStats,
)
from core.services.fx import load_rates
from core.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)


def format_money(amount: Decimal, currency: str) -> str:
    """Amount with its currency code. There is no default currency."""
    code = canonical_currency(currency)[0] if currency else ""
    return f"{code} {amount:,.2f}".strip()


class TransactionPDFService:
    """Service for generating transaction PDF reports."""

    def __init__(self, db: Session):
        self.db = db
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Setup custom styles for PDF generation."""
        # Header style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Title"],
                fontSize=20,
                spaceAfter=30,
                alignment=1,  # Center alignment
                textColor=colors.HexColor("#2c3e50"),
            )
        )

        # Subtitle style
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Normal"],
                fontSize=14,
                spaceAfter=20,
                alignment=1,
                textColor=colors.HexColor("#34495e"),
            )
        )

        # Section header style
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor("#2980b9"),
                borderWidth=1,
                borderColor=colors.HexColor("#2980b9"),
                borderPadding=5,
            )
        )

    async def export_transactions_to_pdf(
        self,
        user: User,
        filters: TransactionExportFilters,
        options: PDFExportOptions,
        custom_filename: Optional[str] = None,
    ) -> Tuple[bytes, PDFExportResponse]:
        """
        Export transactions to PDF with filtering and options.

        Args:
            user: Current user
            filters: Export filters
            options: Export options
            custom_filename: Custom filename (optional)

        Returns:
            Tuple of (PDF bytes, response data)
        """
        try:
            transactions = await self._get_filtered_transactions(user, filters)
            transactions = await self._convert_to_portfolio_currency(transactions)

            if not transactions:
                raise DomainError("No transactions found with the specified filters")

            summary_stats = self._calculate_summary_stats(transactions, filters)

            # Generate filename
            filename = self._generate_filename(user, filters, custom_filename)

            # Create PDF
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )

            # Build PDF content
            story = []

            # Add header
            story.extend(self._build_header(user, filters, summary_stats))

            # Add summary if requested
            if options.include_summary:
                story.extend(self._build_summary_section(summary_stats))
                story.append(PageBreak())

            # Add transactions table
            story.extend(self._build_transactions_table(transactions, options))

            # Add footer
            story.extend(self._build_footer())

            # Build PDF
            doc.build(story)
            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()

            # Create response
            export_id = str(uuid.uuid4())
            response = PDFExportResponse(
                filename=filename,
                file_size=len(pdf_bytes),
                transaction_count=len(transactions),
                summary_stats=summary_stats,
                generated_at=datetime.now(timezone.utc),
                export_id=export_id,
            )

            return pdf_bytes, response

        except Exception as e:
            logger.error("Error generating PDF export: %s", str(e))
            raise

    async def _get_filtered_transactions(
        self, user: User, filters: TransactionExportFilters
    ) -> List[ExportedTransactionData]:
        """Get transactions based on filters."""
        query = (
            self.db.query(Transaction)
            .options(
                joinedload(Transaction.portfolio),
                joinedload(Transaction.asset),
            )
            .join(Portfolio)
            .filter(Portfolio.user_id == user.id)
        )

        # Apply filters
        if filters.portfolio_ids:
            query = query.filter(Transaction.portfolio_id.in_(filters.portfolio_ids))

        if filters.start_date:
            query = query.filter(Transaction.transaction_date >= filters.start_date)

        if filters.end_date:
            query = query.filter(Transaction.transaction_date <= filters.end_date)

        if filters.transaction_types:
            query = query.filter(
                Transaction.transaction_type.in_(filters.transaction_types)
            )

        if filters.asset_symbols:
            query = query.join(Asset).filter(Asset.symbol.in_(filters.asset_symbols))

        if filters.min_amount:
            query = query.filter(Transaction.total_amount >= filters.min_amount)

        if filters.max_amount:
            query = query.filter(Transaction.total_amount <= filters.max_amount)

        # Execute query
        transactions = query.all()

        # Convert to export format
        exported_data = []
        for txn in transactions:
            exported_data.append(
                ExportedTransactionData(
                    id=txn.id,
                    portfolio_name=txn.portfolio.name,
                    asset_symbol=txn.asset.symbol,
                    asset_name=txn.asset.name,
                    transaction_type=txn.transaction_type,
                    quantity=txn.quantity,
                    price=txn.price,
                    total_amount=txn.total_amount,
                    fees=txn.fees,
                    taxes=txn.taxes,
                    transaction_date=txn.transaction_date,
                    settlement_date=txn.settlement_date,
                    notes=txn.notes,
                    reference_number=txn.reference_number,
                    currency=txn.currency,
                    portfolio_currency=txn.portfolio.currency,
                )
            )

        return exported_data

    async def _convert_to_portfolio_currency(
        self, rows: List[ExportedTransactionData]
    ) -> List[ExportedTransactionData]:
        """Convert each row into its portfolio currency. A missing rate stays in its own currency."""
        grouped: dict[str, list[ExportedTransactionData]] = defaultdict(list)
        for row in rows:
            grouped[row.portfolio_currency or row.currency].append(row)
        converted: list[ExportedTransactionData] = []
        for target, group in grouped.items():
            rates = await load_rates(
                market_data_service,
                target,
                [row.currency for row in group],
                strict=False,
            )
            for row in group:
                day = row.transaction_date.date()
                try:
                    converted.append(
                        row.model_copy(
                            update={
                                "price": convert_amount(
                                    row.price, row.currency, target, day, rates
                                ),
                                "total_amount": convert_amount(
                                    row.total_amount, row.currency, target, day, rates
                                ),
                                "fees": convert_amount(
                                    row.fees, row.currency, target, day, rates
                                ),
                                "taxes": convert_amount(
                                    row.taxes, row.currency, target, day, rates
                                ),
                                "currency": canonical_currency(target)[0],
                            }
                        )
                    )
                except MissingFxError:
                    logger.warning(
                        "Leaving %s in %s; no rate into %s on %s",
                        row.asset_symbol,
                        row.currency,
                        target,
                        day,
                    )
                    converted.append(
                        row.model_copy(
                            update={"currency": canonical_currency(row.currency)[0]}
                        )
                    )
        return converted

    def _calculate_summary_stats(
        self,
        transactions: List[ExportedTransactionData],
        filters: Optional[TransactionExportFilters] = None,
    ) -> TransactionSummaryStats:
        """Totals per currency. A single currency also fills the flat total fields."""
        buckets: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {
                "buy": Decimal("0"),
                "sell": Decimal("0"),
                "fees": Decimal("0"),
                "taxes": Decimal("0"),
            }
        )
        for txn in transactions:
            code = canonical_currency(txn.currency)[0]
            bucket = buckets[code]
            if txn.transaction_type == TransactionType.BUY:
                bucket["buy"] += txn.total_amount
            elif txn.transaction_type == TransactionType.SELL:
                bucket["sell"] += txn.total_amount
            bucket["fees"] += txn.fees
            bucket["taxes"] += txn.taxes
        volumes = [
            CurrencyVolume(
                currency=code,
                buy_volume=bucket["buy"],
                sell_volume=bucket["sell"],
                net_flow=bucket["sell"] - bucket["buy"],
                fees=bucket["fees"],
                taxes=bucket["taxes"],
            )
            for code, bucket in sorted(buckets.items())
        ]
        only = volumes[0] if len(volumes) == 1 else None
        unique_assets = len({txn.asset_symbol for txn in transactions})

        # Date range
        if transactions:
            min_date = min(txn.transaction_date for txn in transactions)
            max_date = max(txn.transaction_date for txn in transactions)
            date_range = (
                f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
            )
        else:
            date_range = "No transactions"

        # Portfolios included
        portfolios_included = list(set(txn.portfolio_name for txn in transactions))

        return TransactionSummaryStats(
            total_transactions=len(transactions),
            total_buy_volume=only.buy_volume if only else Decimal("0"),
            total_sell_volume=only.sell_volume if only else Decimal("0"),
            net_flow=only.net_flow if only else Decimal("0"),
            total_fees=only.fees if only else Decimal("0"),
            total_taxes=only.taxes if only else Decimal("0"),
            unique_assets=unique_assets,
            date_range=date_range,
            portfolios_included=portfolios_included,
            currency=only.currency if only else None,
            volumes=volumes,
        )

    def _generate_filename(
        self,
        user: User,
        filters: TransactionExportFilters,
        custom_filename: Optional[str],
    ) -> str:
        """Generate PDF filename."""
        if custom_filename:
            # Sanitize custom filename
            filename = re.sub(r"[^\w\-_\.]", "_", custom_filename)
        else:
            # Generate default filename
            username = re.sub(r"[^\w\-_]", "_", user.username)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            # Add portfolio info if specific portfolios selected
            portfolio_part = ""
            if filters.portfolio_ids and len(filters.portfolio_ids) == 1:
                portfolio = (
                    self.db.query(Portfolio)
                    .filter(Portfolio.id == filters.portfolio_ids[0])
                    .first()
                )
                if portfolio:
                    portfolio_name = re.sub(r"[^\w\-_]", "_", portfolio.name)
                    portfolio_part = f"_{portfolio_name}"
            elif filters.portfolio_ids and len(filters.portfolio_ids) > 1:
                portfolio_part = f"_{len(filters.portfolio_ids)}portfolios"

            filename = f"transactions_{username}{portfolio_part}_{timestamp}"

        return f"{filename}.pdf"

    def _build_header(
        self,
        user: User,
        filters: TransactionExportFilters,
        summary: TransactionSummaryStats,
    ) -> List:
        """Build PDF header section."""
        story = []

        # Title
        title = Paragraph("Transaction Report", self.styles["CustomTitle"])
        story.append(title)
        story.append(Spacer(1, 12))

        # User and generation info
        user_info = f"Generated for: {user.username}"
        if hasattr(user, "profile") and user.profile and user.profile.first_name:
            user_info = f"Generated for: {user.profile.first_name} ({user.username})"

        story.append(Paragraph(user_info, self.styles["CustomSubtitle"]))

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        story.append(
            Paragraph(f"Generated on: {generated_at}", self.styles["CustomSubtitle"])
        )
        story.append(Spacer(1, 20))

        # Filter information
        if (
            filters.portfolio_ids
            or filters.start_date
            or filters.end_date
            or filters.transaction_types
        ):
            story.append(Paragraph("Applied Filters:", self.styles["SectionHeader"]))

            if summary.portfolios_included:
                portfolios_text = ", ".join(summary.portfolios_included)
                story.append(
                    Paragraph(f"Portfolios: {portfolios_text}", self.styles["Normal"])
                )

            if filters.start_date or filters.end_date:
                start = (
                    filters.start_date.strftime("%Y-%m-%d")
                    if filters.start_date
                    else "Beginning"
                )
                end = (
                    filters.end_date.strftime("%Y-%m-%d") if filters.end_date else "End"
                )
                story.append(
                    Paragraph(f"Date Range: {start} to {end}", self.styles["Normal"])
                )

            if filters.transaction_types:
                types_text = ", ".join(
                    [
                        t.value.replace("_", " ").title()
                        for t in filters.transaction_types
                    ]
                )
                story.append(
                    Paragraph(f"Transaction Types: {types_text}", self.styles["Normal"])
                )

            story.append(Spacer(1, 20))

        return story

    def _build_summary_section(self, summary: TransactionSummaryStats) -> List:
        """Build summary statistics section."""
        story = []

        story.append(Paragraph("Summary Statistics", self.styles["SectionHeader"]))
        story.append(Spacer(1, 12))

        # Create summary table
        summary_data = [["Total Transactions", str(summary.total_transactions)]]
        for volume in summary.volumes:
            label = f" ({volume.currency})" if len(summary.volumes) > 1 else ""
            summary_data.extend(
                [
                    [
                        f"Buy volume{label}",
                        format_money(volume.buy_volume, volume.currency),
                    ],
                    [
                        f"Sell volume{label}",
                        format_money(volume.sell_volume, volume.currency),
                    ],
                    [
                        f"Net flow{label}",
                        format_money(volume.net_flow, volume.currency),
                    ],
                    [f"Fees{label}", format_money(volume.fees, volume.currency)],
                    [f"Taxes{label}", format_money(volume.taxes, volume.currency)],
                ]
            )
        summary_data.extend(
            [
                ["Unique Assets", str(summary.unique_assets)],
                ["Date Range", summary.date_range],
            ]
        )

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2.5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.lightgrey],
                    ),
                ]
            )
        )

        story.append(summary_table)
        story.append(Spacer(1, 20))

        return story

    def _build_transactions_table(
        self, transactions: List[ExportedTransactionData], options: PDFExportOptions
    ) -> List:
        """Build transactions table."""
        story = []

        story.append(Paragraph("Transaction Details", self.styles["SectionHeader"]))
        story.append(Spacer(1, 12))

        if not transactions:
            story.append(Paragraph("No transactions found.", self.styles["Normal"]))
            return story

        # Sort transactions
        reverse_sort = options.sort_order.lower() == "desc"
        if options.sort_by == "transaction_date":
            transactions.sort(key=lambda x: x.transaction_date, reverse=reverse_sort)
        elif options.sort_by == "total_amount":
            transactions.sort(key=lambda x: x.total_amount, reverse=reverse_sort)
        elif options.sort_by == "asset_symbol":
            transactions.sort(key=lambda x: x.asset_symbol, reverse=reverse_sort)

        # Table headers
        headers = [
            "Date",
            "Type",
            "Symbol",
            "Asset Name",
            "Quantity",
            "Price",
            "Total Amount",
            "Fees",
        ]

        # Prepare table data
        table_data = [headers]

        for txn in transactions:
            row = [
                txn.transaction_date.strftime("%Y-%m-%d"),
                txn.transaction_type.value.replace("_", " ").title(),
                txn.asset_symbol,
                (
                    txn.asset_name[:20] + "..."
                    if len(txn.asset_name) > 20
                    else txn.asset_name
                ),
                f"{txn.quantity:.4f}",
                format_money(txn.price, txn.currency),
                format_money(txn.total_amount, txn.currency),
                format_money(txn.fees, txn.currency),
            ]
            table_data.append(row)

        # Create table
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    # Header styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980b9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    # Data styling
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.lightgrey],
                    ),
                    # Alignment
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Date
                    ("ALIGN", (1, 1), (1, -1), "LEFT"),  # Type
                    ("ALIGN", (2, 1), (2, -1), "LEFT"),  # Symbol
                    ("ALIGN", (3, 1), (3, -1), "LEFT"),  # Asset name
                    ("ALIGN", (4, 1), (-1, -1), "RIGHT"),  # Numbers
                ]
            )
        )

        story.append(table)
        return story

    def _build_footer(self) -> List:
        """Build PDF footer."""
        story = []
        story.append(Spacer(1, 30))

        footer_text = (
            "This report was generated by Portfolia. "
            "All data is based on your transaction records as of the generation date."
        )
        story.append(Paragraph(footer_text, self.styles["Normal"]))

        return story
