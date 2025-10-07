#!/usr/bin/env python3
"""
Health check router for Portfolia application.
This module provides health check endpoints for monitoring application health.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database.connection import get_db, get_db_health

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check_endpoint():
    """Basic health check endpoint."""
    try:
        health_status = await get_db_health()
        return {
            "status": health_status["overall"],
            "database": health_status["database"],
            "redis": health_status["redis"],
            "timestamp": "2024-01-15T10:30:00Z",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "unknown",
            "redis": "unknown",
            "timestamp": "2024-01-15T10:30:00Z",
            "error": str(e),
        }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with database statistics."""
    try:
        health_status = await get_db_health()

        if health_status["database"] != "healthy":
            raise HTTPException(status_code=503, detail="Database connection failed")

        # Basic database statistics
        try:
            # Test database connection with a simple query
            result = db.execute("SELECT COUNT(*) FROM information_schema.tables")
            table_count = result.scalar()
            db_stats = {"table_count": table_count}
        except Exception as e:
            logger.warning(f"Could not get database statistics: {e}")
            db_stats = {"error": str(e)}

        return {
            "status": health_status["overall"],
            "database": {
                "connection": health_status["database"],
                "redis": health_status["redis"],
                "statistics": db_stats,
            },
            "timestamp": "2024-01-15T10:30:00Z",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")
