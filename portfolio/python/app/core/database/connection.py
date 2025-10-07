import logging
from contextlib import asynccontextmanager
from typing import Optional

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config import settings
from core.database.redis_client import get_redis

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.POOL_RECYCLE,
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis client
redis_client: Optional[redis.Redis] = get_redis()


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database connection."""
    try:
        # Test database connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False


async def create_tables():
    """Create all database tables."""
    try:
        # Import all models to ensure they are registered
        from core.database.models.base import Base

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False


async def get_db_health() -> dict:
    """Get database health status."""
    try:
        # Test database connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Test Redis connection
    try:
        redis_client = get_redis()
        if redis_client and redis_client.ping():
            redis_status = "healthy"
        else:
            redis_status = "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"

    return {
        "database": db_status,
        "redis": redis_status,
        "overall": (
            "healthy"
            if db_status == "healthy" and redis_status == "healthy"
            else "degraded"
        ),
    }


def close_db():
    """Close database connections."""
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        try:
            redis_client.close()
            redis_client = None
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Context manager for database sessions
@asynccontextmanager
async def get_db_session():
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
