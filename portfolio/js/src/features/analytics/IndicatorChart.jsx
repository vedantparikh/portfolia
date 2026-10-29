import { useState } from "react";

import EnhancedChart from "../../components/shared/EnhancedChart";
import { useIndicatorCalculation } from "./queries";

const DEFAULT_INDICATORS = ["rsi_indicator", "macd_indicator"];

// Price chart with the indicator picker, calculated server-side like the analytics view
const IndicatorChart = ({ asset, height = 500, enableFullscreen = false }) => {
  const [period, setPeriod] = useState("30d");
  const [indicators, setIndicators] = useState(DEFAULT_INDICATORS);
  const calculation = useIndicatorCalculation({
    symbol: asset?.symbol,
    period,
    interval: "1d",
    indicators: indicators.map((indicatorName) => ({
      indicator_name: indicatorName,
      parameters: {},
      enabled: true,
    })),
  });

  return (
    <EnhancedChart
      data={calculation.data?.data || []}
      period={period}
      onPeriodChange={setPeriod}
      symbol={asset?.symbol}
      currency={asset?.currency}
      assetId={asset?.id}
      height={height}
      loading={calculation.isFetching}
      showIndicators={true}
      enableIndicatorConfig={true}
      defaultIndicators={indicators}
      onIndicatorsChange={setIndicators}
      indicatorOverlayData={calculation.data?.indicator_series}
      showReturns={true}
      enableFullscreen={enableFullscreen}
      onRefresh={() => calculation.refetch()}
    />
  );
};

export default IndicatorChart;
