"""The only market-data source the rest of the app is allowed to call."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

import pandas as pd


class MarketDataProvider(Protocol):
    """Quotes, history, corporate actions and symbol search."""

    async def current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """Latest price for each symbol that has one."""

    async def previous_closes(self, symbols: List[str]) -> Dict[str, Decimal]:
        """Previous session close for each symbol that has one."""

    async def download(
        self, symbols: List[str], period: str, interval: str
    ) -> Dict[str, pd.DataFrame]:
        """OHLCV frames keyed by symbol."""

    async def history(
        self,
        symbol: str,
        period: str,
        interval: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """One symbol's OHLCV, newest row first. Empty when Yahoo has nothing."""

    async def daily_history(self, symbol: str) -> Optional[Dict[str, Dict[str, float]]]:
        """Split-adjusted closes plus split and dividend events, keyed by date."""

    async def ranges(self, symbol: str, start: date, end: date) -> Dict[str, Any]:
        """Daily low/high, every split, and the listing currency. Empty when missing."""

    async def infos(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Normalised ticker profiles."""

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Symbol matches for a name, ticker or ISIN."""
