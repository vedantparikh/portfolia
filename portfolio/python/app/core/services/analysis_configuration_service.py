"""
Analysis Configuration Service
Service for managing user analysis configurations and templates.
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.database.models.analysis_configuration import (
    AnalysisConfiguration as AnalysisConfigurationModel,
)
from core.schemas.statistical_indicators import (
    COMMON_ANALYSIS_TEMPLATES,
    AnalysisConfiguration,
    AnalysisConfigurationCreate,
    AnalysisConfigurationListResponse,
    AnalysisConfigurationUpdate,
    PredefinedConfiguration,
)


class AnalysisConfigurationService:
    """Service for managing analysis configurations."""

    def __init__(self, db: Session):
        self.db = db

    def create_configuration(
        self, 
        user_id: int, 
        config_data: AnalysisConfigurationCreate
    ) -> AnalysisConfiguration:
        """Create a new analysis configuration."""
        db_config = AnalysisConfigurationModel(
            user_id=user_id,
            name=config_data.name,
            description=config_data.description,
            indicators=config_data.indicators,
            chart_settings=config_data.chart_settings,
            is_public=config_data.is_public,
            tags=config_data.tags
        )
        
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        
        return self._db_to_schema(db_config)

    def get_configuration(self, config_id: int, user_id: Optional[int] = None) -> Optional[AnalysisConfiguration]:
        """Get a specific analysis configuration."""
        query = self.db.query(AnalysisConfigurationModel).filter(
            AnalysisConfigurationModel.id == config_id
        )
        
        # If user_id is provided, only return if it's the user's config or it's public
        if user_id:
            query = query.filter(
                or_(
                    AnalysisConfigurationModel.user_id == user_id,
                    AnalysisConfigurationModel.is_public == True
                )
            )
        
        db_config = query.first()
        if not db_config:
            return None
        
        return self._db_to_schema(db_config)

    def get_user_configurations(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> AnalysisConfigurationListResponse:
        """Get user's analysis configurations."""
        query = self.db.query(AnalysisConfigurationModel).filter(
            AnalysisConfigurationModel.user_id == user_id
        )
        
        total_configurations = query.count()
        configurations = query.offset(skip).limit(limit).all()
        
        return AnalysisConfigurationListResponse(
            configurations=[self._db_to_schema(config) for config in configurations],
            total_configurations=total_configurations,
            user_configurations=total_configurations,
            public_configurations=0  # This would be calculated separately
        )

    def get_public_configurations(
        self, 
        skip: int = 0, 
        limit: int = 100,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> AnalysisConfigurationListResponse:
        """Get public analysis configurations."""
        query = self.db.query(AnalysisConfigurationModel).filter(
            AnalysisConfigurationModel.is_public == True
        )
        
        # Filter by category if provided
        if category:
            query = query.filter(AnalysisConfigurationModel.tags.contains([category]))
        
        # Filter by tags if provided
        if tags:
            for tag in tags:
                query = query.filter(AnalysisConfigurationModel.tags.contains([tag]))
        
        total_configurations = query.count()
        configurations = query.offset(skip).limit(limit).all()
        
        return AnalysisConfigurationListResponse(
            configurations=[self._db_to_schema(config) for config in configurations],
            total_configurations=total_configurations,
            user_configurations=0,
            public_configurations=total_configurations
        )

    def update_configuration(
        self, 
        config_id: int, 
        user_id: int, 
        update_data: AnalysisConfigurationUpdate
    ) -> Optional[AnalysisConfiguration]:
        """Update an analysis configuration."""
        db_config = self.db.query(AnalysisConfigurationModel).filter(
            and_(
                AnalysisConfigurationModel.id == config_id,
                AnalysisConfigurationModel.user_id == user_id
            )
        ).first()
        
        if not db_config:
            return None
        
        # Update fields
        if update_data.name is not None:
            db_config.name = update_data.name
        if update_data.description is not None:
            db_config.description = update_data.description
        if update_data.indicators is not None:
            db_config.indicators = update_data.indicators
        if update_data.chart_settings is not None:
            db_config.chart_settings = update_data.chart_settings
        if update_data.is_public is not None:
            db_config.is_public = update_data.is_public
        if update_data.tags is not None:
            db_config.tags = update_data.tags
        
        db_config.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_config)
        
        return self._db_to_schema(db_config)

    def delete_configuration(self, config_id: int, user_id: int) -> bool:
        """Delete an analysis configuration."""
        db_config = self.db.query(AnalysisConfigurationModel).filter(
            and_(
                AnalysisConfigurationModel.id == config_id,
                AnalysisConfigurationModel.user_id == user_id
            )
        ).first()
        
        if not db_config:
            return False
        
        self.db.delete(db_config)
        self.db.commit()
        
        return True

    def duplicate_configuration(
        self, 
        config_id: int, 
        user_id: int, 
        new_name: str
    ) -> Optional[AnalysisConfiguration]:
        """Duplicate an existing configuration."""
        original_config = self.get_configuration(config_id, user_id)
        if not original_config:
            return None
        
        # Create new configuration with same settings
        new_config_data = AnalysisConfigurationCreate(
            name=new_name,
            description=f"Copy of {original_config.name}",
            indicators=original_config.indicators,
            chart_settings=original_config.chart_settings,
            is_public=False,  # Duplicates are private by default
            tags=original_config.tags + ["duplicate"]
        )
        
        return self.create_configuration(user_id, new_config_data)

    def increment_usage_count(self, config_id: int) -> None:
        """Increment the usage count for a configuration."""
        db_config = self.db.query(AnalysisConfigurationModel).filter(
            AnalysisConfigurationModel.id == config_id
        ).first()
        
        if db_config:
            db_config.usage_count += 1
            self.db.commit()

    def get_popular_configurations(
        self, 
        limit: int = 10
    ) -> List[AnalysisConfiguration]:
        """Get most popular public configurations."""
        configurations = self.db.query(AnalysisConfigurationModel).filter(
            AnalysisConfigurationModel.is_public == True
        ).order_by(
            AnalysisConfigurationModel.usage_count.desc()
        ).limit(limit).all()
        
        return [self._db_to_schema(config) for config in configurations]

    def search_configurations(
        self, 
        query: str, 
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> AnalysisConfigurationListResponse:
        """Search configurations by name, description, or tags."""
        search_query = self.db.query(AnalysisConfigurationModel)
        
        # Apply user filter
        if user_id:
            search_query = search_query.filter(
                or_(
                    AnalysisConfigurationModel.user_id == user_id,
                    AnalysisConfigurationModel.is_public == True
                )
            )
        else:
            search_query = search_query.filter(
                AnalysisConfigurationModel.is_public == True
            )
        
        # Apply search filters
        search_query = search_query.filter(
            or_(
                AnalysisConfigurationModel.name.ilike(f"%{query}%"),
                AnalysisConfigurationModel.description.ilike(f"%{query}%"),
                AnalysisConfigurationModel.tags.any(query)
            )
        )
        
        total_configurations = search_query.count()
        configurations = search_query.offset(skip).limit(limit).all()
        
        return AnalysisConfigurationListResponse(
            configurations=[self._db_to_schema(config) for config in configurations],
            total_configurations=total_configurations,
            user_configurations=0,  # This would be calculated separately
            public_configurations=total_configurations
        )

    def get_predefined_templates(self) -> Dict[str, PredefinedConfiguration]:
        """Get predefined analysis templates."""
        return COMMON_ANALYSIS_TEMPLATES

    def create_from_template(
        self, 
        user_id: int, 
        template_name: str, 
        custom_name: Optional[str] = None
    ) -> Optional[AnalysisConfiguration]:
        """Create a configuration from a predefined template."""
        templates = self.get_predefined_templates()
        template = templates.get(template_name)
        
        if not template:
            return None
        
        config_name = custom_name or f"{template.name} - Custom"
        
        config_data = AnalysisConfigurationCreate(
            name=config_name,
            description=template.description,
            indicators=template.indicators,
            chart_settings=None,
            is_public=False,
            tags=template.tags + ["template", template.difficulty_level]
        )
        
        return self.create_configuration(user_id, config_data)

    def get_configuration_statistics(self, user_id: int) -> Dict[str, any]:
        """Get statistics about user's configurations."""
        user_configs = self.db.query(AnalysisConfigurationModel).filter(
            AnalysisConfigurationModel.user_id == user_id
        ).all()
        
        total_configs = len(user_configs)
        public_configs = len([c for c in user_configs if c.is_public])
        private_configs = total_configs - public_configs
        
        # Count by tags
        tag_counts = {}
        for config in user_configs:
            for tag in config.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Most used indicators
        indicator_counts = {}
        for config in user_configs:
            for indicator in config.indicators:
                indicator_name = indicator.indicator_name
                indicator_counts[indicator_name] = indicator_counts.get(indicator_name, 0) + 1
        
        return {
            "total_configurations": total_configs,
            "public_configurations": public_configs,
            "private_configurations": private_configs,
            "most_used_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "most_used_indicators": sorted(indicator_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "average_indicators_per_config": sum(len(c.indicators) for c in user_configs) / max(total_configs, 1)
        }

    def _db_to_schema(self, db_config: AnalysisConfigurationModel) -> AnalysisConfiguration:
        """Convert database model to schema."""
        return AnalysisConfiguration(
            id=db_config.id,
            user_id=db_config.user_id,
            name=db_config.name,
            description=db_config.description,
            indicators=db_config.indicators,
            chart_settings=db_config.chart_settings,
            is_public=db_config.is_public,
            tags=db_config.tags,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at,
            usage_count=db_config.usage_count
        )
