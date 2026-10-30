"""
The next-euro planner: buy-only split of new money, detected savings plans
and the goal projection (maths in core/domain/planner.py).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    PortfolioAllocation,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from core.domain.fx import convert_amount, convert_closes
from core.domain.planner import (
    Purchase,
    buy_only_split,
    detect_savings_plans,
    monthly_returns,
    project_goal,
    with_annual_mean,
)
from core.domain.positions import split_factor
from core.errors import DomainError
from core.services.fx import load_rates
from modules.analytics.calculations import PortfolioCalculationService
from modules.portfolios.service import PortfolioService


def months_until(today: date, target: date) -> int:
    """Whole months from `today` to `target` (a month counts once its day is reached)."""
    months = (target.year - today.year) * 12 + target.month - today.month
    return months - (1 if target.day < today.day else 0)


class PlannerService:
    def __init__(self, db: Session):
        self.db = db
        self.calculations = PortfolioCalculationService(db)

    async def _holdings(self, portfolio: Portfolio) -> List[Any]:
        return [
            h
            for h in await PortfolioService(self.db).get_portfolio_holdings(
                portfolio.id
            )
            if h.quantity > 0
        ]

    def _names(self, asset_ids) -> Dict[int, Asset]:
        return {
            a.id: a for a in self.db.query(Asset).filter(Asset.id.in_(set(asset_ids)))
        }

    async def invest(
        self, portfolio: Portfolio, amount: float, min_amount: float
    ) -> Dict[str, Any]:
        """Where `amount` of new money goes to move toward the targets without selling."""
        holdings = await self._holdings(portfolio)
        priced = {h.asset_id: h for h in holdings if h.current_value is not None}
        targets = {
            t.asset_id: float(t.target_percentage)
            for t in self.db.query(PortfolioAllocation).filter(
                PortfolioAllocation.portfolio_id == portfolio.id,
                PortfolioAllocation.is_active == True,
            )
        }
        unpriced = sorted(
            h.symbol
            for h in holdings
            if h.current_value is None and h.asset_id in targets
        )
        targets = {
            a: t
            for a, t in targets.items()
            if a in priced or a not in {h.asset_id for h in holdings}
        }
        values = {a: float(h.current_value) for a, h in priced.items()}
        mode = "targets" if targets else "current_weights"
        weights = targets or values
        buys = buy_only_split(values, weights, amount, min_amount)
        names = self._names(weights)
        untargeted = sum(v for a, v in values.items() if a not in weights)

        rows = []
        for buy in buys:
            holding = priced.get(buy.asset_id)
            price = (
                holding.current_value / holding.quantity
                if holding and holding.quantity
                else None
            )
            asset = names.get(buy.asset_id)
            rows.append(
                {
                    **vars(buy),
                    "symbol": asset.symbol if asset else str(buy.asset_id),
                    "name": asset.name if asset else None,
                    "price": price,
                    "shares": buy.amount / price if price else None,
                }
            )
        return {
            "portfolio_id": portfolio.id,
            "currency": portfolio.currency,
            "amount": amount,
            "min_amount": min_amount,
            "mode": mode,
            "buys": rows,
            "untargeted_value": untargeted,
            "unpriced": unpriced,
        }

    async def savings_plans(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Recurring purchases, with what their shares are worth at today's price."""
        buys = (
            self.db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio.id,
                Transaction.transaction_type == TransactionType.BUY,
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .order_by(Transaction.transaction_date)
            .all()
        )
        currency = portfolio.currency
        rates = await load_rates(
            self.calculations.market_data_service,
            currency,
            [t.currency for t in buys],
            strict=False,
        )
        purchases = []
        for t in buys:
            day = t.transaction_date.date()
            try:
                amount = convert_amount(
                    t.total_amount, t.currency, currency, day, rates
                )
            except DomainError:
                continue
            purchases.append(
                Purchase(
                    asset_id=t.asset_id,
                    day=day,
                    amount=float(amount),
                    quantity=float(t.quantity),
                    fee_free=not (t.fees or Decimal(0)),
                )
            )
        today = datetime.now(timezone.utc).date()
        plans = detect_savings_plans(purchases, today)
        if not plans:
            return {
                "portfolio_id": portfolio.id,
                "currency": currency,
                "plans": [],
                "monthly_total": 0.0,
            }

        ids = sorted({p.asset_id for p in plans})
        _, splits, _, _ = await self.calculations.get_market_history(ids)
        prices = {
            h.asset_id: h.current_value / h.quantity
            for h in await self._holdings(portfolio)
            if h.current_value is not None and h.quantity
        }
        names = self._names(ids)
        rows = []
        for plan in plans:
            run = [
                p
                for p in purchases
                if p.asset_id == plan.asset_id and plan.first <= p.day <= plan.last
            ]
            shares = (
                sum(
                    p.quantity
                    * float(split_factor(splits.get(plan.asset_id, []), p.day))
                    for p in run
                    if p.fee_free or not any(q.fee_free for q in run)
                )
                if run
                else plan.quantity
            )
            price = prices.get(plan.asset_id)
            asset = names.get(plan.asset_id)
            rows.append(
                {
                    **vars(plan),
                    "symbol": asset.symbol if asset else str(plan.asset_id),
                    "name": asset.name if asset else None,
                    "quantity": shares,
                    "value_now": shares * price if price is not None else None,
                }
            )
        return {
            "portfolio_id": portfolio.id,
            "currency": currency,
            "plans": rows,
            "monthly_total": sum(p.monthly_amount for p in plans if p.active),
        }

    async def goal(
        self,
        portfolio: Portfolio,
        target: float,
        target_date: date,
        monthly: Optional[float],
        annual_return_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Likely range of the portfolio's value at `target_date`, and the saving it needs."""
        today = datetime.now(timezone.utc).date()
        months = months_until(today, target_date)
        if months < 1:
            raise DomainError("Pick a goal date at least a month from today")
        holdings = await self._holdings(portfolio)
        start_value = sum(float(h.current_value or 0) for h in holdings)
        if monthly is None:
            monthly = (await self.savings_plans(portfolio))["monthly_total"]

        symbol = self.calculations.default_benchmark(portfolio)
        market = self.calculations.market_data_service
        history = await market.get_daily_history(symbol)
        if not history or history["close"].empty:
            raise DomainError(f"No price history for {symbol} to simulate with")
        info = await market.get_ticker_info(symbol) or {}
        closes = history["close"]
        if info.get("currency"):
            rates = await load_rates(market, portfolio.currency, [info["currency"]])
            closes = convert_closes(closes, info["currency"], portfolio.currency, rates)
        index = pd.DatetimeIndex(closes.index)
        if index.tz is not None:
            index = index.tz_localize(None)
        month_ends = (
            pd.Series(closes.to_numpy(dtype=float), index=index)
            .resample("ME")
            .last()
            .dropna()
        )
        history_returns = monthly_returns(month_ends.to_numpy())
        returns = (
            history_returns
            if annual_return_pct is None
            else with_annual_mean(history_returns, annual_return_pct)
        )
        projection = project_goal(start_value, monthly, months, returns, goal=target)

        month_dates = pd.date_range(
            pd.Timestamp(today) + pd.offsets.MonthEnd(1), periods=months, freq="ME"
        )
        return {
            "portfolio_id": portfolio.id,
            "currency": portfolio.currency,
            "target": target,
            "target_date": target_date,
            "months": months,
            "start_value": start_value,
            "monthly": monthly,
            "deposits": projection.deposits,
            "final": {str(p): v for p, v in projection.final.items()},
            "probability_pct": projection.probability_pct,
            "required_monthly": {
                str(p): v for p, v in projection.required_monthly.items()
            },
            "points": [
                {
                    "date": day.date(),
                    **{
                        f"p{p}": projection.percentiles[p][i]
                        for p in projection.percentiles
                    },
                }
                for i, day in enumerate(month_dates)
            ],
            "basis": {
                "symbol": symbol,
                "name": info.get("long_name") or info.get("short_name") or symbol,
                "first_month": month_ends.index[0].date(),
                "months_of_history": int(len(returns)),
                "history_annual_pct": float(
                    ((1 + history_returns.mean()) ** 12 - 1) * 100
                ),
                "assumed_annual_pct": annual_return_pct,
                "paths": projection.paths,
            },
        }
