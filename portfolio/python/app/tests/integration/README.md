# Integration tests

`tests/integration/` hits the API with the test SQLite database from `conftest.py`. It does not need the compose stack, and it must not be run inside `portfolio-api-1`.

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
| `test_api_endpoints.py` | A broad pass over mounted routes |
| `test_security.py` | Auth and ownership |
| `test_transaction_concurrency.py` | Overlapping writes |

Entries in `tests/quarantine.txt` still apply. A red quarantined test is expected; a new failure outside that file is not. Older notes in this directory that tell you to `cd python/api` and run a shell script are obsolete. There is no `python/api` tree and no separate integration shell script.
