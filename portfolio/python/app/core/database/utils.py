"""
Database utility functions for common operations.
"""

import logging
from datetime import timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    User,
    UserSession,
)

logger = logging.getLogger(__name__)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_portfolios(db: Session, user_id: int) -> List[Portfolio]:
    """Get all portfolios for a user."""
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).all()


def get_portfolio_assets(db: Session, portfolio_id: int) -> List[PortfolioAsset]:
    """Get all assets in a portfolio."""
    return (
        db.query(PortfolioAsset)
        .filter(PortfolioAsset.portfolio_id == portfolio_id)
        .all()
    )


def get_asset_by_symbol(db: Session, symbol: str) -> Optional[Asset]:
    """Get asset by symbol."""
    return db.query(Asset).filter(Asset.symbol == symbol).first()


def get_portfolio_transactions(
    db: Session, portfolio_id: int, limit: int = 100
) -> List[Transaction]:
    """Get recent transactions for a portfolio."""
    return (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.desc())
        .limit(limit)
        .all()
    )


def calculate_portfolio_value(db: Session, portfolio_id: int) -> Dict[str, float]:
    """Calculate current portfolio value and performance metrics."""
    try:
        # Get portfolio assets with current values
        assets = (
            db.query(PortfolioAsset)
            .filter(PortfolioAsset.portfolio_id == portfolio_id)
            .all()
        )

        total_cost_basis = 0.0
        total_current_value = 0.0
        total_unrealized_pnl = 0.0

        for asset in assets:
            total_cost_basis += float(asset.cost_basis_total)
            if asset.current_value is not None:
                total_current_value += float(asset.current_value)
                total_unrealized_pnl += float(asset.unrealized_pnl or 0.0)

        # Calculate percentages
        total_return_percent = 0.0
        if total_cost_basis > 0:
            total_return_percent = (total_unrealized_pnl / total_cost_basis) * 100

        return {
            "total_cost_basis": total_cost_basis,
            "total_current_value": total_current_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_return_percent": total_return_percent,
            "asset_count": len(assets),
        }

    except Exception as e:
        logger.error(f"Error calculating portfolio value: {e}")
        return {
            "total_cost_basis": 0.0,
            "total_current_value": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_return_percent": 0.0,
            "asset_count": 0,
        }


def get_portfolio_performance_summary(
    db: Session, portfolio_id: int, days: int = 30
) -> Dict[str, Any]:
    """Get portfolio performance summary for a specific time period."""
    try:
        # Get portfolio transactions within the time period
        from datetime import datetime, timedelta

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .all()
        )

        # Calculate metrics
        total_buys = sum(1 for t in transactions if t.is_buy)
        total_sells = sum(1 for t in transactions if t.is_sell)
        total_volume = sum(float(t.total_amount) for t in transactions)

        # Get current portfolio value
        portfolio_value = calculate_portfolio_value(db, portfolio_id)

        return {
            "period_days": days,
            "start_date": start_date,
            "end_date": end_date,
            "total_transactions": len(transactions),
            "buy_transactions": total_buys,
            "sell_transactions": total_sells,
            "total_volume": total_volume,
            "current_portfolio_value": portfolio_value["total_current_value"],
            "total_return": portfolio_value["total_unrealized_pnl"],
            "total_return_percent": portfolio_value["total_return_percent"],
        }

    except Exception as e:
        logger.error(f"Error getting portfolio performance summary: {e}")
        return {}


def cleanup_expired_sessions(db: Session) -> int:
    """Clean up expired user sessions."""
    try:
        from datetime import datetime

        expired_sessions = (
            db.query(UserSession)
            .filter(UserSession.expires_at < datetime.now(timezone.utc))
            .all()
        )

        count = len(expired_sessions)
        for session in expired_sessions:
            db.delete(session)

        db.commit()
        logger.info(f"Cleaned up {count} expired sessions")
        return count

    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")
        db.rollback()
        return 0


def get_database_stats(db: Session) -> Dict[str, Any]:
    """Get database statistics."""
    try:
        stats = {}

        # Count records in each table
        stats["users"] = db.query(User).count()
        stats["portfolios"] = db.query(Portfolio).count()
        stats["assets"] = db.query(Asset).count()
        stats["transactions"] = db.query(Transaction).count()
        stats["portfolio_assets"] = db.query(PortfolioAsset).count()

        # Get active sessions
        from datetime import datetime

        stats["active_sessions"] = (
            db.query(UserSession)
            .filter(
                UserSession.expires_at > datetime.now(timezone.utc),
                UserSession.is_active == True,
            )
            .count()
        )

        return stats

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {}


def validate_database_integrity(db: Session) -> Dict[str, Any]:
    """Validate database integrity and relationships."""
    try:
        issues = []

        # Check for orphaned portfolio assets
        orphaned_assets = (
            db.query(PortfolioAsset)
            .outerjoin(Portfolio, PortfolioAsset.portfolio_id == Portfolio.id)
            .filter(Portfolio.id.is_(None))
            .all()
        )

        if orphaned_assets:
            issues.append(f"Found {len(orphaned_assets)} orphaned portfolio assets")

        # Check for orphaned transactions
        orphaned_transactions = (
            db.query(Transaction)
            .outerjoin(Portfolio, Transaction.portfolio_id == Portfolio.id)
            .filter(Portfolio.id.is_(None))
            .all()
        )

        if orphaned_transactions:
            issues.append(f"Found {len(orphaned_transactions)} orphaned transactions")

        # Check for duplicate portfolio assets
        duplicate_assets = (
            db.query(
                PortfolioAsset.portfolio_id,
                PortfolioAsset.asset_id,
                func.count(PortfolioAsset.id),
            )
            .group_by(PortfolioAsset.portfolio_id, PortfolioAsset.asset_id)
            .having(func.count(PortfolioAsset.id) > 1)
            .all()
        )

        if duplicate_assets:
            issues.append(f"Found {len(duplicate_assets)} duplicate portfolio assets")

        return {"valid": len(issues) == 0, "issues": issues, "issue_count": len(issues)}

    except Exception as e:
        logger.error(f"Error validating database integrity: {e}")
        return {"valid": False, "issues": [f"Validation error: {e}"], "issue_count": 1}
