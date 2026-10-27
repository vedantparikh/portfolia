"""Golden tests for FX. Every expected number is worked out by hand."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
import pytest

from core.database.models import Asset, Portfolio, Transaction, TransactionType, User
from core.database.models.asset import AssetType
from core.domain.fx import (
    MissingFxError,
    canonical_currency,
    convert_amount,
    convert_closes,
    convert_series,
    convert_trades,
    rate_on,
)
from core.domain.positions import Trade
from core.services.market_data_service import MarketDataService
from modules.analytics.calculations import PortfolioCalculationService


def _series(days, values):
    return pd.Series(values, index=pd.to_datetime(days))


def test_canonical_currency_scales_minor_units_once():
    assert canonical_currency("GBp") == ("GBP", Decimal(100))
    assert canonical_currency("GBX") == ("GBP", Decimal(100))
    assert canonical_currency("ILA") == ("ILS", Decimal(100))
    assert canonical_currency("gbp") == ("GBP", Decimal(1))
    assert canonical_currency("EUR") == ("EUR", Decimal(1))


def test_convert_series_uses_the_rate_on_the_day_and_carries_it_forward():
    prices = _series(["2024-01-02", "2024-01-03", "2024-01-04"], [100, 100, 100])
    rates = _series(["2024-01-02", "2024-01-04"], [0.9, 0.99])

    converted = convert_series(prices, rates, "USD", "EUR")

    assert list(converted.round(10)) == [90.0, 90.0, 99.0]


def test_convert_series_raises_when_the_rate_starts_after_the_price():
    prices = _series(["2024-01-02"], [100])
    rates = _series(["2024-01-03"], [0.9])

    with pytest.raises(MissingFxError, match="USD to EUR on or before 2024-01-02"):
        convert_series(prices, rates, "USD", "EUR")


def test_rate_on_uses_the_latest_rate_on_or_before_the_day():
    rates = _series(["2024-01-02", "2024-01-05"], [0.9, 1.1])

    assert rate_on(rates, date(2024, 1, 4), "USD", "EUR") == Decimal("0.9")
    assert rate_on(rates, date(2024, 1, 5), "USD", "EUR") == Decimal("1.1")


def test_gbp_pence_become_pounds_without_a_rate():
    closes = _series(["2024-01-02"], [25000])

    converted = convert_closes(closes, "GBp", "GBP", {})

    assert list(converted) == [250.0]


def test_same_currency_series_is_the_same_object():
    closes = _series(["2024-01-02"], [100])

    assert convert_closes(closes, "EUR", "EUR", {}) is closes


def test_cash_already_in_the_portfolio_currency_is_not_converted():
    amount = convert_amount(
        Decimal("900"),
        "EUR",
        "EUR",
        date(2024, 1, 2),
        {"USD": _series(["2024-01-02"], [0.5])},
    )

    assert amount == Decimal("900")


def test_usd_cash_converts_at_the_trade_date():
    rates = {"USD": _series(["2024-01-02", "2024-01-04"], [0.9, 0.99])}

    assert convert_amount(
        Decimal("1000"), "USD", "EUR", date(2024, 1, 3), rates
    ) == Decimal("900.0")


def test_convert_trades_scales_price_and_cash_together():
    trade = Trade(
        id=7,
        asset_id=1,
        transaction_type=TransactionType.BUY,
        transaction_date=date(2024, 1, 2),
        quantity=Decimal("10"),
        price=Decimal("100"),
        total_amount=Decimal("1000"),
    )
    rates = {"USD": _series(["2024-01-02"], [0.9])}

    converted = convert_trades([trade], {7: "USD"}, "EUR", rates)

    assert converted[0].total_amount == Decimal("900.0")
    assert converted[0].price == Decimal("90.0")
    assert converted[0].quantity == Decimal("10")


def test_convert_trades_leaves_portfolio_currency_cash_unchanged():
    trade = Trade(
        id=7,
        asset_id=1,
        transaction_type=TransactionType.BUY,
        transaction_date=date(2024, 1, 2),
        quantity=Decimal("10"),
        price=Decimal("90"),
        total_amount=Decimal("900"),
    )

    converted = convert_trades([trade], {7: "EUR"}, "EUR", {})

    assert converted[0] is trade


def _book(
    test_db, portfolio_currency, asset_currency, cash_currency, total, price, qty=10
):
    user = User(email="fx-series@example.com", username="fxseries", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P", currency=portfolio_currency)
    asset = Asset(
        symbol="AAPL",
        name="Apple",
        asset_type=AssetType.EQUITY,
        currency=asset_currency,
        user_id=user.id,
    )
    test_db.add_all([portfolio, asset])
    test_db.flush()
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal(qty),
            price=Decimal(price),
            total_amount=Decimal(total),
            currency=cash_currency,
            transaction_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
    )
    test_db.commit()
    return portfolio


def _service(test_db, monkeypatch, closes, rates=None):
    service = PortfolioCalculationService(test_db)

    async def history(symbol):
        return {
            "close": closes,
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    async def fx(quote, portfolio):
        if rates is None:
            raise MissingFxError(quote, portfolio)
        return rates

    monkeypatch.setattr(service.market_data_service, "get_daily_history", history)
    monkeypatch.setattr(service.market_data_service, "get_fx_rates", fx)
    return service


def _closes(values):
    return pd.Series(values, index=pd.to_datetime(["2024-01-02", "2024-01-03"]))


@pytest.mark.asyncio
async def test_flat_share_price_and_a_ten_percent_fx_rise(test_db, monkeypatch):
    # 10 shares bought for 1000 USD. EUR per USD goes from 0.90 to 0.99. Price stays 100.
    portfolio = _book(test_db, "EUR", "USD", "USD", "1000", "100")
    rates = pd.Series([0.9, 0.99], index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    service = _service(test_db, monkeypatch, _closes([100, 100]), rates)

    result = await service.get_performance_series(
        portfolio.id, portfolio.user_id, "inception"
    )

    assert [p["value"] for p in result["points"]] == pytest.approx([900, 990])
    assert result["points"][0]["invested"] == pytest.approx(900)


@pytest.mark.asyncio
async def test_eur_cash_is_not_converted_again(test_db, monkeypatch):
    # Statement cash is already 900 EUR. Only the 100 USD close is converted at 0.90.
    portfolio = _book(test_db, "EUR", "USD", "EUR", "900", "90")
    rates = pd.Series([0.9, 0.9], index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    service = _service(test_db, monkeypatch, _closes([100, 100]), rates)

    result = await service.get_performance_series(
        portfolio.id, portfolio.user_id, "inception"
    )

    assert [p["value"] for p in result["points"]] == pytest.approx([900, 900])
    assert [p["invested"] for p in result["points"]] == pytest.approx([900, 900])


@pytest.mark.asyncio
async def test_missing_fx_is_an_error_not_an_unconverted_value(test_db, monkeypatch):
    portfolio = _book(test_db, "EUR", "USD", "USD", "1000", "100")
    service = _service(test_db, monkeypatch, _closes([100, 100]), rates=None)
    result = await service.get_performance_series(
        portfolio.id, portfolio.user_id, "inception"
    )

    assert result["points"] == []
    assert "No exchange rate from USD to EUR" in result["error"]


@pytest.mark.asyncio
async def test_pence_prices_are_scaled_to_pounds(test_db, monkeypatch):
    portfolio = _book(test_db, "GBP", "GBp", "GBP", "2500", "250")
    service = _service(test_db, monkeypatch, _closes([25000, 25000]))

    result = await service.get_performance_series(
        portfolio.id, portfolio.user_id, "inception"
    )

    assert [p["value"] for p in result["points"]] == [2500, 2500]


@pytest.mark.asyncio
async def test_fx_rate_inverts_the_reverse_yahoo_pair(monkeypatch):
    service = MarketDataService()

    async def history(symbol):
        if symbol == "USDEUR=X":
            return None
        assert symbol == "EURUSD=X"
        return {
            "close": pd.Series([1.25], index=pd.to_datetime(["2024-01-02"])),
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    monkeypatch.setattr(service, "get_daily_history", history)
    rates = await service.get_fx_rates("USD", "EUR")

    assert float(rates.iloc[0]) == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_fx_rate_raises_when_neither_pair_exists(monkeypatch):
    service = MarketDataService()

    async def history(symbol):
        return None

    monkeypatch.setattr(service, "get_daily_history", history)
    with pytest.raises(MissingFxError, match="USD to EUR"):
        await service.get_fx_rates("USD", "EUR")
