"""
Transactions management router with authentication.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import (
    get_current_active_user,
    get_current_verified_user,
)
from core.database.connection import get_db
from core.database.models import User
from core.schemas.portfolio import Transaction as TransactionSchema
from core.schemas.portfolio import TransactionCreate, TransactionUpdate
from core.services import PortfolioService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """
    Create a new transaction. The service layer handles all logic,
    including asset state recalculation.
    """
    portfolio_service = PortfolioService(db=db)

    new_transaction = await portfolio_service.add_transaction(
        portfolio_id=transaction_data.portfolio_id,
        transaction_data=transaction_data,
        user_id=current_user.id,
    )

    if not new_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or you do not have permission to access it.",
        )
    return new_transaction


@router.get("/", response_model=List[TransactionSchema])
def get_user_transactions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    portfolio_id: Optional[int] = Query(
        None, description="Filter by a specific portfolio ID"
    ),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
):
    """
    Get transactions for the current user.
    Can be filtered by a specific portfolio_id.
    """
    portfolio_service = PortfolioService(db=db)

    if portfolio_id is not None:
        # Case 1: A specific portfolio is requested
        transactions = portfolio_service.get_portfolio_transactions(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
    else:
        # Case 2: No portfolio specified, get all transactions for the user
        transactions = portfolio_service.get_all_user_transactions(
            user_id=current_user.id, limit=limit, offset=offset
        )

    return transactions


@router.get("/{transaction_id}", response_model=TransactionSchema)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific transaction by ID."""
    portfolio_service = PortfolioService(db=db)

    transaction = portfolio_service.get_transaction(
        transaction_id=transaction_id, user_id=current_user.id
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or access denied.",
        )
    return transaction


@router.put("/{transaction_id}", response_model=TransactionSchema)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Update a transaction. The service layer handles recalculation."""
    portfolio_service = PortfolioService(db=db)

    updated_transaction = await portfolio_service.update_transaction(
        transaction_id=transaction_id,
        transaction_data=transaction_update,
        user_id=current_user.id,
    )

    if not updated_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or access denied.",
        )
    return updated_transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction. The service layer handles recalculation."""
    portfolio_service = PortfolioService(db=db)

    success = await portfolio_service.delete_transaction(
        transaction_id=transaction_id, user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or access denied.",
        )
    return None  # FastAPI returns 204 No Content
