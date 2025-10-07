#!/usr/bin/env python3
"""
Demonstration script for the comprehensive logging system.
Run this script to see the logging system in action.
"""

import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logging_config import (
    get_logger,
    log_api_request,
    log_api_response,
    log_database_operation,
    log_error_with_context,
    log_function_call,
    log_function_result,
    log_performance_metric,
    log_security_event,
    setup_logging,
)


def demo_basic_logging():
    """Demonstrate basic logging functionality."""
    logger = get_logger(__name__)

    logger.info("🚀 Starting logging demonstration")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("⚠️ This is a warning message")
    logger.error("❌ This is an error message")
    logger.critical("🚨 This is a critical message")


def demo_function_logging():
    """Demonstrate function call and result logging."""
    logger = get_logger(__name__)

    def process_data(data, user_id):
        start_time = time.time()

        # Log function call
        log_function_call(
            logger, "process_data", data_type=type(data).__name__, user_id=user_id
        )

        # Simulate processing
        time.sleep(0.1)
        result = f"Processed {len(data)} items"

        # Log function result
        execution_time = time.time() - start_time
        log_function_result(logger, "process_data", result, execution_time)

        return result

    # Test the function
    data = ["item1", "item2", "item3"]
    result = process_data(data, "user123")
    logger.info(f"Function result: {result}")


def demo_database_logging():
    """Demonstrate database operation logging."""
    logger = get_logger(__name__)

    # Simulate database operations
    log_database_operation(
        logger, "SELECT", "users", "user123", email="user@example.com"
    )
    log_database_operation(logger, "INSERT", "users", "user456", username="newuser")
    log_database_operation(logger, "UPDATE", "users", "user123", field="email")
    log_database_operation(logger, "DELETE", "sessions", "session789")


def demo_api_logging():
    """Demonstrate API request/response logging."""
    logger = get_logger(__name__)

    # Simulate API request
    start_time = time.time()
    client_ip = "192.168.1.100"
    user_id = "user123"

    # Log request
    log_api_request(logger, "GET", "/app/users", user_id, client_ip, query="profile")

    # Simulate processing
    time.sleep(0.05)

    # Log response
    response_time = time.time() - start_time
    log_api_response(logger, "GET", "/app/users", 200, response_time, data_size=1024)


def demo_security_logging():
    """Demonstrate security event logging."""
    logger = get_logger(__name__)

    # Simulate security events
    log_security_event(
        logger, "LOGIN_ATTEMPT", "user123", "192.168.1.100", "Successful login"
    )
    log_security_event(
        logger, "RATE_LIMIT_EXCEEDED", None, "192.168.1.101", "API endpoint /app/data"
    )
    log_security_event(
        logger,
        "SUSPICIOUS_ACTIVITY",
        "user456",
        "192.168.1.102",
        "Multiple failed logins",
    )


def demo_performance_logging():
    """Demonstrate performance metric logging."""
    logger = get_logger(__name__)

    # Simulate performance metrics
    log_performance_metric(
        logger, "database_query_time", 0.125, "seconds", table="users"
    )
    log_performance_metric(
        logger, "api_response_time", 45.2, "milliseconds", endpoint="/app/users"
    )
    log_performance_metric(
        logger, "memory_usage", 128.5, "MB", component="data_processor"
    )


def demo_error_logging():
    """Demonstrate error logging with context."""
    logger = get_logger(__name__)

    try:
        # Simulate an error
        raise ValueError("Invalid data format")
    except Exception as e:
        # Log error with context
        log_error_with_context(
            logger,
            e,
            "Data processing operation",
            user_id="user123",
            data_id="data456",
            operation_type="transform",
        )


def demo_sensitive_data_filtering():
    """Demonstrate sensitive data filtering in logs."""
    logger = get_logger(__name__)

    # These sensitive parameters will be automatically filtered
    log_function_call(
        logger,
        "authenticate_user",
        username="testuser",
        password="secret123",  # This will be masked
        api_key="sk-1234567890",  # This will be masked
        token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
    )  # This will be masked


def main():
    """Main demonstration function."""
    print("🎯 Portfolia API Logging System Demonstration")
    print("=" * 50)

    # Setup logging with different configurations
    print("\n📝 Setting up logging system...")
    setup_logging(
        log_level="DEBUG",
        log_file="demo_logging.log",
        log_dir="logs",
        enable_console=True,
        enable_file=True,
        enable_json=False,
    )

    # Run demonstrations
    print("\n🔍 Running logging demonstrations...")

    demo_basic_logging()
    demo_function_logging()
    demo_database_logging()
    demo_api_logging()
    demo_security_logging()
    demo_performance_logging()
    demo_error_logging()
    demo_sensitive_data_filtering()

    print("\n✅ Logging demonstration completed!")
    print("\n📁 Check the following locations for logs:")
    print("   - Console output (above)")
    print("   - Log file: logs/demo_logging.log")
    print("\n🔧 To change log level, set LOG_LEVEL environment variable:")
    print("   export LOG_LEVEL=DEBUG  # For more detailed logs")
    print("   export LOG_LEVEL=WARNING  # For fewer logs")


if __name__ == "__main__":
    main()
