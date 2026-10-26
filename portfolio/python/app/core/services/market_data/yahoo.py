"""Yahoo Finance, behind one concurrency limit and one backoff policy."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd  # type: ignore
import yfinance as yf  # type: ignore

from core.services.market_data.sessions import previous_session_close

logger = logging.getLogger(__name__)

YAHOO_CONCURRENCY = 4
YAHOO_ATTEMPTS = 3
YAHOO_BASE_DELAY = 0.5


class YahooMarketDataProvider:
    """yfinance calls. At most `concurrency` run at once; failures back off."""

    def __init__(
        self,
        concurrency: int = YAHOO_CONCURRENCY,
        attempts: int = YAHOO_ATTEMPTS,
        base_delay: float = YAHOO_BASE_DELAY,
    ) -> None:
        self._gate = asyncio.Semaphore(concurrency)
        self.attempts = attempts
        self.base_delay = base_delay

    async def run(self, func, /, *args, **kwargs):
        """Run a blocking Yahoo call with the shared limit and exponential backoff."""
        delay = self.base_delay
        for attempt in range(self.attempts):
            try:
                async with self._gate:
                    return await asyncio.to_thread(func, *args, **kwargs)
            except Exception:
                if attempt + 1 >= self.attempts:
                    raise
                logger.warning(
                    "Yahoo call failed (attempt %d/%d); retrying in %.1fs",
                    attempt + 1,
                    self.attempts,
                    delay,
                )
                await asyncio.sleep(delay)
                delay *= 2

    async def current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        return await self.run(self._current_prices, symbols)

    async def previous_closes(self, symbols: List[str]) -> Dict[str, Decimal]:
        return await self.run(self._previous_closes, symbols)

    async def download(
        self, symbols: List[str], period: str, interval: str
    ) -> Dict[str, pd.DataFrame]:
        return await self.run(self._download, symbols, period, interval)

    async def history(
        self,
        symbol: str,
        period: str,
        interval: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        return await self.run(
            self._history, symbol, period, interval, start_date, end_date
        )

    async def daily_history(self, symbol: str) -> Optional[Dict[str, Dict[str, float]]]:
        return await self.run(self._daily_history, symbol)

    async def ranges(self, symbol: str, start: date, end: date) -> Dict[str, Any]:
        return await self.run(self._ranges, symbol, start, end)

    async def infos(self, symbols: List[str]) -> List[Dict[str, Any]]:
        return await self.run(self._infos, symbols)

    async def search(self, query: str) -> List[Dict[str, Any]]:
        return await self.run(self._search, query)

    def _current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        prices: Dict[str, Decimal] = {}
        tickers = yf.Tickers(" ".join(symbols))
        for ticker in tickers.tickers.values():
            symbol = ticker.ticker
            try:
                price = (
                    ticker.info.get("regularMarketPrice")
                    or ticker.info.get("currentPrice")
                    or ticker.info.get("previousClose")
                )
                if price:
                    prices[symbol.upper()] = Decimal(str(price))
            except Exception:
                logger.warning("Could not retrieve price for %s", symbol)
        return prices

    def _previous_closes(self, symbols: List[str], now=None) -> Dict[str, Decimal]:
        """Last completed session, not the older of two downloaded rows."""
        if not symbols:
            return {}
        now = now or datetime.now(timezone.utc)
        data = yf.download(
            tickers=list(symbols),
            period="10d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            group_by="ticker",
        )
        if data is None or data.empty:
            return {}
        closes: Dict[str, Decimal] = {}
        for symbol in symbols:
            price = previous_session_close(_close_series(data, symbol), now)
            if price is not None:
                closes[symbol.upper()] = price
        return closes

    def _download(
        self, symbols: List[str], period: str, interval: str
    ) -> Dict[str, pd.DataFrame]:
        data = yf.download(
            tickers=" ".join(symbols),
            period=period,
            interval=interval,
            group_by="ticker",
            progress=False,
        )
        if isinstance(data.columns, pd.MultiIndex):
            return {
                symbol: data[symbol].dropna(how="all").reset_index()
                for symbol in symbols
                if symbol in data
            }
        if not data.empty:
            return {symbols[0]: data.dropna(how="all").reset_index()}
        return {}

    def _history(
        self,
        symbol: str,
        period: str,
        interval: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        if start_date and end_date:
            data = ticker.history(start=start_date, end=end_date, interval=interval)
        else:
            data = ticker.history(period=period, interval=interval)
        if not isinstance(data, pd.DataFrame) or data.empty:
            return pd.DataFrame()
        data = data.reset_index()
        expected = ["Date", "Open", "High", "Low", "Close", "Volume"]
        if not all(col in data.columns for col in expected):
            return pd.DataFrame()
        return data.sort_values(by="Date", ascending=False)

    def _daily_history(self, symbol: str) -> Optional[Dict[str, Dict[str, float]]]:
        data = yf.Ticker(symbol).history(
            period="max", interval="1d", auto_adjust=False, actions=True
        )
        if not isinstance(data, pd.DataFrame) or data.empty:
            return None
        days = data.index.tz_localize(None).strftime("%Y-%m-%d")
        out: Dict[str, Dict[str, float]] = {}
        for column, name in (
            ("Close", "close"),
            ("Stock Splits", "splits"),
            ("Dividends", "dividends"),
        ):
            values = data[column] if column in data else pd.Series(dtype=float)
            out[name] = {
                day: float(value)
                for day, value in zip(days, values)
                if pd.notna(value) and (name == "close" or value > 0)
            }
        if not out["close"]:
            return None
        return out

    def _ranges(self, symbol: str, start: date, end: date) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        data = ticker.history(
            start=start, end=end + timedelta(days=1), auto_adjust=False
        )
        if not isinstance(data, pd.DataFrame) or data.empty:
            return {}
        days = data.index.tz_localize(None).strftime("%Y-%m-%d")
        splits = ticker.splits
        return {
            "currency": (ticker.history_metadata or {}).get("currency"),
            "ranges": {
                day: [float(low), float(high)]
                for day, low, high in zip(days, data["Low"], data["High"])
                if pd.notna(low) and pd.notna(high)
            },
            "splits": {
                ts.strftime("%Y-%m-%d"): float(ratio)
                for ts, ratio in splits.items()
                if ratio > 0
            },
        }

    def _infos(self, symbols: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        tickers = yf.Tickers(" ".join(symbols))
        for symbol in symbols:
            try:
                info = tickers.tickers[symbol].info
                if info and info.get("symbol"):
                    results.append(_ticker_information(info))
                else:
                    logger.warning("Incomplete info fetched for symbol: %s", symbol)
            except Exception:
                logger.error("Error processing ticker info for %s", symbol)
        return results

    def _search(self, query: str) -> List[Dict[str, Any]]:
        found = yf.Search(query, max_results=20, news_count=0)
        quotes = found.quotes or []
        return [
            _quote(quote)
            for quote in quotes
            if isinstance(quote, dict) and quote.get("symbol")
        ]


def _close_series(data: pd.DataFrame, symbol: str) -> pd.Series:
    """The Close column for one symbol, for either Yahoo column layout."""
    symbol = symbol.upper()
    if isinstance(data.columns, pd.MultiIndex):
        levels = [data.columns.get_level_values(i) for i in range(data.columns.nlevels)]
        if symbol in levels[0]:
            frame = data[symbol]
        elif symbol in levels[-1]:
            frame = data.xs(symbol, axis=1, level=-1)
        else:
            return pd.Series(dtype=float)
    else:
        frame = data
    if isinstance(frame, pd.Series):
        return frame
    if "Close" not in frame.columns:
        return pd.Series(dtype=float)
    return frame["Close"]


def _first(raw: Dict[str, Any], *keys: str):
    for key in keys:
        value = raw.get(key)
        if value:
            return value
    return None


def _quote(raw: Dict[str, Any]) -> Dict[str, Any]:
    cap = raw.get("marketCap", raw.get("market_cap"))
    try:
        market_cap = int(cap) if cap is not None and cap != "" else None
    except (TypeError, ValueError):
        market_cap = None
    return {
        "symbol": raw["symbol"],
        "short_name": _first(raw, "shortName", "shortname", "short_name"),
        "long_name": _first(raw, "longName", "longname", "long_name"),
        "quote_type": _first(raw, "quoteType", "quotetype", "quote_type"),
        "exchange": _first(raw, "exchDisp", "exchdisp", "exchange"),
        "market": raw.get("market"),
        "currency": raw.get("currency"),
        "sector": _first(raw, "sectorDisp", "sector"),
        "industry": _first(raw, "industryDisp", "industry"),
        "market_cap": market_cap,
    }


def _ticker_information(ticker_info: Dict[str, Any]) -> Dict[str, Any]:
    return {
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
        "current_price": ticker_info.get(
            "currentPrice", ticker_info.get("regularMarketPrice")
        ),
        "price_change_percentage_24h": ticker_info.get("regularMarketChangePercent", 0),
        "previous_close": ticker_info.get("previousClose"),
        "open": ticker_info.get("open"),
        "day_low": ticker_info.get("dayLow"),
        "low_52w": ticker_info.get("fiftyTwoWeekLow"),
        "high_52w": ticker_info.get("fiftyTwoWeekHigh"),
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
