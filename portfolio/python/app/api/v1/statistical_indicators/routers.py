"""
Simplified Statistical Indicators API Router
Basic API endpoints for user-configurable statistical indicators.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.auth.dependencies import (
    get_client_ip,
    get_current_user,
    get_optional_current_user,
)
from app.core.auth.utils import is_rate_limited
from app.core.database.connection import get_db
from app.core.database.models.user import User
from app.core.schemas.statistical_indicators import (
    AnalysisConfiguration,
    AnalysisConfigurationCreate,
    AnalysisConfigurationListResponse,
    AnalysisConfigurationUpdate,
    IndicatorCalculationRequest,
    IndicatorCalculationResponse,
    IndicatorConfiguration,
    IndicatorRegistryResponse,
    IndicatorValidationError,
)
from app.core.services.analysis_configuration_service import (
    AnalysisConfigurationService,
)
from app.core.services.enhanced_statistical_service import EnhancedStatisticalService

router = APIRouter(prefix="/statistical-indicators", tags=["statistical-indicators"])


@router.get("/indicators", response_model=IndicatorRegistryResponse)
async def get_available_indicators(
        category: Optional[str] = Query(None, description="Filter by indicator category"),
        search: Optional[str] = Query(None, description="Search indicators by name or description"),
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Get all available statistical indicators."""
    try:
        service = EnhancedStatisticalService(db)
        indicators_data = await service.get_available_indicators()

        indicators = indicators_data["indicators"]

        # Filter by category if provided
        if category:
            indicators = [ind for ind in indicators if ind["category"] == category]

        # Search if provided
        if search:
            search_lower = search.lower()
            indicators = [ind for ind in indicators
                          if search_lower in ind["name"].lower() or
                          search_lower in ind["description"].lower()]

        return IndicatorRegistryResponse(
            indicators=indicators,
            categories=indicators_data["categories"],
            total_indicators=len(indicators)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching indicators: {str(e)}")


@router.post("/calculate", response_model=IndicatorCalculationResponse)
async def calculate_indicators(
        request: IndicatorCalculationRequest,
        current_user: User = Depends(get_optional_current_user),
        request_obj: Request = None,
        db: Session = Depends(get_db)
):
    """Calculate indicators for a symbol using configuration or custom indicators."""
    # Rate limiting for unauthenticated users
    if not current_user:
        client_ip = get_client_ip(request_obj) if request_obj else "unknown"
        if is_rate_limited(
                client_ip, "calculate_indicators", max_attempts=10, window_seconds=3600
        ):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please authenticate or try again later.",
            )

    try:
        service = EnhancedStatisticalService(db)
        result = await service.calculate_indicators(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating indicators: {str(e)}")


# Analysis Configuration Endpoints
@router.post("/configurations", response_model=AnalysisConfiguration)
async def create_configuration(
        config_data: AnalysisConfigurationCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Create a new analysis configuration."""
    try:
        service = AnalysisConfigurationService(db)
        result = service.create_configuration(current_user.id, config_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating configuration: {str(e)}")


@router.get("/configurations", response_model=AnalysisConfigurationListResponse)
async def get_configurations(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        user_only: bool = Query(False, description="Only return user's configurations"),
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Get analysis configurations."""
    try:
        service = AnalysisConfigurationService(db)

        if user_only and current_user:
            result = service.get_user_configurations(current_user.id, skip, limit)
        else:
            result = service.get_public_configurations(skip, limit)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching configurations: {str(e)}")


@router.get("/configurations/{config_id}", response_model=AnalysisConfiguration)
async def get_configuration(
        config_id: int,
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Get a specific analysis configuration."""
    try:
        service = AnalysisConfigurationService(db)
        result = service.get_configuration(
            config_id,
            current_user.id if current_user else None
        )

        if not result:
            raise HTTPException(status_code=404, detail="Configuration not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching configuration: {str(e)}")


@router.put("/configurations/{config_id}", response_model=AnalysisConfiguration)
async def update_configuration(
        config_id: int,
        update_data: AnalysisConfigurationUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Update an analysis configuration."""
    try:
        service = AnalysisConfigurationService(db)
        result = service.update_configuration(config_id, current_user.id, update_data)

        if not result:
            raise HTTPException(status_code=404, detail="Configuration not found or access denied")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")


@router.delete("/configurations/{config_id}")
async def delete_configuration(
        config_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Delete an analysis configuration."""
    try:
        service = AnalysisConfigurationService(db)
        success = service.delete_configuration(config_id, current_user.id)

        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found or access denied")

        return {"message": "Configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting configuration: {str(e)}")


@router.get("/templates")
async def get_predefined_templates(
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Get predefined analysis templates."""
    try:
        service = EnhancedStatisticalService(db)
        templates = await service.get_predefined_templates()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching templates: {str(e)}")


@router.post("/templates/{template_name}/create", response_model=AnalysisConfiguration)
async def create_from_template(
        template_name: str,
        custom_name: Optional[str] = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Create a configuration from a predefined template."""
    try:
        service = EnhancedStatisticalService(db)
        result = await service.create_configuration_from_template(
            current_user.id, template_name, custom_name
        )

        if not result:
            raise HTTPException(status_code=404, detail="Template not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating from template: {str(e)}")


@router.post("/validate", response_model=List[IndicatorValidationError])
async def validate_indicator_configuration(
        config: IndicatorConfiguration,
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Validate an indicator configuration."""
    try:
        service = EnhancedStatisticalService(db)
        errors = await service.validate_indicator_configuration(config)
        return errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating configuration: {str(e)}")


# Additional endpoints for enhanced functionality
@router.post("/configurations/{config_id}/duplicate", response_model=AnalysisConfiguration)
async def duplicate_configuration(
        config_id: int,
        new_name: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Duplicate an existing configuration."""
    try:
        service = AnalysisConfigurationService(db)
        result = service.duplicate_configuration(config_id, current_user.id, new_name)

        if not result:
            raise HTTPException(status_code=404, detail="Configuration not found or access denied")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error duplicating configuration: {str(e)}")


@router.get("/configurations/search", response_model=AnalysisConfigurationListResponse)
async def search_configurations(
        q: str = Query(..., description="Search query"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Search configurations by name, description, or tags."""
    try:
        service = AnalysisConfigurationService(db)
        result = service.search_configurations(
            q,
            current_user.id if current_user else None,
            skip,
            limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching configurations: {str(e)}")


@router.get("/statistics")
async def get_statistics(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get user's configuration statistics."""
    try:
        service = EnhancedStatisticalService(db)
        stats = await service.get_configuration_statistics(current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


@router.get("/popular")
async def get_popular_configurations(
        limit: int = Query(10, ge=1, le=50),
        current_user: User = Depends(get_optional_current_user),
        db: Session = Depends(get_db)
):
    """Get popular public configurations."""
    try:
        service = EnhancedStatisticalService(db)
        configs = await service.get_popular_configurations(limit)
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular configurations: {str(e)}")
