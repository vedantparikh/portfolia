# Integration tests

`tests/integration/` drives the real app through `TestClient` with the SQLite test database from `tests/conftest.py`. `tests/integration/conftest.py` adds the `api` client, an in-memory Redis (`fake_redis`) and a captured outbox (`sent_emails`). Market data is stubbed per test, so nothing touches the network. It does not need the compose stack, and it must not be run inside `portfolio-api-1`.

```bash
# from portfolio/
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/python/app:/app" -w /app \
  -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/t.db \
  -e PYTHONDONTWRITEBYTECODE=1 portfolio-api \
  python -m pytest tests/integration -q -p no:cacheprovider
```

Files:

| File | Covers |
|---|---|
| `test_api_endpoints.py` | Meta routes, registration/login/logout, validation and the error envelope, symbol search, indicator requests |
| `test_security.py` | Password reset, token rotation, rate limits, ownership |
| `test_transaction_concurrency.py` | Overlapping writes |

`tests/quarantine.txt` must stay empty. A failing test is fixed or, if its code is gone, deleted.
