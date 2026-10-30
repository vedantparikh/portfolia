"""Dividend income golden tests (core/domain/dividends.py), worked out by hand."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from core.domain.dividends import (
    Expected,
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


def test_income_by_month_and_year_fills_empty_periods():
    payments = [
        Payment(1, date(2026, 1, 15), 10.0, 2.64),
        Payment(2, date(2026, 1, 30), 5.0, 0.0),
        Payment(1, date(2026, 3, 10), 20.0, 5.28),
    ]

    months = income_by(payments, "month", date(2026, 4, 2))

    assert [m.period for m in months] == [date(2026, m, 1) for m in (1, 2, 3, 4)]
    assert (months[0].gross, months[0].tax, months[0].payments) == (15.0, 2.64, 2)
    assert months[0].net == pytest.approx(12.36)
    assert (months[1].gross, months[1].payments) == (0.0, 0)
    assert months[2].net == pytest.approx(14.72)
    (year,) = income_by(payments, "year", date(2026, 4, 2))
    assert (year.period, year.gross, year.payments) == (date(2026, 1, 1), 35.0, 3)
    assert year.tax == pytest.approx(7.92)
    assert income_by([], "month", date(2026, 4, 2)) == []


def test_trailing_takes_the_last_365_days_up_to_today():
    events = [
        (date(2025, 10, 30), 1.0),
        (date(2025, 10, 31), 0.5),
        (date(2026, 10, 30), 0.25),
        (date(2026, 10, 31), 9.0),
    ]
    assert trailing(events, date(2026, 10, 30)) == 0.75


def test_growth_compares_the_last_two_complete_years():
    events = [
        (date(2024, 3, 1), 0.5),
        (date(2024, 9, 1), 0.5),
        (date(2025, 3, 1), 0.6),
        (date(2025, 9, 1), 0.6),
        (date(2026, 2, 1), 5.0),
    ]
    assert per_share_by_year(events) == {2024: 1.0, 2025: 1.2, 2026: 5.0}
    assert growth_pct(events, date(2026, 3, 1)) == pytest.approx(20)
    assert growth_pct(events[:2], date(2026, 3, 1)) is None
    assert growth_pct(events, date(2025, 3, 1)) is None


def test_pay_lag_is_the_median_days_after_the_ex_date():
    events = [(date(2026, 3, 2), 1.0), (date(2026, 6, 1), 1.0)]
    paid = [date(2026, 3, 20), date(2026, 6, 25), date(2026, 12, 1)]
    # 18 and 24 days; December is more than 90 days after any ex-date
    assert pay_lag_days(events, paid) == 21
    assert pay_lag_days(events, []) == 0


def test_expected_repeats_the_last_twelve_months_for_the_shares_held():
    events = [
        (date(2025, 5, 15), 0.6),
        (date(2025, 11, 14), 0.5),
        (date(2026, 5, 15), 0.7),
    ]
    today = date(2026, 10, 30)

    coming = expected_payments(1, events, 10, today, lag_days=21)

    # 2025-11-14 + 1 year + 21 days, 2026-05-15 + 1 year + 21 days
    assert coming == [
        Expected(1, date(2026, 12, 5), 0.5, 5.0),
        Expected(1, date(2027, 6, 5), 0.7, pytest.approx(7.0)),
    ]
    (leap,) = expected_payments(1, [(date(2024, 2, 29), 1.0)], 1, date(2024, 3, 1))
    assert leap.day == date(2025, 2, 28)

    months = expected_by_month(coming, today)
    assert [m for m, _, _ in months][0] == date(2026, 10, 1)
    assert len(months) == 9
    assert {m: a for m, a, _ in months if a} == {
        date(2026, 12, 1): 5.0,
        date(2027, 6, 1): pytest.approx(7.0),
    }
    assert expected_by_month([], today) == []


def test_yields_and_tax_rate():
    assert yield_pct(2, 50) == 4
    assert yield_pct(2, None) is None
    assert yield_pct(2, 0) is None
    today = date(2026, 10, 30)
    old = Payment(1, date(2024, 1, 1), 100.0, 0.0)
    recent = Payment(1, date(2026, 6, 1), 100.0, 26.375)
    assert tax_rate_pct([old, recent], today) == pytest.approx(26.375)
    assert tax_rate_pct([old], today) == 0
    assert tax_rate_pct([], today) == 0


@pytest.fixture
def book(test_db, monkeypatch):
    """A EUR portfolio holding 12 A (cost 600, now 55) and 10 B (no dividends), two A payments."""
    from core.database.models import (
        Asset,
        Portfolio,
        Transaction,
        TransactionType,
        User,
    )
    from core.database.models.asset import AssetType
    from modules.portfolios.service import PortfolioService

    user = User(email="div@example.com", username="dividends", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="D", currency="EUR")
    a = Asset(
        symbol="AAA",
        name="A plc",
        asset_type=AssetType.EQUITY,
        user_id=user.id,
        currency="EUR",
    )
    b = Asset(
        symbol="BBB",
        name="B AG",
        asset_type=AssetType.EQUITY,
        user_id=user.id,
        currency="EUR",
    )
    test_db.add_all([portfolio, a, b])
    test_db.flush()
    now = datetime.now(timezone.utc)
    for days, amount, taxes, shares in (
        (200, "7.36", "2.64", "10"),
        (500, "5", "0", "5"),
    ):
        test_db.add(
            Transaction(
                portfolio_id=portfolio.id,
                asset_id=a.id,
                transaction_type=TransactionType.DIVIDEND,
                quantity=Decimal(shares),
                price=Decimal(amount) / Decimal(shares),
                total_amount=Decimal(amount),
                taxes=Decimal(taxes),
                currency="EUR",
                transaction_date=now - timedelta(days=days),
            )
        )
    test_db.commit()

    async def holdings(self, portfolio_id):
        return [
            SimpleNamespace(
                asset_id=a.id,
                symbol="AAA",
                quantity=12.0,
                current_value=660.0,
                cost_basis_total=600.0,
            ),
            SimpleNamespace(
                asset_id=b.id,
                symbol="BBB",
                quantity=10.0,
                current_value=1000.0,
                cost_basis_total=900.0,
            ),
        ]

    monkeypatch.setattr(PortfolioService, "get_portfolio_holdings", holdings)
    return SimpleNamespace(portfolio=portfolio, a=a, b=b, user=user, now=now)


def _market(monkeypatch, service, dividends, splits=None):
    async def history(symbol):
        return {
            "close": pd.Series(dtype=float),
            "splits": splits
            if symbol == "AAA" and splits is not None
            else pd.Series(dtype=float),
            "dividends": dividends if symbol == "AAA" else pd.Series(dtype=float),
        }

    monkeypatch.setattr(service.market_data_service, "get_daily_history", history)


def _ago(now, days):
    return pd.Timestamp((now - timedelta(days=days)).date())


@pytest.mark.asyncio
async def test_service_income_expected_and_yields(test_db, book, monkeypatch):
    from modules.analytics.dividends import DividendService

    service = DividendService(test_db)
    now = book.now
    # Ex-dates 20 days before each payment, plus one more a year before
    _market(
        monkeypatch,
        service,
        pd.Series([0.8, 0.8, 1.0], index=[_ago(now, d) for d in (700, 520, 220)]),
    )

    result = await service.income(book.portfolio)

    received = result["received"]
    assert (received["gross"], received["payments"]) == (15, 2)
    assert received["tax"] == pytest.approx(2.64)
    assert received["gross_12m"] == pytest.approx(10)
    (row,) = result["holdings"]
    assert result["no_dividends"] == ["BBB"]
    # 1.00 a share in the last 12 months × 12 shares; price 55, average cost 50
    assert row["per_share_12m"] == 1.0
    assert row["expected_12m"] == pytest.approx(12)
    assert row["current_yield_pct"] == pytest.approx(100 / 55)
    assert row["yield_on_cost_pct"] == pytest.approx(2)
    assert row["pay_lag_days"] == 20
    assert row["received_total"] == pytest.approx(15)
    assert row["source"] == "market"
    expected = result["expected"]
    # Last 12 months' tax 2.64 of 10 gross
    assert expected["tax_rate_pct"] == pytest.approx(26.4)
    assert expected["net_12m"] == pytest.approx(12 * 0.736)
    assert expected["yield_pct"] == pytest.approx(12 / 1660 * 100)
    assert expected["yield_on_cost_pct"] == pytest.approx(2)
    (paying,) = [m for m in result["calendar"] if m["amount"]]
    (payment,) = paying["payments"]
    assert payment["day"] == (now - timedelta(days=220)).date().replace(
        year=(now - timedelta(days=220)).year + 1
    ) + timedelta(days=20)
    assert sum(m["gross"] for m in result["monthly"]) == pytest.approx(15)


@pytest.mark.asyncio
async def test_service_falls_back_to_own_payments_in_todays_shares(
    test_db, book, monkeypatch
):
    from modules.analytics.dividends import DividendService

    service = DividendService(test_db)
    # No dividends on record for the listing; a 2-for-1 split 100 days ago
    _market(
        monkeypatch,
        service,
        pd.Series(dtype=float),
        splits=pd.Series([2.0], index=[_ago(book.now, 100)]),
    )

    result = await service.income(book.portfolio)

    (row,) = result["holdings"]
    # 10 gross on 10 shares = 1.00, 0.50 in today's shares; × 12 held
    assert row["source"] == "payments"
    assert row["per_share_12m"] == pytest.approx(0.5)
    assert row["expected_12m"] == pytest.approx(6)
    assert row["pay_lag_days"] == 0


def test_dividend_route_checks_ownership(client, test_db, book, monkeypatch):
    from core.auth.dependencies import get_current_active_user
    from core.services.market_data_service import MarketDataService
    from main import app

    async def history(self, symbol):
        return None

    monkeypatch.setattr(MarketDataService, "get_daily_history", history)
    app.dependency_overrides[get_current_active_user] = lambda: book.user
    try:
        base = "/api/v1/analytics/portfolios"
        body = client.get(f"{base}/{book.portfolio.id}/dividends").json()
        assert body["received"]["payments"] == 2
        assert body["holdings"][0]["source"] == "payments"
        assert client.get(f"{base}/999999/dividends").status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
