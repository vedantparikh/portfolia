"""
Trade Republic through pytr's web login (the same flow as Bachat's connector).

Phone and PIN start a login; the person confirms in the Trade Republic app or
types an authenticator code. The login spans several requests, so its state
(process id, device info, cookies) goes back to the caller to store encrypted;
the PIN is never part of it. A refresh downloads new documents and rewrites
account_transactions.csv and portfolio.csv in the shared pytr folder.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class ConnectorError(Exception):
    """Trade Republic refused or failed; the message is safe to show."""


class ReauthRequiredError(ConnectorError):
    """The stored session is no longer accepted."""


DOC_NAMES = "{iso_date} {time} {title}"
# pytr refuses to build its API object without a PIN; after the login the PIN is never sent again.
NO_PIN = "0000"
CONFIRMED = {"CONFIRMED", "COMPLETED"}


@dataclass(frozen=True, slots=True)
class PendingLogin:
    state: dict[str, Any]
    needs_code: bool
    countdown: int


@dataclass(frozen=True, slots=True)
class LoginCheck:
    confirmed: bool
    session: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class Refreshed:
    session: dict[str, Any]
    events: int
    documents: int
    positions: int


class TradeRepublicClient(Protocol):
    def start(self, phone: str, pin: str) -> PendingLogin: ...

    def check(self, state: dict[str, Any], code: str | None) -> LoginCheck: ...

    def refresh(self, session: dict[str, Any], folder: Path) -> Refreshed: ...


def _cookies(api: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "expires": c.expires,
            "secure": c.secure,
        }
        for c in api._websession.cookies
    ]


def _files(folder: Path) -> int:
    return sum(1 for _ in folder.rglob("*.pdf")) if folder.is_dir() else 0


def _replace(source: Path, target: Path) -> None:
    """Copy, then rename over the target, so a reader never sees half a file."""
    partial = target.with_name(f".{target.name}.partial")
    shutil.copyfile(source, partial)
    os.replace(partial, target)


class PytrClient:
    """pytr's `TradeRepublicApi`, `DL` and `Portfolio`, imported on use."""

    def _api(self, phone: str, pin: str = NO_PIN, waf_token: str | None = None) -> Any:
        from pytr.api import TradeRepublicApi

        return TradeRepublicApi(
            phone_no=phone,
            pin=pin,
            save_cookies=False,
            use_v2_login=True,
            waf_token=waf_token,
        )

    def _restore(self, state: dict[str, Any]) -> Any:
        api = self._api(state["phone"])
        api._device_info = state.get("device_info")
        api._process_id = state.get("process_id")
        api._required_action = state.get("required_action")
        for c in state.get("cookies", []):
            api._websession.cookies.set(
                c["name"],
                c["value"],
                domain=c["domain"],
                path=c["path"],
                expires=c["expires"],
                secure=c["secure"],
            )
        return api

    def _session(self, api: Any, phone: str) -> dict[str, Any]:
        return {
            "phone": phone,
            "device_info": api._device_info,
            "cookies": _cookies(api),
        }

    def start(self, phone: str, pin: str) -> PendingLogin:
        import requests

        api = self._api(phone, pin)
        try:
            try:
                countdown = api.initiate_weblogin()
            except ValueError as exc:
                if "WAF" not in str(exc):
                    raise
                # Blocked by the load balancer: solve its challenge in Python (no browser), once.
                api = self._api(phone, pin, waf_token="awswaf")  # noqa: S106
                countdown = api.initiate_weblogin()
        except ValueError as exc:
            raise ConnectorError(str(exc)) from None
        except requests.RequestException as exc:
            raise ConnectorError(
                f"Trade Republic did not answer: {exc.__class__.__name__}"
            ) from None
        state = {
            **self._session(api, phone),
            "process_id": api._process_id,
            "required_action": api._required_action,
        }
        return PendingLogin(
            state=state,
            needs_code=api.weblogin_needs_authenticator,
            countdown=int(countdown),
        )

    def check(self, state: dict[str, Any], code: str | None) -> LoginCheck:
        import requests

        api = self._restore(state)
        try:
            if api.weblogin_needs_authenticator:
                if not code:
                    raise ConnectorError("Enter the code from your authenticator app")
                api.complete_weblogin(code)
            else:
                status = api._get_weblogin_process().get("status")
                if status == "PENDING":
                    return LoginCheck(confirmed=False)
                if status not in CONFIRMED:
                    raise ConnectorError(f"Trade Republic ended the login ({status})")
        except ValueError as exc:
            raise ConnectorError(str(exc)) from None
        except requests.RequestException as exc:
            raise ConnectorError(
                f"Trade Republic did not answer: {exc.__class__.__name__}"
            ) from None
        return LoginCheck(confirmed=True, session=self._session(api, state["phone"]))

    def refresh(self, session: dict[str, Any], folder: Path) -> Refreshed:
        import requests
        from pytr.dl import DL
        from pytr.portfolio import Portfolio

        api = self._restore(session)
        try:
            api.settings()
        except requests.RequestException:
            raise ReauthRequiredError(
                "The Trade Republic session ended: log in again"
            ) from None
        docs = folder / "docs"
        before = _files(docs)
        download = DL(
            api,
            docs,
            DOC_NAMES,
            export_transactions=True,
            max_workers=4,
            lang="en",
        )
        download.do_dl()
        exported = docs / "account_transactions.csv"
        if not exported.is_file():
            raise ConnectorError("pytr did not write a transactions CSV")
        _replace(exported, folder / "account_transactions.csv")
        portfolio = Portfolio(
            api, include_watchlist=False, output=folder / "portfolio.csv", lang="en"
        )
        portfolio.get()
        return Refreshed(
            session=self._session(api, session["phone"]),
            events=len(download.tl.events),
            documents=_files(docs) - before,
            positions=len(portfolio.positions),
        )


_OVERRIDE: list[TradeRepublicClient] = []


def trade_republic_client() -> TradeRepublicClient:
    """Tests swap in a fake with `override_trade_republic_client`."""
    return _OVERRIDE[0] if _OVERRIDE else PytrClient()


def override_trade_republic_client(client: TradeRepublicClient | None) -> None:
    _OVERRIDE.clear()
    if client is not None:
        _OVERRIDE.append(client)
