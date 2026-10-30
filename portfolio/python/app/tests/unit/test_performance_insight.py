"""
Golden tests for core/domain/insight.py: contribution per holding, calendar
returns, drawdowns, the timing effect and the currency effect. Every expected
number is worked out by hand in the comments.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from core.database.models import TransactionType
from core.domain.insight import (
    benchmark_returns,
    calendar_returns,
    contributions,
    currency_effect,
    drawdowns,
    timing_effect,
)
from core.domain.positions import Trade
from core.domain.returns import compute_daily_returns, period_summary
from core.domain.valuation import daily_series_by_asset

D1, D2, D3, D4 = (date(2026, 3, d) for d in (2, 3, 4, 5))


def trade(kind, asset_id, qty, total, day, id=0):
    return Trade(
        id=id,
        asset_id=asset_id,
        transaction_type=kind,
        transaction_date=day,
        quantity=Decimal(str(qty)),
        price=Decimal(str(total / qty)),
        total_amount=Decimal(str(total)),
    )


def closes(values, days=(D1, D2, D3, D4)):
    return pd.Series(values, index=pd.to_datetime(list(days[: len(values)])))


@pytest.fixture
def two_assets():
    # A: 10 @ 100 on D1, closes 100, 110, 110, 121 → worth 1,210
    # B: 5 @ 200 on D2, closes 200, 200, 180, 198, all sold on D4 for 990
    trades = [
        trade(TransactionType.BUY, 1, 10, 1000, D1, 1),
        trade(TransactionType.BUY, 2, 5, 1000, D2, 2),
        trade(TransactionType.SELL, 2, 5, 990, D4, 3),
    ]
    prices = {1: closes([100, 110, 110, 121]), 2: closes([200, 200, 180, 198])}
    return daily_series_by_asset(trades, prices, D4)


def test_asset_frames_add_up_to_the_portfolio(two_assets):
    series, assets = two_assets

    for column in ("value", "inflow", "outflow"):
        total = sum(frame[column] for frame in assets.values())
        assert total.tolist() == pytest.approx(series[column].tolist())
    assert assets[2]["quantity"].tolist() == [0, 5, 5, 0]
    assert assets[1]["price"].tolist() == [100, 110, 110, 121]


def test_contributions_by_hand(two_assets):
    series, assets = two_assets
    # Values 1000, 2100, 2000, 1210 (+990 out); returns 0, +5 %, −4.76 %, +10 %;
    # TWR = 1.05 × 2000/2100 × 1.1 − 1 = 10 %.
    # A: D2 +100/2000 at growth 1, D4 +110/2000 at growth 1.0 → 5 + 5.5 = 10.5 pp
    # B: D3 −100/2100 at growth 1.05 = −5 pp, D4 +90/2000 at growth 1.0 = +4.5 pp
    found = {c.asset_id: c for c in contributions(series, assets)}

    assert found[1].contribution_pp == pytest.approx(10.5)
    assert found[2].contribution_pp == pytest.approx(-0.5)
    assert found[1].profit == pytest.approx(210)
    assert found[2].profit == pytest.approx(-10)
    assert (found[2].inflow, found[2].outflow, found[2].end_value) == (1000, 990, 0)
    summary = period_summary(series)
    assert sum(c.contribution_pp for c in found.values()) == pytest.approx(
        summary["twr_pct"]
    )
    assert sum(c.profit for c in found.values()) == pytest.approx(summary["profit"])
    assert [c.asset_id for c in contributions(series, assets)] == [1, 2]


def test_contributions_of_a_later_period_open_with_the_value_before_it(two_assets):
    series, assets = two_assets
    # From D3: opening 2100. A: 0/2100, then 110/2000 at growth 2000/2100
    found = {c.asset_id: c for c in contributions(series, assets, D3)}

    assert found[1].start_value == 1100
    assert found[1].profit == pytest.approx(110)
    assert found[1].contribution_pp == pytest.approx(110 / 2000 * 2000 / 2100 * 100)
    assert sum(c.contribution_pp for c in found.values()) == pytest.approx(
        period_summary(series, D3)["twr_pct"]
    )


def test_timing_effect_by_hand(two_assets):
    series, _ = two_assets
    # Steady rate g = 1.1^(1/4) − 1 per session. 1,000 grows 4 sessions, the
    # second 1,000 grows 3, 990 leaves after the last: profit 200 actual.
    g = 1.1**0.25 - 1
    steady_end = (1000 * (1 + g) + 1000) * (1 + g) ** 3 - 990
    steady_profit = steady_end - (2000 - 990)

    result = timing_effect(series)

    assert result.profit == pytest.approx(200)
    assert result.steady_profit == pytest.approx(steady_profit)
    assert result.timing_effect == pytest.approx(200 - steady_profit)
    assert result.steady_daily_pct == pytest.approx(g * 100)


def test_no_timing_effect_without_flows():
    series, _ = daily_series_by_asset(
        [trade(TransactionType.BUY, 1, 10, 1000, D1)],
        {1: closes([100, 90, 120, 130])},
        D4,
    )
    result = timing_effect(series)
    assert result.profit == pytest.approx(300)
    assert result.timing_effect == pytest.approx(0, abs=1e-9)


def test_calendar_returns_compound_and_flag_partial_periods():
    days = pd.to_datetime(["2026-01-30", "2026-02-02", "2026-02-27", "2026-03-02"])
    returns = pd.Series([0.1, 0.1, -0.5, 0.2], index=days)

    months = calendar_returns(returns, "M", date(2026, 1, 30), date(2026, 3, 2))
    years = calendar_returns(returns, "Y", date(2026, 1, 30), date(2026, 3, 2))

    assert [(m.period, round(m.return_pct, 6), m.partial) for m in months] == [
        ("2026-01", 10.0, True),
        ("2026-02", -45.0, False),
        ("2026-03", 20.0, True),
    ]
    # 1.1 × 1.1 × 0.5 × 1.2 − 1 = −27.4 %
    assert [(y.period, round(y.return_pct, 6), y.partial) for y in years] == [
        ("2026", -27.4, True)
    ]
    assert months[1].start == date(2026, 2, 1)


def test_benchmark_returns_use_the_last_close_before_each_day():
    days = pd.to_datetime(["2026-03-03", "2026-03-04"])
    bench = pd.Series(
        [100.0, 110.0, 99.0],
        index=pd.to_datetime(["2026-02-27", "2026-03-02", "2026-03-04"]),
    )
    # 03-03 has no close: 110 carried → 0 %; 03-04: 99 / 110 − 1 = −10 %
    assert benchmark_returns(bench, days).tolist() == pytest.approx([0.0, -0.1])


def test_drawdowns_by_hand():
    days = pd.to_datetime(
        ["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06"]
    )
    # Equity 1.1, 0.55, 0.825, 1.155, 1.0395: −50 % from 03-02, back above on
    # 03-05; then −10 % from 03-05, not recovered.
    returns = pd.Series([0.1, -0.5, 0.5, 0.4, -0.1], index=days)

    result = drawdowns(returns, date(2026, 3, 2))

    assert result.max_pct == pytest.approx(-50)
    assert result.current_pct == pytest.approx(-10)
    first, second = result.episodes
    assert (first.peak_date, first.trough_date, first.recovery_date) == (
        date(2026, 3, 2),
        date(2026, 3, 3),
        date(2026, 3, 5),
    )
    assert (first.depth_pct, first.days_to_trough, first.days_to_recover) == (
        pytest.approx(-50),
        1,
        3,
    )
    assert (second.peak_date, second.recovery_date, second.days_to_recover) == (
        date(2026, 3, 5),
        None,
        None,
    )
    assert second.depth_pct == pytest.approx(-10)
    assert result.underwater.tolist() == pytest.approx([0, -50, -25, 0, -10])


def test_drawdown_from_the_period_start():
    days = pd.to_datetime(["2026-03-02", "2026-03-03"])
    result = drawdowns(pd.Series([-0.2, 0.1], index=days), date(2026, 3, 1))

    (episode,) = result.episodes
    assert episode.peak_date == date(2026, 3, 1)
    assert episode.depth_pct == pytest.approx(-20)
    assert episode.recovery_date is None


def test_currency_effect_is_the_profit_at_a_constant_local_price():
    # 3 shares at a constant $10; EUR per USD 0.90, 0.95, 0.92 → closes 9.0, 9.5, 9.2
    rate = closes([0.90, 0.95, 0.92])
    series, assets = daily_series_by_asset(
        [trade(TransactionType.BUY, 1, 3, 27, D1)], {1: rate * 10}, D3
    )

    effect = currency_effect(assets[1], rate)

    # 3 × 10 × (0.95 − 0.90) + 3 × 10 × (0.92 − 0.95) = 1.5 − 0.9
    assert effect == pytest.approx(0.6)
    assert effect == pytest.approx(period_summary(series)["profit"])
    # From D3 only the last day's −0.9 counts
    assert currency_effect(assets[1], rate, D3) == pytest.approx(-0.9)


def test_compute_daily_returns_unchanged_by_the_breakdown(two_assets):
    series, _ = two_assets
    assert compute_daily_returns(series, 0.0).tolist() == pytest.approx(
        [0.0, 0.05, 2000 / 2100 - 1, 0.1]
    )


@pytest.mark.asyncio
async def test_service_reports_insight_for_a_foreign_holding(test_db, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from core.database.models import Asset, Portfolio, Transaction, User
    from core.database.models.asset import AssetType
    from modules.analytics.calculations import PortfolioCalculationService

    user = User(email="insight@example.com", username="insight", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P", currency="EUR")
    asset = Asset(
        symbol="USA", name="US Co", asset_type=AssetType.EQUITY, user_id=user.id
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    bought = datetime.now(timezone.utc) - timedelta(days=20)
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("3"),
            price=Decimal("10"),
            total_amount=Decimal("30"),
            currency="USD",
            transaction_date=bought,
        )
    )
    test_db.commit()

    days = pd.bdate_range(bought.date(), periods=3)
    before = days.insert(0, days[0] - pd.Timedelta(days=3))
    # $10 flat; EUR per USD 0.90, 0.95, 0.92 → worth 27, 28.5, 27.6: all currency
    histories = {
        "USA": pd.Series([10.0, 10.0, 10.0], index=days),
        "USDEUR=X": pd.Series([0.90, 0.90, 0.95, 0.92], index=before),
        "EUNL.DE": pd.Series([100.0, 100.0, 110.0, 121.0], index=before),
    }
    service = PortfolioCalculationService(test_db)

    async def history(symbol):
        return {
            "close": histories[symbol],
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    async def info(symbol):
        return {"long_name": "MSCI World", "currency": "EUR"}

    monkeypatch.setattr(service.market_data_service, "get_daily_history", history)
    monkeypatch.setattr(service.market_data_service, "get_ticker_info", info)

    result = await service.get_performance_insight(portfolio.id, user.id, "inception")

    (holding,) = result["contributions"]
    assert holding["symbol"] == "USA"
    assert holding["quote_currency"] == "USD"
    assert holding["profit"] == pytest.approx(0.6)
    assert holding["currency_effect"] == pytest.approx(0.6)
    assert holding["contribution_pp"] == pytest.approx(result["twr_pct"])
    assert result["currency_effect"]["by_currency"] == [
        {"currency": "USD", "effect": pytest.approx(0.6)}
    ]
    assert result["timing"]["timing_effect"] == pytest.approx(0, abs=1e-9)
    # Benchmark: 0 %, +10 %, +10 % on the portfolio's days
    (year,) = result["years"]
    assert year["benchmark_pct"] == pytest.approx(21.0)
    assert year["return_pct"] == pytest.approx((27.6 / 27 - 1) * 100)
    assert result["benchmark"]["symbol"] == "EUNL.DE"
    assert result["drawdown"]["max_pct"] == pytest.approx((27.6 / 28.5 - 1) * 100)
    assert [p["drawdown_pct"] for p in result["drawdown"]["points"]][0] == 0
