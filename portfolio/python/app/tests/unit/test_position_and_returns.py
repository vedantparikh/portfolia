"""
Unit tests for the core money math: transaction totals, FIFO positions,
cash-flow-adjusted returns, TWR, CAGR, drawdown and XIRR cash flows.

These are pure calculations: no database, Redis or network.
"""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest
from pydantic import ValidationError

from core.database.models import Transaction, TransactionType
from core.schemas.portfolio import (
    TransactionCreate,
    TransactionUpdate,
    check_transaction_numbers,
)
from modules.analytics.calculations import (
    PortfolioCalculationService,
    compute_daily_returns,
)
from modules.portfolios.service import OversellError, compute_position

BUY = TransactionType.BUY
SELL = TransactionType.SELL
DIVIDEND = TransactionType.DIVIDEND


def tx(kind, qty, price, day, fees=0, taxes=0):
    """Build a transaction-like object with a server-computed total."""
    qty, price, fees, taxes = (Decimal(str(v)) for v in (qty, price, fees, taxes))
    return SimpleNamespace(
        transaction_type=kind,
        quantity=qty,
        price=price,
        fees=fees,
        taxes=taxes,
        total_amount=Transaction.compute_total_amount(kind, qty, price, fees, taxes),
        transaction_date=datetime(2025, 1, day, tzinfo=timezone.utc),
    )


@pytest.fixture
def calc():
    # The pure helpers don't touch the database
    return PortfolioCalculationService(db=None)


class TestComputeTotalAmount:
    def test_buy_adds_fees_and_taxes(self):
        total = Transaction.compute_total_amount(
            BUY, Decimal("10"), Decimal("100"), Decimal("5"), Decimal("1")
        )
        assert total == Decimal("1006")

    def test_sell_subtracts_fees_and_taxes(self):
        total = Transaction.compute_total_amount(
            SELL, Decimal("10"), Decimal("100"), Decimal("5"), Decimal("1")
        )
        assert total == Decimal("994")

    def test_other_types_are_gross(self):
        total = Transaction.compute_total_amount(
            DIVIDEND, Decimal("10"), Decimal("0.5"), Decimal("1")
        )
        assert total == Decimal("5.0")

    def test_transfer_in_adds_fees_and_transfer_out_subtracts_them(self):
        assert Transaction.compute_total_amount(
            TransactionType.TRANSFER_IN, Decimal("10"), Decimal("50"), Decimal("5")
        ) == Decimal("505")
        assert Transaction.compute_total_amount(
            TransactionType.TRANSFER_OUT, Decimal("10"), Decimal("50"), Decimal("5")
        ) == Decimal("495")


class TestComputePosition:
    def test_fees_are_part_of_cost_basis(self):
        position = compute_position([tx(BUY, 10, 100, 1, fees=5)])
        assert position["quantity"] == Decimal("10")
        assert position["cost_basis_total"] == Decimal("1005")

    def test_fifo_partial_sell_realizes_net_proceeds(self):
        position = compute_position(
            [
                tx(BUY, 10, 100, 1, fees=10),  # lot 1: 1010
                tx(BUY, 10, 200, 2),  # lot 2: 2000
                tx(SELL, 15, 300, 3, fees=15),  # proceeds 4485
            ]
        )
        # Sold all of lot 1 (1010) and half of lot 2 (1000)
        assert position["quantity"] == Decimal("5")
        assert position["cost_basis_total"] == Decimal("1000")
        assert position["cost_of_sold"] == Decimal("2010")
        assert position["realized_pnl"] == Decimal("4485") - Decimal("2010")

    def test_full_exit_leaves_nothing(self):
        position = compute_position([tx(BUY, 3, 10, 1), tx(SELL, 3, 12, 2)])
        assert position["quantity"] == 0
        assert position["cost_basis_total"] == 0
        assert position["realized_pnl"] == Decimal("6")

    def test_oversell_is_rejected(self):
        with pytest.raises(OversellError):
            compute_position([tx(BUY, 1, 10, 1), tx(SELL, 2, 10, 2)])

    def test_sell_before_any_buy_is_rejected(self):
        with pytest.raises(OversellError):
            compute_position([tx(SELL, 1, 10, 1)])


def history(rows):
    df = pd.DataFrame(rows, columns=["value", "inflow", "outflow"])
    df["net_cash_flow"] = df["inflow"] - df["outflow"]
    return df


class TestDailyReturns:
    def test_first_buy_at_flat_price_is_zero_return(self):
        df = history([(1000, 1000, 0), (1000, 0, 0)])
        returns = compute_daily_returns(df, opening_value=0.0)
        assert returns.tolist() == pytest.approx([0.0, 0.0])

    def test_full_exit_is_measured_not_minus_100(self):
        # Held 1000 overnight, sold everything today for 1010
        df = history([(1000, 0, 0), (0, 0, 1010)])
        returns = compute_daily_returns(df, opening_value=1000.0)
        assert returns.iloc[1] == pytest.approx(0.01)

    def test_deposit_is_not_counted_as_growth(self):
        # 1000 held flat, then another 1000 invested at the same price
        df = history([(1000, 0, 0), (2000, 1000, 0)])
        returns = compute_daily_returns(df, opening_value=1000.0)
        assert returns.tolist() == pytest.approx([0.0, 0.0])

    def test_no_capital_at_risk_is_nan(self):
        df = history([(0, 0, 0)])
        returns = compute_daily_returns(df, opening_value=0.0)
        assert returns.isna().all()


class TestTwrCagrDrawdown:
    def test_twr_ignores_cash_flows(self, calc):
        # +10% on day 2, then a deposit, then +10% on day 4 => 21%
        df = history(
            [
                (1000, 1000, 0),
                (1100, 0, 0),
                (2100, 1000, 0),
                (2310, 0, 0),
            ]
        )
        df["daily_return"] = compute_daily_returns(df, opening_value=0.0)
        assert calc._calculate_twr(df) == pytest.approx(21.0)

    def test_twr_with_buy_flat_is_zero_not_minus_50(self, calc):
        df = history([(1000, 1000, 0), (1000, 0, 0)])
        df["daily_return"] = compute_daily_returns(df, opening_value=0.0)
        assert calc._calculate_twr(df) == pytest.approx(0.0)

    def test_cagr_annualises_over_one_year(self, calc):
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2022, 1, 1, tzinfo=timezone.utc)
        # 21% over ~2 years ~= 10% a year
        assert calc._calculate_cagr(21.0, start, end) == pytest.approx(10.0, abs=0.02)

    def test_cagr_not_annualised_under_one_year(self, calc):
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 6, 1, tzinfo=timezone.utc)
        assert calc._calculate_cagr(5.0, start, end) == 5.0

    def test_max_drawdown_ignores_deposits_and_withdrawals(self, calc):
        # A withdrawal halves the value but is not a loss
        df = history([(1000, 1000, 0), (500, 0, 500), (500, 0, 0)])
        df["daily_return"] = compute_daily_returns(df, opening_value=0.0)
        assert calc._calculate_max_drawdown(df) == pytest.approx(0.0)

    def test_volatility_is_none_without_enough_returns(self, calc):
        df = history([(1000, 1000, 0)])
        df["daily_return"] = compute_daily_returns(df, opening_value=0.0)
        assert calc._calculate_volatility(df) is None


class TestXirrCashFlows:
    def test_investor_cash_flow_signs(self):
        flow = PortfolioCalculationService._investor_cash_flow
        assert flow(tx(BUY, 1, 100, 1, fees=1)) == -101.0
        assert flow(tx(SELL, 1, 100, 1, fees=1)) == 99.0
        assert flow(tx(DIVIDEND, 1, 2, 1)) == 2.0
        assert flow(tx(TransactionType.TRANSFER_IN, 1, 40, 1, fees=1)) == -41.0
        assert flow(tx(TransactionType.TRANSFER_OUT, 1, 40, 1, fees=1)) == 39.0
        assert flow(tx(TransactionType.SPLIT, 2, 0, 1)) is None

    @pytest.mark.asyncio
    async def test_xirr_works_with_dividends_and_non_cash_types(self, calc):
        transactions = [
            tx(BUY, 10, 100, 1),
            tx(DIVIDEND, 10, 1, 2),
            tx(TransactionType.SPLIT, 2, 0, 3),
        ]
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = await calc._calculate_xirr(transactions, 1100.0, None, end)
        assert result is not None
        assert result > 0


class _StubQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return SimpleNamespace(symbol="ACME")


class _StubDb:
    def query(self, *args, **kwargs):
        return _StubQuery()


class TestPortfolioHistory:
    @pytest.fixture
    def calc_with_prices(self, monkeypatch):
        calc = PortfolioCalculationService(db=_StubDb())
        # Close of 100 until Jan 3, then 110. Indexed by date, like get_price_data.
        prices = pd.DataFrame(
            {"Close": [100.0] * 3 + [110.0] * 4},
            index=[d.date() for d in pd.bdate_range("2025-01-01", "2025-01-09")],
        )

        async def fake_daily_history(symbol):
            return {
                "close": pd.Series(
                    prices["Close"].values, index=pd.to_datetime(prices.index)
                ),
                "splits": pd.Series(dtype=float),
                "dividends": pd.Series(dtype=float),
            }

        monkeypatch.setattr(
            calc.market_data_service, "get_daily_history", fake_daily_history
        )
        return calc

    @pytest.mark.asyncio
    async def test_history_uses_business_days_and_full_exit(self, calc_with_prices):
        def at(day):
            return datetime(2025, 1, day, 12, tzinfo=timezone.utc)

        buy = tx(BUY, 10, 100, 1)
        buy.transaction_date = at(1)  # Wednesday
        buy.asset_id = 1
        sell = tx(SELL, 10, 110, 4)
        sell.transaction_date = at(4)  # Saturday -> booked on Monday the 6th
        sell.asset_id = 1

        df = await calc_with_prices.get_portfolio_history(
            [buy, sell], None, datetime(2025, 1, 9, tzinfo=timezone.utc)
        )

        assert all(day.weekday() < 5 for day in df.index)
        monday = df.loc["2025-01-06"]
        assert monday["value"] == 0
        assert monday["outflow"] == pytest.approx(1100.0)
        # Worth 1000 at Friday's close, sold for 1100 on Monday: +10%, not -100%
        assert monday["daily_return"] == pytest.approx(0.10)
        assert calc_with_prices._calculate_twr(df) == pytest.approx(10.0)


def _create(**overrides):
    values = dict(
        portfolio_id=1,
        asset_id=1,
        transaction_type=TransactionType.BUY,
        quantity=Decimal("1"),
        price=Decimal("10"),
        currency="EUR",
        transaction_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    values.update(overrides)
    return TransactionCreate(**values)


class TestTransactionNumbers:
    def test_a_buy_can_be_free_but_not_empty(self):
        assert _create(price=Decimal("0")).price == 0
        with pytest.raises(ValidationError):
            _create(quantity=Decimal("0"))
        with pytest.raises(ValidationError):
            _create(price=Decimal("-1"))

    def test_transfers_need_a_positive_quantity(self):
        _create(transaction_type=TransactionType.TRANSFER_IN, price=Decimal("0"))
        with pytest.raises(ValidationError):
            _create(
                transaction_type=TransactionType.TRANSFER_OUT, quantity=Decimal("0")
            )

    def test_an_imported_dividend_may_have_no_share_count(self):
        row = _create(
            transaction_type=TransactionType.DIVIDEND,
            quantity=Decimal("0"),
            price=Decimal("0"),
        )
        assert row.quantity == 0

    def test_a_partial_update_rejects_only_what_it_sends(self):
        assert TransactionUpdate(notes="moved").notes == "moved"
        with pytest.raises(ValidationError):
            TransactionUpdate(price=Decimal("-1"))
        with pytest.raises(ValidationError):
            TransactionUpdate(
                transaction_type=TransactionType.SELL, quantity=Decimal("0")
            )

    def test_a_merged_buy_cannot_keep_a_zero_quantity(self):
        with pytest.raises(ValueError, match="quantity must be greater than 0"):
            check_transaction_numbers(TransactionType.BUY, Decimal("0"), Decimal("10"))
        check_transaction_numbers(TransactionType.DIVIDEND, Decimal("0"), Decimal("0"))
