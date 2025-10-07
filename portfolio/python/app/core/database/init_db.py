#!/usr/bin/env python3
"""
Database initialization script for Portfolia application.
This script creates all database tables and initializes the database.
"""

import asyncio
import sys
from pathlib import Path
import logging

from core.database.connection import get_db_health

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database asynchronously."""
    try:
        logger.info("Starting database initialization...")

        # Check database health
        health_status = await get_db_health()
        if health_status["database"] != "healthy":
            logger.error(
                "Database connection failed. Please check your PostgreSQL configuration."
            )
            return False

        # Check Redis health
        if health_status["redis"] != "healthy":
            logger.warning(
                "Redis connection failed. Some features may not work properly."
            )

        # Initialize database tables
        logger.info("Creating database tables...")
        from core.database.connection import create_tables

        if not await create_tables():
            logger.error("Failed to create database tables")
            return False

        logger.info("Database initialization completed successfully!")

        # Verify tables were created
        health_status = await get_db_health()
        if health_status["database"] == "healthy":
            logger.info("Database health check passed.")
            return True
        else:
            logger.error("Database health check failed after initialization.")
            return False

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def main():
    """Initialize the database (synchronous wrapper for backward compatibility)."""
    return asyncio.run(init_database())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
