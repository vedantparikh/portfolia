"""
Indicator Registry Service
Service for managing and executing statistical indicators dynamically.
"""

import inspect
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

import pandas as pd
import polars as pl
from sqlalchemy.orm import Session

from core.schemas.statistical_indicators import (
    IndicatorCalculationError,
    IndicatorCategory,
    IndicatorConfiguration,
    IndicatorDefinition,
    IndicatorParameter,
    IndicatorParameterType,
    IndicatorPerformanceMetrics,
    IndicatorValidationError,
)
from utils.indicators.base import BaseIndicator
from utils.indicators.momentum_indicators import MomentumIndicators
from utils.indicators.trend_indicators import TrendIndicators
from utils.indicators.volatility_indicators import VolatilityIndicators
from utils.indicators.volume_indicators import VolumeIndicators


class IndicatorRegistryService:
    """Service for managing and executing statistical indicators."""

    def __init__(self, db: Session):
        self.db = db
        self._indicator_registry: Dict[str, IndicatorDefinition] = {}
        self._indicator_classes: Dict[str, Type] = {}
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Initialize the indicator registry with all available indicators."""
        indicator_classes_to_register = [
            (MomentumIndicators, "momentum"),
            (TrendIndicators, "trend"),
            (VolatilityIndicators, "volatility"),
            (VolumeIndicators, "volume"),
        ]
        for cls, category in indicator_classes_to_register:
            self._register_indicator_class(cls, category)

    def _register_indicator_class(self, indicator_class: Type, category: str) -> None:
        """Register an indicator class and its methods."""
        class_name = indicator_class.__name__
        self._indicator_classes[class_name] = indicator_class

        # Get all public methods that end with '_indicator'
        methods = [
            method_name
            for method_name in dir(indicator_class)
            if method_name.endswith("_indicator") and not method_name.startswith("_")
        ]

        for method_name in methods:
            method = getattr(indicator_class, method_name)
            if not callable(method):
                continue

            sig = inspect.signature(method)
            parameters = self._extract_parameters_from_signature(sig, method_name)
            required_columns = self._get_required_columns(method_name, category)
            output_columns = self._get_output_columns(method_name)

            indicator_def = IndicatorDefinition(
                name=method_name,
                category=IndicatorCategory(category),
                description=f"{method_name.replace('_', ' ').title()} indicator",
                parameters=parameters,
                output_columns=output_columns,
                required_columns=required_columns,
                class_name=class_name,
                method_name=method_name,
            )
            self._indicator_registry[method_name] = indicator_def

    def _extract_parameters_from_signature(
        self, sig: inspect.Signature, method_name: str
    ) -> List[IndicatorParameter]:
        """Extract parameter definitions from a method signature."""
        parameters = []
        type_mapping = {
            bool: IndicatorParameterType.BOOLEAN,
            float: IndicatorParameterType.FLOAT,
            str: IndicatorParameterType.STRING,
            int: IndicatorParameterType.INTEGER,
        }

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = type_mapping.get(
                param.annotation, IndicatorParameterType.INTEGER
            )
            default_value = (
                param.default if param.default != inspect.Parameter.empty else None
            )
            required = param.default == inspect.Parameter.empty

            param_def = IndicatorParameter(
                name=param_name,
                type=param_type,
                default_value=default_value,
                description=f"Parameter {param_name} for {method_name}",
                required=required,
            )

            self._add_parameter_constraints(param_def)
            parameters.append(param_def)
        return parameters

    def _add_parameter_constraints(self, param_def: IndicatorParameter) -> None:
        """Add min/max value constraints to common indicator parameters."""
        param_name = param_def.name
        if param_name in [
            "window",
            "window_slow",
            "window_fast",
            "window_sign",
            "smooth1",
            "smooth2",
            "smooth_window",
        ]:
            param_def.min_value = 1
            param_def.max_value = 200
        elif param_name in ["window_dev", "multiplier"]:
            param_def.min_value = 0.1
            param_def.max_value = 10.0
        elif param_name in ["step", "max_step", "constant"]:
            param_def.min_value = 0.001
            param_def.max_value = 1.0

    def _get_required_columns(self, method_name: str, category: str) -> List[str]:
        """Get required columns for an indicator method."""
        base_columns = {"close"}

        if category in ["volatility", "trend"]:
            base_columns.update(["high", "low"])

        if category == "volume":
            base_columns.add("volume")

        # Specific indicators that need additional columns
        if method_name in ["stoch_oscillator_indicator", "stoch_rsi_indicator"]:
            base_columns.update(["high", "low"])

        return sorted(list(base_columns))

    def _get_output_columns(self, method_name: str) -> List[str]:
        """Get output columns for an indicator method."""
        output_mapping = {
            "rsi_indicator": ["rsi"],
            "roc_indicator": ["roc"],
            "stoch_rsi_indicator": ["stoch_rsi", "stoch_rsi_k", "stoch_rsi_d"],
            "stoch_oscillator_indicator": ["stoch", "stoch_signal"],
            "macd_indicator": ["macd", "signal", "histogram"],
            "adx_indicator": ["adx", "adx_pos", "adx_neg"],
            "aroon_indicator": ["aroon_up", "aroon_down", "aroon_indicator"],
            "psar_indicator": [
                "psar",
                "psar_down",
                "psar_down_indicator",
                "psar_up",
                "psar_up_indicator",
            ],
            "cci_indicator": ["cci"],
            "bollinger_bands_indicator": [
                "bb_bbm",
                "bb_bbh",
                "bb_bbl",
                "bb_bbhi",
                "bb_bbli",
            ],
            "average_true_range_indicator": ["average_true_range"],
            "keltner_channel_indicator": [
                "keltner_channel_mband",
                "keltner_channel_hband",
                "keltner_channel_lband",
                "keltner_channel_pband",
                "keltner_channel_wband",
                "keltner_channel_hband_indicator",
                "keltner_channel_lband_indicator",
            ],
            "mfi_indicator": ["mfi"],
            "vpt_indicator": ["vpt_cumulative"],
            "vwap_indicator": ["vwap"],
            "obv_indicator": ["obv"],
            "force_index_indicator": ["force_index_smoothed"],
        }
        return output_mapping.get(method_name, [method_name.upper()])

    def get_available_indicators(self) -> List[IndicatorDefinition]:
        """Get all available indicators."""
        return list(self._indicator_registry.values())

    def get_indicators_by_category(
        self, category: IndicatorCategory
    ) -> List[IndicatorDefinition]:
        """Get indicators by category."""
        return [
            ind for ind in self._indicator_registry.values() if ind.category == category
        ]

    def get_indicator_definition(
        self, indicator_name: str
    ) -> Optional[IndicatorDefinition]:
        """Get definition for a specific indicator."""
        return self._indicator_registry.get(indicator_name)

    def validate_indicator_configuration(
        self, config: IndicatorConfiguration
    ) -> List[IndicatorValidationError]:
        """Validate an indicator configuration."""
        errors: List[IndicatorValidationError] = []
        indicator_def = self.get_indicator_definition(config.indicator_name)

        if not indicator_def:
            return [
                IndicatorValidationError(
                    indicator_name=config.indicator_name,
                    parameter_name="indicator_name",
                    error_message=f"Indicator '{config.indicator_name}' not found.",
                    provided_value=config.indicator_name,
                )
            ]

        # Ensure parameters is a dictionary before validation
        parameters: Any = config.parameters
        if isinstance(parameters, str):
            try:
                config.parameters = json.loads(parameters)
            except json.JSONDecodeError:
                return [
                    IndicatorValidationError(
                        indicator_name=config.indicator_name,
                        parameter_name="parameters",
                        error_message="Parameters field is a malformed JSON string.",
                        provided_value=parameters,
                    )
                ]

        provided_params = config.parameters.keys()
        defined_params = {p.name for p in indicator_def.parameters}

        for param_name in provided_params - defined_params:
            errors.append(
                IndicatorValidationError(
                    indicator_name=config.indicator_name,
                    parameter_name=param_name,
                    error_message=f"Unknown parameter '{param_name}'.",
                    provided_value=config.parameters.get(param_name),
                )
            )

        for param_def in indicator_def.parameters:
            if param_def.name in config.parameters:
                value = config.parameters[param_def.name]
                errors.extend(
                    self._validate_parameter_value(
                        config.indicator_name, param_def, value
                    )
                )

        for param_def in indicator_def.parameters:
            if param_def.required and param_def.name not in provided_params:
                errors.append(
                    IndicatorValidationError(
                        indicator_name=config.indicator_name,
                        parameter_name=param_def.name,
                        error_message=(
                            f"Required parameter '{param_def.name}' is missing."
                        ),
                    )
                )
        return errors

    def _validate_parameter_value(
        self,
        indicator_name: str,
        param_def: IndicatorParameter,
        value: Any,
    ) -> List[IndicatorValidationError]:
        """Validate a single parameter's value against its definition."""
        errors = []
        param_name = param_def.name
        type_checks = {
            IndicatorParameterType.INTEGER: (int,),
            IndicatorParameterType.FLOAT: (int, float),
            IndicatorParameterType.BOOLEAN: (bool,),
            IndicatorParameterType.STRING: (str,),
        }

        expected_types = type_checks.get(param_def.type)
        if expected_types and not isinstance(value, expected_types):
            errors.append(
                IndicatorValidationError(
                    indicator_name=indicator_name,
                    parameter_name=param_name,
                    error_message=f"Parameter '{param_name}' has incorrect type.",
                    provided_value=value,
                    expected_type=param_def.type.value,
                )
            )
            return errors

        if param_def.min_value is not None and value < param_def.min_value:
            errors.append(
                IndicatorValidationError(
                    indicator_name=indicator_name,
                    parameter_name=param_name,
                    error_message=(f"Value must be >= {param_def.min_value}."),
                    provided_value=value,
                )
            )

        if param_def.max_value is not None and value > param_def.max_value:
            errors.append(
                IndicatorValidationError(
                    indicator_name=indicator_name,
                    parameter_name=param_name,
                    error_message=(f"Value must be <= {param_def.max_value}."),
                    provided_value=value,
                )
            )
        return errors

    def calculate_indicators(
        self, data: pd.DataFrame, configurations: List[IndicatorConfiguration]
    ) -> Tuple[
        pl.DataFrame, List[IndicatorCalculationError], IndicatorPerformanceMetrics
    ]:
        """
        Calculate indicators based on a list of configurations.
        Accepts a pandas DataFrame and converts it internally to Polars for processing.
        """
        start_time = time.time()
        errors: List[IndicatorCalculationError] = []

        try:
            result_df = BaseIndicator(pl.from_pandas(data)).df
        except Exception as e:
            err = self._create_calculation_error(
                "DataFrame Conversion",
                e,
                f"Failed to convert pandas DataFrame to Polars: {e}",
            )
            performance_metrics = self._calculate_performance_metrics(
                start_time, time.time(), pl.DataFrame(), configurations, [err]
            )
            return pl.DataFrame(), [err], performance_metrics

        indicators_by_class = self._group_configs_by_class(configurations, errors)

        for class_name, configs in indicators_by_class.items():
            try:
                indicator_class = self._indicator_classes[class_name]
                indicator_instance = indicator_class(result_df)

                for config, indicator_def in configs:
                    try:
                        method = getattr(indicator_instance, indicator_def.method_name)
                        temp_df = method(**config.parameters)

                        outputs = [
                            col
                            for col in indicator_def.output_columns
                            if col in temp_df.columns
                        ]
                        result_df = result_df.with_columns(
                            temp_df.select(outputs).rename(
                                {col: f"{col}_{config.id}" for col in outputs}
                            )
                        )

                    except Exception as e:
                        errors.append(
                            self._create_calculation_error(config.indicator_name, e)
                        )

            except Exception as e:
                for config, _ in configs:
                    msg = f"Failed to initialize class {class_name}: {e}"
                    errors.append(
                        self._create_calculation_error(config.indicator_name, e, msg)
                    )

        end_time = time.time()
        performance_metrics = self._calculate_performance_metrics(
            start_time, end_time, result_df, configurations, errors
        )
        return result_df, errors, performance_metrics

    def _group_configs_by_class(
        self,
        configurations: List[IndicatorConfiguration],
        errors: List[IndicatorCalculationError],
    ) -> Dict[str, List[Tuple[IndicatorConfiguration, IndicatorDefinition]]]:
        """Group valid and enabled configurations by their class name."""
        indicators_by_class: Dict[
            str, List[Tuple[IndicatorConfiguration, IndicatorDefinition]]
        ] = {}
        for i, config in enumerate(configurations):
            if not config.enabled:
                continue

            # FIX: Check if parameters is a string and parse it into a dictionary.
            parameters: Any = config.parameters
            if isinstance(parameters, str):
                try:
                    config.parameters = json.loads(parameters)
                except json.JSONDecodeError:
                    errors.append(
                        self._create_calculation_error(
                            config.indicator_name,
                            ValueError("Malformed JSON string in parameters field."),
                        )
                    )
                    continue  # Skip this invalid configuration

            if not config.id:
                config.id = f"{i}_{hash(str(config.parameters))}"

            indicator_def = self.get_indicator_definition(config.indicator_name)
            if not indicator_def:
                errors.append(
                    self._create_calculation_error(
                        config.indicator_name,
                        ValueError(f"Indicator '{config.indicator_name}' not found."),
                    )
                )
                continue

            class_name = indicator_def.class_name
            if class_name not in indicators_by_class:
                indicators_by_class[class_name] = []
            indicators_by_class[class_name].append((config, indicator_def))
        return indicators_by_class

    def _create_calculation_error(
        self,
        indicator_name: str,
        exception: Exception,
        custom_message: Optional[str] = None,
    ) -> IndicatorCalculationError:
        """Create a standardized IndicatorCalculationError object."""
        return IndicatorCalculationError(
            symbol="unknown",
            indicator_name=indicator_name,
            error_message=custom_message or str(exception),
            error_type=type(exception).__name__,
            timestamp=datetime.now(),
        )

    def _calculate_performance_metrics(
        self,
        start_time: float,
        end_time: float,
        result_df: pl.DataFrame,
        configurations: List[IndicatorConfiguration],
        errors: List[IndicatorCalculationError],
    ) -> IndicatorPerformanceMetrics:
        """Calculate and return performance metrics for the calculation run."""
        enabled_configs_count = sum(1 for c in configurations if c.enabled)
        success_rate = (
            1.0 - (len(errors) / enabled_configs_count)
            if enabled_configs_count > 0
            else 1.0
        )
        return IndicatorPerformanceMetrics(
            calculation_time_ms=(end_time - start_time) * 1000,
            memory_usage_mb=result_df.estimated_size("mb"),
            data_points_processed=len(result_df),
            indicators_calculated=enabled_configs_count,
            success_rate=success_rate,
        )

    def get_indicator_categories(self) -> List[str]:
        """Get all available indicator category names."""
        return [category.value for category in IndicatorCategory]

    def search_indicators(self, query: str) -> List[IndicatorDefinition]:
        """Search indicators by name or description (case-insensitive)."""
        query_lower = query.lower()
        return [
            indicator
            for indicator in self._indicator_registry.values()
            if query_lower in indicator.name.lower()
            or query_lower in indicator.description.lower()
        ]

    def get_indicator_statistics(self) -> Dict[str, Any]:
        """Get summary statistics about the registered indicators."""
        categories: Dict[str, int] = {}
        for indicator in self._indicator_registry.values():
            category = indicator.category.value
            categories[category] = categories.get(category, 0) + 1

        return {
            "total_indicators": len(self._indicator_registry),
            "indicators_by_category": categories,
        }
