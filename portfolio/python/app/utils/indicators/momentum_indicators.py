import logging

import polars as pl

from utils.indicators import BaseIndicator

logger = logging.getLogger(__name__)


class MomentumIndicators(BaseIndicator):
    """Returns a Polars Dataframe with calculated different Momentum Indicators."""

    def rsi_indicator(self, window: int = 14, fillna: bool = False) -> pl.DataFrame:
        """
        Relative Strength Index (RSI)
        Compares the magnitude of recent gains and losses over a specified time
        period to measure speed and change of price movements of a security. It is
        primarily used to attempt to identify overbought or oversold conditions in
        the trading of an asset.
        https://www.investopedia.com/terms/r/rsi.asp
        :param window: N -Period.
        :param fillna: If True, fill NaN values.
        :return: DataFrame with RSI indicator field.
        """
        # Calculate price changes
        self.df = self.df.with_columns([pl.col("close").diff().alias("price_change")])

        # Calculate gains and losses
        self.df = self.df.with_columns(
            [
                pl.when(pl.col("price_change") > 0)
                .then(pl.col("price_change"))
                .otherwise(0)
                .alias("gains"),
                pl.when(pl.col("price_change") < 0)
                .then(-pl.col("price_change"))
                .otherwise(0)
                .alias("losses"),
            ]
        )

        # Wilder's smoothing: an EMA with alpha = 1/window
        min_periods = 0 if fillna else window

        self.df = self.df.with_columns(
            [
                pl.col("gains")
                .ewm_mean(alpha=1 / window, adjust=False, min_samples=min_periods)
                .alias("avg_gains"),
                pl.col("losses")
                .ewm_mean(alpha=1 / window, adjust=False, min_samples=min_periods)
                .alias("avg_losses"),
            ]
        )

        # Calculate RSI
        self.df = self.df.with_columns(
            [
                pl.when(pl.col("avg_losses") == 0)
                .then(100.0)
                .otherwise(
                    100.0
                    - (100.0 / (1.0 + (pl.col("avg_gains") / pl.col("avg_losses"))))
                )
                .alias("rsi")
            ]
        )

        # Clean up temporary columns
        self.df = self.df.drop(
            ["price_change", "gains", "losses", "avg_gains", "avg_losses"]
        )

        if fillna:
            self.df = self.df.with_columns(
                [pl.col("rsi").fill_null(strategy="forward")]
            )

        return self.df

    def roc_indicator(self, window: int = 12, fillna: bool = False) -> pl.DataFrame:
        """
        Rate of Change (ROC)
        https://school.stockcharts.com/doku.php?id=technical_indicators:rate_of_change_roc_and_momentum
        :param window: N -Period.
        :param fillna: If True, fill NaN values.
        :return: DataFrame with ROC indicator field.
        """
        # Calculate ROC: ((Current Price - Price n periods ago) / Price n periods ago) * 100
        self.df = self.df.with_columns(
            [
                (
                    (pl.col("close") - pl.col("close").shift(window))
                    / pl.col("close").shift(window)
                    * 100
                ).alias("roc")
            ]
        )

        # ***FIXED***: Changed `if not fillna:` to `if fillna:`
        if fillna:
            self.df = self.df.with_columns(
                [pl.col("roc").fill_null(strategy="forward")]
            )

        return self.df

    def stoch_rsi_indicator(
        self, window: int = 14, smooth1: int = 3, smooth2: int = 3, fillna: bool = False
    ) -> pl.DataFrame:
        """
        Stochastic RSI
        https://www.investopedia.com/terms/s/stochrsi.asp
        :param window: N -Period.
        :param smooth1: Moving average of Stochastic RSI.
        :param smooth2: Moving average of %K.
        :param fillna: If True, fill NaN values.
        :return: DataFrame with Stochastic RSI indicator fields.
        """
        # First calculate RSI if not already present
        if "rsi" not in self.df.columns:
            self.df = self.rsi_indicator(window=window, fillna=fillna)

        # Raw StochRSI = (RSI - lowest RSI) / (highest RSI - lowest RSI), in percent;
        # %K = SMA(raw, smooth1), %D = SMA(%K, smooth2)
        self.df = self.df.with_columns(
            [
                pl.col("rsi").rolling_min(window_size=window).alias("rsi_min"),
                pl.col("rsi").rolling_max(window_size=window).alias("rsi_max"),
            ]
        )
        self.df = self.df.with_columns(
            pl.when(pl.col("rsi_max") == pl.col("rsi_min"))
            .then(None)
            .otherwise(
                (pl.col("rsi") - pl.col("rsi_min"))
                / (pl.col("rsi_max") - pl.col("rsi_min"))
                * 100
            )
            .alias("stoch_rsi")
        )
        self.df = self.df.with_columns(
            pl.col("stoch_rsi").rolling_mean(window_size=smooth1).alias("stoch_rsi_k")
        )
        self.df = self.df.with_columns(
            pl.col("stoch_rsi_k").rolling_mean(window_size=smooth2).alias("stoch_rsi_d")
        )

        # Clean up temporary columns
        self.df = self.df.drop(["rsi_min", "rsi_max"])

        # ***FIXED***: Changed `if not fillna:` to `if fillna:`
        if fillna:
            self.df = self.df.with_columns(
                [
                    pl.col("stoch_rsi").fill_null(strategy="forward"),
                    pl.col("stoch_rsi_d").fill_null(strategy="forward"),
                    pl.col("stoch_rsi_k").fill_null(strategy="forward"),
                ]
            )

        return self.df

    def stoch_oscillator_indicator(
        self, window: int = 14, smooth_window: int = 3, fillna: bool = False
    ) -> pl.DataFrame:
        """
        Stochastic Oscillator
        https://school.stockcharts.com/doku.php?id=technical_indicators:stochastic_oscillator_fast_slow_and_full
        :param window: N -Period.
        :param smooth_window: SMA period over stoch_k.
        :param fillna: If True, fill NaN values.
        :return: DataFrame with Stochastic Oscillator indicator fields.
        """
        # Calculate Stochastic Oscillator
        # %K = (Close - Low_min) / (High_max - Low_min) * 100
        self.df = self.df.with_columns(
            [
                pl.col("low").rolling_min(window_size=window).alias("low_min"),
                pl.col("high").rolling_max(window_size=window).alias("high_max"),
            ]
        )

        self.df = self.df.with_columns(
            [
                pl.when(pl.col("high_max") == pl.col("low_min"))
                .then(0.0)
                .otherwise(
                    (
                        (pl.col("close") - pl.col("low_min"))
                        / (pl.col("high_max") - pl.col("low_min"))
                    )
                    * 100
                )
                .alias("stoch")
            ]
        )

        # %D = SMA of %K
        self.df = self.df.with_columns(
            [
                pl.col("stoch")
                .rolling_mean(window_size=smooth_window)
                .alias("stoch_signal")
            ]
        )

        # Clean up temporary columns
        self.df = self.df.drop(["low_min", "high_max"])

        if fillna:
            self.df = self.df.with_columns(
                [
                    pl.col("stoch").fill_null(strategy="forward"),
                    pl.col("stoch_signal").fill_null(strategy="forward"),
                ]
            )

        return self.df

    def all_momentum_indicators(self) -> pl.DataFrame:
        """
        Applies all momentum indicators.
        :return: DataFrame with the all defined momentum indicators.
        """
        self.df = self.rsi_indicator()
        self.df = self.roc_indicator()
        self.df = self.stoch_rsi_indicator()
        self.df = self.stoch_oscillator_indicator()
        return self.df


# Convenience functions (No changes needed, these are fine)
def calculate_rsi(prices: pl.Series, window: int = 14) -> pl.Series:
    """Calculate RSI for a price series."""
    df = pl.DataFrame({"close": prices})
    indicator = MomentumIndicators(df)
    result = indicator.rsi_indicator(window=window)
    return result["rsi"]


def calculate_macd(
    prices: pl.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pl.DataFrame:
    """Calculate MACD for a price series."""
    pl.DataFrame({"Close": prices})
    # This would need a trend indicators class
    # For now, return empty DataFrame as in original
    logger.warning("MACD is a trend indicator; this is a stub function.")
    return pl.DataFrame()


def calculate_stochastic(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    k_window: int = 14,
    d_window: int = 3,
) -> pl.DataFrame:
    """Calculate Stochastic Oscillator."""
    df = pl.DataFrame({"high": high, "low": low, "close": close})
    indicator = MomentumIndicators(df)
    result = indicator.stoch_oscillator_indicator(
        window=k_window, smooth_window=d_window
    )
    return result.select(["stoch", "stoch_signal"])
