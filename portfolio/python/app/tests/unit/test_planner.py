"""
Golden tests for core/domain/planner.py: the buy-only split, savings-plan
detection and the goal projection. Expected numbers are worked out by hand.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from core.domain.planner import (
    Purchase,
    buy_only_split,
    detect_savings_plans,
    monthly_returns,
    project_goal,
    with_annual_mean,
)

A, B, C, D = 1, 2, 3, 4
VALUES = {A: 600.0, B: 300.0, C: 100.0}
TARGETS = {A: 50.0, B: 30.0, C: 20.0}


def amounts(buys):
    return {b.asset_id: round(b.amount, 6) for b in buys}


def test_split_fills_the_whole_gap_when_the_money_covers_it():
    # After 1,200: targets 600 / 360 / 240 → buy B 60 and C 140, nothing of A
    buys = buy_only_split(VALUES, TARGETS, 200)

    assert amounts(buys) == {A: 0, B: 60, C: 140}
    assert [b.asset_id for b in buys] == [C, B, A]
    assert {b.asset_id: round(b.weight_after_pct, 6) for b in buys} == {
        A: 50,
        B: 30,
        C: 20,
    }
    assert buys[0].weight_before_pct == pytest.approx(10)


def test_split_tops_up_the_most_underweight_first():
    # C is at half its target (100 of 200 at level 1,000); 100 brings C to
    # 200 = 20 % of 1,000 while B is already at 30 % of 1,000
    assert amounts(buy_only_split(VALUES, TARGETS, 100)) == {A: 0, B: 0, C: 100}
    # 150: level (150 + 400) / 0.5 = 1,100 → C 120, B 30
    assert amounts(buy_only_split(VALUES, TARGETS, 150)) == {A: 0, B: 30, C: 120}


def test_split_beyond_the_targets_keeps_the_target_weights():
    # 1,000 more: level 2,000 → A 400, B 300, C 300
    buys = buy_only_split(VALUES, TARGETS, 1000)
    assert amounts(buys) == {A: 400, B: 300, C: 300}
    assert sum(b.amount for b in buys) == pytest.approx(1000)


def test_split_ignores_holdings_without_a_target_and_normalises_targets():
    values = {**VALUES, D: 5000.0}
    # Targets 5 / 3 / 2 are 50 / 30 / 20 %; D has none and gets nothing
    buys = buy_only_split(values, {A: 5, B: 3, C: 2}, 200)
    assert amounts(buys) == {A: 0, B: 60, C: 140}
    assert {b.target_pct for b in buys} == {50, 30, 20}


def test_split_drops_buys_below_the_minimum_and_splits_again():
    # 150 → B 30, C 120; with a 50 minimum B is dropped and C takes all 150
    assert amounts(buy_only_split(VALUES, TARGETS, 150, min_amount=50)) == {
        A: 0,
        B: 0,
        C: 150,
    }
    assert buy_only_split(VALUES, TARGETS, 0) == []
    assert buy_only_split(VALUES, {}, 100) == []


def test_split_buys_an_unheld_target_first():
    # E targeted at 10 % but not held. Ratios value ÷ target: E 0, C 555.6,
    # B 1,111, A 1,333. E alone would need level 900 > 555.6, so C joins:
    # level (90 + 100) / 0.28 = 678.6 → E 67.86, C 22.14
    buys = amounts(buy_only_split(VALUES, {A: 45, B: 27, C: 18, 5: 10}, 90))
    assert buys[5] == pytest.approx(0.1 * 190 / 0.28, abs=1e-6)
    assert buys[C] == pytest.approx(0.18 * 190 / 0.28 - 100, abs=1e-6)
    assert buys[A] == buys[B] == 0


def monthly(asset_id, start, count, amount=100.0, fee_free=True, step=None):
    days = (
        [
            date(
                start.year + (start.month - 1 + i) // 12,
                (start.month - 1 + i) % 12 + 1,
                start.day,
            )
            for i in range(count)
        ]
        if step is None
        else [start + timedelta(days=step * i) for i in range(count)]
    )
    return [Purchase(asset_id, d, amount, amount / 50, fee_free) for d in days]


def test_detects_a_monthly_plan_and_ignores_extra_manual_buys():
    rows = monthly(A, date(2026, 1, 2), 6) + [
        Purchase(A, date(2026, 3, 15), 900.0, 18.0, False)
    ]

    (plan,) = detect_savings_plans(rows, date(2026, 7, 10))

    assert (plan.rhythm, plan.executions, plan.amount) == ("monthly", 6, 100)
    assert plan.invested == 600
    assert plan.quantity == pytest.approx(12)
    assert (plan.first, plan.last) == (date(2026, 1, 2), date(2026, 6, 2))
    assert (plan.executions_per_month, plan.monthly_amount) == (1, 100)
    assert plan.active


def broker_days(first_month, months, days=(2, 9, 16, 23)):
    """A broker's plan calendar: fixed days of the month, a weekend moved to Monday."""
    found = []
    for i in range(months):
        year = first_month.year + (first_month.month - 1 + i) // 12
        month = (first_month.month - 1 + i) % 12 + 1
        for d in days:
            day = date(year, month, d)
            found.append(
                day
                + timedelta(days=(7 - day.weekday()) % 7 if day.weekday() >= 5 else 0)
            )
    return found


def plan_buys(asset_id, days, amount, fee_free=True):
    return [Purchase(asset_id, d, amount, amount / 50, fee_free) for d in days]


def test_a_weekly_broker_plan_is_four_executions_a_month():
    # 2nd, 9th, 16th, 23rd from June to October 2026: 20 executions, gaps of
    # 7 days and 9–12 across the month end (weekends moved to Monday). Five
    # weeks in a month still means four executions.
    days = broker_days(date(2026, 6, 1), 5)
    assert date(2026, 8, 3) in days  # 2 August 2026 is a Sunday

    (plan,) = detect_savings_plans(plan_buys(A, days, 150.0), date(2026, 10, 28))

    assert (plan.rhythm, plan.executions_per_month, plan.executions) == (
        "weekly",
        4,
        20,
    )
    assert plan.monthly_amount == 600
    assert plan.invested == 20 * 150
    assert plan.previous_amount is None
    assert plan.active


def test_two_weekly_and_monthly_plans_by_their_executions_a_month():
    twice = broker_days(date(2026, 3, 1), 6, days=(2, 16))
    once = broker_days(date(2026, 3, 1), 6, days=(2,))

    plans = {
        p.asset_id: p
        for p in detect_savings_plans(
            plan_buys(A, twice, 100.0) + plan_buys(B, once, 250.0), date(2026, 8, 20)
        )
    }

    assert (plans[A].rhythm, plans[A].monthly_amount) == ("every two weeks", 200)
    assert (plans[B].rhythm, plans[B].monthly_amount) == ("monthly", 250)


def test_a_raised_plan_shows_the_amount_before_the_change():
    days = broker_days(date(2026, 1, 1), 10)
    rows = plan_buys(A, days[:17], 100.0) + plan_buys(A, days[17:], 300.0)

    (plan,) = detect_savings_plans(rows, date(2026, 10, 28))

    # 17 × 100 + 23 × 300; the per-month figure uses today's amount
    assert (plan.amount, plan.previous_amount) == (300, 100)
    assert plan.invested == 17 * 100 + 23 * 300
    assert plan.monthly_amount == 1200
    assert plan.executions == 40


def test_a_restarted_plan_shows_its_earlier_run_as_stopped():
    earlier = plan_buys(C, broker_days(date(2025, 8, 1), 3)[:10], 100.0)
    later = plan_buys(C, broker_days(date(2026, 5, 1), 6)[3:], 150.0)
    stopped = plan_buys(D, broker_days(date(2025, 1, 1), 5, days=(10,)), 50.0)

    plans = detect_savings_plans(earlier + later + stopped, date(2026, 10, 28))

    assert [(p.asset_id, p.executions, p.amount, p.active) for p in plans] == [
        (C, 21, 150, True),
        (C, 10, 100, False),
        (D, 5, 50, False),
    ]
    assert plans[1].last == earlier[-1].day
    assert sum(p.quantity for p in plans[0].purchases) == pytest.approx(
        plans[0].quantity
    )


def test_changing_amounts_on_a_steady_rhythm_are_not_a_plan():
    days = broker_days(date(2024, 2, 1), 2)
    amounts = [3205.0, 4120.5, 7755.2, 2990.0, 5100.0, 3376.6, 6410.0, 4800.0]
    rows = [Purchase(A, d, a, 1, True) for d, a in zip(days, amounts)]

    assert detect_savings_plans(rows, date(2024, 4, 1)) == []


def test_irregular_buys_are_not_a_plan():
    rows = [
        Purchase(A, date(2026, 1, 1), 100, 1, True),
        Purchase(A, date(2026, 1, 4), 100, 1, True),
        Purchase(A, date(2026, 2, 20), 100, 1, True),
        Purchase(A, date(2026, 6, 1), 100, 1, True),
    ]
    assert detect_savings_plans(rows, date(2026, 6, 2)) == []
    assert detect_savings_plans(rows[:2], date(2026, 6, 2)) == []


def test_projection_with_a_steady_return_by_hand():
    # 1 % every month: 1,000 start and 100 a month (paid at the start of each
    # month) for 24 months
    history = np.full(36, 0.01)
    g = 1.01**24
    annuity = sum(1.01**k for k in range(1, 25))
    expected = 1000 * g + 100 * annuity

    result = project_goal(1000, 100, 24, history, goal=5000, paths=50)

    assert result.final[10] == pytest.approx(expected)
    assert result.final[90] == pytest.approx(expected)
    assert result.percentiles[50][0] == pytest.approx(1100 * 1.01)
    assert len(result.percentiles[50]) == 24
    assert result.deposits == 1000 + 100 * 24
    assert result.probability_pct == 0
    assert result.required_monthly[50] == pytest.approx((5000 - 1000 * g) / annuity)


def test_projection_reaches_a_small_goal_without_saving():
    result = project_goal(1000, 0, 12, np.full(24, 0.01), goal=500, paths=10)
    assert result.probability_pct == 100
    assert result.required_monthly == {50: 0, 75: 0, 90: 0}


def test_projection_is_repeatable_and_ordered():
    rng = np.random.default_rng(5)
    history = rng.normal(0.006, 0.045, 200)

    first = project_goal(10_000, 300, 120, history, goal=80_000)
    again = project_goal(10_000, 300, 120, history, goal=80_000)

    assert first.final == again.final
    assert first.final[10] < first.final[50] < first.final[90]
    assert (
        first.required_monthly[50]
        < first.required_monthly[75]
        < first.required_monthly[90]
    )
    assert 0 < first.probability_pct < 100


def test_projection_rejects_impossible_inputs():
    with pytest.raises(ValueError):
        project_goal(1000, 100, 0, np.full(24, 0.01))
    with pytest.raises(ValueError):
        project_goal(1000, 100, 12, np.full(5, 0.01))


def test_monthly_returns_from_month_end_closes():
    assert monthly_returns([100, 110, float("nan"), 99]).tolist() == pytest.approx(
        [0.1, -0.1]
    )


def test_assumed_return_keeps_the_swings_and_moves_the_average():
    history = np.array([0.05, -0.03, 0.02, 0.0])
    shifted = with_annual_mean(history, 7)

    assert shifted.mean() == pytest.approx(1.07 ** (1 / 12) - 1)
    assert np.diff(shifted) == pytest.approx(np.diff(history))


@pytest.fixture
def book(test_db, monkeypatch):
    """A EUR portfolio with a monthly €100 plan in A, one bigger manual buy of B, targets 50/50."""
    from datetime import datetime, timezone
    from decimal import Decimal
    from types import SimpleNamespace

    from core.database.models import (
        Asset,
        Portfolio,
        PortfolioAllocation,
        Transaction,
        TransactionType,
        User,
    )
    from core.database.models.asset import AssetType
    from modules.portfolios.service import PortfolioService

    user = User(email="plan@example.com", username="planner", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="P", currency="EUR")
    a = Asset(
        symbol="AAA",
        name="A plc",
        asset_type=AssetType.ETF,
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
    today = datetime.now(timezone.utc)
    for months_back in range(6, 0, -1):
        test_db.add(
            Transaction(
                portfolio_id=portfolio.id,
                asset_id=a.id,
                transaction_type=TransactionType.BUY,
                quantity=Decimal("2"),
                price=Decimal("50"),
                total_amount=Decimal("100"),
                fees=Decimal("0"),
                currency="EUR",
                transaction_date=today - timedelta(days=30.44 * months_back),
            )
        )
    test_db.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=b.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("90"),
            total_amount=Decimal("901"),
            fees=Decimal("1"),
            currency="EUR",
            transaction_date=today - timedelta(days=40),
        )
    )
    for asset in (a, b):
        test_db.add(
            PortfolioAllocation(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                target_percentage=Decimal("50"),
                is_active=True,
            )
        )
    test_db.commit()

    async def holdings(self, portfolio_id):
        # A: 12 shares at 55 = 660; B: 10 at 100 = 1,000
        return [
            SimpleNamespace(
                asset_id=a.id, symbol="AAA", quantity=12.0, current_value=660.0
            ),
            SimpleNamespace(
                asset_id=b.id, symbol="BBB", quantity=10.0, current_value=1000.0
            ),
        ]

    monkeypatch.setattr(PortfolioService, "get_portfolio_holdings", holdings)
    return SimpleNamespace(portfolio=portfolio, a=a, b=b, user=user)


def _market(monkeypatch, service, closes):
    async def history(symbol):
        return {
            "close": closes,
            "splits": pd.Series(dtype=float),
            "dividends": pd.Series(dtype=float),
        }

    async def info(symbol):
        return {"long_name": "World", "currency": "EUR"}

    monkeypatch.setattr(
        service.calculations.market_data_service, "get_daily_history", history
    )
    monkeypatch.setattr(
        service.calculations.market_data_service, "get_ticker_info", info
    )


@pytest.mark.asyncio
async def test_service_splits_new_money_toward_the_targets(test_db, book):
    from modules.analytics.planner import PlannerService

    # 660 / 1,000 with 50/50 targets: after 2,060 each target is 1,030 → A 370, B 30
    result = await PlannerService(test_db).invest(book.portfolio, 400, 1)

    rows = {r["symbol"]: r for r in result["buys"]}
    assert result["mode"] == "targets"
    assert rows["AAA"]["amount"] == pytest.approx(370)
    assert rows["BBB"]["amount"] == pytest.approx(30)
    assert rows["AAA"]["shares"] == pytest.approx(370 / 55)
    assert rows["AAA"]["weight_after_pct"] == pytest.approx(50)


@pytest.mark.asyncio
async def test_service_finds_the_monthly_plan(test_db, book, monkeypatch):
    from modules.analytics.planner import PlannerService

    service = PlannerService(test_db)
    _market(
        monkeypatch, service, pd.Series([1.0], index=pd.to_datetime(["2020-01-01"]))
    )

    result = await service.savings_plans(book.portfolio)

    (plan,) = result["plans"]
    assert (plan["symbol"], plan["rhythm"], plan["executions"]) == ("AAA", "monthly", 6)
    assert plan["invested"] == 600
    assert plan["quantity"] == 12
    assert plan["value_now"] == pytest.approx(660)
    assert result["monthly_total"] == pytest.approx(100)


@pytest.mark.asyncio
async def test_service_projects_the_goal_from_the_benchmark(test_db, book, monkeypatch):
    from datetime import date

    from modules.analytics.planner import PlannerService

    service = PlannerService(test_db)
    month_ends = pd.date_range("2015-01-31", periods=61, freq="ME")
    _market(
        monkeypatch, service, pd.Series(100 * 1.01 ** np.arange(61), index=month_ends)
    )
    target_date = date.today().replace(day=1) + timedelta(days=400)

    history = await service.goal(book.portfolio, 5000, target_date, None, None)
    assumed = await service.goal(book.portfolio, 5000, target_date, 50.0, 0.0)

    # Default monthly = the active plan; history is +1 % a month
    assert history["monthly"] == pytest.approx(100)
    assert history["start_value"] == 1660
    assert history["basis"]["history_annual_pct"] == pytest.approx((1.01**12 - 1) * 100)
    months = history["months"]
    expected = 1660 * 1.01**months + 100 * sum(1.01**k for k in range(1, months + 1))
    assert history["final"]["50"] == pytest.approx(expected)
    # 0 % a year assumed: the value is just what goes in
    assert assumed["final"]["50"] == pytest.approx(1660 + 50 * months, rel=1e-3)
    assert len(history["points"]) == months
    with pytest.raises(Exception, match="month"):
        await service.goal(book.portfolio, 5000, date.today(), None)


def test_planner_routes_check_ownership_and_inputs(client, test_db, book):
    from core.auth.dependencies import get_current_active_user
    from main import app

    app.dependency_overrides[get_current_active_user] = lambda: book.user
    try:
        base = f"/api/v1/analytics/portfolios/{book.portfolio.id}/planner"
        assert client.get(f"{base}/invest?amount=0").status_code == 422
        assert client.get(f"{base}/invest?amount=400").json()["mode"] == "targets"
        assert client.get(f"{base}/goal?target=1").status_code == 422
        other = "/api/v1/analytics/portfolios/999999/planner/invest?amount=10"
        assert client.get(other).status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
