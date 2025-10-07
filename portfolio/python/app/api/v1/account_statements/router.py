"""
Account statement parsing and bulk transaction creation router.
"""

import base64
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session

from core.auth.dependencies import get_current_verified_user
from core.database.connection import get_db
from core.database.models import User
from core.schemas.account_statements import (
    BulkCreateResponse,
    BulkTransactionCreate,
    ParseResponse,
    ProvidersResponse,
)
from core.services.account_statement_service import AccountStatementService

router = APIRouter(prefix="/account-statements", tags=["account-statements"])


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ProvidersResponse:
    """Get list of supported account statement providers."""
    service = AccountStatementService(db)
    providers = service.get_supported_providers()
    return ProvidersResponse(providers=providers)


@router.post("/parse", response_model=ParseResponse)
async def parse_statement(
    # This is the standard way to handle file uploads and fixes the previous error.
    provider_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ParseResponse:
    """Parse PDF account statement and extract transaction data."""
    service = AccountStatementService(db)

    try:
        # Read the file content as bytes from the upload
        file_bytes = await file.read()

        # The service layer expects a base64 encoded string, so we encode the bytes.
        file_content_b64 = base64.b64encode(file_bytes).decode('utf-8')

        parsed_data = service.parse_statement(
            provider_id=provider_id,
            file_content=file_content_b64,
            filename=file.filename
        )
        return ParseResponse(parsed_data=parsed_data)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while parsing the statement: {str(e)}"
        ) from e


@router.post("/transactions/bulk-create", response_model=BulkCreateResponse)
async def bulk_create_transactions(
    request: BulkTransactionCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> BulkCreateResponse:
    """Create multiple transactions from parsed data."""
    service = AccountStatementService(db)

    try:
        created_transactions, summary = await service.create_bulk_transactions(
            portfolio_id=request.portfolio_id,
            transactions_data=request.transactions,
            user_id=current_user.id
        )

        return BulkCreateResponse(
            created_transactions=created_transactions,
            summary=summary
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while creating transactions: {str(e)}"
        ) from e