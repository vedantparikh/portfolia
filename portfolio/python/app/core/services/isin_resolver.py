"""
Map ISINs from a broker export to the Yahoo listing they were traded on.

Yahoo search by ISIN usually returns only the primary listing (AAPL in USD),
while a German broker fills in EUR on a German venue. Candidates therefore come
from ISIN search, name search and every German venue of any German code found;
each candidate is scored by how many of the statement's fills fall inside that
day's low-high range (after undoing later splits). Ties go to the venue whose
hours are closest to Trade Republic's (LS Exchange, 7:30-23:00), which Yahoo
does not carry.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from core.database.models import Asset
from core.schemas.account_statements import (
    Fill,
    InstrumentResolution,
    ListingCandidate,
    ParsedInstrument,
)
from core.services.market_data_service import MarketDataService

GERMAN_VENUES = (".F", ".SG", ".DE", ".MU", ".DU", ".HM", ".BE", ".HA")
VENUE_NAMES = {
    ".F": "Frankfurt",
    ".SG": "Stuttgart",
    ".DE": "XETRA",
    ".MU": "Munich",
    ".DU": "Düsseldorf",
    ".HM": "Hamburg",
    ".BE": "Berlin",
    ".HA": "Hanover",
}
TOLERANCE = 0.01
MATCHED = 0.9
PLAUSIBLE = 0.5
MAX_SEARCH_RESULTS = 14
MAX_CANDIDATES = 30


def crypto_symbol(isin: str) -> Optional[str]:
    """Trade Republic's crypto pseudo-ISINs: XF000XRP0018 → XRP-EUR."""
    if not isin.startswith("XF000"):
        return None
    code = isin[5:].rstrip("0123456789")
    return f"{code}-EUR" if code else None


def german_variants(symbols: Iterable[str]) -> List[str]:
    """Every German venue for each German code seen (APC.F → APC.DE, APC.SG, …)."""
    roots = sorted(
        {
            s.rsplit(".", 1)[0]
            for s in symbols
            if "." in s and "." + s.rsplit(".", 1)[1] in GERMAN_VENUES
        }
    )
    return [root + venue for root in roots for venue in GERMAN_VENUES]


def venue_rank(symbol: str) -> int:
    suffix = "." + symbol.rsplit(".", 1)[1] if "." in symbol else ""
    return (
        GERMAN_VENUES.index(suffix) if suffix in GERMAN_VENUES else len(GERMAN_VENUES)
    )


def fill_match(
    fills: List[Fill], ranges: Dict[str, List[float]], splits: Dict[str, float]
) -> Tuple[int, int]:
    """(fills inside the day's range, fills on days with a range)."""
    hits = checked = 0
    for fill in fills:
        day_range = ranges.get(fill.date)
        if not day_range:
            continue
        factor = 1.0
        for split_day, ratio in splits.items():
            if split_day > fill.date:
                factor *= ratio
        price = float(Decimal(fill.price)) / factor
        low, high = day_range
        checked += 1
        hits += low * (1 - TOLERANCE) <= price <= high * (1 + TOLERANCE)
    return hits, checked


def rank(candidates: List[ListingCandidate], currency: str) -> List[ListingCandidate]:
    """Best match first; within 5 points prefer the account currency, then the venue order."""

    def key(c: ListingCandidate) -> tuple[int, bool, int, int]:
        bucket = -round((c.match_percent or 0) / 5)
        return (bucket, c.currency != currency, venue_rank(c.symbol), -c.fills_checked)

    return sorted(candidates, key=key)


class IsinResolver:
    def __init__(self, db: Session, market_data: Optional[MarketDataService] = None):
        self.db = db
        self.market_data = market_data or MarketDataService()
        self._limit = asyncio.Semaphore(8)

    async def resolve(
        self, instruments: List[ParsedInstrument], user_id: int, currency: str = "EUR"
    ) -> List[InstrumentResolution]:
        mapped = {
            asset.isin: asset
            for asset in self.db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.isin.in_([i.isin for i in instruments]),
            )
        }
        return list(
            await asyncio.gather(
                *(
                    self._resolve_one(i, mapped.get(i.isin), currency)
                    for i in instruments
                )
            )
        )

    async def _resolve_one(
        self, instrument: ParsedInstrument, asset: Optional[Asset], currency: str
    ) -> InstrumentResolution:
        if asset is not None:
            return InstrumentResolution(
                isin=instrument.isin,
                status="existing",
                suggested_symbol=asset.symbol,
                asset_id=asset.id,
            )

        listings = await self._candidates(instrument)
        if not instrument.fills:
            candidates = [
                ListingCandidate(symbol=s, exchange=e) for s, e in listings.items()
            ]
            return InstrumentResolution(
                isin=instrument.isin, status="unmatched", candidates=candidates
            )

        days = [date.fromisoformat(f.date) for f in instrument.fills]
        start, end = min(days) - timedelta(days=3), max(days) + timedelta(days=3)
        scored = await asyncio.gather(
            *(
                self._score(s, e, instrument.fills, start, end)
                for s, e in listings.items()
            )
        )
        candidates = rank([c for c in scored if c is not None], currency)
        best = candidates[0] if candidates else None
        best_match = (best.match_percent or 0) if best else 0
        if (
            best is not None
            and best_match >= MATCHED * 100
            and best.currency == currency
        ):
            status = "matched"
        elif best_match >= PLAUSIBLE * 100:
            status = "uncertain"
        else:
            status = "unmatched"
        return InstrumentResolution(
            isin=instrument.isin,
            status=status,
            suggested_symbol=(
                best.symbol if best is not None and status != "unmatched" else None
            ),
            candidates=candidates[:10],
        )

    async def _candidates(
        self, instrument: ParsedInstrument
    ) -> Dict[str, Optional[str]]:
        crypto = crypto_symbol(instrument.isin)
        if crypto:
            return {crypto: "crypto"}
        found: Dict[str, Optional[str]] = {}
        listings = []
        for query in (instrument.isin, instrument.name):
            listings += await self._search(query)
        for name in {li["name"] for li in listings[:3] if li.get("name")} - {
            instrument.name
        }:
            listings += await self._search(name)
        for li in listings:
            if li["quote_type"] != "CRYPTOCURRENCY" and len(found) < MAX_SEARCH_RESULTS:
                found.setdefault(li["symbol"], li.get("exchange"))
        variants = german_variants(found)
        if not variants:
            primary = [s for s in found if "." not in s and "=" not in s][:2]
            variants = german_variants(p + GERMAN_VENUES[0] for p in primary)
        for symbol in variants[: MAX_CANDIDATES - len(found)]:
            found.setdefault(symbol, VENUE_NAMES["." + symbol.rsplit(".", 1)[1]])
        return found

    async def _search(self, query: str) -> list:
        async with self._limit:
            return await self.market_data.search_listings(query)

    async def _score(
        self,
        symbol: str,
        exchange: Optional[str],
        fills: List[Fill],
        start: date,
        end: date,
    ) -> Optional[ListingCandidate]:
        async with self._limit:
            data = await self.market_data.get_daily_ranges(symbol, start, end)
        if not data:
            return None
        hits, checked = fill_match(fills, data["ranges"], data["splits"])
        if not checked:
            return None
        return ListingCandidate(
            symbol=symbol,
            exchange=exchange,
            currency=data.get("currency"),
            match_percent=round(100 * hits / checked, 1),
            fills_checked=checked,
        )
