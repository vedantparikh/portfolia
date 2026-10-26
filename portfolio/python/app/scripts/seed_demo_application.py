#!/usr/bin/env python3
"""
Demo seed via HTTP APIs (except DB bootstrap for the demo user credentials).

End-to-end flow (like a user in the UI):
1. DB bootstrap: verified user + password so login works.
2. POST /api/v1/auth/login → JWT.
3. For each instrument: GET /api/v1/stock/symbols?name=… (Yahoo search, same as the app).
   Pick the quote that matches the intended ticker (EQUITY/ETF preferred).
4. POST /api/v1/assets/bulk-create with the resolved symbols. If yfinance fails, the request uses
   allow_minimal_on_market_data_failure (API) so demo assets are still created.
5. Portfolios, transactions, allocations, benchmarks, watchlist, optional analysis config — all via API.
6. Verification GETs.

Run the API on the host (not inside Docker) so Yahoo/yfinance use your machine’s network/DNS, e.g.:

  cd portfolio/python/app && python start_api.py

Then:

  python scripts/seed_demo_application.py --base-url http://localhost:8000 --reset

Default credentials: demo.user@example.com / demouser / DemoApp!234

Transaction volume is capped (see --max-trades-*) so runs finish in reasonable time.



Email: demo.user@example.com
Username: demouser
Password: DemoApp!234
cd portfolio/python/app
python scripts/seed_demo_application.py --base-url http://localhost:8000 --reset

python scripts/seed_demo_application.py --base-url http://localhost:8000 --no-minimal-assets
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone
from datetime import time as dt_time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import httpx

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from config import settings  # noqa: E402
from core.auth.utils import get_password_hash  # noqa: E402
from core.database.connection import SessionLocal  # noqa: E402
from core.database.models import (  # noqa: E402
    User,
    UserProfile,
)

logger = logging.getLogger(__name__)
UTC = timezone.utc

# Intended US listing (Yahoo symbol). Search queries mimic typing in the app’s symbol search.
DAY_PORTFOLIO_TICKERS: List[str] = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "JPM",
    "V",
    "DIS",
    "NFLX",
    "AMD",
    "INTC",
]

WEEK_PORTFOLIO_TICKERS: List[str] = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
]

MONTH_PORTFOLIO_TICKERS: List[str] = ["AAPL", "MSFT", "JPM", "V"]

BENCHMARK_TICKER = "SPY"

# Natural-language search strings for GET /api/v1/stock/symbols?name=…
YAHOO_SEARCH_QUERY: Dict[str, str] = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "NVDA": "NVIDIA",
    "JPM": "JPMorgan",
    "V": "Visa",
    "DIS": "Disney",
    "NFLX": "Netflix",
    "AMD": "AMD",
    "INTC": "Intel",
    "SPY": "SPDR S&P 500",
}


def _business_days(start: date, end: date) -> Iterator[date]:
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def _first_business_day_of_month(y: int, m: int) -> date:
    first = date(y, m, 1)
    while first.weekday() >= 5:
        first += timedelta(days=1)
    return first


def _monthly_trade_dates(start: date, end: date) -> List[date]:
    out: List[date] = []
    y, m = start.year, start.month
    while True:
        d = _first_business_day_of_month(y, m)
        if d < start:
            pass
        elif d > end:
            break
        else:
            out.append(d)
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
        if date(y, m, 1) > end:
            break
    return out


class _MarketHistory:
    """
    Real Yahoo history for the demo, in the prices a broker statement would show.
    Yahoo closes and dividends are split-adjusted back in time, so they are
    multiplied by the splits that came later to get the price actually paid.
    """

    def __init__(self, symbols: Sequence[str], start: date) -> None:
        import yfinance as yf

        self.closes: Dict[str, Dict[date, Decimal]] = {}
        self.splits: Dict[str, Dict[date, Decimal]] = {}
        self.dividends: Dict[str, Dict[date, Decimal]] = {}
        for sym in symbols:
            h = yf.Ticker(sym).history(start=start, auto_adjust=False, actions=True)
            days = [d.date() for d in h.index.tz_localize(None)]
            splits = {
                d: Decimal(str(r)) for d, r in zip(days, h["Stock Splits"]) if r > 0
            }

            def later(day: date, splits=splits) -> Decimal:
                f = Decimal(1)
                for ex, r in splits.items():
                    if ex > day:
                        f *= r
                return f

            self.splits[sym] = splits
            self.closes[sym] = {
                d: (Decimal(str(c)) * later(d)).quantize(Decimal("0.0001"))
                for d, c in zip(days, h["Close"])
                if c == c
            }
            self.dividends[sym] = {
                d: (Decimal(str(v)) * later(d)).quantize(Decimal("0.000001"))
                for d, v in zip(days, h["Dividends"])
                if v > 0
            }


class _Rng:
    def __init__(self, seed: int) -> None:
        self._s = seed % (2**32)

    def random(self) -> float:
        self._s = (self._s * 1103515245 + 12345) % (2**31)
        return self._s / 2**31

    def randint(self, a: int, b: int) -> int:
        return a + int(self.random() * (b - a + 1))

    def choice_bool(self, p: float) -> bool:
        return self.random() < p


def _simulate_trades(
    symbols_in_order: Sequence[str],
    trade_dates: Iterable[date],
    rng_seed: int,
    trades_per_day_prob: float,
    label: str,
    max_trades: Optional[int],
    market: _MarketHistory,
) -> List[Tuple[str, str, Decimal, Decimal, datetime, str]]:
    """
    Returns (symbol, buy|sell|dividend, qty, price, when, note) in date order.

    Trades are spread evenly over the whole period (the probability is thinned
    so about `max_trades` happen), at the real close of the day. Shares follow
    splits, and every dividend paid on shares held becomes a transaction.
    """
    rng = _Rng(rng_seed)
    out: List[Tuple[str, str, Decimal, Decimal, datetime, str]] = []
    positions: Dict[str, Decimal] = {s: Decimal("0") for s in symbols_in_order}
    trade_days = set(trade_dates)
    if not trade_days:
        return out
    if max_trades:
        trades_per_day_prob = min(
            trades_per_day_prob, max_trades / (len(trade_days) * len(symbols_in_order))
        )
    first, last = min(trade_days), max(trade_days)
    build_until = first + (last - first) * 0.3

    for d in _business_days(first, last):
        for sym in symbols_in_order:
            if d in market.splits[sym]:
                positions[sym] *= market.splits[sym][d]
            div = market.dividends[sym].get(d)
            if div and positions[sym] > 0:
                when = datetime.combine(d, dt_time(12, 0), tzinfo=UTC)
                out.append(
                    (sym, "dividend", positions[sym], div, when, f"[{label}] dividend")
                )

        if d not in trade_days:
            continue
        for sym in symbols_in_order:
            price = market.closes[sym].get(d)
            if price is None or not rng.choice_bool(trades_per_day_prob):
                continue
            pos = positions[sym]
            if pos <= 0 or d <= build_until:
                q = Decimal(str(rng.randint(5, 35))) + Decimal("0.25")
                when = datetime.combine(d, dt_time(14, 30), tzinfo=UTC)
                out.append((sym, "buy", q, price, when, f"[{label}] accumulate"))
                positions[sym] += q
            elif rng.choice_bool(0.28):
                sell_frac = Decimal(str(rng.randint(15, 35))) / Decimal("100")
                q = min((pos * sell_frac).quantize(Decimal("0.0001")), pos)
                if q <= 0:
                    continue
                when = datetime.combine(d, dt_time(15, 0), tzinfo=UTC)
                out.append((sym, "sell", q, price, when, f"[{label}] trim"))
                positions[sym] -= q
            else:
                q = Decimal(str(rng.randint(3, 20))) + Decimal("0.5")
                when = datetime.combine(d, dt_time(14, 45), tzinfo=UTC)
                out.append((sym, "buy", q, price, when, f"[{label}] add"))
                positions[sym] += q

    return out


def _reset_demo_user(db, email: str) -> None:
    u = db.query(User).filter(User.email == email.lower()).first()
    if u:
        logger.info("DB reset: removing user id=%s (%s)", u.id, u.email)
        prof = db.query(UserProfile).filter(UserProfile.user_id == u.id).first()
        if prof:
            db.delete(prof)
            db.flush()
        db.delete(u)
        db.commit()


def _ensure_demo_user_db(
    email: str,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            existing.is_verified = True
            existing.is_active = True
            existing.password_hash = get_password_hash(password)
            db.commit()
            prof = (
                db.query(UserProfile).filter(UserProfile.user_id == existing.id).first()
            )
            if not prof:
                db.add(
                    UserProfile(
                        user_id=existing.id,
                        first_name=first_name,
                        last_name=last_name,
                        timezone="UTC",
                        currency_preference="USD",
                        language_preference="en",
                    )
                )
                db.commit()
            logger.info(
                "DB: updated demo user id=%s (verified, password reset)", existing.id
            )
            return

        user = User(
            email=email.lower(),
            username=username.lower(),
            password_hash=get_password_hash(password),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()
        db.add(
            UserProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                timezone="UTC",
                currency_preference="USD",
                language_preference="en",
            )
        )
        db.commit()
        logger.info("DB: created demo user id=%s username=%s", user.id, user.username)
    finally:
        db.close()


class _TokenAuth:
    def __init__(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        self._access = access_token
        self._refresh = refresh_token
        self._expires_at = time.time() + float(expires_in) - 45.0

    def headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._access}"}

    def needs_refresh(self) -> bool:
        return time.time() >= self._expires_at

    def apply_refresh(self, data: Dict[str, Any]) -> None:
        self._access = data["access_token"]
        self._refresh = data["refresh_token"]
        self._expires_at = time.time() + float(data["expires_in"]) - 45.0


async def _refresh_if_needed(
    client: httpx.AsyncClient, base: str, auth: _TokenAuth
) -> None:
    if not auth.needs_refresh():
        return
    r = await client.post(
        f"{base}/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {auth._refresh}"},
    )
    r.raise_for_status()
    auth.apply_refresh(r.json())
    logger.info("Refreshed access token (expires_in=%s)", r.json().get("expires_in"))


async def _request(
    client: httpx.AsyncClient,
    base: str,
    auth: _TokenAuth,
    method: str,
    path: str,
    **kwargs: Any,
) -> httpx.Response:
    await _refresh_if_needed(client, base, auth)
    h = kwargs.pop("headers", {}) or {}
    h.update(auth.headers())
    resp = await client.request(method, f"{base}{path}", headers=h, **kwargs)
    if resp.status_code >= 400:
        logger.error(
            "HTTP %s %s -> %s body=%s",
            method,
            path,
            resp.status_code,
            resp.text[:2000],
        )
    resp.raise_for_status()
    return resp


def _norm_sym_base(s: str) -> str:
    return s.upper().split(".")[0].split("-")[0]


def _pick_symbol_from_search(
    results: List[Dict[str, Any]], intended_ticker: str
) -> Optional[str]:
    """Pick the Yahoo quote row that matches the intended listing (EQUITY/ETF first)."""
    if not results:
        return None
    want = intended_ticker.upper()
    want_base = _norm_sym_base(want)
    for r in results:
        sym = (r.get("symbol") or "").strip()
        if not sym:
            continue
        if sym.upper() == want or _norm_sym_base(sym) == want_base:
            return sym.upper()
    for r in results:
        qt = (r.get("quote_type") or r.get("quoteType") or "").upper()
        if qt in ("EQUITY", "ETF"):
            sym = (r.get("symbol") or "").strip()
            if sym:
                return sym.upper()
    sym = (results[0].get("symbol") or "").strip()
    return sym.upper() if sym else None


async def resolve_tickers_via_yahoo_search(
    client: httpx.AsyncClient,
    base: str,
    auth: _TokenAuth,
    tickers: Sequence[str],
    delay_sec: float,
) -> Dict[str, str]:
    """
    GET /api/v1/stock/symbols?name=… (Yahoo search on the API) for each instrument.
    Returns map canonical_key (e.g. AAPL) -> symbol string for bulk-create (e.g. AAPL or BRK.B).
    """
    out: Dict[str, str] = {}
    unique = list(dict.fromkeys(tickers))
    for i, t in enumerate(unique):
        if i:
            await asyncio.sleep(delay_sec)
        key = t.upper()
        q = YAHOO_SEARCH_QUERY.get(key, t)
        await _refresh_if_needed(client, base, auth)
        resp = await client.get(
            f"{base}/api/v1/stock/symbols",
            params={"name": q},
            headers=auth.headers(),
            timeout=client.timeout,
        )
        if resp.status_code != 200:
            logger.warning(
                "Yahoo search %r (%s): HTTP %s — using raw ticker",
                q,
                key,
                resp.status_code,
            )
            out[key] = key
            continue
        rows = resp.json()
        if not isinstance(rows, list):
            logger.warning("Bad search JSON for %r — using raw ticker", q)
            out[key] = key
            continue
        picked = _pick_symbol_from_search(rows, key)
        if not picked:
            logger.warning("No matching quote for %s — using raw ticker", key)
            out[key] = key
        else:
            logger.info("Search %r -> picked %s (intent %s)", q, picked, key)
            out[key] = picked
    return out


def _tx_payload(
    portfolio_id: int,
    asset_id: int,
    side: str,
    qty: Decimal,
    price: Decimal,
    when: datetime,
    notes: str,
) -> Dict[str, Any]:
    total = (qty * price).quantize(Decimal("0.0001"))
    return {
        "portfolio_id": portfolio_id,
        "asset_id": asset_id,
        "transaction_type": side,
        "status": "completed",
        "quantity": str(qty),
        "price": str(price),
        "total_amount": str(total),
        "currency": "USD",
        "transaction_date": when.isoformat(),
        "fees": "0",
        "taxes": "0",
        "notes": notes,
    }


async def run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    base = args.base_url.rstrip("/")

    if args.reset:
        db = SessionLocal()
        try:
            _reset_demo_user(db, args.email)
        finally:
            db.close()

    _ensure_demo_user_db(
        args.email,
        args.username,
        args.password,
        args.first_name,
        args.last_name,
    )

    end = date.today()
    start = end - timedelta(days=365 * args.years + 10)
    day_days = list(_business_days(start, end))
    week_days = [d for d in day_days if d.weekday() == 0]
    month_days = _monthly_trade_dates(start, end)

    timeout = httpx.Timeout(args.timeout, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        login_r = await client.post(
            f"{base}/api/v1/auth/login",
            json={"username": args.username, "password": args.password},
        )
        login_r.raise_for_status()
        tok = login_r.json()
        logger.info(
            "Login OK: token_type=%s expires_in=%s",
            tok.get("token_type"),
            tok.get("expires_in"),
        )
        auth = _TokenAuth(
            tok["access_token"], tok["refresh_token"], int(tok["expires_in"])
        )

        me = await _request(client, base, auth, "GET", "/api/v1/auth/me")
        me_js = me.json()
        logger.info(
            "GET /auth/me -> id=%s verified=%s active=%s",
            me_js.get("id"),
            me_js.get("is_verified"),
            me_js.get("is_active"),
        )
        if not me_js.get("is_verified"):
            logger.error("User is not verified; many endpoints will fail.")
            return 1

        all_intended = sorted(
            set(DAY_PORTFOLIO_TICKERS)
            | set(WEEK_PORTFOLIO_TICKERS)
            | set(MONTH_PORTFOLIO_TICKERS)
            | {BENCHMARK_TICKER}
        )
        if args.skip_yahoo_search:
            sym_map = {t.upper(): t.upper() for t in all_intended}
            logger.info("Skipping Yahoo search; using raw tickers: %s", all_intended)
        else:
            logger.info(
                "Resolving %s tickers via GET /api/v1/stock/symbols (run API locally for Yahoo)",
                len(all_intended),
            )
            sym_map = await resolve_tickers_via_yahoo_search(
                client, base, auth, all_intended, args.search_delay
            )

        daily_syms = [sym_map[t.upper()] for t in DAY_PORTFOLIO_TICKERS]
        weekly_syms = [sym_map[t.upper()] for t in WEEK_PORTFOLIO_TICKERS]
        monthly_syms = [sym_map[t.upper()] for t in MONTH_PORTFOLIO_TICKERS]

        logger.info("Loading real price history from Yahoo")
        market = await asyncio.to_thread(
            _MarketHistory, sorted(set(daily_syms + weekly_syms + monthly_syms)), start
        )
        daily_trades = _simulate_trades(
            daily_syms,
            day_days,
            11,
            args.daily_trade_prob,
            "daily",
            args.max_trades_daily,
            market,
        )
        weekly_trades = _simulate_trades(
            weekly_syms,
            week_days,
            22,
            1.0,
            "weekly",
            args.max_trades_weekly,
            market,
        )
        monthly_trades = _simulate_trades(
            monthly_syms,
            month_days,
            33,
            1.0,
            "monthly",
            args.max_trades_monthly,
            market,
        )
        logger.info(
            "Synthetic trade rows: daily=%s weekly=%s monthly=%s",
            len(daily_trades),
            len(weekly_trades),
            len(monthly_trades),
        )

        # Portfolios
        p_daily = await _request(
            client,
            base,
            auth,
            "POST",
            "/api/v1/portfolios/",
            json={
                "name": "Demo — Day trading (dense history)",
                "description": "~3y frequent trades (demo, API-seeded)",
                "currency": "USD",
                "is_active": True,
                "is_public": True,
            },
        )
        p_week = await _request(
            client,
            base,
            auth,
            "POST",
            "/api/v1/portfolios/",
            json={
                "name": "Demo — Weekly rhythm",
                "description": "~3y weekly trades (demo, API-seeded)",
                "currency": "USD",
                "is_active": True,
                "is_public": False,
            },
        )
        p_month = await _request(
            client,
            base,
            auth,
            "POST",
            "/api/v1/portfolios/",
            json={
                "name": "Demo — Monthly rhythm",
                "description": "~3y monthly trades (demo, API-seeded)",
                "currency": "USD",
                "is_active": True,
                "is_public": False,
            },
        )
        id_daily = p_daily.json()["id"]
        id_week = p_week.json()["id"]
        id_month = p_month.json()["id"]
        logger.info(
            "Created portfolios daily=%s weekly=%s monthly=%s",
            id_daily,
            id_week,
            id_month,
        )

        all_syms = sorted({sym_map[t.upper()] for t in all_intended})
        bulk = await _request(
            client,
            base,
            auth,
            "POST",
            "/api/v1/assets/bulk-create",
            json={
                "symbols": all_syms,
                "allow_minimal_on_market_data_failure": args.allow_minimal_assets,
            },
        )
        bulk_js = bulk.json()
        created_n = len(bulk_js.get("created", []))
        failed = bulk_js.get("failed", [])
        logger.info(
            "POST /assets/bulk-create -> created=%s failed=%s",
            created_n,
            len(failed),
        )
        if failed:
            logger.warning("Bulk asset failures (first 5): %s", failed[:5])

        assets_r = await _request(
            client,
            base,
            auth,
            "GET",
            "/api/v1/assets/",
            params={"limit": 1000},
        )
        sym_to_id: Dict[str, int] = {}
        for row in assets_r.json():
            sym_to_id[row["symbol"].upper()] = row["id"]
        missing = [s for s in all_syms if s.upper() not in sym_to_id]
        if missing:
            logger.error("Missing asset ids for symbols: %s", missing)
            return 1
        spy_key = sym_map[BENCHMARK_TICKER.upper()]
        spy_id = sym_to_id[spy_key.upper()]

        sem = asyncio.Semaphore(args.concurrency)

        async def post_one_tx(
            pid: int, spec: Tuple[str, str, Decimal, Decimal, datetime, str]
        ) -> None:
            sym, side, qty, price, when, note = spec
            aid = sym_to_id[sym.upper()]
            body = _tx_payload(pid, aid, side, qty, price, when, note)
            async with sem:
                await _request(
                    client, base, auth, "POST", "/api/v1/transactions/", json=body
                )

        async def post_in_order(pid: int, trades) -> None:
            # In date order: the API rejects a sell posted before its buys
            for t in trades:
                await post_one_tx(pid, t)

        logger.info("Posting transactions (each portfolio in date order)...")
        await asyncio.gather(
            post_in_order(id_daily, daily_trades),
            post_in_order(id_week, weekly_trades),
            post_in_order(id_month, monthly_trades),
        )

        def alloc_body(pid: int, symbols: Sequence[str]) -> List[Dict[str, Any]]:
            aids = [sym_to_id[s.upper()] for s in symbols]
            n = len(aids)
            pct = (Decimal("100") / Decimal(n)).quantize(Decimal("0.0001"))
            rows: List[Dict[str, Any]] = []
            for i, aid in enumerate(sorted(aids)):
                tp = pct if i < n - 1 else Decimal("100") - pct * (n - 1)
                rows.append(
                    {
                        "portfolio_id": pid,
                        "asset_id": aid,
                        "target_percentage": str(tp),
                        "rebalance_frequency": "monthly",
                        "is_active": True,
                    }
                )
            return rows

        for pid, syms, label in (
            (id_daily, daily_syms, "daily"),
            (id_week, weekly_syms, "weekly"),
            (id_month, monthly_syms, "monthly"),
        ):
            ar = await _request(
                client,
                base,
                auth,
                "POST",
                f"/api/v1/analytics/portfolios/{pid}/allocations",
                json=alloc_body(pid, syms),
            )
            logger.info(
                "POST allocations (%s) -> status=%s count=%s",
                label,
                ar.status_code,
                len(ar.json()),
            )

        bench_payload = {
            "portfolio_id": 0,
            "benchmark_asset_id": spy_id,
            "benchmark_name": "S&P 500 (SPY)",
            "benchmark_type": "index",
            "is_active": True,
            "is_primary": True,
        }
        for pid, label in (
            (id_daily, "daily"),
            (id_week, "weekly"),
            (id_month, "monthly"),
        ):
            body = {**bench_payload, "portfolio_id": pid}
            br = await _request(
                client,
                base,
                auth,
                "POST",
                f"/api/v1/analytics/portfolios/{pid}/benchmarks",
                json=body,
            )
            logger.info("POST benchmark (%s) -> id=%s", label, br.json().get("id"))

        wl = await _request(
            client,
            base,
            auth,
            "POST",
            "/api/v1/watchlists/",
            json={
                "name": "Demo watchlist",
                "description": "Symbols for UI demo",
                "is_public": False,
            },
        )
        wl_id = wl.json()["id"]
        await _request(
            client,
            base,
            auth,
            "POST",
            f"/api/v1/watchlists/{wl_id}/items/bulk",
            json={
                "symbols": [
                    sym_map["AAPL"],
                    sym_map["MSFT"],
                    sym_map["GOOGL"],
                    sym_map[BENCHMARK_TICKER.upper()],
                ]
            },
        )
        logger.info("Watchlist id=%s bulk symbols added", wl_id)

        try:
            ind_r = await _request(
                client, base, auth, "GET", "/api/v1/statistical-indicators/indicators"
            )
            inds = ind_r.json().get("indicators") or []
            ind_names = [i.get("name") for i in inds if isinstance(i, dict)]
            rsi_name = next(
                (n for n in ind_names if n and "RSI" in n.upper()),
                ind_names[0] if ind_names else "RSI",
            )

            cfg = await _request(
                client,
                base,
                auth,
                "POST",
                "/api/v1/statistical-indicators/configurations",
                json={
                    "name": "Demo analysis",
                    "description": "Auto-seeded",
                    "indicators": [
                        {
                            "indicator_name": rsi_name,
                            "parameters": {"period": 14},
                            "enabled": True,
                        }
                    ],
                    "chart_settings": {"theme": "dark"},
                    "is_public": False,
                    "tags": ["demo"],
                },
            )
            logger.info("Analysis configuration id=%s", cfg.json().get("id"))
        except Exception as e:
            logger.warning("Skipping analysis configuration (optional): %s", e)

        # --- Verification reads ---
        plist = await _request(client, base, auth, "GET", "/api/v1/portfolios/")
        logger.info("VERIFY GET /portfolios -> count=%s", len(plist.json()))

        for pid, name in (
            (id_daily, "daily"),
            (id_week, "weekly"),
            (id_month, "monthly"),
        ):
            summ = await _request(
                client, base, auth, "GET", f"/api/v1/portfolios/{pid}/summary"
            )
            s = summ.json()
            logger.info(
                "VERIFY summary %s portfolio_id=%s total_assets=%s tx_hint=%s cost=%s value=%s",
                name,
                s.get("portfolio_id"),
                s.get("total_assets"),
                s.get("recent_transactions"),
                s.get("total_cost_basis"),
                s.get("total_current_value"),
            )

            txlist = await _request(
                client,
                base,
                auth,
                "GET",
                "/api/v1/transactions/",
                params={"portfolio_id": pid, "limit": 10000},
            )
            logger.info(
                "VERIFY GET transactions portfolio=%s count=%s",
                name,
                len(txlist.json()),
            )

        logger.info(
            "Done. Log in on the UI with username=%s password=%s (email %s)",
            args.username,
            "(set via --password)",
            args.email,
        )
        return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed demo data via Portfolia HTTP API.")
    p.add_argument(
        "--base-url",
        default=settings.API_URL.rstrip("/"),
        help="API base URL (default from settings.API_URL)",
    )
    p.add_argument("--email", default="demo.user@example.com")
    p.add_argument("--username", default="demouser")
    p.add_argument("--password", default="DemoApp!234")
    p.add_argument("--first-name", default="Demo", dest="first_name")
    p.add_argument("--last-name", default="User", dest="last_name")
    p.add_argument("--years", type=int, default=3)
    p.add_argument(
        "--daily-trade-prob",
        type=float,
        default=0.82,
        dest="daily_trade_prob",
    )
    p.add_argument(
        "--max-trades-daily",
        type=int,
        default=500,
        dest="max_trades_daily",
        help="Cap API calls for daily portfolio (each is POST /transactions)",
    )
    p.add_argument(
        "--max-trades-weekly", type=int, default=200, dest="max_trades_weekly"
    )
    p.add_argument(
        "--max-trades-monthly", type=int, default=120, dest="max_trades_monthly"
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Parallel transaction POSTs (reduce if API overloads)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout seconds",
    )
    p.add_argument("--reset", action="store_true")
    p.add_argument(
        "--skip-yahoo-search",
        action="store_true",
        dest="skip_yahoo_search",
        help="Do not call GET /stock/symbols; use raw ticker strings (for broken Yahoo from API)",
    )
    p.add_argument(
        "--search-delay",
        type=float,
        default=0.35,
        dest="search_delay",
        help="Seconds between Yahoo search calls (rate limiting)",
    )
    p.add_argument(
        "--no-minimal-assets",
        action="store_false",
        dest="allow_minimal_assets",
        default=True,
        help="Do not pass allow_minimal_on_market_data_failure (require yfinance for bulk-create)",
    )
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
