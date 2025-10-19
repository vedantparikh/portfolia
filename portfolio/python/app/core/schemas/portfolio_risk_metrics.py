from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    """A nested model for portfolio risk metrics."""

    annualized_volatility_pct: Optional[Decimal] = Field(
        None, description="Annualized portfolio volatility in percent."
    )
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio.")
    max_drawdown: Optional[Decimal] = Field(
        None, description="The largest peak-to-trough decline in portfolio value."
    )
    value_at_risk_95_pct: Optional[Decimal] = Field(
        None, description="95% Value at Risk (VaR) in percent."
    )
    value_at_risk_99_pct: Optional[Decimal] = Field(
        None, description="99% Value at Risk (VaR) in percent."
    )
    sortino_ratio: Optional[Decimal] = Field(None, description="Sortino ratio.")
    cvar_95: Optional[Decimal] = Field(None, description="95% Value at Risk (VaR) in percent.")
    calmar_ratio: Optional[Decimal] = Field(None, description="Calmar ratio.")


class RiskAssessmentMetrics(BaseModel):
    """A nested model for portfolio risk assessment metrics."""

    level: Optional[str] = Field(None, description="Level of risk assessment.")
    reasoning: Optional[str] = Field(None, description="Reasoning for risk assessment.")


class RiskCalculationResponse(BaseModel):
    """
    Defines the structure for a portfolio risk calculation response,
    encapsulating identification, period, potential errors, and a
    comprehensive set of risk metrics.
    """

    portfolio_id: int = Field(..., description="The unique identifier for the portfolio.")
    period: str = Field(..., description="The time period for which the risk was calculated (e.g., '1Y', 'YTD').")
    error: Optional[str] = Field(None, description="An error message if the calculation failed, otherwise null.")
    metrics: RiskMetrics = Field(..., description="A container for the calculated risk metrics.")
    risk_assessment: Optional[RiskAssessmentMetrics] = Field(
        ..., description="A container for the risk assessment metrics."
        )
