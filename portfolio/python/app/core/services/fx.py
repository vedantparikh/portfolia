"""Load the Yahoo rates `core.domain.fx` multiplies by. No conversion maths here."""

import logging
from typing import Iterable

import pandas as pd

from core.domain.fx import MissingFxError, canonical_currency
from core.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


async def load_rates(
    market_data: MarketDataService,
    portfolio_currency: str,
    currencies: Iterable[str | None],
    *,
    strict: bool = True,
) -> dict[str, pd.Series]:
    """
    `{major quote: portfolio-per-1-quote}` for every currency that is not already
    the portfolio's. Same-currency books return `{}` and fetch nothing.
    """
    portfolio, _ = canonical_currency(portfolio_currency)
    rates: dict[str, pd.Series] = {}
    for code in currencies:
        major, _ = canonical_currency(code)
        if not major or major == portfolio or major in rates:
            continue
        try:
            rates[major] = await market_data.get_fx_rates(major, portfolio)
        except MissingFxError:
            if strict:
                raise
            logger.warning("No exchange rate from %s to %s", major, portfolio)
    return rates
