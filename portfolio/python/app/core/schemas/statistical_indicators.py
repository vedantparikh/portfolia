"""
Statistical Indicators Configuration Schemas
Pydantic schemas for user-configurable statistical indicators and analysis configurations.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator


class IndicatorCategory(str, Enum):
    """Categories of technical indicators."""

    MOMENTUM = "momentum"
    TREND = "trend"
    VOLATILITY = "volatility"
    VOLUME = "volume"


class IndicatorParameterType(str, Enum):
    """Types of indicator parameters."""

    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"


class IndicatorParameter(BaseModel):
    """Parameter definition for an indicator."""

    name: str = Field(..., description="Parameter name")
    type: IndicatorParameterType = Field(..., description="Parameter type")
    default_value: Any = Field(..., description="Default parameter value")
    min_value: Optional[Union[int, float]] = Field(
        None, description="Minimum value for numeric parameters"
    )
    max_value: Optional[Union[int, float]] = Field(
        None, description="Maximum value for numeric parameters"
    )
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")


class IndicatorDefinition(BaseModel):
    """Definition of a statistical indicator."""

    name: str = Field(..., description="Indicator name")
    category: IndicatorCategory = Field(..., description="Indicator category")
    description: str = Field(..., description="Indicator description")
    parameters: List[IndicatorParameter] = Field(
        ..., description="Indicator parameters"
    )
    output_columns: List[str] = Field(..., description="Output column names")
    required_columns: List[str] = Field(
        ...,
        description="Required input columns (e.g., ['Close', 'High', 'Low', 'Volume'])",
    )
    class_name: str = Field(..., description="Python class name for the indicator")
    method_name: str = Field(
        ..., description="Method name to call on the indicator class"
    )


class IndicatorConfiguration(BaseModel):
    """User configuration for a specific indicator."""

    id: Optional[str] = Field(
        None, description="Unique identifier for this indicator instance"
    )
    indicator_name: str = Field(..., description="Name of the indicator")
    parameters: Dict[str, Any] = Field(..., description="Parameter values")
    enabled: bool = Field(default=True, description="Whether indicator is enabled")
    display_name: Optional[str] = Field(None, description="Custom display name")
    color: Optional[str] = Field(None, description="Color for chart display")
    line_style: Optional[str] = Field(
        None, description="Line style for chart (solid, dashed, dotted)"
    )
    line_width: Optional[int] = Field(None, description="Line width for chart")
    y_axis: Optional[str] = Field(
        None, description="Y-axis to plot on (primary, secondary)"
    )
    z_index: Optional[int] = Field(None, description="Z-index for layering indicators")
    opacity: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Opacity for the indicator line"
    )
    show_in_legend: bool = Field(default=True, description="Whether to show in legend")
    group: Optional[str] = Field(
        None, description="Group for organizing related indicators"
    )


class AnalysisConfigurationBase(BaseModel):
    """Base analysis configuration."""

    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    indicators: List[IndicatorConfiguration] = Field(
        ..., description="List of indicator configurations"
    )
    chart_settings: Optional[Dict[str, Any]] = Field(
        None, description="Chart display settings"
    )
    is_public: bool = Field(
        default=False, description="Whether configuration is public"
    )
    tags: List[str] = Field(default_factory=list, description="Configuration tags")


class AnalysisConfigurationCreate(AnalysisConfigurationBase):
    """Create analysis configuration request."""

    pass


class AnalysisConfigurationUpdate(BaseModel):
    """Update analysis configuration request."""

    name: Optional[str] = None
    description: Optional[str] = None
    indicators: Optional[List[IndicatorConfiguration]] = None
    chart_settings: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class AnalysisConfiguration(AnalysisConfigurationBase):
    """Analysis configuration response."""

    id: int = Field(..., description="Configuration ID")
    user_id: int = Field(..., description="User ID who created the configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    usage_count: int = Field(
        default=0, description="Number of times this configuration has been used"
    )

    class Config:
        from_attributes = True


class IndicatorCalculationRequest(BaseModel):
    """Request to calculate indicators for a symbol."""

    symbol: str = Field(..., description="Stock symbol")
    period: str = Field(
        default="max",
        description="Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)",
    )
    interval: str = Field(
        default="1d",
        description="Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)",
    )
    configuration_id: Optional[int] = Field(
        None, description="Analysis configuration ID"
    )
    indicators: Optional[List[IndicatorConfiguration]] = Field(
        None, description="Custom indicator configurations"
    )
    start_date: Optional[datetime] = Field(None, description="Start date for data")
    end_date: Optional[datetime] = Field(None, description="End date for data")

    @validator("indicators", always=True)
    def validate_indicators(
        cls, v: Optional[List[IndicatorConfiguration]], values: Dict[str, Any]
    ) -> Optional[List[IndicatorConfiguration]]:
        """Validate that either configuration_id or indicators is provided."""
        if not values.get("configuration_id") and not v:
            raise ValueError("Either configuration_id or indicators must be provided")
        return v


class IndicatorDataPoint(BaseModel):
    """Single data point for an indicator."""

    date: str = Field(..., description="Date in ISO format")
    value: float = Field(..., description="Indicator value")
    formatted_value: Optional[str] = Field(
        None, description="Formatted value for display"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class IndicatorSeries(BaseModel):
    """Series data for a single indicator instance."""

    id: str = Field(..., description="Unique identifier for this indicator instance")
    indicator_name: str = Field(..., description="Name of the indicator")
    display_name: str = Field(..., description="Display name for the chart")
    data: List[IndicatorDataPoint] = Field(
        ..., description="Data points for this indicator"
    )
    color: str = Field(..., description="Color for chart display")
    line_style: str = Field(default="solid", description="Line style")
    line_width: int = Field(default=1, description="Line width")
    y_axis: str = Field(default="secondary", description="Y-axis to plot on")
    z_index: int = Field(default=0, description="Z-index for layering")
    opacity: float = Field(default=1.0, description="Opacity")
    show_in_legend: bool = Field(default=True, description="Show in legend")
    group: Optional[str] = Field(None, description="Group for organization")
    parameters: Dict[str, Any] = Field(
        ..., description="Parameters used for calculation"
    )


class PriceDataPoint(BaseModel):
    """Single price data point."""

    date: str = Field(..., description="Date in ISO format")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: Optional[float] = Field(None, description="Volume")
    adjusted_close: Optional[float] = Field(None, description="Adjusted closing price")


class VolumeDataPoint(BaseModel):
    """Single volume data point."""

    date: str = Field(..., description="Date in ISO format")
    volume: float = Field(..., description="Volume")
    color: Optional[str] = Field(None, description="Color for volume bars")


class ChartMetadata(BaseModel):
    """Chart metadata information."""

    symbol: str = Field(..., description="Stock symbol")
    period: str = Field(..., description="Data period")
    interval: str = Field(..., description="Data interval")
    start_date: str = Field(..., description="Start date in ISO format")
    end_date: str = Field(..., description="End date in ISO format")
    total_records: int = Field(..., description="Total number of data records")
    indicators_count: int = Field(..., description="Number of indicators applied")
    calculation_time_ms: Optional[float] = Field(
        None, description="Calculation time in milliseconds"
    )
    data_source: str = Field(default="market_data", description="Data source")
    last_updated: str = Field(..., description="Last updated timestamp")


class IndicatorCalculationResponse(BaseModel):
    """Response containing calculated indicator data."""

    symbol: str = Field(..., description="Stock symbol")
    period: str = Field(..., description="Data period")
    interval: str = Field(..., description="Data interval")
    start_date: datetime = Field(..., description="Data start date")
    end_date: datetime = Field(..., description="Data end date")
    configuration_name: Optional[str] = Field(
        None, description="Configuration name used"
    )
    data: List[Dict[str, Any]] = Field(..., description="Calculated indicator data")
    indicators_applied: List[str] = Field(
        ..., description="List of indicators that were applied"
    )
    total_records: int = Field(..., description="Total number of data records")

    # Enhanced fields for React UI
    indicator_series: List[IndicatorSeries] = Field(
        ..., description="Indicator series data"
    )
    volume_data: Optional[List[VolumeDataPoint]] = Field(
        None, description="Volume data"
    )
    metadata: ChartMetadata = Field(..., description="Chart metadata")


class ReactChartConfig(BaseModel):
    """Configuration for React chart components."""

    height: int = Field(default=600, description="Chart height in pixels")
    width: Optional[int] = Field(None, description="Chart width in pixels")
    show_legend: bool = Field(default=True, description="Show legend")
    show_grid: bool = Field(default=True, description="Show grid lines")
    show_crosshair: bool = Field(default=True, description="Show crosshair on hover")
    theme: str = Field(default="light", description="Chart theme (light, dark)")
    animation: bool = Field(default=True, description="Enable animations")
    responsive: bool = Field(default=True, description="Make chart responsive")


class ReactChartData(BaseModel):
    """Chart data structure optimized for React components."""

    chart_type: str = Field(..., description="Chart type (candlestick, line, bar)")
    price_data: List[PriceDataPoint] = Field(
        ..., description="Price data for main chart"
    )
    indicator_series: List[IndicatorSeries] = Field(..., description="Indicator series")
    volume_data: Optional[List[VolumeDataPoint]] = Field(
        None, description="Volume data"
    )
    config: ReactChartConfig = Field(..., description="Chart configuration")
    metadata: ChartMetadata = Field(..., description="Chart metadata")


class IndicatorRegistryResponse(BaseModel):
    """Response containing available indicators registry."""

    indicators: List[IndicatorDefinition] = Field(
        ..., description="Available indicators"
    )
    categories: List[IndicatorCategory] = Field(..., description="Available categories")
    total_indicators: int = Field(..., description="Total number of indicators")


class AnalysisConfigurationListResponse(BaseModel):
    """Response for listing analysis configurations."""

    configurations: List[AnalysisConfiguration] = Field(
        ..., description="Analysis configurations"
    )
    total_configurations: int = Field(..., description="Total number of configurations")
    user_configurations: int = Field(..., description="Number of user's configurations")
    public_configurations: int = Field(
        ..., description="Number of public configurations"
    )


class IndicatorPerformanceMetrics(BaseModel):
    """Performance metrics for indicator calculations."""

    calculation_time_ms: float = Field(
        ..., description="Calculation time in milliseconds"
    )
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    data_points_processed: int = Field(
        ..., description="Number of data points processed"
    )
    indicators_calculated: int = Field(
        ..., description="Number of indicators calculated"
    )
    success_rate: float = Field(..., description="Success rate (0-1)")


class IndicatorValidationError(BaseModel):
    """Indicator validation error."""

    indicator_name: str = Field(..., description="Indicator name")
    parameter_name: str = Field(..., description="Parameter name")
    error_message: str = Field(..., description="Error message")
    provided_value: Any = Field(None, description="Provided value")
    expected_type: Optional[str] = Field(None, description="Expected type")


class IndicatorCalculationError(BaseModel):
    """Indicator calculation error."""

    symbol: str = Field(..., description="Stock symbol")
    indicator_name: str = Field(..., description="Indicator name")
    error_message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    timestamp: datetime = Field(..., description="Error timestamp")


# Predefined indicator configurations for common use cases
class PredefinedConfiguration(BaseModel):
    """Predefined analysis configuration."""

    name: str = Field(..., description="Configuration name")
    description: str = Field(..., description="Configuration description")
    category: str = Field(..., description="Configuration category")
    indicators: List[IndicatorConfiguration] = Field(
        ..., description="Indicator configurations"
    )
    tags: List[str] = Field(..., description="Configuration tags")
    difficulty_level: str = Field(
        ..., description="Difficulty level (beginner, intermediate, advanced)"
    )


# Common analysis templates
COMMON_ANALYSIS_TEMPLATES = {
    "basic_technical_analysis": PredefinedConfiguration(
        name="Basic Technical Analysis",
        description="Essential indicators for basic technical analysis",
        category="beginner",
        indicators=[
            IndicatorConfiguration(
                id="rsi_14",
                indicator_name="rsi_indicator",
                parameters={"window": 14, "fillna": False},
                display_name="RSI (14)",
                color="#FF6B6B",
                y_axis="secondary",
                group="momentum",
            ),
            IndicatorConfiguration(
                id="macd_12_26_9",
                indicator_name="macd_indicator",
                parameters={
                    "window_slow": 26,
                    "window_fast": 12,
                    "window_sign": 9,
                    "fillna": False,
                },
                display_name="MACD",
                color="#4ECDC4",
                y_axis="secondary",
                group="trend",
            ),
            IndicatorConfiguration(
                id="bb_20_2",
                indicator_name="bollinger_bands_indicator",
                parameters={"window": 20, "window_dev": 2, "fillna": False},
                display_name="Bollinger Bands",
                color="#45B7D1",
                y_axis="primary",
                group="volatility",
            ),
        ],
        tags=["beginner", "momentum", "trend", "volatility"],
        difficulty_level="beginner",
    ),
    "advanced_momentum": PredefinedConfiguration(
        name="Advanced Momentum Analysis",
        description="Comprehensive momentum indicators for advanced analysis",
        category="advanced",
        indicators=[
            IndicatorConfiguration(
                indicator_name="rsi_indicator",
                parameters={"window": 14, "fillna": False},
                display_name="RSI (14)",
                color="#FF6B6B",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="stoch_rsi_indicator",
                parameters={"window": 14, "smooth1": 3, "smooth2": 3, "fillna": False},
                display_name="Stochastic RSI",
                color="#FF9F43",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="stoch_oscillator_indicator",
                parameters={"window": 14, "smooth_window": 3, "fillna": False},
                display_name="Stochastic Oscillator",
                color="#10AC84",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="roc_indicator",
                parameters={"window": 12, "fillna": False},
                display_name="Rate of Change",
                color="#5F27CD",
                y_axis="secondary",
            ),
        ],
        tags=["advanced", "momentum", "oscillators"],
        difficulty_level="advanced",
    ),
    "trend_analysis": PredefinedConfiguration(
        name="Trend Analysis",
        description="Comprehensive trend analysis with multiple timeframes",
        category="intermediate",
        indicators=[
            IndicatorConfiguration(
                indicator_name="macd_indicator",
                parameters={
                    "window_slow": 26,
                    "window_fast": 12,
                    "window_sign": 9,
                    "fillna": False,
                },
                display_name="MACD",
                color="#4ECDC4",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="adx_indicator",
                parameters={"window": 14, "fillna": False},
                display_name="ADX",
                color="#FF6B6B",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="aroon_indicator",
                parameters={"window": 25, "fillna": False},
                display_name="Aroon",
                color="#45B7D1",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="cci_indicator",
                parameters={"window": 20, "constant": 0.015, "fillna": False},
                display_name="CCI",
                color="#10AC84",
                y_axis="secondary",
            ),
        ],
        tags=["intermediate", "trend", "directional"],
        difficulty_level="intermediate",
    ),
    "volatility_analysis": PredefinedConfiguration(
        name="Volatility Analysis",
        description="Comprehensive volatility analysis for risk assessment",
        category="intermediate",
        indicators=[
            IndicatorConfiguration(
                indicator_name="bollinger_bands_indicator",
                parameters={"window": 20, "window_dev": 2, "fillna": False},
                display_name="Bollinger Bands",
                color="#45B7D1",
                y_axis="primary",
            ),
            IndicatorConfiguration(
                indicator_name="average_true_range_indicator",
                parameters={"window": 14, "fillna": False},
                display_name="ATR",
                color="#FF6B6B",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="keltner_channel_indicator",
                parameters={
                    "window": 20,
                    "window_atr": 10,
                    "multiplier": 2,
                    "fillna": False,
                },
                display_name="Keltner Channels",
                color="#10AC84",
                y_axis="primary",
            ),
        ],
        tags=["intermediate", "volatility", "risk"],
        difficulty_level="intermediate",
    ),
    "volume_analysis": PredefinedConfiguration(
        name="Volume Analysis",
        description="Comprehensive volume analysis for confirmation signals",
        category="intermediate",
        indicators=[
            IndicatorConfiguration(
                indicator_name="mfi_indicator",
                parameters={"window": 14, "fillna": False},
                display_name="Money Flow Index",
                color="#FF6B6B",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="obv_indicator",
                parameters={"fillna": False},
                display_name="On-Balance Volume",
                color="#4ECDC4",
                y_axis="secondary",
            ),
            IndicatorConfiguration(
                indicator_name="vwap_indicator",
                parameters={"fillna": False},
                display_name="VWAP",
                color="#45B7D1",
                y_axis="primary",
            ),
            IndicatorConfiguration(
                indicator_name="force_index_indicator",
                parameters={"window": 13, "fillna": False},
                display_name="Force Index",
                color="#10AC84",
                y_axis="secondary",
            ),
        ],
        tags=["intermediate", "volume", "confirmation"],
        difficulty_level="intermediate",
    ),
    "multi_timeframe_analysis": PredefinedConfiguration(
        name="Multi-Timeframe Analysis",
        description="Same indicators with different timeframes for comprehensive analysis",
        category="advanced",
        indicators=[
            # RSI with different periods
            IndicatorConfiguration(
                id="rsi_14",
                indicator_name="rsi_indicator",
                parameters={"window": 14, "fillna": False},
                display_name="RSI (14)",
                color="#FF6B6B",
                y_axis="secondary",
                group="momentum",
                z_index=3,
            ),
            IndicatorConfiguration(
                id="rsi_21",
                indicator_name="rsi_indicator",
                parameters={"window": 21, "fillna": False},
                display_name="RSI (21)",
                color="#FF9F43",
                y_axis="secondary",
                group="momentum",
                z_index=2,
                line_style="dashed",
            ),
            # Volume with different periods
            IndicatorConfiguration(
                id="volume_sma_15",
                indicator_name="mfi_indicator",
                parameters={"window": 15, "fillna": False},
                display_name="MFI (15)",
                color="#10AC84",
                y_axis="secondary",
                group="volume",
                z_index=1,
            ),
            IndicatorConfiguration(
                id="volume_sma_30",
                indicator_name="mfi_indicator",
                parameters={"window": 30, "fillna": False},
                display_name="MFI (30)",
                color="#5F27CD",
                y_axis="secondary",
                group="volume",
                z_index=0,
                line_style="dotted",
            ),
            # Bollinger Bands with different periods
            IndicatorConfiguration(
                id="bb_20_2",
                indicator_name="bollinger_bands_indicator",
                parameters={"window": 20, "window_dev": 2, "fillna": False},
                display_name="BB (20,2)",
                color="#45B7D1",
                y_axis="primary",
                group="volatility",
                z_index=1,
            ),
            IndicatorConfiguration(
                id="bb_50_2.5",
                indicator_name="bollinger_bands_indicator",
                parameters={"window": 50, "window_dev": 2.5, "fillna": False},
                display_name="BB (50,2.5)",
                color="#FF6B6B",
                y_axis="primary",
                group="volatility",
                z_index=0,
                opacity=0.7,
            ),
        ],
        tags=["advanced", "multi-timeframe", "comprehensive"],
        difficulty_level="advanced",
    ),
}


class GfsReadingSchema(BaseModel):
    timeframe: Literal["monthly", "weekly", "daily"]
    rsi: float
    as_of: date


class GfsStrategyResponse(BaseModel):
    """RSI(14) of monthly, weekly and daily closes; all < 30 buy, all > 70 sell."""

    symbol: str
    action: Literal["buy", "sell", "hold"]
    readings: List[GfsReadingSchema]


class MacdSignalSchema(BaseModel):
    date: date
    action: Literal["buy", "sell"]
    close: float
    macd: float
    signal: float
    trend_ema: float


class MacdStrategyResponse(BaseModel):
    """MACD(12, 26, 9) crosses that pass the zero-line and 200-day EMA rules."""

    symbol: str
    since: date
    signals: List[MacdSignalSchema]
