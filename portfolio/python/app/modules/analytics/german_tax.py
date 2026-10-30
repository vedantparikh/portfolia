"""
German tax view of a euro portfolio: the year as its bank settles it, the
Vorabpauschale and loss or allowance harvesting (maths in core/domain/german_tax.py).
"""

import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from core.database.models import (
    Asset,
    Portfolio,
    TaxEntry,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from core.database.models.asset import AssetType
from core.domain.fx import (
    canonical_currency,
    convert_amount,
    convert_closes,
    convert_trades,
)
from core.domain.german_tax import (
    BASISZINS_PCT,
    EQUITY_FUND_EXEMPTION,
    Kind,
    open_lots,
    sale_lots,
    settle,
    sparerpauschbetrag,
    split_allowance,
    tax_rate_pct,
    taxable_share,
    vorabpauschale,
    vorabpauschale_credit,
    vorabpauschale_per_share,
)
from core.domain.positions import to_trades
from core.errors import DomainError
from core.services.fx import load_rates
from modules.analytics.calculations import PortfolioCalculationService
from modules.portfolios.service import PortfolioService

FUNDS = (AssetType.ETF, AssetType.MUTUALFUND)
CRYPTO_PAIR = re.compile(r"^[A-Z0-9]+-(USD|EUR)$")


def kind_of(asset: Optional[Asset]) -> Optional[Kind]:
    """share, fund (equity fund assumed) or other; None for crypto (private sales, § 23 EStG)."""
    if asset is None:
        return "other"
    if asset.asset_type == AssetType.CRYPTOCURRENCY or CRYPTO_PAIR.match(
        asset.symbol or ""
    ):
        return None
    if asset.asset_type == AssetType.EQUITY:
        return "share"
    if asset.asset_type in FUNDS:
        return "fund"
    return "other"


def _close_on(closes: pd.Series, day: date) -> Optional[float]:
    index = pd.DatetimeIndex(closes.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    eligible = closes.to_numpy(dtype=float)[index <= pd.Timestamp(day)]
    return float(eligible[-1]) if len(eligible) else None


class GermanTaxService:
    def __init__(self, db: Session, today: Optional[date] = None):
        self.db = db
        self.today = today
        self.calculations = PortfolioCalculationService(db)
        self.market = self.calculations.market_data_service

    async def _book(self, portfolio: Portfolio) -> Dict[str, Any]:
        if canonical_currency(portfolio.currency)[0] != "EUR":
            raise DomainError("The German tax view needs a portfolio in euros")
        transactions = (
            self.db.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio.id,
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .order_by(Transaction.transaction_date, Transaction.id)
            .all()
        )
        if not transactions:
            raise DomainError("This portfolio has no transactions yet")
        asset_ids = sorted({t.asset_id for t in transactions})
        assets = {a.id: a for a in self.db.query(Asset).filter(Asset.id.in_(asset_ids))}
        kinds = {a: kind_of(assets.get(a)) for a in asset_ids}
        (
            closes,
            splits,
            symbols,
            currencies,
        ) = await self.calculations.get_market_history(asset_ids)
        rates = await load_rates(
            self.market,
            "EUR",
            list(currencies.values()) + [t.currency for t in transactions],
            strict=False,
        )
        moving = [
            t
            for t in transactions
            if kinds[t.asset_id] is not None
            and t.transaction_type
            not in (TransactionType.DIVIDEND, TransactionType.FEE)
        ]
        trades = convert_trades(
            to_trades(moving, splits),
            {t.id: t.currency for t in moving},
            "EUR",
            rates,
        )

        def euros(amount, currency, when) -> float:
            return float(convert_amount(amount or 0, currency, "EUR", when, rates))

        dividends: Dict[int, List[tuple]] = {}
        withheld: Dict[int, float] = {}
        for t in transactions:
            day = t.transaction_date.date()
            withheld[day.year] = withheld.get(day.year, 0.0) + euros(
                t.taxes, t.currency, day
            )
            if t.transaction_type == TransactionType.DIVIDEND and kinds[t.asset_id]:
                gross = Decimal(t.total_amount) + Decimal(t.taxes or 0)
                dividends.setdefault(day.year, []).append(
                    (t.asset_id, euros(gross, t.currency, day))
                )
        for e in self.db.query(TaxEntry).filter(TaxEntry.portfolio_id == portfolio.id):
            day = e.entry_date.date()
            withheld[day.year] = withheld.get(day.year, 0.0) + euros(
                e.amount, e.currency, day
            )

        today = self.today or datetime.now(timezone.utc).date()
        first_year = transactions[0].transaction_date.year
        vp: Dict[int, Dict[int, Dict[str, float]]] = {}
        for asset_id, kind in kinds.items():
            if kind != "fund" or asset_id not in closes:
                continue
            series = convert_closes(
                closes[asset_id], currencies.get(asset_id), "EUR", rates
            )
            history = await self.market.get_daily_history(symbols[asset_id])
            paid = history["dividends"] if history is not None else pd.Series()
            for year in range(first_year, today.year + 1):
                rate = BASISZINS_PCT.get(year, 0.0)
                start = _close_on(series, date(year - 1, 12, 31))
                end = _close_on(series, min(date(year, 12, 31), today))
                if start is None or end is None:
                    continue
                distributions = sum(
                    euros(v, currencies.get(asset_id), d.date())
                    for d, v in paid.items()
                    if d.year == year
                )
                vp.setdefault(asset_id, {})[year] = {
                    "start_price": start,
                    "end_price": end,
                    "distributions": distributions,
                    "per_share": vorabpauschale_per_share(
                        start, end, distributions, rate
                    ),
                }
        return {
            "assets": assets,
            "symbols": symbols,
            "kinds": kinds,
            "trades": trades,
            "sales": sale_lots(trades),
            "dividends": dividends,
            "withheld": withheld,
            "vp": vp,
            "first_year": first_year,
            "today": today,
        }

    def _year_items(
        self, book: Dict[str, Any], year: int
    ) -> Dict[int, Dict[str, float]]:
        """Per asset: taxable sale gains, credits, dividends and last year's Vorabpauschale."""
        kinds, vp = book["kinds"], book["vp"]
        rows: Dict[int, Dict[str, float]] = {}

        def row(asset_id: int) -> Dict[str, float]:
            return rows.setdefault(
                asset_id,
                {
                    "sale_gain": 0.0,
                    "vorabpauschale_credit": 0.0,
                    "dividends": 0.0,
                    "vorabpauschale": 0.0,
                },
            )

        for lot in book["sales"]:
            if lot.sold_on.year != year:
                continue
            r = row(lot.asset_id)
            r["sale_gain"] += lot.gain
            if kinds[lot.asset_id] == "fund":
                per_year = {
                    y: v["per_share"] for y, v in vp.get(lot.asset_id, {}).items()
                }
                r["vorabpauschale_credit"] += vorabpauschale_credit(lot, per_year)
        for asset_id, gross in book["dividends"].get(year, []):
            row(asset_id)["dividends"] += gross
        held = open_lots(book["trades"], date(year - 1, 12, 31))
        for asset_id, years in vp.items():
            if year - 1 in years and asset_id in held:
                amount = vorabpauschale(
                    held[asset_id], years[year - 1]["per_share"], year - 1
                )
                if amount:
                    row(asset_id)["vorabpauschale"] += amount
        for asset_id, r in rows.items():
            kind = kinds[asset_id]
            share = taxable_share(kind)
            sales = (r["sale_gain"] - r["vorabpauschale_credit"]) * share
            income = (r["dividends"] + r["vorabpauschale"]) * share
            r["share_pot"] = sales if kind == "share" else 0.0
            r["other_pot"] = income + (0.0 if kind == "share" else sales)
            r["taxable"] = r["share_pot"] + r["other_pot"]
        return rows

    def _settle_years(self, book, last_year: int, allowance, joint: bool, rate: float):
        """Every year from the first to `last_year`, carrying each pot's loss forward."""
        settled = []
        share_in = other_in = 0.0
        for year in range(book["first_year"], last_year + 1):
            items = self._year_items(book, year)
            share_net = sum(r["share_pot"] for r in items.values())
            other_net = sum(r["other_pot"] for r in items.values())
            limit = (
                allowance if allowance is not None else sparerpauschbetrag(year, joint)
            )
            result = settle(share_net, other_net, limit, rate, share_in, other_in)
            settled.append((year, items, result, share_in, other_in, limit))
            share_in, other_in = result.share_loss_carried, result.other_loss_carried
        return settled

    async def year(
        self,
        portfolio: Portfolio,
        year: Optional[int],
        allowance: Optional[float],
        joint: bool,
        church_pct: float,
    ) -> Dict[str, Any]:
        book = await self._book(portfolio)
        today = book["today"]
        year = year or today.year
        if not book["first_year"] <= year <= today.year:
            raise DomainError(
                f"Pick a year between {book['first_year']} and {today.year}"
            )
        rate = tax_rate_pct(church_pct)
        settled = self._settle_years(book, year, allowance, joint, rate)
        _, items, result, share_in, other_in, limit = settled[-1]
        kinds, assets, symbols = book["kinds"], book["assets"], book["symbols"]

        def described(asset_id: int) -> Dict[str, Any]:
            asset = assets.get(asset_id)
            return {
                "asset_id": asset_id,
                "symbol": symbols.get(asset_id, str(asset_id)),
                "name": asset.name if asset else None,
                "kind": kinds[asset_id],
            }

        lots_now = open_lots(book["trades"], min(date(year, 12, 31), today))
        funds = []
        for asset_id, years in book["vp"].items():
            if year not in years or asset_id not in lots_now:
                continue
            v = years[year]
            amount = vorabpauschale(lots_now[asset_id], v["per_share"], year)
            funds.append(
                {
                    **described(asset_id),
                    "shares": sum(q for _, q in lots_now[asset_id]),
                    **v,
                    "amount": amount,
                    "taxable": amount * taxable_share("fund"),
                }
            )
        funds.sort(key=lambda f: -f["amount"])
        vp_taxable = sum(f["taxable"] for f in funds)

        harvest, tax_free = [], []
        if year == today.year:
            holdings = await PortfolioService(self.db).get_portfolio_holdings(
                portfolio.id
            )
            for h in holdings:
                kind = kinds.get(h.asset_id, kind_of(assets.get(h.asset_id)))
                if kind is None or h.quantity <= 0 or h.current_value is None:
                    continue
                unrealized = float(h.current_value) - float(h.cost_basis_total)
                taxable = unrealized * taxable_share(kind)
                if unrealized < 0:
                    shares = result.share_net + (taxable if kind == "share" else 0)
                    other = result.other_net + (taxable if kind != "share" else 0)
                    after = settle(shares, other, limit, rate, share_in, other_in)
                    harvest.append(
                        {
                            **described(h.asset_id),
                            "kind": kind,
                            "unrealized": unrealized,
                            "taxable": taxable,
                            "tax_saved": result.tax - after.tax,
                        }
                    )
                elif unrealized > 0:
                    tax_free.append(
                        {
                            **described(h.asset_id),
                            "kind": kind,
                            "unrealized": unrealized,
                            "taxable": taxable,
                        }
                    )
            harvest.sort(key=lambda r: (-r["tax_saved"], r["unrealized"]))
            tax_free.sort(key=lambda r: -r["unrealized"])

        return {
            "portfolio_id": portfolio.id,
            "currency": "EUR",
            "year": year,
            "years": list(range(book["first_year"], today.year + 1)),
            "assumptions": {
                "allowance": limit,
                "joint": joint,
                "church_pct": church_pct,
                "rate_pct": rate,
                "basiszins_pct": BASISZINS_PCT.get(year),
                "equity_fund_exemption_pct": EQUITY_FUND_EXEMPTION * 100,
            },
            "settlement": {
                **vars(result),
                "share_loss_in": share_in,
                "other_loss_in": other_in,
                "allowance": limit,
                "withheld": book["withheld"].get(year, 0.0),
            },
            "items": sorted(
                ({**described(a), **r} for a, r in items.items()),
                key=lambda r: -abs(r["taxable"]),
            ),
            "history": [
                {
                    "year": y,
                    "income": s.income,
                    "allowance_used": s.allowance_used,
                    "tax": s.tax,
                    "withheld": book["withheld"].get(y, 0.0),
                    "share_loss_carried": s.share_loss_carried,
                    "other_loss_carried": s.other_loss_carried,
                }
                for y, _, s, _, _, _ in settled
            ],
            "vorabpauschale": {
                "year": year,
                "basiszins_pct": BASISZINS_PCT.get(year),
                "estimate": year == today.year,
                "due": date(year + 1, 1, 2),
                "funds": funds,
                "amount": sum(f["amount"] for f in funds),
                "taxable": vp_taxable,
                "tax": vp_taxable * rate / 100,
            },
            "harvest": harvest,
            "tax_free_gains": tax_free,
            "excluded": sorted(
                symbols.get(a, str(a)) for a, k in kinds.items() if k is None
            ),
        }

    async def allowance(self, portfolios: List[Portfolio], year: int, joint: bool):
        """Each euro portfolio's capital income before the allowance, and a split of it."""
        rows = []
        for portfolio in portfolios:
            if canonical_currency(portfolio.currency)[0] != "EUR":
                continue
            try:
                book = await self._book(portfolio)
            except DomainError:
                continue
            if year < book["first_year"]:
                continue
            settled = self._settle_years(book, year, 0.0, joint, tax_rate_pct())
            rows.append(
                {
                    "portfolio_id": portfolio.id,
                    "name": portfolio.name,
                    "income": settled[-1][2].income,
                }
            )
        total = sparerpauschbetrag(year, joint)
        split = split_allowance({r["portfolio_id"]: r["income"] for r in rows}, total)
        for r in rows:
            r["suggested"] = split[r["portfolio_id"]]
        return {
            "year": year,
            "allowance": total,
            "income": sum(r["income"] for r in rows),
            "portfolios": rows,
        }
