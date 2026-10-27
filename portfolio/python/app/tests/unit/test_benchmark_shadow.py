"""Benchmark shadow portfolio: the portfolio's own cash flows, invested in the benchmark."""

from datetime import date

import pandas as pd
import pytest

from core.domain.benchmark import shadow_series
from core.domain.returns import period_summary
from core.domain.valuation import MissingPriceError

DAYS = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])


def _portfolio(values=(1000.0, 1700.0, 1500.0, 1600.0)):
    return pd.DataFrame(
        {
            "value": list(values),
            "inflow": [1000.0, 550.0, 0.0, 0.0],
            "outflow": [0.0, 0.0, 330.0, 0.0],
        },
        index=DAYS,
    )


def _closes(first=pd.Timestamp("2025-01-01")):
    return pd.Series(
        [100.0, 110.0, 121.0, 110.0, 132.0],
        index=pd.DatetimeIndex([first, *DAYS]),
    )


def test_inception_shadow_buys_at_the_previous_close_and_sells_at_the_close():
    shadow = shadow_series(_portfolio(), _closes(), None)

    # 10 units @100, +5 @110, -3 @110 → 12 units
    assert shadow["value"].tolist() == pytest.approx([1100.0, 1815.0, 1320.0, 1584.0])
    assert shadow["inflow"].tolist() == [1000.0, 550.0, 0.0, 0.0]
    assert shadow["outflow"].tolist() == [0.0, 0.0, 330.0, 0.0]
    assert shadow["shortfall"].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_shadow_twr_is_the_benchmark_return_and_profit_follows_the_flows():
    summary = period_summary(shadow_series(_portfolio(), _closes(), None))

    assert summary["twr_pct"] == pytest.approx(32.0)
    assert summary["net_contributions"] == pytest.approx(1220.0)
    assert summary["profit"] == pytest.approx(364.0)


def test_period_shadow_starts_with_the_portfolio_value_before_the_period():
    start = date(2025, 1, 6)
    shadow = shadow_series(_portfolio(), _closes(), start)
    summary = period_summary(shadow, start)

    units = 1700.0 / 121.0 - 3.0
    assert summary["start_value"] == pytest.approx(1700.0)
    assert summary["end_value"] == pytest.approx(units * 132.0)
    assert summary["twr_pct"] == pytest.approx((132.0 / 121.0 - 1) * 100)
    assert summary["profit"] == pytest.approx(units * 132.0 - 1700.0 + 330.0)


def test_withdrawal_larger_than_the_shadow_is_recorded_as_shortfall():
    portfolio = _portfolio()
    portfolio.loc[DAYS[2], "outflow"] = 5000.0
    shadow = shadow_series(portfolio, _closes(), None)

    assert shadow["value"].iloc[2] == 0.0
    assert shadow["outflow"].iloc[2] == pytest.approx(1650.0)
    assert shadow["shortfall"].iloc[-1] == pytest.approx(5000.0 - 1650.0)


def test_benchmark_gaps_are_carried_forward():
    closes = _closes().drop(DAYS[2])
    shadow = shadow_series(_portfolio(), closes, None)

    # the third day reuses 121 as its close: sell 330/121 units
    assert shadow["value"].iloc[2] == pytest.approx((15 - 330 / 121) * 121)


def test_benchmark_without_a_price_before_the_period_is_an_error():
    with pytest.raises(MissingPriceError, match="2025-01-02"):
        shadow_series(_portfolio(), _closes(first=pd.Timestamp("2025-01-08")), None)


@pytest.fixture
def portfolio(test_db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from core.database.models import (
        Asset,
        Portfolio,
        Transaction,
        TransactionType,
        User,
    )
    from core.database.models.asset import AssetType

    user = User(email="bench@example.com", username="bench", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P", currency="EUR")
    asset = Asset(symbol="AAA", name="A", asset_type=AssetType.EQUITY, user_id=user.id)
    test_db.add_all([portfolio, asset])
    test_db.flush()
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            total_amount=Decimal("1000"),
            transaction_date=datetime.now(timezone.utc) - timedelta(days=20),
        )
    )
    test_db.commit()
    return portfolio


@pytest.mark.asyncio
async def test_service_compares_against_the_shadow(test_db, monkeypatch, portfolio):
    from datetime import datetime, timedelta, timezone

    from modules.analytics.calculations import PortfolioCalculationService

    start = (datetime.now(timezone.utc) - timedelta(days=20)).date()
    days = pd.bdate_range(start, periods=3)
    histories = {
        "AAA": pd.Series([100.0, 110.0, 121.0], index=days),
        "SPY": pd.Series(
            [50.0, 50.0, 55.0, 60.5],
            index=days.insert(0, days[0] - pd.Timedelta(days=3)),
        ),
        # The book is EUR and the listing is USD. A rate of 1 keeps the hand
        # numbers; the conversion itself is covered in test_fx.py.
        "USDEUR=X": pd.Series(
            [1.0, 1.0, 1.0, 1.0],
            index=days.insert(0, days[0] - pd.Timedelta(days=3)),
        ),
    }
    service = PortfolioCalculationService(test_db)

    async def history(symbol):
        return {
            "close": histories[symbol],
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series([0.5], index=[days[1]])
            if symbol == "SPY"
            else pd.Series(dtype=float),
        }

    async def info(symbol):
        return {"long_name": "SPDR S&P 500", "currency": "USD"}

    monkeypatch.setattr(service.market_data_service, "get_daily_history", history)
    monkeypatch.setattr(service.market_data_service, "get_ticker_info", info)

    result = await service.get_benchmark_comparison(
        portfolio.id, portfolio.user_id, "inception", "spy"
    )

    assert result["benchmark"]["symbol"] == "SPY"
    assert [p["benchmark_value"] for p in result["points"]] == pytest.approx(
        [1000.0, 1100.0, 1210.0]
    )
    assert result["shadow"]["twr_pct"] == pytest.approx(21.0)
    assert result["portfolio"]["twr_pct"] == pytest.approx(21.0)
    assert result["difference"]["profit"] == pytest.approx(0.0)
    assert not any("quoted in USD" in w for w in result["warnings"])
    assert any("paid 1 dividends" in w for w in result["warnings"])


def test_default_benchmark_follows_the_portfolio_currency(test_db, portfolio):
    from modules.analytics.calculations import PortfolioCalculationService

    assert (
        PortfolioCalculationService(test_db).default_benchmark(portfolio) == "EUNL.DE"
    )
