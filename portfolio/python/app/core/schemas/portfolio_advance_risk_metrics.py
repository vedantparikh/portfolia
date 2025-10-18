from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AdvanceRiskMetrics(BaseModel):
    """A nested model for portfolio advance risk metrics."""

    beta: Optional[Decimal] = Field(
        None, description="Beta parameter for portfolio advance risk metrics."
    )
    jensens_alpha_pct: Optional[Decimal] = Field(None, description="Alpha percentage.")
    concentration_risk_hhi: Optional[Decimal] = Field(
        None, description="The risk of concentration.")
    diversification_ratio: Optional[Decimal] = Field(None, description="Diversification ratio.")
    effective_number_of_assets: Optional[Decimal] = Field(
        None, description="Effective number of assets."
    )


class AdvanceRiskCalculationResponse(BaseModel):
    """
    Defines the structure for a portfolio risk calculation response,
    encapsulating identification, period, potential errors, and a
    comprehensive set of risk metrics.
    """

    portfolio_id: int = Field(..., description="The unique identifier for the portfolio.")
    period: str = Field(..., description="The time period for which the risk was calculated (e.g., '1Y', 'YTD').")
    error: Optional[str] = Field(None, description="An error message if the calculation failed, otherwise null.")
    metrics: AdvanceRiskMetrics = Field(..., description="A container for the calculated risk metrics.")
