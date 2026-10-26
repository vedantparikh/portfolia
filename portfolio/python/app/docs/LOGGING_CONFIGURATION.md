# Logging

`main.py` calls `setup_logging` from `core/logging_config.py` at import.

| Environment variable | Default | Effect |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root level. Also a `config.py` setting; the process uses the environment value. |
| `LOG_FILE` | `portfolia_api_<UTC timestamp>.log` | File name inside `LOG_DIR`. |
| `LOG_DIR` | `logs` | Created on startup. Gitignored. |
| `LOG_JSON` | `false` | `true` switches the formatter to a single-line JSON-ish format. |

Console logging is on. The file handler rotates at 10 MB and keeps 5 files. Uvicorn, FastAPI, httpx, and yfinance log at INFO. Pandas and numpy log at WARNING. SQLAlchemy's logger is set to WARNING by `setup_logging`.

The engine can still echo SQL. If `docker compose logs api` is a stream of statements, that echo is on in `core/database/connection.py`. It is a known dev-stack behaviour, not a second log configuration.

Helpers in `logging_config.py` (`log_function_call`, `log_api_request`, `log_security_event`, and the others) exist. Most call sites log with `get_logger` directly. There is no Sentry and no log shipper. `docker compose logs` is the operational view; the container's json-file driver keeps 3 files of 10 MB.

The database URL is logged with the password stripped (everything up to `@` removed). Do not add a log line that prints `settings` whole.
