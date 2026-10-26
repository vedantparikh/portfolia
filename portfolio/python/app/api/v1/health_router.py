"""
Simple test router to verify API structure.
"""

from fastapi import APIRouter

router = APIRouter(tags=["test"])


@router.get("/")
def test_endpoint():
    """Test endpoint to verify API routing works."""
    return {
        "message": "Test endpoint working!",
        "status": "success",
        "router": "test_router",
    }


@router.get("/health")
def test_health():
    """Test health endpoint."""
    return {"status": "healthy", "service": "test_router"}
