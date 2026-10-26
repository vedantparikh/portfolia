"""
Market Data Service - yfinance only
Handles fetching real-time market data from yfinance without database storage.
"""

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd  # type: ignore

from core.database.redis_client import get_redis
from core.domain.fx import MissingFxError, canonical_currency
from core.services.market_data.provider import MarketDataProvider
from core.services.market_data.yahoo import YahooMarketDataProvider

logger = logging.getLogger(__name__)

_LISTING_TYPES = ("EQUITY", "ETF", "MUTUALFUND", "CRYPTOCURRENCY")


class MarketDataService:
    """Cached market data. Yahoo calls go through one provider."""

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        redis_client=None,
    ) -> None:
        self.provider = provider or YahooMarketDataProvider()
        self.redis_client = redis_client if redis_client is not None else get_redis()
        # Define TTLs for different data types
        self.info_cache_ttl: int = 15 * 60  # 15 minutes for general info
        self.price_cache_ttl: int = 60  # 1 minute for current prices
        self.close_cache_ttl: int = 12 * 60 * 60  # 12 hours for previous day's close
        self.daily_history_cache_ttl: int = 6 * 60 * 60
        self.listing_cache_ttl: int = 7 * 24 * 60 * 60
        self.range_cache_ttl: int = 24 * 60 * 60

    def _get_info_cache_key(self, symbol: str) -> str:
        """Generates a consistent cache key for ticker info."""
        return f"yfinance:info:{symbol.upper()}"

    def _get_price_cache_key(self, symbol: str) -> str:
        """Generates a consistent cache key for current price."""
        return f"yfinance:price:{symbol.upper()}"

    def _get_yesterdays_close_cache_key(self, symbol: str) -> str:
        """Generates a consistent cache key for yesterday's close price."""
        return f"yfinance:yesterday_close:{symbol.upper()}"

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """OPTIMIZED: Wraps the batch method for efficiency."""
        prices = await self.get_current_prices([symbol])
        price = prices.get(symbol.upper())
        return float(price) if price is not None else None

    async def get_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        ADAPTED: Fetches current prices for a list of symbols, with caching,
        using the custom RedisClient.
        """
        if not symbols:
            return {}

        prices: Dict[str, Decimal] = {}
        symbols_upper = [s.upper() for s in symbols]
        symbols_to_fetch = set(symbols_upper)

        # 1. Check Redis cache using the custom client's mget
        cache_keys = [self._get_price_cache_key(s) for s in symbols_upper]
        # Your mget conveniently returns a dictionary of found keys to values
        cached_data = await asyncio.to_thread(self.redis_client.mget, cache_keys)

        for symbol in symbols_upper:
            cache_key = self._get_price_cache_key(symbol)
            if cache_key in cached_data:
                # The custom client's mget already deserializes from JSON
                prices[symbol] = Decimal(str(cached_data[cache_key]))
                symbols_to_fetch.remove(symbol)

        if symbols_to_fetch:
            logger.info(
                "Fetching current prices for %d symbols from API.",
                len(symbols_to_fetch),
            )
            try:
                fetched = await self.provider.current_prices(list(symbols_to_fetch))
            except Exception:
                logger.error("Current price fetch failed for %s", symbols_to_fetch)
                fetched = {}
            new_prices_to_cache: Dict[str, str] = {}
            for symbol, price in fetched.items():
                symbol = symbol.upper()
                prices[symbol] = price
                new_prices_to_cache[self._get_price_cache_key(symbol)] = str(price)
            if new_prices_to_cache:
                await asyncio.to_thread(
                    self.redis_client.mset,
                    new_prices_to_cache,
                    self.price_cache_ttl,
                )
        return prices

    async def get_yesterdays_close(self, symbol: str) -> Optional[float]:
        """OPTIMIZED: Wraps the batch method."""
        closes = await self.get_yesterdays_closes([symbol])
        close_price = closes.get(symbol.upper())
        return float(close_price) if close_price is not None else None

    async def get_yesterdays_closes(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        ADAPTED & OPTIMIZED: Fetches previous day's closing prices with caching,
        using a true batch operation for API calls.
        """
        if not symbols:
            return {}

        closes: Dict[str, Decimal] = {}
        symbols_upper = [s.upper() for s in symbols]
        symbols_to_fetch = set(symbols_upper)

        # 1. Check Redis cache (this part is already good)
        cache_keys = [self._get_yesterdays_close_cache_key(s) for s in symbols_upper]
        cached_data = await asyncio.to_thread(self.redis_client.mget, cache_keys)

        for symbol in symbols_upper:
            cache_key = self._get_yesterdays_close_cache_key(symbol)
            if cache_key in cached_data:
                closes[symbol] = Decimal(str(cached_data[cache_key]))
                symbols_to_fetch.remove(symbol)

        if symbols_to_fetch:
            logger.info(
                "Fetching yesterday's close for %d symbols from API in a single batch.",
                len(symbols_to_fetch),
            )
            try:
                fetched = await self.provider.previous_closes(list(symbols_to_fetch))
            except Exception as e:
                logger.error(
                    "Failed to fetch historical data for yesterdays's closes: %s", e
                )
                fetched = {}
            new_closes_to_cache = {
                self._get_yesterdays_close_cache_key(symbol): str(price)
                for symbol, price in fetched.items()
            }
            closes.update(fetched)
            if new_closes_to_cache:
                await asyncio.to_thread(
                    self.redis_client.mset,
                    new_closes_to_cache,
                    self.close_cache_ttl,
                )

        return closes

    async def get_historical_data(
        self, symbols: List[str], period: str = "1y", interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Historical OHLCV for several tickers, one frame each.
        """
        if not symbols:
            return {}
        try:
            return await self.provider.download(symbols, period, interval)
        except Exception as e:
            logger.error("Historical download failed: %s", e)
            return {}

    async def fetch_ticker_data(
        self,
        symbol: str,
        period: str = "max",
        interval: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch ticker data from yfinance with retry logic.

        Args:
            symbol: Stock symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with market data, or an empty frame if Yahoo has nothing
        """
        try:
            return await self.provider.history(
                symbol, period, interval, start_date, end_date
            )
        except Exception as e:
            logger.error("All attempts failed for %s: %s", symbol, e)
            return pd.DataFrame()

    async def get_daily_history(self, symbol: str) -> Optional[Dict[str, pd.Series]]:
        """
        Daily history for valuation: `close` is split-adjusted but not
        dividend-adjusted (dividends come from DIVIDEND transactions), plus the
        `splits` (ratio) and `dividends` (per share) on their ex-dates.
        Series are indexed by naive dates. Cached in Redis; None if unavailable.
        """
        key = f"yfinance:daily:{symbol.upper()}"
        cached = await asyncio.to_thread(self.redis_client.get, key)
        if not cached:
            try:
                cached = await self.provider.daily_history(symbol)
            except Exception as e:
                logger.error("Daily history fetch failed for %s: %s", symbol, e)
                return None
            if not cached or not cached["close"]:
                return None
            await asyncio.to_thread(
                self.redis_client.set,
                key,
                cached,
                ex_seconds=self.daily_history_cache_ttl,
            )

        return {
            name: pd.Series(
                list(values.values()), index=pd.to_datetime(list(values)), dtype=float
            )
            for name, values in cached.items()
        }

    async def get_fx_rates(self, quote: str, portfolio: str) -> pd.Series:
        """
        Portfolio currency per 1 unit of `quote`, from Yahoo `{QUOTE}{PORTFOLIO}=X`.

        Falls back to the inverse pair. Cached with the other daily history (6h).
        Same currency is not a rate; callers skip the fetch.
        """
        quote_major, _ = canonical_currency(quote)
        portfolio_major, _ = canonical_currency(portfolio)
        if quote_major == portfolio_major:
            return pd.Series(dtype=float)
        direct = await self.get_daily_history(f"{quote_major}{portfolio_major}=X")
        if direct is not None and not direct["close"].dropna().empty:
            return direct["close"]
        inverse = await self.get_daily_history(f"{portfolio_major}{quote_major}=X")
        if inverse is not None:
            close = inverse["close"].replace(0, pd.NA).dropna()
            inverted = (
                (1.0 / close).replace([float("inf"), float("-inf")], pd.NA).dropna()
            )
            if not inverted.empty:
                return inverted
        raise MissingFxError(quote_major, portfolio_major)

    async def search_quotes(self, query: str) -> List[Dict[str, Any]]:
        """Every Yahoo match for a name, ticker or ISIN. Cached for 7 days."""
        key = f"yfinance:search:{query.strip().lower()}"
        cached = await asyncio.to_thread(self.redis_client.get, key)
        if cached is not None:
            return cached
        try:
            quotes = await self.provider.search(query)
        except Exception as e:
            logger.warning("Symbol search failed for %r: %s", query, e)
            return []
        await asyncio.to_thread(
            self.redis_client.set, key, quotes, ex_seconds=self.listing_cache_ttl
        )
        return quotes

    async def search_listings(self, query: str) -> List[Dict[str, Any]]:
        """Equities, ETFs, funds and crypto from the same search as the UI."""
        return [
            {
                "symbol": quote["symbol"],
                "exchange": quote.get("exchange"),
                "quote_type": quote.get("quote_type"),
                "name": quote.get("long_name") or quote.get("short_name"),
            }
            for quote in await self.search_quotes(query)
            if quote.get("quote_type") in _LISTING_TYPES
        ]

    async def get_daily_ranges(
        self, symbol: str, start: date, end: date
    ) -> Optional[Dict[str, Any]]:
        """
        Daily low/high between start and end (split-adjusted, as Yahoo serves
        them), every split of the listing (ratio by date) and its currency.
        None when the listing has no prices in the window.
        """
        key = f"yfinance:ranges:{symbol.upper()}:{start}:{end}"
        cached = await asyncio.to_thread(self.redis_client.get, key)
        if cached is None:
            try:
                cached = await self.provider.ranges(symbol, start, end)
            except Exception as e:
                logger.info("No daily ranges for %s: %s", symbol, e)
                cached = {}
            await asyncio.to_thread(
                self.redis_client.set, key, cached, ex_seconds=self.range_cache_ttl
            )
        return cached or None

    def get_supported_periods(self) -> List[str]:
        """Get list of supported period values."""
        return ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]

    def get_supported_intervals(self) -> List[str]:
        """Get list of supported interval values."""
        return [
            "1m",
            "2m",
            "5m",
            "15m",
            "30m",
            "60m",
            "90m",
            "1h",
            "1d",
            "5d",
            "1wk",
            "1mo",
            "3mo",
        ]

    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status.
        Note: This is a basic implementation using market hours.
        """
        try:
            # Get current time in Eastern Time (US market timezone)
            import pytz  # type: ignore

            et = pytz.timezone("US/Eastern")
            now_et = datetime.now(et)

            # Basic market hours check (9:30 AM - 4:00 PM ET, Monday-Friday)
            is_weekday = now_et.weekday() < 5  # Monday = 0, Friday = 4
            market_open_time = now_et.replace(
                hour=9, minute=30, second=0, microsecond=0
            )
            market_close_time = now_et.replace(
                hour=16, minute=0, second=0, microsecond=0
            )

            is_market_hours = market_open_time <= now_et <= market_close_time
            is_open = is_weekday and is_market_hours

            return {
                "is_open": is_open,
                "current_time_et": now_et.isoformat(),
                "next_open": None,  # Would need more complex logic
                "next_close": None,  # Would need more complex logic
                "timezone": "US/Eastern",
            }

        except Exception as e:
            logger.error("Error getting market status: %s", e)
            return {"is_open": None, "error": "Market status unavailable"}

    async def get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """OPTIMIZED: Wraps the cached batch method."""
        results = await self.get_symbols_info([symbol])
        return results[0] if results else None

    async def get_symbols_info(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        ADAPTED: Gets comprehensive ticker info, using the custom RedisClient.
        """
        if not symbols:
            return []

        results: List[Dict[str, Any]] = []
        symbols_in_request = set(s.upper() for s in symbols)
        symbols_found_in_cache = set()

        # 1. Check Redis cache
        cache_keys = [self._get_info_cache_key(s) for s in symbols_in_request]
        cached_data = await asyncio.to_thread(self.redis_client.mget, cache_keys)

        for data in cached_data.values():
            if data and "symbol" in data:
                results.append(data)
                symbols_found_in_cache.add(data["symbol"])

        symbols_to_fetch = list(symbols_in_request - symbols_found_in_cache)

        if not symbols_to_fetch:
            return results

        logger.info(
            "Fetching info for %d symbols from API: %s",
            len(symbols_to_fetch),
            ", ".join(symbols_to_fetch),
        )
        try:
            fetched = await self.provider.infos(symbols_to_fetch)
        except Exception as e:
            logger.error("Ticker info fetch failed: %s", e)
            return results
        new_data_to_cache: Dict[str, Dict[str, Any]] = {}
        for extracted in fetched:
            results.append(extracted)
            symbol = extracted.get("symbol")
            if symbol:
                new_data_to_cache[self._get_info_cache_key(symbol)] = extracted
        if new_data_to_cache:
            await asyncio.to_thread(
                self.redis_client.mset,
                new_data_to_cache,
                self.info_cache_ttl,
            )
        return results


# Global instance
market_data_service = MarketDataService()
