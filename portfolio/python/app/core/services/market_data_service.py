"""
Market Data Service - yfinance only
Handles fetching real-time market data from yfinance without database storage.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd  # type: ignore
import yfinance as yf  # type: ignore

from core.database.redis_client import get_redis

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing market data operations using yfinance only."""

    def __init__(self) -> None:
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.redis_client = get_redis()
        # Define TTLs for different data types
        self.info_cache_ttl: int = 15 * 60  # 15 minutes for general info
        self.price_cache_ttl: int = 60  # 1 minute for current prices
        self.close_cache_ttl: int = 12 * 60 * 60  # 12 hours for previous day's close

    def _get_info_cache_key(self, symbol: str) -> str:
        """Generates a consistent cache key for ticker info."""
        return f"yfinance:info:{symbol.upper()}"

    def _get_price_cache_key(self, symbol: str) -> str:
        """Generates a consistent cache key for current price."""
        return f"yfinance:price:{symbol.upper()}"

    def _get_yesterdays_close_cache_key(self, symbol: str) -> str:
        """Generates a consistent cache key for yesterday's close price."""
        return f"yfinance:yesterday_close:{symbol.upper()}"

    def get_major_indices(self) -> Dict[str, str]:
        us_indexes = [
            {
                "name": "S&P 500",
                "symbol": "^GSPC"
            },
            {
                "name": "Dow Jones Industrial Average",
                "symbol": "^DJI"
            },
            {
                "name": "NASDAQ Composite",
                "symbol": "^IXIC"
            },
            {
                "name": "NASDAQ-100",
                "symbol": "^NDX"
            },
            {
                "name": "Russell 2000",
                "symbol": "^RUT"
            },
            {
                "name": "CBOE Volatility Index (VIX)",
                "symbol": "^VIX"
            },
            {
                "name": "S&P 100",
                "symbol": "^OEX"
            },
            {
                "name": "S&P MidCap 400",
                "symbol": "^MID"
            },
            {
                "name": "Russell 1000",
                "symbol": "^RUI"
            },
            {
                "name": "Russell 3000",
                "symbol": "^RUA"
            },
            {
                "name": "NYSE COMPOSITE",
                "symbol": "^NYA"
            },
            {
                "name": "Dow Jones Transportation Average",
                "symbol": "^DJT"
            },
            {
                "name": "Dow Jones Utility Average",
                "symbol": "^DJU"
            }
        ]
        major_world_indexes = [
            # --- Americas ---
            {
                "name": "S&P/TSX Composite (Canada)",
                "symbol": "^GSPTSE"
            },
            {
                "name": "IBOVESPA (Brazil)",
                "symbol": "^BVSP"
            },
            {
                "name": "IPC (Mexico)",
                "symbol": "^MXX"
            },

            # --- Europe ---
            {
                "name": "FTSE 100 (UK)",
                "symbol": "^FTSE"
            },
            {
                "name": "DAX (Germany)",
                "symbol": "^GDAXI"
            },
            {
                "name": "CAC 40 (France)",
                "symbol": "^FCHI"
            },
            {
                "name": "STOXX Europe 600",
                "symbol": "^STOXX"
            },
            {
                "name": "IBEX 35 (Spain)",
                "symbol": "^IBEX"
            },
            {
                "name": "FTSE MIB (Italy)",
                "symbol": "^FTMIB"
            },
            {
                "name": "Swiss Market Index (SMI)",
                "symbol": "^SSMI"
            },
            {
                "name": "AEX (Netherlands)",
                "symbol": "^AEX"
            },

            # --- Asia / Pacific ---
            {
                "name": "Nikkei 225 (Japan)",
                "symbol": "^N225"
            },
            {
                "name": "Hang Seng Index (Hong Kong)",
                "symbol": "^HSI"
            },
            {
                "name": "SSE Composite (Shanghai)",
                "symbol": "000001.SS"
            },
            {
                "name": "Shenzhen Component",
                "symbol": "399001.SZ"
            },
            {
                "name": "KOSPI (South Korea)",
                "symbol": "^KS11"
            },
            {
                "name": "S&P/ASX 200 (Australia)",
                "symbol": "^AXJO"
            },
            {
                "name": "TAIEX (Taiwan)",
                "symbol": "^TWII"
            },
            {
                "name": "Straits Times Index (Singapore)",
                "symbol": "^STI"
            }
        ]
        india_indexes = [
            {
                "name": "NIFTY 50",
                "symbol": "^NSEI"
            },
            {
                "name": "BSE SENSEX",
                "symbol": "^BSESN"
            },
            {
                "name": "NIFTY Bank",
                "symbol": "^NSEBANK"
            },
            {
                "name": "India VIX",
                "symbol": "^NIFVIX"
            },
            {
                "name": "NIFTY Next 50",
                "symbol": "^NN50"
            },
            {
                "name": "NIFTY 100",
                "symbol": "^CNX100"
            },
            {
                "name": "NIFTY 500",
                "symbol": "^CRSLDX"
            },
            {
                "name": "NIFTY Midcap 100",
                "symbol": "^CNXMIDCAP"
            }
        ]

        return us_indexes + india_indexes + major_world_indexes

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

        # 2. Fetch missing symbols from yfinance
        if symbols_to_fetch:
            logger.info("Fetching current prices for %d symbols from API.", len(symbols_to_fetch))
            tickers = yf.Tickers(" ".join(symbols_to_fetch))
            new_prices_to_cache: Dict[str, str] = {}

            for ticker in tickers.tickers.values():
                symbol = ticker.ticker
                try:
                    price = (
                            ticker.info.get("regularMarketPrice")
                            or ticker.info.get("currentPrice")
                            or ticker.info.get("previousClose")
                    )
                    if price:
                        prices[symbol] = Decimal(str(price))
                        cache_key = self._get_price_cache_key(symbol)
                        new_prices_to_cache[cache_key] = str(price)
                except Exception:
                    logger.warning("Could not retrieve price for %s", symbol)

            # 3. Cache the newly fetched data by calling `set` in a loop
            if new_prices_to_cache:
                for key, price_str in new_prices_to_cache.items():
                    await asyncio.to_thread(
                        self.redis_client.set,
                        key,
                        price_str,
                        ex_seconds=self.price_cache_ttl
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

        # 2. Fetch all missing symbols in a SINGLE API call
        if symbols_to_fetch:
            logger.info(
                "Fetching yesterday's close for %d symbols from API in a single batch.",
                len(symbols_to_fetch)
            )
            try:
                # Use yf.download for a true batch request. Get last 2 days.
                data = yf.download(
                    tickers=list(symbols_to_fetch),
                    period="2d",
                    interval="1d",
                    progress=False,
                )

                if not data.empty:
                    # Group by symbol for easy processing
                    grouped = data.groupby(axis=1, level=0)
                    new_closes_to_cache: Dict[str, str] = {}

                    for symbol, group_df in grouped:
                        symbol_upper = symbol.upper()
                        # Sort by date to ensure the latest is last
                        group_df = group_df.sort_index()
                        if len(group_df) > 1:
                            # The previous close is the 'Close' of the first row
                            previous_close = group_df['Close'].iloc[0]
                            if pd.notna(previous_close):
                                closes[symbol_upper] = Decimal(str(previous_close))
                                cache_key = self._get_yesterdays_close_cache_key(symbol_upper)
                                new_closes_to_cache[cache_key] = str(previous_close)

                    # 3. Cache new data (your logic is fine, just now truly batched)
                    if new_closes_to_cache:
                        for key, price_str in new_closes_to_cache.items():
                            await asyncio.to_thread(
                                self.redis_client.set,
                                key,
                                price_str,
                                ex_seconds=self.close_cache_ttl
                            )

            except Exception as e:
                logger.error(
                    "Failed to fetch historical data for yesterdays's closes: %s", e
                )

        return closes

    async def get_historical_data(self, symbols: List[str], period: str = "1y", interval: str = "1d") -> Dict[
        str, pd.DataFrame]:
        """
        A new, optimized method for fetching historical data for multiple tickers.
        Uses yf.download and returns a dictionary of DataFrames, one for each symbol.
        """
        if not symbols:
            return {}

        def fetch_sync():
            data = yf.download(
                tickers=" ".join(symbols),
                period=period,
                interval=interval,
                group_by='ticker',  # Crucial for separating data by ticker
                progress=False,
            )
            return data

        data = await asyncio.to_thread(fetch_sync)

        # yf.download returns a MultiIndex DataFrame for multiple tickers
        if isinstance(data.columns, pd.MultiIndex):
            # Create a dictionary of dataframes for each symbol
            return {symbol: data[symbol].dropna(how='all').reset_index() for symbol in symbols if symbol in data}
        # For a single ticker, it returns a simple DataFrame
        elif not data.empty:
            return {symbols[0]: data.dropna(how='all').reset_index()}

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
            DataFrame with market data or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.info("Fetching data for %s (attempt %d)", symbol, attempt + 1)

                ticker = yf.Ticker(symbol)

                if start_date and end_date:
                    data = ticker.history(
                        start=start_date, end=end_date, interval=interval
                    )
                else:
                    data = ticker.history(period=period, interval=interval)

                if not isinstance(data, pd.DataFrame) or data.empty:
                    logger.warning("No data returned for %s", symbol)
                    return pd.DataFrame()

                logger.info("Successfully fetched %d records for %s", len(data), symbol)

                # Reset index to make Date a column
                data = data.reset_index()

                # Ensure we have the expected columns
                expected_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
                if not all(col in data.columns for col in expected_columns):
                    logger.warning("Missing expected columns in data for %s", symbol)
                    return pd.DataFrame()

                # Sort by date descending (most recent first)
                data = data.sort_values(by="Date", ascending=False)

                return data

            except Exception as e:
                logger.error("Attempt %d failed for %s: %s", attempt + 1, symbol, e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("All attempts failed for %s", symbol)
                    return pd.DataFrame()

    async def search_symbols(
            self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:  # noqa: ARG002
        """
        Search for stock symbols using yfinance.
        Note: This is a basic implementation. For production, consider using
        a dedicated symbol search API.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching symbols with basic info
        """
        try:
            # This is a simple implementation - in production you might want
            # to use a more sophisticated search API

            # Try to get info for the query as a direct symbol
            ticker_info = await self.get_ticker_info(query.upper())

            if ticker_info:
                return [
                    {
                        "symbol": ticker_info["symbol"],
                        "name": ticker_info.get("longName")
                                or ticker_info.get("shortName"),
                        "exchange": ticker_info.get("exchange"),
                        "currency": ticker_info.get("currency"),
                        "type": ticker_info.get("quoteType"),
                    }
                ]
            else:
                return []

        except Exception as e:
            logger.error("Error searching symbols for query '%s': %s", query, e)
            return []

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
            return {"is_open": None, "error": str(e)}

    def _extract_ticker_information(self, ticker_info: Dict[str, Any]) -> Dict[str, Any]:
        # Extract and normalize the information
        ticker_data = {
            "symbol": ticker_info.get("symbol").upper(),
            "long_name": ticker_info.get("longName"),
            "short_name": ticker_info.get("shortName"),
            "sector": ticker_info.get("sector"),
            "industry": ticker_info.get("industry"),
            "exchange": ticker_info.get("exchangeDisp", ticker_info.get("exchange")),
            "currency": ticker_info.get("currency"),
            "country": ticker_info.get("country"),
            "quote_type": ticker_info.get("quoteType"),
            "market_cap": ticker_info.get("marketCap"),
            "current_price": ticker_info.get("currentPrice", ticker_info.get("regularMarketPrice")),
            "price_change_percentage_24h": ticker_info.get('regularMarketChangePercent', 0),
            "previous_close": ticker_info.get("previousClose"),
            "open": ticker_info.get("open"),
            "day_low": ticker_info.get("dayLow"),
            "low_52w": ticker_info.get('fiftyTwoWeekLow'),
            "high_52w": ticker_info.get('fiftyTwoWeekHigh'),
            "day_high": ticker_info.get("dayHigh"),
            "volume": ticker_info.get("volume"),
            "average_volume": ticker_info.get("averageVolume"),
            "volume_24h": ticker_info.get("regularMarketVolume"),
            "beta": ticker_info.get("beta"),
            "trailing_PE": ticker_info.get("trailingPE"),
            "forward_PE": ticker_info.get("forwardPE"),
            "dividend_yield": ticker_info.get("dividendYield"),
            "payout_ratio": ticker_info.get("payoutRatio"),
            "book_value": ticker_info.get("bookValue"),
            "price_to_book": ticker_info.get("priceToBook"),
            "earnings_growth": ticker_info.get("earningsGrowth"),
            "revenue_growth": ticker_info.get("revenueGrowth"),
            "return_on_asset": ticker_info.get("returnOnAssets"),
            "return_on_equity": ticker_info.get("returnOnEquity"),
            "free_cashflow": ticker_info.get("freeCashflow"),
            "operating_cashflow": ticker_info.get("operatingCashflow"),
            "total_debt": ticker_info.get("totalDebt"),
            "total_cash": ticker_info.get("totalCash"),
            "long_business_summary": ticker_info.get("longBusinessSummary"),
            "website": ticker_info.get("website"),
            "full_time_employees": ticker_info.get("fullTimeEmployees"),
        }
        return ticker_data

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
            if data and 'symbol' in data:
                results.append(data)
                symbols_found_in_cache.add(data['symbol'])

        symbols_to_fetch = list(symbols_in_request - symbols_found_in_cache)

        if not symbols_to_fetch:
            return results

        # 2. Fetch missing symbols
        logger.info("Fetching info for %d symbols from API: %s", len(symbols_to_fetch), ", ".join(symbols_to_fetch))
        tickers = yf.Tickers(" ".join(symbols_to_fetch))
        new_data_to_cache: Dict[str, Dict[str, Any]] = {}

        for symbol in symbols_to_fetch:
            try:
                info = tickers.tickers[symbol].info
                if info and info.get("symbol"):
                    extracted_data = self._extract_ticker_information(info)
                    results.append(extracted_data)
                    cache_key = self._get_info_cache_key(symbol)
                    # Store the dict directly; your client's `set` will serialize it
                    new_data_to_cache[cache_key] = extracted_data
                else:
                    logger.warning("Incomplete info fetched for symbol: %s", symbol)
            except Exception as e:
                logger.error("Error processing ticker info for %s: %s", symbol, e)

        # 3. Cache new data by calling `set` in a loop
        if new_data_to_cache:
            for key, data_dict in new_data_to_cache.items():
                await asyncio.to_thread(
                    self.redis_client.set,
                    key,
                    data_dict,
                    ex_seconds=self.info_cache_ttl
                )
        return results


# Global instance
market_data_service = MarketDataService()
