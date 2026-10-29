"""
Enhanced Statistical Service
Service for calculating indicators with user configurations and chart data generation.
"""

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, cast

import polars as pl
from sqlalchemy.orm import Session

from core.errors import DomainError, NotFoundError, public_message
from core.schemas.statistical_indicators import (
    IndicatorCalculationRequest,
    IndicatorCalculationResponse,
    IndicatorConfiguration,
    VolumeDataPoint,
)
from core.services.analysis_configuration_service import (
    AnalysisConfigurationService,
)
from core.services.indicator_registry_service import IndicatorRegistryService
from core.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

WARM_UP_DAYS = 400


def period_start(period: str, now: datetime) -> Optional[date]:
    """First day of a chart period ('30d', '3mo', '1y', 'ytd'); None for 'max' or unknown."""
    if period == "ytd":
        return date(now.year, 1, 1)
    match = re.fullmatch(r"(\d+)(d|mo|y)", period or "")
    if not match:
        return None
    count, unit = int(match.group(1)), match.group(2)
    days = {"d": 1, "mo": 30.44, "y": 365.25}[unit] * count
    return (now - timedelta(days=round(days))).date()


class EnhancedStatisticalService:
    """Enhanced service for statistical calculations with user configurations."""

    def __init__(self, db: Session):
        self.db = db
        self.indicator_registry = IndicatorRegistryService(db)
        self.configuration_service = AnalysisConfigurationService(db)
        self.market_data_service = MarketDataService()

    async def calculate_indicators(
        self, request: IndicatorCalculationRequest, user_id: Optional[int] = None
    ) -> IndicatorCalculationResponse:
        """Calculate indicators based on user configuration."""

        try:
            # Get market data
            # Indicators need history before the visible window (MACD ~35 bars,
            # Wilder averages several times their window): fetch ~250 trading days
            # more, calculate on all of it, return only the requested period.
            window_start = period_start(request.period, datetime.now())
            if window_start:
                market_data = await self.market_data_service.fetch_ticker_data(
                    symbol=request.symbol,
                    interval=request.interval,
                    start_date=(
                        window_start - timedelta(days=WARM_UP_DAYS)
                    ).isoformat(),
                    end_date=(date.today() + timedelta(days=1)).isoformat(),
                )
            else:
                market_data = await self.market_data_service.fetch_ticker_data(
                    symbol=request.symbol,
                    period=request.period,
                    interval=request.interval,
                )

            if market_data.empty:
                raise DomainError(f"No market data found for symbol {request.symbol}")
            # fetch_ticker_data returns newest first; indicators run forward in time
            market_data = market_data.sort_values("Date").reset_index(drop=True)

            # Get indicator configurations
            if request.configuration_id:
                config = self.configuration_service.get_configuration(
                    request.configuration_id, user_id=user_id
                )
                if not config:
                    raise NotFoundError(
                        f"Configuration {request.configuration_id} not found"
                    )
                indicator_configs = config.indicators
                configuration_name = config.name
            else:
                indicator_configs = cast(
                    List[IndicatorConfiguration], request.indicators
                )
                configuration_name = "Custom Configuration"

            # Validate all indicator configurations
            validation_errors = []
            for indicator_config in indicator_configs:
                errors = self.indicator_registry.validate_indicator_configuration(
                    indicator_config
                )
                validation_errors.extend(errors)

            if validation_errors:
                error_messages = [e.error_message for e in validation_errors]
                raise DomainError(f"Validation errors: {error_messages}")

            # Calculate indicators
            result_df, calculation_errors, performance_metrics = (
                self.indicator_registry.calculate_indicators(
                    market_data, indicator_configs
                )
            )
            if window_start:
                result_df = result_df.filter(pl.col("date").dt.date() >= window_start)
            for error in calculation_errors:
                logger.warning(
                    "Indicator %s failed: %s", error.indicator_name, error.error_message
                )

            # Convert to response format
            data_records = result_df.to_dicts()

            # Extract indicator names that were applied
            applied_indicators = [
                config.indicator_name for config in indicator_configs if config.enabled
            ]

            # Generate enhanced response data
            indicator_series = self._prepare_indicator_series(
                result_df, indicator_configs
            )
            volume_data = self._prepare_volume_data(result_df)
            metadata = self._prepare_metadata(
                request.symbol,
                request.period,
                request.interval,
                result_df,
                len(applied_indicators),
                performance_metrics,
            )

            # Increment usage count if using a saved configuration
            if request.configuration_id:
                self.configuration_service.increment_usage_count(
                    request.configuration_id
                )

            return IndicatorCalculationResponse(
                symbol=request.symbol,
                period=request.period,
                interval=request.interval,
                start_date=(
                    result_df["date"].min() if result_df.height else datetime.now()
                ),
                end_date=(
                    result_df["date"].max() if result_df.height else datetime.now()
                ),
                configuration_name=configuration_name,
                data=data_records,
                indicators_applied=applied_indicators,
                total_records=len(data_records),
                indicator_series=indicator_series,
                volume_data=volume_data,
                metadata=metadata,
            )

        except Exception as e:
            raise DomainError(
                public_message(e, "Indicators could not be calculated")
            ) from e

    def _prepare_indicator_data(
        self, df: pl.DataFrame, indicator_configs: List[IndicatorConfiguration]
    ) -> List[Dict[str, Any]]:
        """Prepare indicator data for chart display."""
        indicator_data = []

        for config in indicator_configs:
            if not config.enabled:
                continue

            # Get indicator definition to find output columns
            indicator_def = self.indicator_registry.get_indicator_definition(
                config.indicator_name
            )
            if not indicator_def:
                continue

            # Prepare data for each output column
            for output_col in indicator_def.output_columns:
                if output_col in df.columns:
                    data_points = []
                    for row in df.to_dicts():
                        if output_col in row and row[output_col] is not None:
                            data_points.append(
                                {
                                    "x": (
                                        row["date"].isoformat()
                                        if isinstance(row["date"], datetime)
                                        else str(row["date"])
                                    ),
                                    "y": float(row[output_col]),
                                }
                            )

                    if data_points:
                        indicator_data.append(
                            {
                                "name": (
                                    config.display_name
                                    or f"{config.indicator_name}_{output_col}"
                                ),
                                "indicator_name": config.indicator_name,
                                "output_column": output_col,
                                "data": data_points,
                                "color": config.color or "#000000",
                                "line_style": config.line_style or "solid",
                                "line_width": config.line_width or 1,
                                "y_axis": config.y_axis or "secondary",
                            }
                        )

        return indicator_data

    def _prepare_volume_data(self, df: pl.DataFrame) -> List[VolumeDataPoint]:
        """Prepare volume data for indicator calculation response."""
        volume_data = []

        for row in df.to_dicts():
            if "volume" in row and "date" in row and row["volume"] is not None:
                volume_data.append(
                    VolumeDataPoint(
                        date=(
                            row["date"].isoformat()
                            if isinstance(row["date"], datetime)
                            else str(row["date"])
                        ),
                        volume=float(row["volume"]),
                    )
                )

        return volume_data

    def _prepare_volume_data_for_chart(self, df: pl.DataFrame) -> List[Dict[str, Any]]:
        """Prepare volume data for chart response (legacy format)."""
        volume_data = []

        for row in df.to_dicts():
            if "volume" in row and "date" in row and row["volume"] is not None:
                volume_data.append(
                    {
                        "x": (
                            row["date"].isoformat()
                            if isinstance(row["date"], datetime)
                            else str(row["date"])
                        ),
                        "y": float(row["volume"]),
                    }
                )

        return volume_data

    def _prepare_indicator_series(
        self, df: pl.DataFrame, indicator_configs: List[IndicatorConfiguration]
    ) -> List[Dict[str, Any]]:
        """Prepare indicator series data for charts using efficient, vectorized operations."""  # noqa: E501
        indicator_series = []

        for config in indicator_configs:
            if not config.enabled or not config.id:
                continue

            # Get indicator definition to find output columns
            indicator_def = self.indicator_registry.get_indicator_definition(
                config.indicator_name
            )
            if not indicator_def:
                continue

            # Prepare data for each output column
            for output_col in indicator_def.output_columns:
                col_name = f"{output_col}_{config.id}"
                if col_name not in df.columns:
                    continue

                data_points = (
                    df.lazy()
                    .filter(pl.col(col_name).is_not_null())
                    .select(
                        [
                            pl.col("date")
                            .dt.strftime("%Y-%m-%dT%H:%M:%S%.f")
                            .alias("date"),
                            pl.col(col_name).cast(pl.Float64).alias("value"),
                            (
                                pl.col(col_name).cast(pl.Utf8)
                                + " ("
                                + pl.lit(output_col)
                                + ")"
                            ).alias("formatted_value"),
                            pl.struct(
                                [
                                    pl.lit(config.id).alias("indicator_id"),
                                    pl.lit(output_col).alias("parameter"),
                                ]
                            ).alias("metadata"),
                        ]
                    )
                    .collect()
                    .to_dicts()
                )

                if data_points:
                    indicator_series.append(
                        {
                            "id": f"{config.id}_{output_col}",
                            "indicator_name": config.indicator_name,
                            "display_name": (
                                f"{config.display_name or config.indicator_name} "
                                f"({output_col})"
                            ),
                            "data": data_points,
                            "color": config.color or "#000000",
                            "line_style": config.line_style or "solid",
                            "line_width": config.line_width or 1,
                            "y_axis": config.y_axis or "secondary",
                            "z_index": config.z_index or 0,
                            "opacity": config.opacity or 1.0,
                            "show_in_legend": config.show_in_legend,
                            "group": config.group,
                            "parameters": config.parameters,
                        }
                    )

        return indicator_series

    def _prepare_metadata(
        self,
        symbol: str,
        period: str,
        interval: str,
        df: pl.DataFrame,
        indicators_count: int,
        performance_metrics: Any,
    ) -> Dict[str, Any]:
        """Prepare chart metadata."""
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "start_date": (
                cast(date, df["date"].min()).isoformat()
                if "date" in df.columns
                else datetime.now().isoformat()
            ),
            "end_date": (
                cast(date, df["date"].max()).isoformat()
                if "date" in df.columns
                else datetime.now().isoformat()
            ),
            "total_records": len(df),
            "indicators_count": indicators_count,
            "calculation_time_ms": (
                performance_metrics.calculation_time_ms if performance_metrics else None
            ),
            "data_source": "market_data",
            "last_updated": datetime.now().isoformat(),
        }

    async def get_available_indicators(self) -> Dict[str, Any]:
        """Get all available indicators and their definitions."""
        indicators = self.indicator_registry.get_available_indicators()
        categories = self.indicator_registry.get_indicator_categories()
        statistics = self.indicator_registry.get_indicator_statistics()

        return {
            "indicators": [ind.dict() for ind in indicators],
            "categories": categories,  # categories is already a list of strings
            "statistics": statistics,
        }

    async def get_predefined_templates(self) -> Dict[str, Any]:
        """Get predefined analysis templates."""
        templates = self.configuration_service.get_predefined_templates()
        return {name: template.dict() for name, template in templates.items()}

    async def create_configuration_from_template(
        self, user_id: int, template_name: str, custom_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a configuration from a predefined template."""
        config = self.configuration_service.create_from_template(
            user_id, template_name, custom_name
        )
        return config.dict() if config else None

    async def validate_indicator_configuration(
        self, config: IndicatorConfiguration
    ) -> List[Dict[str, Any]]:
        """Validate an indicator configuration."""
        errors = self.indicator_registry.validate_indicator_configuration(config)
        return [error.dict() for error in errors]

    async def get_configuration_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics about user's configurations."""
        return self.configuration_service.get_configuration_statistics(user_id)

    async def search_configurations(
        self, query: str, user_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> Dict[str, Any]:
        """Search configurations."""
        result = self.configuration_service.search_configurations(
            query, user_id, skip, limit
        )
        return result.dict()

    async def get_popular_configurations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular public configurations."""
        configs = self.configuration_service.get_popular_configurations(limit)
        return [config.dict() for config in configs]
