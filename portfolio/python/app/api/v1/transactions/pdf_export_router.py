"""
Transaction PDF Export Router
API endpoints for exporting transaction PDFs.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_active_user
from core.database.connection import get_db
from core.database.models import User
from core.errors import public_message
from core.schemas.pdf_export import PDFExportResponse, TransactionExportRequest
from core.services.transaction_pdf_export_service import TransactionPDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions/pdf", tags=["transaction-pdf"])


@router.post("/export", response_model=PDFExportResponse)
async def export_transactions_pdf(
    export_request: TransactionExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PDFExportResponse:
    """
    Export transactions to PDF with filtering and options.

    This endpoint generates a comprehensive PDF report of transactions
    with customizable filters and formatting options.
    """
    try:
        pdf_service = TransactionPDFService(db)

        pdf_bytes, response_data = await pdf_service.export_transactions_to_pdf(
            user=current_user,
            filters=export_request.filters,
            options=export_request.options,
            custom_filename=export_request.custom_filename,
        )

        # Return the response data (PDF bytes are handled separately)
        return response_data

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_message(e, "The PDF could not be created"),
        ) from e


@router.post("/export/download")
async def download_transactions_pdf(
    export_request: TransactionExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """
    Export and download transactions PDF directly.

    This endpoint generates and returns the PDF file directly for download.
    """
    try:
        pdf_service = TransactionPDFService(db)

        pdf_bytes, response_data = await pdf_service.export_transactions_to_pdf(
            user=current_user,
            filters=export_request.filters,
            options=export_request.options,
            custom_filename=export_request.custom_filename,
        )

        # Return PDF as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={response_data.filename}",
                "Content-Length": str(len(pdf_bytes)),
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=public_message(e, "The PDF could not be created"),
        ) from e


@router.post("/export/preview", response_model=dict)
async def preview_export(
    export_request: TransactionExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Preview the export without generating the PDF.

    This endpoint returns information about what would be included
    in the PDF export based on the provided filters.
    """
    pdf_service = TransactionPDFService(db)

    # Get filtered transactions for preview
    transactions = await pdf_service._get_filtered_transactions(
        user=current_user, filters=export_request.filters
    )
    transactions = await pdf_service._convert_to_portfolio_currency(transactions)

    summary_stats = pdf_service._calculate_summary_stats(
        transactions, export_request.filters
    )

    # Generate filename
    filename = pdf_service._generate_filename(
        user=current_user,
        filters=export_request.filters,
        custom_filename=export_request.custom_filename,
    )

    return {
        "filename": filename,
        "transaction_count": len(transactions),
        "summary_stats": summary_stats.dict(),
        "estimated_pages": max(
            1,
            len(transactions) // 25
            + (2 if export_request.options.include_summary else 1),
        ),
        "filters_applied": {
            "portfolio_ids": export_request.filters.portfolio_ids,
            "date_range": {
                "start": export_request.filters.start_date,
                "end": export_request.filters.end_date,
            },
            "transaction_types": export_request.filters.transaction_types,
            "asset_symbols": export_request.filters.asset_symbols,
        },
        "options": export_request.options.dict(),
    }
