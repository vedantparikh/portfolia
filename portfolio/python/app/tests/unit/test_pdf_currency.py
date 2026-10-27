"""PDF totals stay in one currency and print that currency's code."""

from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from core.database.models.transaction import TransactionType
from core.database.redis_client import RedisClient
from core.schemas.pdf_export import ExportedTransactionData
from core.services.transaction_pdf_export_service import (
    TransactionPDFService,
    format_money,
)


def _row(**overrides) -> ExportedTransactionData:
    values = {
        "id": 1,
        "portfolio_name": "Book",
        "asset_symbol": "SAP",
        "asset_name": "SAP",
        "transaction_type": TransactionType.BUY,
        "quantity": Decimal("1"),
        "price": Decimal("10"),
        "total_amount": Decimal("10"),
        "fees": Decimal("1"),
        "taxes": Decimal("0"),
        "transaction_date": datetime(2024, 1, 2, tzinfo=timezone.utc),
        "settlement_date": None,
        "notes": None,
        "reference_number": None,
        "currency": "EUR",
        "portfolio_currency": "EUR",
    }
    values.update(overrides)
    return ExportedTransactionData(**values)


def _stats(rows):
    service = TransactionPDFService.__new__(TransactionPDFService)
    return service._calculate_summary_stats(rows)


def test_one_currency_fills_the_flat_totals():
    stats = _stats(
        [
            _row(),
            _row(
                id=2,
                transaction_type=TransactionType.SELL,
                total_amount=Decimal("4"),
            ),
        ]
    )
    assert stats.currency == "EUR"
    assert stats.total_buy_volume == Decimal("10")
    assert stats.total_sell_volume == Decimal("4")
    assert stats.net_flow == Decimal("-6")
    assert stats.volumes[0].fees == Decimal("2")
    assert format_money(stats.total_buy_volume, stats.currency) == "EUR 10.00"


def test_two_currencies_are_not_added_together():
    stats = _stats(
        [
            _row(),
            _row(id=2, currency="USD", total_amount=Decimal("7"), fees=Decimal("0")),
        ]
    )
    assert stats.currency is None
    assert stats.total_buy_volume == Decimal("0")
    assert {volume.currency: volume.buy_volume for volume in stats.volumes} == {
        "EUR": Decimal("10"),
        "USD": Decimal("7"),
    }


def test_format_money_uses_the_currency_code():
    assert format_money(Decimal("1.5"), "usd") == "USD 1.50"
    assert "$" not in format_money(Decimal("1"), "USD")


async def test_amounts_convert_into_the_portfolio_currency(monkeypatch):
    rates = {"USD": pd.Series([0.9], index=pd.to_datetime(["2024-01-01"]))}

    async def fake_load(market, portfolio, currencies, *, strict=True):
        assert portfolio == "EUR"
        assert "USD" in currencies
        return rates

    monkeypatch.setattr(
        "core.services.transaction_pdf_export_service.load_rates", fake_load
    )
    service = TransactionPDFService.__new__(TransactionPDFService)
    converted = await service._convert_to_portfolio_currency(
        [_row(currency="USD", portfolio_currency="EUR")]
    )
    assert converted[0].currency == "EUR"
    assert converted[0].total_amount == Decimal("9.0")
    assert converted[0].fees == Decimal("0.9")


async def test_a_missing_rate_stays_in_its_own_currency(monkeypatch):
    async def fake_load(market, portfolio, currencies, *, strict=True):
        return {}

    monkeypatch.setattr(
        "core.services.transaction_pdf_export_service.load_rates", fake_load
    )
    service = TransactionPDFService.__new__(TransactionPDFService)
    converted = await service._convert_to_portfolio_currency(
        [_row(currency="USD", portfolio_currency="EUR", total_amount=Decimal("10"))]
    )
    assert converted[0].currency == "USD"
    assert converted[0].total_amount == Decimal("10")


def test_redis_client_is_not_a_singleton_and_does_not_pickle():
    assert type(RedisClient) is type
    assert not hasattr(RedisClient, "set_raw")
    assert not hasattr(RedisClient, "get_raw")
