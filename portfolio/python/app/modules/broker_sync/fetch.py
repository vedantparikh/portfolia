"""
Fetch from Trade Republic on demand: log in with pytr, download into the shared
pytr folder (the files Bachat writes too), then import into every portfolio of
the user that is linked to the export.
"""

import asyncio
import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from config import settings
from core.database.connection import SessionLocal
from core.database.models import BrokerConnection, Portfolio, User
from core.errors import DomainError
from modules.broker_sync.service import SOURCE, PytrSyncService
from modules.broker_sync.trade_republic import (
    ConnectorError,
    ReauthRequiredError,
    trade_republic_client,
)

logger = logging.getLogger(__name__)

# A run older than this is taken to have died with its process
STALE_RUN = timedelta(minutes=30)


def _fernet() -> Fernet:
    digest = hashlib.sha256(
        f"portfolia-broker-session|{settings.SECRET_KEY}".encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _seal(data: Dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def _open(secret: Optional[str]) -> Optional[Dict[str, Any]]:
    if not secret:
        return None
    try:
        return json.loads(_fernet().decrypt(secret.encode()))
    except (InvalidToken, ValueError):
        return None


class TradeRepublicFetchService:
    def __init__(self, db: Session):
        self.db = db
        self.sync = PytrSyncService(db)

    def _require(self, user: User) -> None:
        if not self.sync.available_for(user):
            raise DomainError("Trade Republic sync is not set up for this account")

    def _connection(self, user_id: int) -> Optional[BrokerConnection]:
        return (
            self.db.query(BrokerConnection)
            .filter(
                BrokerConnection.user_id == user_id,
                BrokerConnection.source == SOURCE,
            )
            .first()
        )

    def _running(self, connection: Optional[BrokerConnection]) -> bool:
        return bool(
            connection
            and connection.fetch_status == "running"
            and connection.fetch_started_at
            and datetime.now(timezone.utc) - connection.fetch_started_at < STALE_RUN
        )

    def status(self, user: User) -> Dict[str, Any]:
        connection = self._connection(user.id)
        connected = bool(
            connection and connection.status == "connected" and _open(connection.secret)
        )
        return {
            "available": self.sync.available_for(user),
            "file_updated_at": self.sync.file_info()["updated_at"],
            "connected": connected,
            "login_pending": bool(connection and connection.status == "pending"),
            "session_expired": bool(connection and connection.status == "expired"),
            "fetch_status": "running"
            if self._running(connection)
            else (
                "failed"
                if connection and connection.fetch_status == "running"
                else (connection.fetch_status if connection else "idle")
            ),
            "fetch_started_at": connection.fetch_started_at if connection else None,
            "fetch_finished_at": connection.fetch_finished_at if connection else None,
            "fetch_report": connection.fetch_report if connection else None,
        }

    async def start_login(self, user: User, phone: str, pin: str) -> Dict[str, Any]:
        self._require(user)
        try:
            pending = await asyncio.to_thread(
                trade_republic_client().start, phone.strip(), pin.strip()
            )
        except ConnectorError as e:
            raise DomainError(str(e)) from None
        connection = self._connection(user.id)
        if connection is None:
            connection = BrokerConnection(
                user_id=user.id, source=SOURCE, status="pending", fetch_status="idle"
            )
            self.db.add(connection)
        connection.status = "pending"
        connection.secret = _seal(pending.state)
        self.db.flush()
        return {"needs_code": pending.needs_code, "countdown": pending.countdown}

    async def confirm_login(self, user: User, code: Optional[str]) -> bool:
        self._require(user)
        connection = self._connection(user.id)
        state = _open(connection.secret) if connection else None
        if connection is None or connection.status != "pending" or state is None:
            raise DomainError("Start the Trade Republic login first")
        try:
            check = await asyncio.to_thread(
                trade_republic_client().check, state, (code or "").strip() or None
            )
        except ConnectorError as e:
            connection.status = "expired"
            connection.secret = None
            self.db.flush()
            raise DomainError(str(e)) from None
        if not check.confirmed or check.session is None:
            return False
        connection.status = "connected"
        connection.secret = _seal(check.session)
        self.db.flush()
        return True

    def disconnect(self, user: User) -> None:
        connection = self._connection(user.id)
        if connection is not None:
            connection.status = "expired"
            connection.secret = None
            self.db.flush()

    def begin_fetch(self, user: User) -> None:
        """Mark a run as started; `run_fetch` does the work after the response."""
        self._require(user)
        if not self.sync.path.parent.is_dir():
            raise DomainError(
                "The Trade Republic folder is not available on this server"
            )
        connection = self._connection(user.id)
        if connection is None or connection.status != "connected":
            raise DomainError("Log in to Trade Republic first")
        if self._running(connection):
            raise DomainError("A fetch from Trade Republic is already running")
        connection.fetch_status = "running"
        connection.fetch_started_at = datetime.now(timezone.utc)
        connection.fetch_finished_at = None
        connection.fetch_report = None
        self.db.flush()


async def run_fetch(user_id: int) -> None:
    """Download, then import into the user's linked portfolios. Own DB session."""
    db = SessionLocal()
    try:
        service = TradeRepublicFetchService(db)
        connection = service._connection(user_id)
        if connection is None:
            return
        report: Dict[str, Any]
        session = _open(connection.secret)
        try:
            if session is None:
                raise ReauthRequiredError("Log in to Trade Republic again")
            refreshed = await asyncio.to_thread(
                trade_republic_client().refresh, session, service.sync.path.parent
            )
        except ReauthRequiredError as e:
            connection.status = "expired"
            connection.secret = None
            connection.fetch_status = "failed"
            report = {"error": str(e)}
        except ConnectorError as e:
            connection.fetch_status = "failed"
            report = {"error": str(e)}
        except Exception:
            logger.exception("Trade Republic fetch failed for user %s", user_id)
            connection.fetch_status = "failed"
            report = {"error": "The download from Trade Republic failed"}
        else:
            connection.secret = _seal(refreshed.session)
            imports = []
            portfolios = (
                db.query(Portfolio)
                .filter(
                    Portfolio.user_id == user_id,
                    Portfolio.sync_source == SOURCE,
                    Portfolio.is_active == True,
                )
                .all()
            )
            for portfolio in portfolios:
                try:
                    result = await PytrSyncService(db).sync(portfolio)
                except Exception:
                    logger.exception(
                        "pytr import failed for portfolio %s", portfolio.id
                    )
                    db.rollback()
                    result = {"failed": 1, "errors": ["Import failed"]}
                imports.append(
                    {
                        "portfolio_id": portfolio.id,
                        "name": portfolio.name,
                        "created": result.get("created", 0),
                        "tax_entries_created": result.get("tax_entries_created", 0),
                        "failed": result.get("failed", 0),
                    }
                )
            connection.fetch_status = "succeeded"
            report = {
                "events": refreshed.events,
                "documents": refreshed.documents,
                "positions": refreshed.positions,
                "portfolios": imports,
            }
        connection.fetch_report = report
        connection.fetch_finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Trade Republic fetch for user %s: %s", user_id, report)
    finally:
        db.close()
