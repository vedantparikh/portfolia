"""Process liveness, and readiness of Postgres and Redis."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.database.connection import get_db_health

router = APIRouter(tags=["health"])


@router.get("/live")
def live():
    """The process is serving. This does not check Postgres or Redis."""
    return {"status": "ok"}


async def _dependencies() -> JSONResponse:
    report = await get_db_health()
    healthy = report["database"] == "healthy" and report["redis"] == "healthy"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "unhealthy",
            "database": report["database"],
            "redis": report["redis"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )


@router.get("/ready")
async def ready():
    """Postgres and Redis are reachable."""
    return await _dependencies()


@router.get("/")
async def health():
    """Same check as /health/ready. Compose and Gatus call this path."""
    return await _dependencies()
