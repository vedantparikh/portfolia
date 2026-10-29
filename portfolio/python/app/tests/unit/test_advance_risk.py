"""Advanced metrics with closed positions and holdings Yahoo cannot price."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from modules.analytics.advance_risk import PortfolioAdvanceRiskMetricsService

DAYS = pd.bdate_range("2025-11-03", periods=250)


def prices(seed):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(rng.normal(0, 0.01, len(DAYS)).cumsum())
    return pd.DataFrame({"Close": close}, index=DAYS.date)


@pytest.mark.asyncio
async def test_closed_and_unpriced_holdings_are_left_out():
    service = PortfolioAdvanceRiskMetricsService(db=None)
    history = pd.DataFrame(
        {"daily_return": prices(1)["Close"].pct_change().to_numpy()}, index=DAYS
    )
    frames = {"AAA": prices(2), "BBB": prices(3), "EUNL.DE": prices(4)}

    async def price_data(symbol):
        # An ISIN Yahoo rejects comes back as an empty frame
        return frames.get(symbol, pd.DataFrame())

    async def portfolio_history(*args):
        return history

    async def holdings(portfolio_id):
        return [
            SimpleNamespace(symbol="AAA", quantity=10, current_value=600.0),
            SimpleNamespace(symbol="BBB", quantity=5, current_value=300.0),
            SimpleNamespace(symbol="DE000HM54L25", quantity=2, current_value=100.0),
            SimpleNamespace(symbol="DE000HT63521", quantity=0, current_value=None),
        ]

    service.calculation_service = SimpleNamespace(
        get_transactions=lambda *args: [object()],
        get_portfolio_history=portfolio_history,
        get_price_data=price_data,
        default_benchmark_for=lambda portfolio_id: "EUNL.DE",
    )
    service.portfolio_service = SimpleNamespace(get_portfolio_holdings=holdings)

    result = await service.calculate_advanced_metrics(16, "1y")

    assert "error" not in result, result
    metrics = result["metrics"]
    assert result["benchmark_symbol"] == "EUNL.DE"
    assert metrics["beta"] is not None
    # Weights 0.6, 0.3, 0.1 over the open positions; the closed one counts nowhere
    assert metrics["concentration_risk_hhi"] == pytest.approx(0.36 + 0.09 + 0.01)
    assert metrics["diversification_ratio"] > 1
