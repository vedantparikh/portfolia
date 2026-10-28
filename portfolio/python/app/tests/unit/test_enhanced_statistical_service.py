"""
Tests for Enhanced Statistical Service
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.schemas.statistical_indicators import (
    IndicatorCalculationRequest,
    IndicatorConfiguration,
)
from core.services.enhanced_statistical_service import EnhancedStatisticalService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def service(mock_db):
    """Enhanced statistical service instance."""
    return EnhancedStatisticalService(mock_db)


@pytest.fixture
def sample_indicators():
    """Sample indicator configurations."""
    return [
        IndicatorConfiguration(
            indicator_name="rsi_indicator",
            parameters={"window": 14, "fillna": False},
            enabled=True,
            display_name="RSI (14)",
            color="#FF6B6B",
            y_axis="secondary",
        ),
        IndicatorConfiguration(
            indicator_name="macd_indicator",
            parameters={
                "window_slow": 26,
                "window_fast": 12,
                "window_sign": 9,
                "fillna": False,
            },
            enabled=True,
            display_name="MACD",
            color="#4ECDC4",
            y_axis="secondary",
        ),
    ]


@pytest.fixture
def sample_request(sample_indicators):
    """Sample calculation request."""
    return IndicatorCalculationRequest(
        symbol="AAPL", period="6mo", interval="1d", indicators=sample_indicators
    )


class TestEnhancedStatisticalService:
    """Test cases for Enhanced Statistical Service."""

    @pytest.mark.asyncio
    async def test_get_available_indicators(self, service):
        """Test getting available indicators."""
        with patch.object(
            service.indicator_registry, "get_available_indicators"
        ) as mock_get:
            # Mock indicator objects with .dict() method
            mock_indicator = Mock()
            mock_indicator.dict.return_value = {
                "name": "rsi_indicator",
                "category": "momentum",
                "description": "RSI indicator",
                "parameters": [],
                "output_columns": ["RSI"],
                "required_columns": ["Close"],
                "class_name": "MomentumIndicators",
                "method_name": "rsi_indicator",
            }
            mock_get.return_value = [mock_indicator]

            # Mock categories and statistics
            with patch.object(
                service.indicator_registry, "get_indicator_categories"
            ) as mock_categories:
                mock_categories.return_value = [
                    "momentum",
                    "trend",
                    "volatility",
                    "volume",
                ]

                with patch.object(
                    service.indicator_registry, "get_indicator_statistics"
                ) as mock_stats:
                    mock_stats.return_value = {"total_indicators": 16}

            result = await service.get_available_indicators()

            assert "indicators" in result
            assert "categories" in result
            assert "statistics" in result
            assert len(result["indicators"]) == 1
            assert result["indicators"][0]["name"] == "rsi_indicator"

    @pytest.mark.asyncio
    async def test_calculate_indicators_validation_error(self, service, sample_request):
        """Test indicator calculation with validation errors."""
        # Mock market data service
        mock_market_data = Mock()
        mock_market_data.empty = False

        with patch.object(
            service.market_data_service, "fetch_ticker_data", new_callable=AsyncMock
        ) as mock_get_data:
            mock_get_data.return_value = mock_market_data

            # Mock validation errors
            with patch.object(
                service.indicator_registry, "validate_indicator_configuration"
            ) as mock_validate:
                from core.schemas.statistical_indicators import (
                    IndicatorValidationError,
                )

                mock_validate.return_value = [
                    IndicatorValidationError(
                        indicator_name="rsi_indicator",
                        parameter_name="window",
                        error_message="Invalid window value",
                        provided_value=-1,
                        expected_type="integer",
                    )
                ]

                with pytest.raises(ValueError, match="Validation errors"):
                    await service.calculate_indicators(sample_request)

    @pytest.mark.asyncio
    async def test_calculate_indicators_no_data(self, service, sample_request):
        """Test indicator calculation with no market data."""
        # Mock empty market data
        mock_market_data = Mock()
        mock_market_data.empty = True

        with patch.object(
            service.market_data_service, "fetch_ticker_data", new_callable=AsyncMock
        ) as mock_get_data:
            mock_get_data.return_value = mock_market_data

            with pytest.raises(ValueError, match="No market data found"):
                await service.calculate_indicators(sample_request)

    @pytest.mark.asyncio
    async def test_get_predefined_templates(self, service):
        """Test getting predefined templates."""
        with patch.object(
            service.configuration_service, "get_predefined_templates"
        ) as mock_get:
            # Mock template objects with .dict() method
            mock_template = Mock()
            mock_template.dict.return_value = {
                "name": "Basic Technical Analysis",
                "description": "Essential indicators",
                "indicators": [],
            }
            mock_templates = {"basic_technical_analysis": mock_template}
            mock_get.return_value = mock_templates

            result = await service.get_predefined_templates()

            assert "basic_technical_analysis" in result
            assert (
                result["basic_technical_analysis"]["name"] == "Basic Technical Analysis"
            )

    @pytest.mark.asyncio
    async def test_validate_indicator_configuration(self, service):
        """Test indicator configuration validation."""
        config = IndicatorConfiguration(
            indicator_name="rsi_indicator",
            parameters={"window": 14, "fillna": False},
            enabled=True,
        )

        with patch.object(
            service.indicator_registry, "validate_indicator_configuration"
        ) as mock_validate:
            mock_validate.return_value = []

            errors = await service.validate_indicator_configuration(config)

            assert errors == []
            mock_validate.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_create_configuration_from_template(self, service):
        """Test creating configuration from template."""
        with patch.object(
            service.configuration_service, "create_from_template"
        ) as mock_create:
            mock_config = Mock()
            mock_config.dict.return_value = {"id": 1, "name": "Test Config"}
            mock_create.return_value = mock_config

            result = await service.create_configuration_from_template(
                1, "test_template", "Custom Name"
            )

            assert result == {"id": 1, "name": "Test Config"}
            mock_create.assert_called_once_with(1, "test_template", "Custom Name")

    def test_prepare_indicator_data(self, service):
        """Test preparing indicator data for chart."""
        # Mock DataFrame
        mock_df = Mock()
        mock_df.to_dicts.return_value = [{"date": datetime(2023, 1, 1), "rsi": 50.0}]
        mock_df.columns = ["date", "rsi"]

        indicators = [
            IndicatorConfiguration(
                indicator_name="rsi_indicator",
                parameters={"window": 14, "fillna": False},
                enabled=True,
                display_name="RSI (14)",
                color="#FF6B6B",
                y_axis="secondary",
            )
        ]

        # Mock indicator definition
        with patch.object(
            service.indicator_registry, "get_indicator_definition"
        ) as mock_get_def:
            mock_def = Mock()
            mock_def.output_columns = ["rsi"]
            mock_get_def.return_value = mock_def

            result = service._prepare_indicator_data(mock_df, indicators)

            assert len(result) == 1
            assert result[0]["name"] == "RSI (14)"
            assert result[0]["indicator_name"] == "rsi_indicator"
            assert result[0]["color"] == "#FF6B6B"
            assert result[0]["y_axis"] == "secondary"

    def test_prepare_volume_data(self, service):
        """Test preparing volume data for indicator calculation response."""
        # Mock DataFrame
        mock_df = Mock()
        mock_df.to_dicts.return_value = [
            {"date": datetime(2023, 1, 1), "volume": 1000000}
        ]

        result = service._prepare_volume_data(mock_df)

        assert len(result) == 1
        assert result[0].volume == 1000000
        assert result[0].date == "2023-01-01T00:00:00"
