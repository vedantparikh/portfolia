"""
Dividend income of a portfolio: received from its DIVIDEND transactions,
expected from the holdings' last 12 months of dividends per share (maths in
core/domain/dividends.py).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from core.domain.dividends import (
    Event,
    Payment,
    expected_by_month,
    expected_payments,
    growth_pct,
    income_by,
    pay_lag_days,
    per_share_by_year,
    tax_rate_pct,
    trailing,
    yield_pct,
)
from core.domain.fx import convert_amount
from core.domain.positions import split_factor
from core.errors import DomainError
from core.services.fx import load_rates
from core.services.market_data_service import MarketDataService
from core.services.trade_prices import is_trade_priced
from modules.portfolios.service import PortfolioService

YEARS_SHOWN = 6


class DividendService:
    def __init__(self, db: Session):
        self.db = db
        self.market_data_service = MarketDataService()

    async def income(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Dividends received, the next 12 months expected, yields and growth per holding."""
        currency = portfolio.currency
        today = datetime.now(timezone.utc).date()
        rows = (
            self.db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio.id,
                Transaction.transaction_type == TransactionType.DIVIDEND,
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .order_by(Transaction.transaction_date)
            .all()
        )
        holdings = [
            h
            for h in await PortfolioService(self.db).get_portfolio_holdings(
                portfolio.id
            )
            if h.quantity > 0
        ]
        assets = {
            a.id: a
            for a in self.db.query(Asset).filter(
                Asset.id.in_(
                    {h.asset_id for h in holdings} | {t.asset_id for t in rows}
                )
            )
        }
        rates = await load_rates(
            self.market_data_service,
            currency,
            [t.currency for t in rows] + [a.currency for a in assets.values()],
            strict=False,
        )

        payments: List[Payment] = []
        paid: Dict[int, List[Any]] = {}
        for t in rows:
            day = t.transaction_date.date()
            try:
                gross = convert_amount(
                    Decimal(t.total_amount) + Decimal(t.taxes or 0),
                    t.currency,
                    currency,
                    day,
                    rates,
                )
                tax = convert_amount(t.taxes or 0, t.currency, currency, day, rates)
            except DomainError:
                continue
            payments.append(Payment(t.asset_id, day, float(gross), float(tax)))
            paid.setdefault(t.asset_id, []).append((payments[-1], t.quantity))

        holding_rows = []
        expected = []
        no_dividends = []
        for h in holdings:
            asset = assets.get(h.asset_id)
            if asset is None or is_trade_priced(asset):
                continue
            history = await self.market_data_service.get_daily_history(asset.symbol)
            events: List[Event] = []
            source = "market"
            try:
                if history is not None:
                    events = [
                        (
                            day.date(),
                            float(
                                convert_amount(
                                    value, asset.currency, currency, today, rates
                                )
                            ),
                        )
                        for day, value in history["dividends"].items()
                        if value > 0
                    ]
                if not events and paid.get(h.asset_id):
                    source = "payments"
                    splits = (
                        [
                            (day.date(), Decimal(str(ratio)))
                            for day, ratio in history["splits"].items()
                        ]
                        if history is not None
                        else []
                    )
                    events = [
                        (
                            p.day,
                            p.gross
                            / float(Decimal(quantity) * split_factor(splits, p.day)),
                        )
                        for p, quantity in paid[h.asset_id]
                        if quantity and quantity > 0
                    ]
            except DomainError:
                events = []
            if not events:
                no_dividends.append(h.symbol)
                continue

            own = [p for p, _ in paid.get(h.asset_id, [])]
            lag = (
                pay_lag_days(events, [p.day for p in own]) if source == "market" else 0
            )
            per_share = trailing(events, today)
            coming = expected_payments(h.asset_id, events, h.quantity, today, lag)
            expected.extend(coming)
            price = (
                h.current_value / h.quantity if h.current_value is not None else None
            )
            years = per_share_by_year(events)
            holding_rows.append(
                {
                    "asset_id": h.asset_id,
                    "symbol": h.symbol,
                    "name": asset.name,
                    "quantity": h.quantity,
                    "source": source,
                    "per_share_12m": per_share,
                    "expected_12m": sum(e.amount for e in coming),
                    "current_yield_pct": yield_pct(per_share, price),
                    "yield_on_cost_pct": yield_pct(
                        per_share, h.cost_basis_total / h.quantity
                    ),
                    "growth_pct": growth_pct(events, today),
                    "per_share_by_year": [
                        {"year": y, "per_share": v}
                        for y, v in years.items()
                        if y > today.year - YEARS_SHOWN
                    ],
                    "last_dividend": max(d for d, _ in events),
                    "pay_lag_days": lag,
                    "received_total": sum(p.gross for p in own),
                    "received_12m": trailing([(p.day, p.gross) for p in own], today),
                }
            )
        holding_rows.sort(key=lambda r: -r["expected_12m"])

        tax_rate = tax_rate_pct(payments, today)
        expected_gross = sum(e.amount for e in expected)
        value = sum(float(h.current_value or 0) for h in holdings)
        cost = sum(
            float(h.cost_basis_total)
            for h in holdings
            if h.asset_id in {r["asset_id"] for r in holding_rows}
        )
        symbols = {h.asset_id: h.symbol for h in holdings}
        return {
            "portfolio_id": portfolio.id,
            "currency": currency,
            "received": {
                "gross": sum(p.gross for p in payments),
                "tax": sum(p.tax for p in payments),
                "net": sum(p.net for p in payments),
                "gross_12m": trailing([(p.day, p.gross) for p in payments], today),
                "net_12m": trailing([(p.day, p.net) for p in payments], today),
                "payments": len(payments),
                "first": payments[0].day if payments else None,
            },
            "expected": {
                "gross_12m": expected_gross,
                "net_12m": expected_gross * (1 - tax_rate / 100),
                "tax_rate_pct": tax_rate,
                "yield_pct": expected_gross / value * 100 if value > 0 else None,
                "yield_on_cost_pct": expected_gross / cost * 100 if cost > 0 else None,
            },
            "monthly": [vars(r) for r in income_by(payments, "month", today)],
            "yearly": [vars(r) for r in income_by(payments, "year", today)],
            "calendar": [
                {
                    "month": month,
                    "amount": amount,
                    "payments": [
                        {
                            "asset_id": e.asset_id,
                            "symbol": symbols.get(e.asset_id, str(e.asset_id)),
                            "day": e.day,
                            "per_share": e.per_share,
                            "amount": e.amount,
                        }
                        for e in items
                    ],
                }
                for month, amount, items in expected_by_month(expected, today)
            ],
            "holdings": holding_rows,
            "no_dividends": sorted(no_dividends),
        }
