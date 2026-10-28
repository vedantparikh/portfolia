"""
Comprehensive logging configuration for the Portfolia API application.
Provides structured logging, different log levels, and formatting.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Default log level
DEFAULT_LOG_LEVEL = "INFO"

# Log format strings
DETAILED_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
)
SIMPLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_FORMAT = '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Set up comprehensive logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file name (without path)
        log_dir: Directory to store log files
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_json: Enable JSON formatted logging
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """

    # Determine log level
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    invalid_level = log_level not in LOG_LEVELS
    if invalid_level:
        log_level = DEFAULT_LOG_LEVEL

    numeric_level = LOG_LEVELS[log_level]

    # Create logs directory if it doesn't exist
    if enable_file and log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

    # Determine log file path
    if log_file is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = f"portfolia_api_{timestamp}.log"

    if log_dir:
        log_file_path = Path(log_dir) / log_file
    else:
        log_file_path = Path(log_file)

    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set root logger level
    root_logger.setLevel(numeric_level)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if enable_json:
            console_formatter = logging.Formatter(JSON_FORMAT)
        else:
            console_formatter = ColoredFormatter(DETAILED_FORMAT)

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)

        if enable_json:
            file_formatter = logging.Formatter(JSON_FORMAT)
        else:
            file_formatter = logging.Formatter(DETAILED_FORMAT)

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set specific logger levels
    loggers_to_configure = {
        "uvicorn": logging.INFO,
        "fastapi": logging.INFO,
        "sqlalchemy": logging.WARNING,
        "httpx": logging.INFO,
        "yfinance": logging.INFO,
        "pandas": logging.WARNING,
        "numpy": logging.WARNING,
        "matplotlib": logging.WARNING,
        "seaborn": logging.WARNING,
        "redis": logging.INFO,
        "alembic": logging.INFO,
    }

    for logger_name, level in loggers_to_configure.items():
        logging.getLogger(logger_name).setLevel(level)

    # Log the configuration
    logger = logging.getLogger(__name__)
    if invalid_level:
        logger.warning("Invalid log level, using %s", DEFAULT_LOG_LEVEL)
    logger.info("Logging configured successfully")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Console logging: {enable_console}")
    logger.info(f"File logging: {enable_file}")
    if enable_file:
        logger.info(f"Log file: {log_file_path}")
    logger.info(f"JSON format: {enable_json}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger, func_name: str, **kwargs: Any) -> None:
    """
    Log function call with parameters.

    Args:
        logger: Logger instance
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    # Filter out sensitive parameters
    sensitive_params = {"password", "password_hash", "token", "api_key", "secret"}
    filtered_kwargs = {
        k: "***" if k in sensitive_params else v for k, v in kwargs.items()
    }

    logger.debug(f"Function call: {func_name}({filtered_kwargs})")


def log_function_result(
    logger: logging.Logger,
    func_name: str,
    result: Any,
    execution_time: Optional[float] = None,
) -> None:
    """
    Log function result and execution time.

    Args:
        logger: Logger instance
        func_name: Name of the function
        result: Function result
        execution_time: Execution time in seconds
    """
    if execution_time is not None:
        logger.debug(
            f"Function result: {func_name} -> {type(result).__name__} (took {execution_time:.4f}s)"
        )
    else:
        logger.debug(f"Function result: {func_name} -> {type(result).__name__}")


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    record_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Log database operations.

    Args:
        logger: Logger instance
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        record_id: Record ID if applicable
        **kwargs: Additional context
    """
    context = f" | {kwargs}" if kwargs else ""
    id_info = f" | ID: {record_id}" if record_id else ""
    logger.info(f"DB {operation} | Table: {table}{id_info}{context}")


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    user_id: Optional[str] = None,
    ip: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Log API request details.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        user_id: User ID if authenticated
        ip: Client IP address
        **kwargs: Additional request context
    """
    user_info = f" | User: {user_id}" if user_id else ""
    ip_info = f" | IP: {ip}" if ip else ""
    context = f" | {kwargs}" if kwargs else ""
    logger.info(f"API {method} {path}{user_info}{ip_info}{context}")


def log_api_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    response_time: float,
    **kwargs: Any,
) -> None:
    """
    Log API response details.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        response_time: Response time in seconds
        **kwargs: Additional response context
    """
    context = f" | {kwargs}" if kwargs else ""
    logger.info(f"API {method} {path} -> {status_code} | {response_time:.4f}s{context}")


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    user_id: Optional[str] = None,
    ip: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """
    Log security-related events.

    Args:
        logger: Logger instance
        event_type: Type of security event
        user_id: User ID if applicable
        ip: IP address if applicable
        details: Additional event details
    """
    user_info = f" | User: {user_id}" if user_id else ""
    ip_info = f" | IP: {ip}" if ip else ""
    details_info = f" | {details}" if details else ""
    logger.warning(f"SECURITY: {event_type}{user_info}{ip_info}{details_info}")


def log_performance_metric(
    logger: logging.Logger,
    metric_name: str,
    value: float,
    unit: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Log performance metrics.

    Args:
        logger: Logger instance
        metric_name: Name of the performance metric
        value: Metric value
        unit: Unit of measurement
        **kwargs: Additional context
    """
    unit_info = f" {unit}" if unit else ""
    context = f" | {kwargs}" if kwargs else ""
    logger.info(f"PERFORMANCE: {metric_name}: {value}{unit_info}{context}")


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Log errors with additional context.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context about where the error occurred
        **kwargs: Additional error context
    """
    context_info = f" | Context: {context}" if context else ""
    additional_info = f" | {kwargs}" if kwargs else ""
    logger.error(
        f"ERROR: {type(error).__name__}: {str(error)}{context_info}{additional_info}",
        exc_info=True,
    )
