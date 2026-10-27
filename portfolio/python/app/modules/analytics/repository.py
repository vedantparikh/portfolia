"""Analytics rows. Does not commit; the request session does."""

from datetime import datetime

from sqlalchemy.orm import Session

from core.database.models import Asset, Portfolio
from core.database.models.portfolio_analytics import (
    PortfolioAllocation,
    PortfolioBenchmark,
    PortfolioPerformanceHistory,
    RebalancingEvent,
)


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_snapshot(
        self, portfolio_id: int, snapshot_id: int
    ) -> PortfolioPerformanceHistory | None:
        return (
            self.db.query(PortfolioPerformanceHistory)
            .filter(
                PortfolioPerformanceHistory.id == snapshot_id,
                PortfolioPerformanceHistory.portfolio_id == portfolio_id,
            )
            .first()
        )

    def delete(self, row) -> None:
        self.db.delete(row)
        self.db.flush()

    def active_allocations(self, portfolio_id: int) -> list[PortfolioAllocation]:
        return (
            self.db.query(PortfolioAllocation)
            .filter(
                PortfolioAllocation.portfolio_id == portfolio_id,
                PortfolioAllocation.is_active,
            )
            .all()
        )

    def get_allocation(
        self, portfolio_id: int, allocation_id: int
    ) -> PortfolioAllocation | None:
        return (
            self.db.query(PortfolioAllocation)
            .filter(
                PortfolioAllocation.id == allocation_id,
                PortfolioAllocation.portfolio_id == portfolio_id,
            )
            .first()
        )

    def save(self, row):
        self.db.flush()
        self.db.refresh(row)
        return row

    def clear_primary_benchmarks(self, portfolio_id: int) -> None:
        self.db.query(PortfolioBenchmark).filter(
            PortfolioBenchmark.portfolio_id == portfolio_id
        ).update({"is_primary": False})

    def add(self, row):
        self.db.add(row)
        self.db.flush()
        self.db.refresh(row)
        return row

    def active_benchmarks(self, portfolio_id: int) -> list[PortfolioBenchmark]:
        return (
            self.db.query(PortfolioBenchmark)
            .filter(
                PortfolioBenchmark.portfolio_id == portfolio_id,
                PortfolioBenchmark.is_active,
            )
            .all()
        )

    def rebalancing_events(
        self, portfolio_id: int, start: datetime
    ) -> list[RebalancingEvent]:
        return (
            self.db.query(RebalancingEvent)
            .filter(
                RebalancingEvent.portfolio_id == portfolio_id,
                RebalancingEvent.event_date >= start,
            )
            .order_by(RebalancingEvent.event_date.desc())
            .all()
        )

    def performance_history(
        self, portfolio_id: int, start: datetime
    ) -> list[PortfolioPerformanceHistory]:
        return (
            self.db.query(PortfolioPerformanceHistory)
            .filter(
                PortfolioPerformanceHistory.portfolio_id == portfolio_id,
                PortfolioPerformanceHistory.snapshot_date >= start,
            )
            .order_by(PortfolioPerformanceHistory.snapshot_date)
            .all()
        )

    def active_assets(self, user_id: int) -> list[Asset]:
        return (
            self.db.query(Asset)
            .filter(Asset.user_id == user_id, Asset.is_active.is_(True))
            .all()
        )

    def active_portfolios(self, user_id: int) -> list[Portfolio]:
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.user_id == user_id, Portfolio.is_active.is_(True))
            .all()
        )
