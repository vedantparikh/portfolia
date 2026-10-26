"""Request id, one access line, and no SQL echo in the API log."""

import ast
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from core.database.connection import engine
from main import app

APP = Path(__file__).resolve().parents[2]
_SKIP = {"tests", "fix_asset_quantities_and_pnl.py"}


def test_sqlalchemy_does_not_echo_sql():
    assert engine.echo is False


def test_each_response_carries_a_request_id(caplog):
    with caplog.at_level(logging.INFO, logger="core.middleware"):
        with TestClient(app) as client:
            response = client.get("/")
    request_id = response.headers["x-request-id"]
    assert request_id
    assert f"request_id={request_id}" in caplog.text
    assert "method=GET" in caplog.text
    assert "path=/" in caplog.text
    assert "status=200" in caplog.text
    assert "duration_ms=" in caplog.text


def test_caller_request_id_is_kept():
    with TestClient(app) as client:
        response = client.get("/", headers={"X-Request-ID": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"


def test_unsafe_request_id_is_replaced():
    with TestClient(app) as client:
        response = client.get("/", headers={"X-Request-ID": "bad id"})
    assert response.headers["x-request-id"] != "bad id"
    assert " " not in response.headers["x-request-id"]


def test_error_body_includes_the_request_id():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/does-not-exist", headers={"X-Request-ID": "err-1"}
        )
    assert response.status_code == 404
    body = response.json()
    assert body["request_id"] == "err-1"
    assert body["error"]["code"] == "not_found"


def test_application_code_does_not_print():
    offenders = []
    for path in APP.rglob("*.py"):
        if _SKIP.intersection(path.parts) or path.name in _SKIP:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                offenders.append(f"{path.relative_to(APP)}:{node.lineno}")
    assert offenders == []
