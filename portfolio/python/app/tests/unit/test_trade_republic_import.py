"""Trade Republic statement parsing and bulk import."""

from decimal import Decimal

import pandas as pd
import pytest

from core.database.models import Asset, Portfolio, Transaction, User
from core.database.models.asset import AssetType
from core.schemas.account_statements import BulkTransactionItem
from core.services.account_statement_service import AccountStatementService
from core.services.parsers.trade_republic import TradeRepublicParser

STATEMENT = """UMSATZÜBERSICHT
DATUM TYP BESCHREIBUNG ZAHLUNGSEINGANG ZAHLUNGSAUSGANG SALDO
01 Jan. 2025 Überweisung Incoming transfer from Jane Doe 2.000,00 € 2.000,00 €
02 Jan. 2025 Handel Buy trade US0378331005 Apple Inc., quantity: 2 301,00 € 1.699,00 €
03 Jan. 2025 Handel Savings plan execution IE00B4L5Y983 iShares Core MSCI World,
quantity: 1,5 150,00 € 1.549,00 €
10 Feb. 2025 Erträge Cash Dividend for ISIN US0378331005 0,37 € 1.549,37 €
11 Feb. 2025 Steuern Tax Optimisation 0,05 € 1.549,42 €
01 März 2025 Zinszahlung Your interest payment 4,20 € 1.553,62 €
05 März 2025 Kartentransaktion Coffee Shop 3,50 € 1.550,12 €
06 März 2025 Handel Sell trade US0378331005 Apple Inc., quantity: 1 159,00 € 1.709,12 €
07 März 2025 Handel Something unexpected 10,00 € 1.719,12 €
BARMITTELÜBERSICHT
"""


@pytest.fixture
def parsed():
    return TradeRepublicParser()._extract_transactions(STATEMENT)


def test_trades_and_dividends_are_imported_in_eur(parsed):
    transactions, _, warnings = parsed

    assert warnings == []
    assert [
        (t.transaction_date, t.transaction_type.value, t.symbol) for t in transactions
    ] == [
        ("2025-01-02", "buy", "US0378331005"),
        ("2025-01-03", "buy", "IE00B4L5Y983"),
        ("2025-02-10", "dividend", "US0378331005"),
        ("2025-03-06", "sell", "US0378331005"),
    ]
    assert {t.currency for t in transactions} == {"EUR"}


def test_trade_fee_is_split_from_the_price(parsed):
    buy, savings_plan, _, sell = parsed[0]

    assert (buy.quantity, buy.price, buy.fees, buy.total_amount) == (
        Decimal("2"),
        Decimal("150"),
        Decimal("1"),
        Decimal("301.00"),
    )
    assert (savings_plan.quantity, savings_plan.price, savings_plan.fees) == (
        Decimal("1.5"),
        Decimal("100"),
        Decimal("0"),
    )
    assert (sell.price, sell.fees, sell.total_amount) == (
        Decimal("160"),
        Decimal("1"),
        Decimal("159.00"),
    )


def test_dividend_keeps_its_cash_amount(parsed):
    dividend = parsed[0][2]

    assert dividend.total_amount == Decimal("0.37")
    assert (dividend.quantity, dividend.price) == (Decimal("0"), Decimal("0"))


def test_cash_rows_and_unknown_trades_are_skipped_with_a_reason(parsed):
    skipped = parsed[1]

    assert [(s.kind, s.amount) for s in skipped] == [
        ("Überweisung", Decimal("2000.00")),
        ("Steuern", Decimal("0.05")),
        ("Zinszahlung", Decimal("4.20")),
        ("Kartentransaktion", Decimal("3.50")),
        ("Handel", Decimal("10.00")),
    ]
    assert all(s.reason for s in skipped)


REAL_LAYOUT = """
01 Juli 2025 - 30 Sept. 2025
UMSATZÜBERSICHT
DATUM TYP BESCHREIBUNG ZAHLUNGSEINGANG ZAHLUNGSAUSGANG SALDO
01 Juli
2025 Handel Buy trade US0378331005 Apple Inc., quantity: 2 301,00 € 1.699,00 €
02 Juli
2025 Handel Savings plan execution IE00B4L5Y983 iShares Core, quantity: 0.056721 10,00 € 1.689,00 €
03 Juli
2025 Erträge Cash Dividend for ISIN US0378331005 0,37 € 1.689,37 €
29 Aug. 2025 Überweisung Incoming transfer 2.000,00 € 3.689,37 € 01 Sept. 2025 Handel Sell trade US0378331005 Apple Inc., quantity: 1 159,00 € 3.848,37 €TRADE REPUBLIC BANK GMBH
BARMITTELÜBERSICHT
"""


def test_real_statement_layout_keeps_every_row():
    parser = TradeRepublicParser()
    transactions, skipped, warnings = parser._extract_transactions(REAL_LAYOUT)
    period = parser._extract_statement_period(REAL_LAYOUT)

    assert warnings == []
    assert (period.start_date, period.end_date) == ("2025-07-01", "2025-09-30")
    assert [
        (t.transaction_date, t.transaction_type.value, t.symbol) for t in transactions
    ] == [
        ("2025-07-01", "buy", "US0378331005"),
        ("2025-07-02", "buy", "IE00B4L5Y983"),
        ("2025-07-03", "dividend", "US0378331005"),
        ("2025-09-01", "sell", "US0378331005"),
    ]
    savings = transactions[1]
    assert savings.quantity == Decimal("0.056721")
    assert savings.fees == Decimal("0")
    assert savings.price == Decimal("10.00") / Decimal("0.056721")
    assert [(s.kind, s.amount) for s in skipped] == [
        ("Überweisung", Decimal("2000.00"))
    ]


def test_parse_reports_counts(monkeypatch):
    parser = TradeRepublicParser()
    monkeypatch.setattr(
        "core.services.parsers.trade_republic.pypdf.PdfReader",
        lambda _: type(
            "R", (), {"pages": [type("P", (), {"extract_text": lambda s: STATEMENT})()]}
        )(),
    )

    result = parser.parse(b"%PDF")

    assert result.metadata.total_transactions == 4
    assert result.metadata.total_skipped == 5


@pytest.fixture
def portfolio(test_db):
    user = User(email="tr@example.com", username="tr", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="TR", currency="EUR")
    asset = Asset(
        symbol="APC.F",
        name="Apple",
        asset_type=AssetType.EQUITY,
        currency="EUR",
        user_id=user.id,
    )
    test_db.add_all([portfolio, asset])
    test_db.commit()
    return portfolio, asset


def _item(asset, **fields):
    return BulkTransactionItem(
        transaction_date="2025-01-02", asset_id=asset.id, **fields
    )


@pytest.mark.asyncio
async def test_bulk_create_keeps_dividend_amount_taxes_and_foreign_cash(
    test_db, portfolio, monkeypatch
):
    portfolio, asset = portfolio
    service = AccountStatementService(test_db)

    async def rates(quote, portfolio_currency):
        return pd.Series([1.0], index=pd.to_datetime(["2020-01-01"]))

    monkeypatch.setattr(
        service.portfolio_service.market_data_service, "get_fx_rates", rates
    )

    created, summary = await service.create_bulk_transactions(
        portfolio.id,
        [
            _item(
                asset,
                transaction_type="buy",
                quantity=Decimal("2"),
                price=Decimal("150"),
                fees=Decimal("1"),
                total_amount=Decimal("301"),
            ),
            _item(
                asset,
                transaction_type="dividend",
                quantity=Decimal("0"),
                price=Decimal("0"),
                total_amount=Decimal("0.37"),
                taxes=Decimal("0.13"),
                currency="eur",
            ),
            _item(
                asset,
                transaction_type="dividend",
                quantity=Decimal("0"),
                price=Decimal("0"),
                total_amount=Decimal("1"),
                currency="USD",
            ),
        ],
        portfolio.user_id,
    )

    assert (summary.total_created, summary.total_failed) == (3, 0)
    rows = test_db.query(Transaction).order_by(Transaction.id).all()
    assert [(r.transaction_type.value, r.total_amount, r.currency) for r in rows] == [
        ("buy", Decimal("301"), "EUR"),
        ("dividend", Decimal("0.37"), "EUR"),
        ("dividend", Decimal("1"), "USD"),
    ]
    assert rows[1].taxes == Decimal("0.13")


@pytest.mark.asyncio
async def test_bulk_create_rejects_an_empty_dividend(test_db, portfolio):
    portfolio, asset = portfolio
    service = AccountStatementService(test_db)

    _, summary = await service.create_bulk_transactions(
        portfolio.id,
        [
            _item(
                asset,
                transaction_type="dividend",
                quantity=Decimal("0"),
                price=Decimal("0"),
                total_amount=Decimal("0"),
            )
        ],
        portfolio.user_id,
    )

    assert (summary.total_created, summary.total_failed) == (0, 1)
    assert "Dividend amount must be positive" in summary.errors[0]


@pytest.mark.parametrize(
    ("text", "iso"),
    [
        ("02 Jan. 2025", "2025-01-02"),
        ("28 Feb. 2025", "2025-02-28"),
        ("06 März 2025", "2025-03-06"),
        ("01 Apr. 2025", "2025-04-01"),
        ("15 Mai 2025", "2025-05-15"),
        ("30 Juni 2025", "2025-06-30"),
        ("04 Juli 2025", "2025-07-04"),
        ("01 Aug. 2025", "2025-08-01"),
        ("09 Sept. 2025", "2025-09-09"),
        ("31 Okt. 2025", "2025-10-31"),
        ("11 Nov. 2025", "2025-11-11"),
        ("24 Dez. 2025", "2025-12-24"),
        ("31 Feb. 2025", ""),
        ("02 Foo 2025", ""),
    ],
)
def test_german_dates(text, iso):
    assert TradeRepublicParser()._parse_german_date(text) == iso
