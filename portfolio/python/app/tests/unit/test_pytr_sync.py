"""A portfolio linked to the Trade Republic export (pytr CSV that Bachat refreshes)."""

from decimal import Decimal

import pandas as pd
import pytest

from config import settings
from core.database.models import Asset, BrokerConnection, Portfolio, Transaction, User
from core.database.models.asset import AssetType
from core.database.models.portfolio import PortfolioAsset
from core.errors import DomainError
from core.schemas.account_statements import InstrumentResolution
from core.services.isin_resolver import IsinResolver
from core.services.market_data_service import MarketDataService
from modules.broker_sync import PytrSyncService
from modules.broker_sync import fetch as fetch_module
from modules.broker_sync.fetch import TradeRepublicFetchService, run_fetch
from modules.broker_sync.trade_republic import (
    LoginCheck,
    PendingLogin,
    ReauthRequiredError,
    Refreshed,
    override_trade_republic_client,
)
from modules.portfolios.service import PortfolioService

HEADER = "Date;Type;Value;Note;ISIN;Shares;Fees;Taxes;ISIN2;Shares2\n"
ROWS = [
    "2025-01-02T09:00:00;Buy;-1001;Lucid Group;US5494981039;100;1;;;\n",
    "2025-09-02T06:57:05;Swap;0;Lucid Group;US5494981039;100.0;;;LUCID GROUP INC. NEW O.N.;10.0\n",
    "2025-10-01T10:00:00;Sell;1499;Lucid Group;US5494982029;10;1;100;;\n",
    "2025-03-01T10:00:00;Buy;-501;Knock-out;DE000HM46ZS7;10;1;;;\n",
    "2024-06-03T17:07:26;Deposit;200;Jane Doe;;;;;;\n",
]


@pytest.fixture
def book(test_db, tmp_path, monkeypatch):
    user = User(email="tr@example.com", username="tr", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="TR", currency="EUR")
    asset = Asset(
        symbol="CH2.F",
        name="Lucid",
        asset_type=AssetType.EQUITY,
        user_id=user.id,
        currency="EUR",
        isin="US5494981039",
    )
    test_db.add_all([portfolio, asset])
    test_db.commit()

    export = tmp_path / "account_transactions.csv"
    export.write_text(HEADER + "".join(ROWS))
    monkeypatch.setattr(settings, "PYTR_EXPORT_PATH", str(export))
    monkeypatch.setattr(settings, "PYTR_SYNC_USERS", ["TR"])

    async def history(self, symbol):
        return {
            "close": pd.Series(dtype=float),
            "splits": pd.Series({pd.Timestamp("2025-09-02"): 0.1}),
            "dividends": pd.Series(dtype=float),
        }

    async def no_price(self, symbol):
        return None

    async def info(self, symbol):
        return {"name": "Knock-out", "currency": "EUR", "quote_type": "EQUITY"}

    async def unmatched(self, instruments, user_id, currency="EUR"):
        return [
            InstrumentResolution(isin=i.isin, status="unmatched") for i in instruments
        ]

    monkeypatch.setattr(MarketDataService, "get_daily_history", history)
    monkeypatch.setattr(MarketDataService, "get_current_price", no_price)
    monkeypatch.setattr(MarketDataService, "get_ticker_info", info)
    monkeypatch.setattr(IsinResolver, "resolve", unmatched)
    return user, portfolio, asset, export


@pytest.mark.asyncio
async def test_sync_imports_and_follows_an_isin_change(test_db, book):
    user, portfolio, asset, _ = book
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)

    report = await sync.sync(portfolio)

    assert report["created"] == 3
    assert [u["isin"] for u in report["trade_priced"]] == ["DE000HM46ZS7"]
    assert report["not_imported"]
    rows = test_db.query(Transaction).filter_by(portfolio_id=portfolio.id).all()
    assert len({r.asset_id for r in rows}) == 2
    holding = (
        test_db.query(PortfolioAsset)
        .filter_by(portfolio_id=portfolio.id, asset_id=asset.id)
        .one()
    )
    # 100 old shares are 10 after the 1:10 swap; all sold, before tax 1499 + 100 - 1001
    assert holding.quantity == 0
    assert holding.realized_pnl == Decimal("598")


@pytest.mark.asyncio
async def test_unchanged_file_is_skipped_and_new_rows_are_added(test_db, book):
    user, portfolio, _, export = book
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)
    await sync.sync(portfolio)

    assert (await sync.sync(portfolio))["created"] == 3  # same report, nothing re-read

    export.write_text(
        HEADER
        + "".join(ROWS)
        + "2025-11-01T10:00:00;Buy;-201;Lucid Group;US5494982029;10;1;;;\n"
    )
    report = await sync.sync(portfolio)
    assert report["created"] == 1
    assert report["already_imported"] == 3
    assert test_db.query(Transaction).filter_by(portfolio_id=portfolio.id).count() == 4


@pytest.mark.asyncio
async def test_unpriced_security_is_valued_from_its_trades(test_db, book):
    user, portfolio, _, _ = book
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)
    await sync.sync(portfolio)

    knock_out = test_db.query(Asset).filter_by(isin="DE000HM46ZS7").one()
    assert (knock_out.symbol, knock_out.price_source) == ("DE000HM46ZS7", "trades")
    holding = (
        test_db.query(PortfolioAsset)
        .filter_by(portfolio_id=portfolio.id, asset_id=knock_out.id)
        .one()
    )
    assert holding.quantity == 10
    assert holding.cost_basis_total == 501


@pytest.mark.asyncio
async def test_redemption_is_booked_as_a_sale(test_db, book):
    user, portfolio, _, export = book
    export.write_text(
        HEADER
        + "".join(ROWS)
        + "2025-06-17T02:37:49;Dividend;0.18;Knock-out;DE000HM46ZS7;10.0;;;;\n"
    )
    (export.parent / "portfolio.csv").write_text(
        "Name;ISIN;quantity;price;avgCost;netValue\nLucid;US5494982029;0;0;0;0\n"
    )
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)

    report = await sync.sync(portfolio)

    assert [r["isin"] for r in report["redeemed"]] == ["DE000HM46ZS7"]
    knock_out = test_db.query(Asset).filter_by(isin="DE000HM46ZS7").one()
    kinds = sorted(
        t.transaction_type.value
        for t in test_db.query(Transaction).filter_by(asset_id=knock_out.id)
    )
    assert kinds == ["buy", "sell"]
    holding = (
        test_db.query(PortfolioAsset)
        .filter_by(portfolio_id=portfolio.id, asset_id=knock_out.id)
        .one()
    )
    assert holding.quantity == 0
    assert holding.realized_pnl == Decimal("-500.82")


@pytest.mark.asyncio
async def test_a_dividend_on_a_position_sold_later_is_not_a_redemption(test_db, book):
    user, portfolio, _, export = book
    export.write_text(
        HEADER
        + "2025-01-02T09:00:00;Buy;-1001;Lucid Group;US5494981039;100;1;;;\n"
        + "2025-02-01T09:00:00;Dividend;5;Lucid Group;US5494981039;100;;;;\n"
        + "2025-03-01T09:00:00;Sell;1100;Lucid Group;US5494981039;100;1;;;\n"
    )
    (export.parent / "portfolio.csv").write_text(
        "Name;ISIN;quantity;price;avgCost;netValue\n"
    )
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)

    report = await sync.sync(portfolio)

    assert report["redeemed"] == []
    assert report["errors"] == []
    assert report["created"] == 3


@pytest.mark.asyncio
async def test_giving_a_ticker_switches_to_market_prices(test_db, book):
    user, portfolio, _, _ = book
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)
    await sync.sync(portfolio)

    await sync.map_instrument(portfolio, "DE000HM46ZS7", "KO.F")

    asset = test_db.query(Asset).filter_by(isin="DE000HM46ZS7").one()
    assert (asset.symbol, asset.price_source) == ("KO.F", None)


def test_link_rules(test_db, book, monkeypatch):
    user, portfolio, _, _ = book
    sync = PytrSyncService(test_db)
    portfolio.currency = "USD"
    with pytest.raises(DomainError):
        sync.link(portfolio, user, True)
    portfolio.currency = "EUR"
    monkeypatch.setattr(settings, "PYTR_SYNC_USERS", ["someone-else"])
    assert not sync.available_for(user)
    with pytest.raises(DomainError):
        sync.link(portfolio, user, True)


@pytest.mark.asyncio
async def test_series_prices_a_trade_priced_asset_from_its_fills(test_db, book):
    from modules.analytics.calculations import PortfolioCalculationService

    user, portfolio, _, _ = book
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)
    await sync.sync(portfolio)
    knock_out = test_db.query(Asset).filter_by(isin="DE000HM46ZS7").one()

    closes, splits, _, _ = await PortfolioCalculationService(
        test_db
    ).get_market_history([knock_out.id])

    assert closes[knock_out.id].to_dict() == {pd.Timestamp("2025-03-01"): 50.0}
    assert splits[knock_out.id] == []


@pytest.mark.asyncio
async def test_tax_refunds_are_imported_once_and_summed(test_db, book, monkeypatch):
    user, portfolio, _, export = book
    export.write_text(
        HEADER
        + "".join(ROWS)
        + "2025-04-01T10:00:00;Dividend;7.5;Knock-out;DE000HM46ZS7;10;;2.5;;\n"
        + "2025-10-02T23:00:00;Tax Refund;40;Steuerkorrektur;;;;;;\n"
        + "2026-01-05T10:00:00;Taxes;-3.5;ETF;IE00B4ND3602;;;3.5;;\n"
        + "2025-11-01T10:00:00;Interest;7.37;Zinsen;;;;2.63;;\n"
    )

    async def no_prices(self, symbols, fetch=True):
        return {}

    monkeypatch.setattr(MarketDataService, "get_current_prices", no_prices)
    monkeypatch.setattr(MarketDataService, "get_yesterdays_closes", no_prices)
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)
    report = await sync.sync(portfolio, force=True)
    again = await sync.sync(portfolio, force=True)

    assert (report["tax_entries_created"], again["tax_entries_created"]) == (2, 0)
    assert (
        "Account-level tax refund: not linked to a trade" not in report["not_imported"]
    )
    summary = await PortfolioService(test_db).get_portfolio_summary(
        portfolio.id, user.id
    )
    assert summary.total_realized_pnl == 598
    assert summary.total_dividends == 10
    assert summary.taxes_withheld == 102.5
    assert summary.tax_adjustments == -36.5
    assert summary.net_taxes_paid == 66
    assert summary.realized_after_tax == 542


class FakeTradeRepublic:
    def __init__(self, export, new_rows=""):
        self.export = export
        self.new_rows = new_rows
        self.checks = 0
        self.expired = False

    def start(self, phone, pin):
        return PendingLogin(
            state={"phone": phone, "process_id": "p1"}, needs_code=False, countdown=60
        )

    def check(self, state, code):
        self.checks += 1
        if self.checks == 1:
            return LoginCheck(confirmed=False)
        return LoginCheck(confirmed=True, session={"phone": state["phone"], "c": 1})

    def refresh(self, session, folder):
        if self.expired:
            raise ReauthRequiredError("The Trade Republic session ended: log in again")
        assert folder == self.export.parent
        self.export.write_text(self.export.read_text() + self.new_rows)
        return Refreshed(
            session={**session, "c": 2}, events=7, documents=1, positions=2
        )


@pytest.fixture
def trade_republic(test_db, book, monkeypatch):
    _, _, _, export = book
    fake = FakeTradeRepublic(
        export, "2025-11-03T10:00:00;Buy;-201;Knock-out;DE000HM46ZS7;4;1;;;\n"
    )
    override_trade_republic_client(fake)

    class Shared:
        def __getattr__(self, name):
            return getattr(test_db, name)

        def close(self):
            pass

    monkeypatch.setattr(fetch_module, "SessionLocal", Shared)
    yield fake
    override_trade_republic_client(None)


@pytest.mark.asyncio
async def test_login_then_fetch_imports_into_linked_portfolios(
    test_db, book, trade_republic
):
    user, portfolio, _, _ = book
    sync = PytrSyncService(test_db)
    sync.link(portfolio, user, True)
    await sync.sync(portfolio)
    service = TradeRepublicFetchService(test_db)

    started = await service.start_login(user, "+4915112345678", "1234")
    assert started == {"needs_code": False, "countdown": 60}
    stored = test_db.query(BrokerConnection).one()
    assert "4915112345678" not in stored.secret and "1234" not in stored.secret
    assert await service.confirm_login(user, None) is False
    assert await service.confirm_login(user, None) is True
    assert service.status(user)["connected"] is True

    service.begin_fetch(user)
    with pytest.raises(DomainError):
        service.begin_fetch(user)
    test_db.commit()
    await run_fetch(user.id)

    status = service.status(user)
    assert status["fetch_status"] == "succeeded"
    assert status["fetch_report"]["events"] == 7
    assert status["fetch_report"]["portfolios"] == [
        {
            "portfolio_id": portfolio.id,
            "name": "TR",
            "created": 1,
            "tax_entries_created": 0,
            "failed": 0,
        }
    ]
    knock_out = test_db.query(Asset).filter_by(isin="DE000HM46ZS7").one()
    holding = (
        test_db.query(PortfolioAsset)
        .filter_by(portfolio_id=portfolio.id, asset_id=knock_out.id)
        .one()
    )
    assert holding.quantity == 14


@pytest.mark.asyncio
async def test_an_ended_session_asks_for_a_new_login(test_db, book, trade_republic):
    user, _, _, _ = book
    service = TradeRepublicFetchService(test_db)
    await service.start_login(user, "+4915112345678", "1234")
    await service.confirm_login(user, None)
    await service.confirm_login(user, None)
    trade_republic.expired = True

    service.begin_fetch(user)
    test_db.commit()
    await run_fetch(user.id)

    status = service.status(user)
    assert status["fetch_status"] == "failed"
    assert status["session_expired"] is True and status["connected"] is False
    assert "log in again" in status["fetch_report"]["error"]
    with pytest.raises(DomainError):
        service.begin_fetch(user)


def test_fetch_needs_a_login(test_db, book):
    user, _, _, _ = book
    with pytest.raises(DomainError, match="Log in"):
        TradeRepublicFetchService(test_db).begin_fetch(user)
