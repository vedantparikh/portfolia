"""
Transactions management router with authentication.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth.dependencies import (
    get_current_active_user,
    get_current_verified_user,
)
from core.database.connection import get_db
from core.database.models import Portfolio, User
from core.database.models import Transaction as TransactionModel
from core.schemas.portfolio import Transaction as TransactionSchema
from core.schemas.portfolio import TransactionCreate, TransactionUpdate
from core.schemas.portfolio_performance import TransactionSummaryResponse
from core.services import PortfolioService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "/", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED
)
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
async def get_user_transactions(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        portfolio_id: Optional[int] = Query(None, description="Filter by a specific portfolio ID"),
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
            portfolio_id=portfolio_id, user_id=current_user.id, limit=limit, offset=offset
        )
    else:
        # Case 2: No portfolio specified, get all transactions for the user
        transactions = portfolio_service.get_all_user_transactions(
            user_id=current_user.id, limit=limit, offset=offset
        )

    return transactions


@router.get("/{transaction_id}", response_model=TransactionSchema)
async def get_transaction(
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


@router.get("/{portfolio_id}/summary", response_model=TransactionSummaryResponse)
async def get_transactions_summary(
        portfolio_id: int,
        start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
):
    """Get transaction summary for a portfolio."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied",
        )

    # Build query
    query = db.query(TransactionModel).filter(
        TransactionModel.portfolio_id == portfolio_id
    )

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(TransactionModel.transaction_date >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD",
            )

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(TransactionModel.transaction_date <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD",
            )

    transactions = query.all()

    # Calculate summary
    total_buy_value = sum(
        float(t.quantity * t.price) for t in transactions if t.transaction_type == "buy"
    )
    total_sell_value = sum(
        float(t.quantity * t.price)
        for t in transactions
        if t.transaction_type == "sell"
    )
    total_dividends = sum(
        float(t.quantity * t.price)
        for t in transactions
        if t.transaction_type == "dividend"
    )
    total_fees = sum(float(t.fees or 0) for t in transactions)

    return TransactionSummaryResponse(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio.name,
        total_transactions=len(transactions),
        total_buy_value=round(total_buy_value, 2),
        total_sell_value=round(total_sell_value, 2),
        total_dividends=round(total_dividends, 2),
        total_fees=round(total_fees, 2),
        net_investment=round(total_buy_value - total_sell_value, 2),
        period={"start_date": start_date, "end_date": end_date},
    )
