"""
Golden tests for core/domain: split-adjusted FIFO positions, the daily value
series and period returns. Every expected number is worked out by hand.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from core.database.models import Transaction, TransactionStatus, TransactionType
from core.domain.fx import convert_trades
from core.domain.positions import (
    OversellError,
    compute_position,
    day_change,
    split_factor,
    to_trades,
)
from core.domain.returns import (
    annualize_pct,
    compute_daily_returns,
    deannualize_pct,
    max_drawdown_pct,
    period_summary,
    xirr_pct,
)
from core.domain.valuation import STALE_PRICE_DAYS, MissingPriceError, daily_series

BUY, SELL, DIVIDEND, TRANSFER_IN, TRANSFER_OUT = (
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.DIVIDEND,
    TransactionType.TRANSFER_IN,
    TransactionType.TRANSFER_OUT,
)


def tx(
    kind,
    qty,
    price,
    day,
    fees=0,
    asset_id=1,
    status=TransactionStatus.COMPLETED,
    id=0,
    taxes=0,
):
    qty, price, fees, taxes = (Decimal(str(v)) for v in (qty, price, fees, taxes))
    return SimpleNamespace(
        id=id,
        asset_id=asset_id,
        status=status,
        transaction_type=kind,
        quantity=qty,
        price=price,
        total_amount=Transaction.compute_total_amount(kind, qty, price, fees, taxes),
        taxes=taxes,
        transaction_date=datetime.combine(
            day, datetime.min.time(), tzinfo=timezone.utc
        ),
    )


def closes(prices):
    return pd.Series(list(prices.values()), index=pd.to_datetime(list(prices.keys())))


THU, FRI, SAT, MON, TUE = (date(2025, 1, d) for d in (2, 3, 4, 6, 7))


class TestSplits:
    def test_factor_only_counts_later_splits(self):
        splits = [(date(2025, 1, 10), Decimal(2)), (date(2025, 6, 1), Decimal(3))]
        assert split_factor(splits, date(2025, 1, 9)) == 6
        assert split_factor(splits, date(2025, 1, 10)) == 3
        assert split_factor(splits, date(2025, 7, 1)) == 1

    def test_trade_before_split_is_in_todays_shares(self):
        trade = to_trades(
            [tx(BUY, 10, 100, THU)], {1: [(date(2025, 1, 10), Decimal(2))]}
        )[0]
        assert (trade.quantity, trade.price, trade.total_amount) == (20, 50, 1000)

    def test_position_after_split_keeps_cost(self):
        trades = to_trades(
            [tx(BUY, 10, 100, THU), tx(SELL, 5, 60, date(2025, 1, 13))],
            {1: [(date(2025, 1, 10), Decimal(2))]},
        )
        position = compute_position(trades)
        # 20 post-split shares cost 1000; selling 5 removes 250 of cost
        assert position["quantity"] == 15
        assert position["cost_basis_total"] == 750
        assert position["realized_pnl"] == 50


class TestReverseSplitAndTax:
    """Beyond Meat on Trade Republic: a 1:30 reverse split, tax withheld on the sale."""

    SPLIT = {1: [(date(2025, 1, 10), Decimal(1) / Decimal(30))]}

    def trades(self):
        return to_trades(
            [
                tx(BUY, 3000, 1, THU, fees=1),
                tx(SELL, 50, 40, date(2025, 1, 13), fees=1, taxes=250),
            ],
            self.SPLIT,
        )

    def test_buy_before_reverse_split_is_in_todays_shares(self):
        buy = self.trades()[0]
        assert float(buy.quantity) == pytest.approx(100)
        assert float(buy.price) == pytest.approx(30)
        assert buy.total_amount == 3001

    def test_realized_is_before_tax(self):
        position = compute_position(self.trades())
        # proceeds 2000 - 1 fee; half the lot cost 1500.50; the 250 tax is not a loss
        assert float(position["quantity"]) == pytest.approx(50)
        assert float(position["cost_basis_total"]) == pytest.approx(1500.5)
        assert float(position["realized_pnl"]) == pytest.approx(498.5)

    def test_series_realizes_before_tax_but_cash_flow_is_net(self):
        series = daily_series(
            self.trades(),
            {1: closes({THU: 30, date(2025, 1, 13): 40})},
            date(2025, 1, 13),
        )
        last = series.iloc[-1]
        assert last["realized_pnl"] == pytest.approx(498.5)
        assert last["outflow"] == pytest.approx(1749)

    def test_tax_converts_with_the_cash(self):
        trade = self.trades()[1]
        converted = convert_trades(
            [trade],
            {trade.id: "USD"},
            "EUR",
            {"USD": pd.Series([0.5], index=[pd.Timestamp(date(2025, 1, 13))])},
        )[0]
        assert converted.taxes == 125
        assert converted.total_amount == Decimal("874.5")


class TestToTrades:
    def test_only_completed_and_buys_before_sells(self):
        trades = to_trades(
            [
                tx(SELL, 1, 10, THU, id=1),
                tx(BUY, 1, 10, THU, id=2),
                tx(BUY, 9, 10, THU, id=3, status=TransactionStatus.PENDING),
                tx(BUY, 9, 10, THU, id=4, status=TransactionStatus.CANCELLED),
            ]
        )
        assert [t.id for t in trades] == [2, 1]

    def test_oversell_is_rejected(self):
        with pytest.raises(OversellError):
            compute_position(to_trades([tx(BUY, 1, 10, THU), tx(SELL, 2, 10, FRI)]))

    def test_transfer_in_is_applied_before_transfer_out_the_same_day(self):
        trades = to_trades(
            [
                tx(TRANSFER_OUT, 5, 10, THU, id=1),
                tx(TRANSFER_IN, 5, 10, THU, id=2),
            ]
        )
        assert [t.transaction_type for t in trades] == [TRANSFER_IN, TRANSFER_OUT]
        position = compute_position(trades)
        assert position["quantity"] == 0
        assert position["realized_pnl"] == 0


class TestTransfers:
    def test_transfer_in_opens_a_lot_at_the_given_cost(self):
        # 10 shares arrive at 50, plus a 5 fee: the lot costs 505
        position = compute_position(to_trades([tx(TRANSFER_IN, 10, 50, THU, fees=5)]))
        assert position["quantity"] == 10
        assert position["cost_basis_total"] == 505
        assert position["realized_pnl"] == 0

    def test_transfer_out_closes_fifo_at_the_given_proceeds(self):
        position = compute_position(
            to_trades(
                [
                    tx(TRANSFER_IN, 10, 50, THU),  # cost 500
                    tx(BUY, 10, 80, FRI),  # cost 800
                    tx(TRANSFER_OUT, 15, 70, MON, fees=10),  # proceeds 1050 - 10
                ]
            )
        )
        # 10 of the first lot (500) and half of the second (400)
        assert position["quantity"] == 5
        assert position["cost_basis_total"] == 400
        assert position["cost_of_sold"] == 900
        assert position["realized_pnl"] == 1040 - 900

    def test_transfer_out_beyond_the_holding_is_rejected(self):
        with pytest.raises(OversellError):
            compute_position(
                to_trades([tx(TRANSFER_IN, 1, 10, THU), tx(TRANSFER_OUT, 2, 10, FRI)])
            )

    def test_transfer_before_a_split_is_in_todays_shares(self):
        trades = to_trades(
            [tx(TRANSFER_IN, 10, 100, THU)],
            {1: [(date(2025, 1, 10), Decimal(2))]},
        )
        assert (trades[0].quantity, trades[0].price, trades[0].total_amount) == (
            20,
            50,
            1000,
        )
        assert compute_position(trades)["quantity"] == 20
        assert compute_position(trades)["cost_basis_total"] == 1000


class TestDailySeries:
    def test_fees_in_cost_and_weekend_trade_counts_next_trading_day(self):
        series = daily_series(
            to_trades([tx(BUY, 10, 100, THU, fees=5), tx(BUY, 10, 110, SAT)]),
            {1: closes({THU: 100, FRI: 110, MON: 120})},
            MON,
        )
        assert list(series.index.date) == [THU, FRI, MON]
        assert series["value"].tolist() == [1000, 1100, 2400]
        assert series["cost_basis"].tolist() == [1005, 1005, 2105]
        assert series["net_invested"].tolist() == [1005, 1005, 2105]
        assert series["inflow"].tolist() == [1005, 0, 1100]

    def test_sell_uses_fifo_and_returns_net_proceeds(self):
        series = daily_series(
            to_trades(
                [
                    tx(BUY, 10, 100, THU),
                    tx(BUY, 10, 200, FRI),
                    tx(SELL, 15, 300, MON, fees=15),
                ]
            ),
            {1: closes({THU: 100, FRI: 200, MON: 300})},
            MON,
        )
        last = series.iloc[-1]
        # sold lot 1 (1000) + half of lot 2 (1000); proceeds 4500 - 15
        assert last["cost_basis"] == 1000
        assert last["realized_pnl"] == 2485
        assert last["outflow"] == 4485
        assert last["net_invested"] == 3000 - 4485
        assert last["value"] == 5 * 300

    def test_transfer_is_a_deposit_and_a_withdrawal(self):
        series = daily_series(
            to_trades(
                [
                    tx(TRANSFER_IN, 10, 100, THU),
                    tx(TRANSFER_OUT, 4, 110, FRI, fees=10),
                ]
            ),
            {1: closes({THU: 100, FRI: 110})},
            FRI,
        )
        assert series["inflow"].tolist() == [1000, 0]
        assert series["outflow"].tolist() == [0, 430]
        assert series["value"].tolist() == [1000, 660]
        assert series["cost_basis"].tolist() == [1000, 600]
        assert series["realized_pnl"].tolist() == [0, 30]
        assert series["dividends"].tolist() == [0, 0]
        assert series["net_invested"].tolist() == [1000, 570]

    def test_dividend_is_cash_returned(self):
        series = daily_series(
            to_trades([tx(BUY, 10, 100, THU), tx(DIVIDEND, 10, 0.5, FRI)]),
            {1: closes({THU: 100, FRI: 100})},
            FRI,
        )
        assert series["dividends"].iloc[-1] == 5
        assert series["outflow"].iloc[-1] == 5
        assert series["net_invested"].iloc[-1] == 995

    def test_price_gap_is_carried_forward(self):
        series = daily_series(
            to_trades([tx(BUY, 1, 10, THU), tx(BUY, 1, 50, THU, asset_id=2)]),
            {1: closes({THU: 10, FRI: 11, MON: 12}), 2: closes({THU: 50, MON: 55})},
            MON,
        )
        assert series["value"].tolist() == [60, 61, 67]
        assert series["stale_price"].tolist() == [False, False, False]

    def test_close_older_than_five_sessions_is_flagged_and_still_used(self):
        days = list(pd.bdate_range("2025-01-06", periods=STALE_PRICE_DAYS + 2))
        series = daily_series(
            to_trades(
                [
                    tx(BUY, 1, 10, days[0]),
                    tx(BUY, 1, 50, days[0], asset_id=2),
                ]
            ),
            {1: closes({day: 10 for day in days}), 2: closes({days[0]: 50})},
            days[-1],
            {2: "OLD"},
        )
        assert series["stale_price"].tolist() == [False] * (STALE_PRICE_DAYS + 1) + [
            True
        ]
        assert series["stale_symbols"].iloc[-1] == ["OLD"]
        assert series["value"].iloc[-1] == 60

    def test_held_asset_without_any_price_is_an_error_not_cost(self):
        with pytest.raises(MissingPriceError):
            daily_series(
                to_trades([tx(BUY, 1, 10, THU), tx(BUY, 1, 50, THU, asset_id=2)]),
                {1: closes({THU: 10}), 2: closes({FRI: 50})},
                FRI,
            )

    def test_tz_aware_prices_are_used_by_date(self):
        prices = closes({THU: 100, FRI: 110})
        prices.index = prices.index.tz_localize("America/New_York")
        series = daily_series(to_trades([tx(BUY, 1, 100, THU)]), {1: prices}, FRI)
        assert series["value"].tolist() == [100, 110]


def frame(values, inflow, outflow=None):
    days = pd.bdate_range("2025-01-06", periods=len(values))
    return pd.DataFrame(
        {"value": values, "inflow": inflow, "outflow": outflow or [0] * len(values)},
        index=days,
    )


class TestPeriodSummary:
    def test_inception_profit_and_twr(self):
        summary = period_summary(frame([1000, 1100, 1210], [1000, 0, 0]))
        assert summary["start_value"] == 0
        assert summary["net_contributions"] == 1000
        assert summary["profit"] == pytest.approx(210)
        assert summary["twr_pct"] == pytest.approx(21)

    def test_mid_period_uses_previous_close_as_opening(self):
        series = frame([1000, 1100, 1210], [1000, 0, 0])
        summary = period_summary(series, date(2025, 1, 7))
        assert summary["start_value"] == 1000
        assert summary["net_contributions"] == 0
        assert summary["profit"] == pytest.approx(210)
        assert summary["twr_pct"] == pytest.approx(21)

    def test_deposit_is_not_return(self):
        # day 2: 1000 more arrives and the whole 2000 earns 5% -> 2100
        summary = period_summary(frame([1000, 2100], [1000, 1000]))
        assert summary["twr_pct"] == pytest.approx(5)
        assert summary["profit"] == pytest.approx(100)

    def test_best_and_worst_day(self):
        summary = period_summary(frame([100, 110, 99], [100, 0, 0]))
        assert summary["best_day"]["return_pct"] == pytest.approx(10)
        assert summary["worst_day"]["return_pct"] == pytest.approx(-10)


class TestAnnualize:
    def test_a_one_year_window_is_annualised(self):
        assert annualize_pct(21.0, 364) == pytest.approx(21.0, abs=0.1)

    def test_shorter_periods_are_not_extrapolated(self):
        assert annualize_pct(5.0, 90) is None


class TestRiskAndXirr:
    def test_drawdown_counts_a_fall_from_the_start(self):
        returns = compute_daily_returns(frame([100, 90, 99, 80], [100, 0, 0, 0]), 0)
        assert max_drawdown_pct(returns) == pytest.approx(-20)

    def test_xirr_one_year_ten_percent(self):
        assert xirr_pct(
            [(date(2024, 1, 1), -1000), (date(2024, 12, 31), 1100)]
        ) == pytest.approx(10, abs=0.05)

    def test_half_year_of_a_ten_percent_rate(self):
        assert deannualize_pct(10.0, 182) == pytest.approx(4.86, abs=0.01)

    def test_xirr_needs_money_in_and_out(self):
        assert xirr_pct([(date(2024, 1, 1), -1000)]) is None


class TestDayChange:
    def test_held_all_day(self):
        assert day_change(Decimal(10), Decimal(100), Decimal(105), []) == (50, 1000)

    def test_buy_today_counts_from_its_price_not_yesterdays_close(self):
        # 10 held from 100 -> 105 (+50); 5 bought at 104 -> 105 (+5)
        pnl, base = day_change(
            Decimal(15), Decimal(100), Decimal(105), [tx(BUY, 5, 104, THU)]
        )
        assert (pnl, base) == (55, 1000 + 520)

    def test_transfer_in_today_counts_from_its_price(self):
        pnl, base = day_change(
            Decimal(15), Decimal(100), Decimal(105), [tx(TRANSFER_IN, 5, 104, THU)]
        )
        assert (pnl, base) == (55, 1000 + 520)

    def test_transfer_out_today_realises_against_the_previous_close(self):
        pnl, base = day_change(
            Decimal(6), Decimal(100), Decimal(105), [tx(TRANSFER_OUT, 4, 102, THU)]
        )
        assert (pnl, base) == (38, 1000)

    def test_sell_today_realises_against_the_previous_close(self):
        # 10 held, 4 sold at 102 (+8), 6 left at 105 (+30)
        pnl, base = day_change(
            Decimal(6), Decimal(100), Decimal(105), [tx(SELL, 4, 102, THU)]
        )
        assert (pnl, base) == (38, 1000)
