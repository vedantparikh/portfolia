"""German tax golden tests (core/domain/german_tax.py), worked out by hand."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from core.database.models import TransactionType
from core.domain.german_tax import (
    SaleLot,
    held_fraction,
    open_lots,
    sale_lots,
    settle,
    sparerpauschbetrag,
    split_allowance,
    tax_rate_pct,
    vorabpauschale,
    vorabpauschale_credit,
    vorabpauschale_per_share,
)
from core.domain.positions import Trade

BUY, SELL, OUT = (
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.TRANSFER_OUT,
)


def trade(i, kind, day, quantity, total, taxes=0):
    return Trade(
        i, 1, kind, day, Decimal(quantity), Decimal(0), Decimal(total), Decimal(taxes)
    )


def test_rates_and_allowance():
    assert tax_rate_pct() == pytest.approx(26.375)
    # 25 % / (1 + 0.25 k) with Soli and church tax on it
    assert tax_rate_pct(9) == pytest.approx(1.145 / 4.09 * 100)
    assert tax_rate_pct(8) == pytest.approx(1.135 / 4.08 * 100)
    assert sparerpauschbetrag(2022) == 801
    assert sparerpauschbetrag(2023) == 1000
    assert sparerpauschbetrag(2023, joint=True) == 2000


def test_sales_close_fifo_lots_and_transfers_close_without_a_sale():
    trades = [
        trade(1, BUY, date(2025, 1, 10), 10, 1000),
        trade(2, BUY, date(2025, 3, 10), 10, 1200),
        trade(3, OUT, date(2025, 4, 1), 5, 0),
        # 1,490 received + 10 tax withheld = 1,500 before tax
        trade(4, SELL, date(2025, 6, 1), 12, 1490, 10),
    ]

    lots = sale_lots(trades)

    # 5 left of the first lot (cost 500), 7 of the second (cost 840)
    assert [(lot.bought_on, lot.quantity) for lot in lots] == [
        (date(2025, 1, 10), 5),
        (date(2025, 3, 10), 7),
    ]
    assert [lot.cost for lot in lots] == pytest.approx([500, 840])
    assert [lot.gain for lot in lots] == pytest.approx([625 - 500, 875 - 840])
    assert open_lots(trades, date(2025, 6, 1)) == {1: [(date(2025, 3, 10), 3)]}
    assert open_lots(trades, date(2025, 2, 1)) == {1: [(date(2025, 1, 10), 10)]}


def test_vorabpauschale_per_share_is_capped_by_the_gain_and_reduced_by_distributions():
    # Base 100 × 2.53 % × 0.7 = 1.771
    assert vorabpauschale_per_share(100, 110, 0, 2.53) == pytest.approx(1.771)
    assert vorabpauschale_per_share(100, 101, 0, 2.53) == pytest.approx(1.0)
    assert vorabpauschale_per_share(100, 95, 0, 2.53) == 0
    assert vorabpauschale_per_share(100, 110, 1.0, 2.53) == pytest.approx(0.771)
    assert vorabpauschale_per_share(100, 110, 5.0, 2.53) == 0
    assert vorabpauschale_per_share(100, 110, 0, -0.45) == 0


def test_shares_bought_during_the_year_count_from_their_month():
    assert held_fraction(date(2025, 3, 10), 2025) == pytest.approx(10 / 12)
    assert held_fraction(date(2025, 1, 31), 2025) == 1
    assert held_fraction(date(2024, 12, 1), 2025) == 1
    assert held_fraction(date(2026, 1, 2), 2025) == 0
    lots = [(date(2024, 5, 1), 10.0), (date(2025, 3, 10), 6.0)]
    # 10 × 1.2 + 6 × 1.2 × 10/12
    assert vorabpauschale(lots, 1.2, 2025) == pytest.approx(18)


def test_a_sale_deducts_the_vorabpauschalen_already_taxed():
    per_share = {2024: 0.5, 2025: 1.2}
    lot = SaleLot(1, date(2026, 2, 1), date(2024, 5, 1), 10, 1000, 1200)
    # 2024: 10 × 0.5 × 8/12; 2025: 10 × 1.2
    assert vorabpauschale_credit(lot, per_share) == pytest.approx(10 / 3 + 12)
    sold_in_2025 = SaleLot(1, date(2025, 12, 15), date(2024, 5, 1), 10, 1000, 1200)
    assert vorabpauschale_credit(sold_in_2025, per_share) == pytest.approx(10 / 3)


def test_settle_keeps_share_losses_in_their_pot():
    rate = 26.375
    # Other losses offset share gains
    a = settle(500, -200, 1000, rate)
    assert (a.income, a.allowance_used, a.allowance_left, a.tax) == (300, 300, 700, 0)
    # Share losses do not offset other income; they carry forward
    b = settle(-400, 1500, 1000, rate)
    assert (b.income, b.taxable, b.share_loss_carried) == (1500, 500, -400)
    assert b.tax == pytest.approx(131.875)
    c = settle(300, -500, 1000, rate)
    assert (c.income, c.other_loss_carried, c.share_loss_carried) == (0, -200, 0)
    d = settle(600, 0, 100, rate, share_loss_in=-400)
    assert (d.income, d.taxable) == (200, 100)
    assert d.tax == pytest.approx(26.375)
    e = settle(-100, -50, 1000, rate)
    assert (e.income, e.share_loss_carried, e.other_loss_carried) == (0, -100, -50)


def test_split_allowance_fills_the_largest_income_first():
    assert split_allowance({1: 700, 2: 500, 3: 0}, 1000) == {1: 700, 2: 300, 3: 0}
    assert split_allowance({1: 200}, 1000) == {1: 1000}
    assert split_allowance({1: 100, 2: 50}, 1000) == {1: 950, 2: 50}
    assert split_allowance({}, 1000) == {}


@pytest.fixture
def book(test_db, monkeypatch):
    """
    EUR: share S bought and sold at +300 in 2025 with a 50 dividend (13.19 tax),
    fund F 10 shares bought June 2024, worth 900 against a cost of 1,000 now.
    """
    from core.database.models import (
        Asset,
        Portfolio,
        TaxEntry,
        Transaction,
        User,
    )
    from core.database.models.asset import AssetType
    from modules.portfolios.service import PortfolioService

    user = User(email="tax@example.com", username="taxes", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="Broker", currency="EUR")
    usd = Portfolio(user_id=user.id, name="US", currency="USD")
    s = Asset(
        symbol="SSS",
        name="S AG",
        asset_type=AssetType.EQUITY,
        user_id=user.id,
        currency="EUR",
    )
    f = Asset(
        symbol="FFF",
        name="F World",
        asset_type=AssetType.ETF,
        user_id=user.id,
        currency="EUR",
    )
    test_db.add_all([portfolio, usd, s, f])
    test_db.flush()

    def add(asset, kind, day, quantity, total, taxes="0"):
        test_db.add(
            Transaction(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                transaction_type=kind,
                quantity=Decimal(quantity),
                price=Decimal(total) / Decimal(quantity),
                total_amount=Decimal(total),
                taxes=Decimal(taxes),
                fees=Decimal(0),
                currency="EUR",
                transaction_date=datetime(*day, 12, tzinfo=timezone.utc),
            )
        )

    add(f, TransactionType.BUY, (2024, 6, 3), "10", "1000")
    add(s, TransactionType.BUY, (2025, 2, 3), "10", "1000")
    add(s, TransactionType.DIVIDEND, (2025, 5, 2), "10", "36.81", "13.19")
    add(s, TransactionType.SELL, (2025, 6, 2), "10", "1300")
    test_db.add(
        TaxEntry(
            portfolio_id=portfolio.id,
            entry_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
            amount=Decimal("2"),
            currency="EUR",
            description="Tax: F World (Acc)",
            source_key="t1",
        )
    )
    test_db.commit()

    closes = pd.Series(
        [90.0, 100.0, 110.0],
        index=pd.to_datetime(["2023-12-29", "2024-12-31", "2025-12-31"]),
    )

    async def history(self, symbol):
        return {
            "close": closes
            if symbol == "FFF"
            else pd.Series([100.0], index=pd.to_datetime(["2025-01-02"])),
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    async def holdings(self, portfolio_id):
        return [
            SimpleNamespace(
                asset_id=f.id,
                symbol="FFF",
                quantity=10.0,
                current_value=900.0,
                cost_basis_total=1000.0,
            )
        ]

    from core.services.market_data_service import MarketDataService

    monkeypatch.setattr(MarketDataService, "get_daily_history", history)
    monkeypatch.setattr(PortfolioService, "get_portfolio_holdings", holdings)
    return SimpleNamespace(portfolio=portfolio, usd=usd, user=user, s=s, f=f)


@pytest.mark.asyncio
async def test_service_settles_a_year_like_the_bank(test_db, book):
    from modules.analytics.german_tax import GermanTaxService

    service = GermanTaxService(test_db, today=date(2026, 10, 30))
    result = await service.year(book.portfolio, 2025, 100.0, False, 0.0)

    # 2024 Vorabpauschale, taxed January 2025: 90 × 2.29 % × 0.7 a share, 7/12 of the year, 70 % taxable
    vp_2024 = 90 * 0.0229 * 0.7 * 10 * 7 / 12
    s = result["settlement"]
    assert s["share_net"] == pytest.approx(300)
    assert s["other_net"] == pytest.approx(50 + vp_2024 * 0.7)
    assert s["income"] == pytest.approx(350 + vp_2024 * 0.7)
    assert s["allowance_used"] == 100
    assert s["tax"] == pytest.approx((250 + vp_2024 * 0.7) * 0.26375)
    assert s["withheld"] == pytest.approx(15.19)
    rows = {r["symbol"]: r for r in result["items"]}
    assert rows["SSS"]["kind"] == "share"
    assert rows["FFF"]["vorabpauschale"] == pytest.approx(vp_2024)
    assert [h["year"] for h in result["history"]] == [2024, 2025]
    assert result["history"][0]["income"] == 0
    # 2025 Vorabpauschale due January 2026: 100 × 2.53 % × 0.7 × 10 shares
    vp = result["vorabpauschale"]
    assert (vp["estimate"], vp["due"]) == (False, date(2026, 1, 2))
    assert vp["amount"] == pytest.approx(17.71)
    assert vp["taxable"] == pytest.approx(17.71 * 0.7)
    assert result["harvest"] == []


@pytest.mark.asyncio
async def test_service_finds_losses_worth_harvesting_this_year(test_db, book):
    from modules.analytics.german_tax import GermanTaxService

    service = GermanTaxService(test_db, today=date(2026, 10, 30))
    result = await service.year(book.portfolio, None, 0.0, False, 0.0)

    # 2026: only the 2025 Vorabpauschale (17.71, 70 % taxable); F's loss of 100 is 70 taxable
    assert result["year"] == 2026
    assert result["settlement"]["tax"] == pytest.approx(17.71 * 0.7 * 0.26375)
    (candidate,) = result["harvest"]
    assert (candidate["symbol"], candidate["kind"]) == ("FFF", "fund")
    assert candidate["taxable"] == pytest.approx(-70)
    assert candidate["tax_saved"] == pytest.approx(17.71 * 0.7 * 0.26375)
    # 2026 so far: start 110, still 110 → no Vorabpauschale
    assert result["vorabpauschale"]["estimate"] is True
    assert result["vorabpauschale"]["amount"] == 0

    split = await service.allowance([book.portfolio, book.usd], 2025, False)
    (row,) = split["portfolios"]
    assert row["income"] == pytest.approx(result["history"][1]["income"])
    assert row["suggested"] == 1000


def test_german_tax_routes_check_ownership_and_currency(client, test_db, book):
    from core.auth.dependencies import get_current_active_user
    from main import app

    app.dependency_overrides[get_current_active_user] = lambda: book.user
    try:
        base = "/api/v1/analytics/portfolios"
        ok = client.get(f"{base}/{book.portfolio.id}/tax/germany?year=2025")
        assert ok.status_code == 200
        assert ok.json()["settlement"]["share_net"] == pytest.approx(300)
        assert client.get(f"{base}/{book.usd.id}/tax/germany").status_code == 400
        assert client.get(f"{base}/999999/tax/germany").status_code == 404
        assert (
            client.get(f"{base}/{book.portfolio.id}/tax/germany?year=2001").status_code
            == 400
        )
        split = client.get("/api/v1/analytics/tax/germany/allowance?year=2025")
        assert [p["name"] for p in split.json()["portfolios"]] == ["Broker"]
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


def test_kinds_follow_the_asset_type_and_crypto_pairs_are_left_out():
    from core.database.models.asset import AssetType
    from modules.analytics.german_tax import kind_of

    def asset(kind, symbol="X"):
        return SimpleNamespace(asset_type=kind, symbol=symbol)

    assert kind_of(asset(AssetType.EQUITY)) == "share"
    assert kind_of(asset(AssetType.ETF)) == "fund"
    assert kind_of(asset(AssetType.MUTUALFUND)) == "fund"
    assert kind_of(asset(AssetType.OTHER)) == "other"
    assert kind_of(asset(AssetType.CRYPTOCURRENCY)) is None
    assert kind_of(asset(AssetType.OTHER, "COIN123-USD")) is None
