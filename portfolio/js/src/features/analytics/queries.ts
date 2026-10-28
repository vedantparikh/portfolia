import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { Id } from "../../shared/api/client";
import { statisticalIndicatorsAPI } from "../../shared/api/indicators";
import { queryClient } from "../../shared/api/queryClient";
import { analyticsAPI } from "./api";

// Rooted under the portfolio so a transaction or portfolio write refreshes them.
export const analyticsKeys = {
  all: (id: Id) => ["portfolios", id, "analytics"] as const,
  risk: (id: Id, period: string) =>
    ["portfolios", id, "analytics", "risk", period] as const,
  allocations: (id: Id) => ["portfolios", id, "analytics", "allocations"] as const,
  rebalancing: (id: Id) => ["portfolios", id, "analytics", "rebalancing"] as const,
  benchmarks: (id: Id) => ["portfolios", id, "analytics", "benchmarks"] as const,
};

const isSet = (id: Id | null | undefined): id is Id =>
  id !== null && id !== undefined && id !== "";

const settled = <T>(result: PromiseSettledResult<T>, fallback: T): T =>
  result.status === "fulfilled" ? result.value : fallback;

export function invalidateAnalytics(portfolioId: Id): Promise<void> {
  return queryClient.invalidateQueries({
    queryKey: analyticsKeys.all(portfolioId),
  });
}

export function useRiskMetrics(portfolioId: Id | null | undefined, period: string) {
  return useQuery({
    queryKey: analyticsKeys.risk(portfolioId ?? "none", period),
    queryFn: async () => {
      const [riskMetrics, advanceRiskMetrics] = await Promise.allSettled([
        analyticsAPI.getPortfolioRiskMetrics(portfolioId!, period),
        analyticsAPI.getPortfolioAdvanceRiskMetrics(portfolioId!, period),
      ]);
      return {
        riskMetrics: settled(riskMetrics, null),
        advanceRiskMetrics: settled(advanceRiskMetrics, null),
      };
    },
    enabled: isSet(portfolioId),
  });
}

export function useAllocations(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: analyticsKeys.allocations(portfolioId ?? "none"),
    queryFn: async () => {
      const [allocations, analysis] = await Promise.allSettled([
        analyticsAPI.getPortfolioAllocations(portfolioId!),
        analyticsAPI.analyzePortfolioAllocation(portfolioId!),
      ]);
      return {
        allocations: settled(allocations, []),
        analysis: settled(analysis, null),
      };
    },
    enabled: isSet(portfolioId),
  });
}

export function useRebalancingRecommendations(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: analyticsKeys.rebalancing(portfolioId ?? "none"),
    queryFn: () => analyticsAPI.getRebalancingRecommendations(portfolioId!),
    enabled: isSet(portfolioId),
  });
}

export function usePortfolioBenchmarks(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: analyticsKeys.benchmarks(portfolioId ?? "none"),
    queryFn: () => analyticsAPI.getPortfolioBenchmarks(portfolioId!),
    enabled: isSet(portfolioId),
  });
}

export const indicatorKeys = {
  all: ["indicators"] as const,
  available: ["indicators", "available"] as const,
  configurations: ["indicators", "configurations"] as const,
  calculation: (request: Record<string, unknown>) =>
    ["indicators", "calculation", request] as const,
};

export function invalidateIndicatorConfigurations(): Promise<void> {
  return queryClient.invalidateQueries({
    queryKey: indicatorKeys.configurations,
  });
}

export function useIndicatorConfigurations(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: indicatorKeys.configurations,
    queryFn: async () =>
      (await statisticalIndicatorsAPI.getConfigurations(0, 100, true))
        ?.configurations || [],
    enabled: options.enabled ?? true,
  });
}

export function useAvailableIndicators() {
  return useQuery({
    queryKey: indicatorKeys.available,
    queryFn: async () => {
      try {
        return (await statisticalIndicatorsAPI.getAvailableIndicators())
          .indicators || [];
      } catch (error) {
        console.error("Failed to load indicators:", error);
        return [];
      }
    },
    staleTime: Infinity,
  });
}

export function useIndicatorCalculation(
  request: Record<string, unknown> & { symbol?: string },
) {
  return useQuery({
    queryKey: indicatorKeys.calculation(request),
    queryFn: () => statisticalIndicatorsAPI.calculateIndicators(request),
    enabled: Boolean(request.symbol),
    placeholderData: keepPreviousData,
  });
}
