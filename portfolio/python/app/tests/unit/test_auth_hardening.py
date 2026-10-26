"""Refresh tokens are stored as hashes, and signing no longer uses python-jose."""

import hashlib

import core.auth.dependencies as deps
from core.auth.utils import (
    create_access_token,
    hash_refresh_token,
    refresh_token_matches,
    verify_token,
)


def test_access_tokens_roundtrip_with_pyjwt():
    token = create_access_token({"sub": "1", "email": "a@example.com"})
    payload = verify_token(token, "access")
    assert payload["sub"] == "1"
    assert payload["type"] == "access"


def test_refresh_token_hash_is_sha256_and_not_the_token():
    token = "plain-refresh-token"
    digest = hash_refresh_token(token)
    assert digest == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert digest != token
    assert refresh_token_matches(digest, token)
    assert not refresh_token_matches(digest, "other")
    assert not refresh_token_matches(token, token)


def test_require_admin_is_gone():
    assert not hasattr(deps, "require_admin")
