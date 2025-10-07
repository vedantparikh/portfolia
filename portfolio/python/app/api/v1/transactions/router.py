"""
Transactions management router with authentication.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from core.auth.dependencies import (
    get_current_active_user,
    get_current_verified_user,
)
from core.database.connection import get_db
from core.database.models import Portfolio, PortfolioAsset, TransactionType, User
from core.database.models import Transaction as TransactionModel
from core.schemas.portfolio import Transaction as TransactionSchema
from core.schemas.portfolio import TransactionCreate, TransactionUpdate
from core.schemas.portfolio_performance import TransactionSummaryResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Create a new portfolio transaction."""
    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == transaction_data.portfolio_id,
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

    # Create transaction
    new_transaction = TransactionModel(
        portfolio_id=transaction_data.portfolio_id,
        asset_id=transaction_data.asset_id,
        transaction_type=transaction_data.transaction_type,
        quantity=transaction_data.quantity,
        price=transaction_data.price,
        transaction_date=transaction_data.transaction_date or datetime.now(timezone.utc),
        fees=transaction_data.fees or 0,
        total_amount=transaction_data.total_amount,
    )

    db.add(new_transaction)
    db.flush()  # Get the transaction ID

    # Update portfolio asset holdings
    portfolio_asset = (
        db.query(PortfolioAsset)
        .filter(
            PortfolioAsset.portfolio_id == transaction_data.portfolio_id,
            PortfolioAsset.asset_id == transaction_data.asset_id,
        )
        .first()
    )

    if transaction_data.transaction_type == TransactionType.BUY:
        if portfolio_asset:
            # Update existing holding
            total_quantity = portfolio_asset.quantity + transaction_data.quantity
            total_cost = portfolio_asset.cost_basis_total + (
                transaction_data.quantity * transaction_data.price
            )
            portfolio_asset.quantity = total_quantity
            portfolio_asset.cost_basis_total = total_cost
            portfolio_asset.cost_basis = total_cost / total_quantity
        else:
            # Create new holding
            portfolio_asset = PortfolioAsset(
                portfolio_id=transaction_data.portfolio_id,
                asset_id=transaction_data.asset_id,
                quantity=transaction_data.quantity,
                cost_basis=transaction_data.price,
                cost_basis_total=transaction_data.quantity * transaction_data.price,
            )
            db.add(portfolio_asset)

    elif transaction_data.transaction_type == TransactionType.SELL:
        if not portfolio_asset or portfolio_asset.quantity < transaction_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient shares to sell",
            )

        # Update holding
        remaining_quantity = portfolio_asset.quantity - transaction_data.quantity
        if remaining_quantity > 0:
            portfolio_asset.quantity = remaining_quantity
            portfolio_asset.cost_basis_total = (
                portfolio_asset.cost_basis * remaining_quantity
            )
        else:
            # Remove holding if all shares sold
            db.delete(portfolio_asset)

    elif transaction_data.transaction_type == TransactionType.DIVIDEND:
        # Dividends don't affect quantity, just record the transaction
        pass

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid transaction type"
        )

    db.commit()
    db.refresh(new_transaction)

    return new_transaction


@router.get("/", response_model=List[TransactionSchema])
async def get_user_transactions(
    portfolio_id: Optional[int] = Query(None, description="Filter by portfolio ID"),
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    transaction_type: Optional[str] = Query(
        None, description="Filter by transaction type"
    ),
    start_date: Optional[str] = Query(
        None, description="Filter by start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="Filter by end date (YYYY-MM-DD)"
    ),
    skip: int = Query(0, ge=0, description="Number of transactions to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of transactions to return"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user's transactions with optional filtering."""
    # Start with user's portfolios
    user_portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == current_user.id, Portfolio.is_active == True)
        .all()
    )

    portfolio_ids = [p.id for p in user_portfolios]

    if not portfolio_ids:
        return []

    # Build query
    query = (
        db.query(TransactionModel)
        .options(
            joinedload(TransactionModel.portfolio),  # Eagerly load the portfolio
            joinedload(TransactionModel.asset),      # Eagerly load the asset
        )
        .filter(TransactionModel.portfolio_id.in_(portfolio_ids))
    )

    if portfolio_id:
        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this portfolio",
            )
        query = query.filter(TransactionModel.portfolio_id == portfolio_id)

    if asset_id:
        query = query.filter(TransactionModel.asset_id == asset_id)

    if transaction_type:
        query = query.filter(TransactionModel.transaction_type == transaction_type)

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

    # Order by date (newest first)
    query = query.order_by(TransactionModel.transaction_date.desc())

    transactions = query.offset(skip).limit(limit).all()

    return transactions


@router.get("/{transaction_id}", response_model=TransactionSchema)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific transaction by ID (user must own the portfolio)."""
    transaction = (
        db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == transaction.portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this transaction",
        )

    return transaction


@router.put("/{transaction_id}", response_model=TransactionSchema)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Update a transaction (user must own the portfolio)."""
    transaction = (
        db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == transaction.portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this transaction",
        )

    # Update only provided fields
    update_data = transaction_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)

    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction (user must own the portfolio)."""
    transaction = (
        db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    # Verify portfolio ownership
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == transaction.portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True,
        )
        .first()
    )

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this transaction",
        )

    # Note: Deleting transactions can affect portfolio calculations
    # In production, you might want to implement a more sophisticated approach
    db.delete(transaction)
    db.commit()

    return None


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
