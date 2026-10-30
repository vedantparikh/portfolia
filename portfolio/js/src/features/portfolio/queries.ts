import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { Id } from "../../shared/api/client";
import { analyticsAPI } from "../analytics/api";
import { transactionAPI } from "../transactions/api";
import { dividendsAPI, plannerAPI, portfolioAPI, portfolioCalculationsAPI } from "./api";

export const portfolioKeys = {
  all: ["portfolios"] as const,
  summary: (id: Id) => ["portfolios", id, "summary"] as const,
  recentTransactions: (id: Id) =>
    ["portfolios", id, "recent-transactions"] as const,
  periods: ["portfolios", "calculation-periods"] as const,
  holdings: (id: Id) => ["portfolios", id, "holdings"] as const,
  series: (id: Id, period: string) =>
    ["portfolios", id, "series", period] as const,
  performance: (id: Id, period: string) =>
    ["portfolios", id, "performance", period] as const,
  multiPeriod: (id: Id) => ["portfolios", id, "multi-period"] as const,
  benchmarkOptions: (currency: string) =>
    ["portfolios", "benchmark-options", currency] as const,
  benchmark: (id: Id, period: string, symbol: string) =>
    ["portfolios", id, "benchmark", period, symbol] as const,
  insight: (id: Id, period: string) =>
    ["portfolios", id, "insight", period] as const,
  plannerInvest: (id: Id, amount: number, minAmount: number) =>
    ["portfolios", id, "planner", "invest", amount, minAmount] as const,
  savingsPlans: (id: Id) => ["portfolios", id, "planner", "savings-plans"] as const,
  dividends: (id: Id) => ["portfolios", id, "dividends"] as const,
  goal: (id: Id, goal: Record<string, unknown>) =>
    ["portfolios", id, "planner", "goal", goal] as const,
  allocationAnalysis: (id: Id) =>
    ["portfolios", id, "analytics", "allocation-analysis"] as const,
  sync: (id: Id) => ["portfolios", id, "sync"] as const,
  pytrAvailability: ["portfolios", "sync", "pytr"] as const,
};

const isId = (id: Id | null | undefined): id is Id =>
  id !== null && id !== undefined && id !== "";

export function usePortfolioHoldings(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: portfolioKeys.holdings(portfolioId ?? "none"),
    queryFn: () => portfolioAPI.getPortfolioHoldings(portfolioId!),
    enabled: isId(portfolioId),
  });
}

export function usePerformanceSeries(
  portfolioId: Id | null | undefined,
  period: string,
) {
  return useQuery({
    queryKey: portfolioKeys.series(portfolioId ?? "none", period),
    queryFn: () =>
      portfolioCalculationsAPI.getPerformanceSeries(portfolioId!, period),
    enabled: isId(portfolioId),
  });
}

export function usePortfolioPerformance(
  portfolioId: Id | null | undefined,
  period: string,
) {
  return useQuery({
    queryKey: portfolioKeys.performance(portfolioId ?? "none", period),
    queryFn: () =>
      portfolioCalculationsAPI.getPortfolioPerformance(portfolioId!, period),
    enabled: isId(portfolioId),
    placeholderData: keepPreviousData,
  });
}

export function useMultiPeriodPerformance(
  portfolioId: Id | null | undefined,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: portfolioKeys.multiPeriod(portfolioId ?? "none"),
    queryFn: () =>
      portfolioCalculationsAPI.getMultiPeriodPerformance(portfolioId!),
    enabled: isId(portfolioId) && (options.enabled ?? true),
  });
}

export function useBenchmarkOptions(currency: string | null | undefined) {
  return useQuery({
    queryKey: portfolioKeys.benchmarkOptions(currency ?? "none"),
    queryFn: async () => {
      try {
        return (
          (await portfolioCalculationsAPI.getBenchmarkOptions(currency!))
            .options || []
        );
      } catch {
        return [];
      }
    },
    enabled: Boolean(currency),
    staleTime: Infinity,
  });
}

export function useBenchmarkComparison(
  portfolioId: Id | null | undefined,
  period: string,
  symbol: string,
) {
  return useQuery({
    queryKey: portfolioKeys.benchmark(portfolioId ?? "none", period, symbol),
    queryFn: () =>
      portfolioCalculationsAPI.getBenchmarkComparison(
        portfolioId!,
        period,
        symbol,
      ),
    enabled: isId(portfolioId) && Boolean(symbol),
  });
}

export function usePerformanceInsight(
  portfolioId: Id | null | undefined,
  period: string,
) {
  return useQuery({
    queryKey: portfolioKeys.insight(portfolioId ?? "none", period),
    queryFn: () =>
      portfolioCalculationsAPI.getPerformanceInsight(portfolioId!, period),
    enabled: isId(portfolioId),
    placeholderData: keepPreviousData,
  });
}

export function useAllocationAnalysis(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: portfolioKeys.allocationAnalysis(portfolioId ?? "none"),
    queryFn: () => analyticsAPI.analyzePortfolioAllocation(portfolioId!),
    enabled: isId(portfolioId),
  });
}

const emptySummary = {
  total_value: 0,
  total_cost: 0,
  day_change: 0,
  total_assets: 0,
  total_transactions: 0,
};

const isSet = (id: Id | null | undefined): id is Id =>
  id !== null && id !== undefined && id !== "";

export function usePortfolios() {
  return useQuery({
    queryKey: portfolioKeys.all,
    queryFn: () => portfolioAPI.getPortfolios(),
  });
}

export function usePortfolioAccountSummary(portfolioId: Id | null) {
  return useQuery({
    queryKey: portfolioKeys.summary(portfolioId ?? "none"),
    queryFn: async () => {
      try {
        return await portfolioAPI.getPortfolioSummary(portfolioId!);
      } catch (error) {
        console.warn("Failed to load portfolio summary:", error);
        return emptySummary;
      }
    },
    enabled: isSet(portfolioId),
  });
}

export function useRecentPortfolioTransactions(portfolioId: Id | null) {
  return useQuery({
    queryKey: portfolioKeys.recentTransactions(portfolioId ?? "none"),
    queryFn: async () => {
      try {
        const rows = await transactionAPI.getPortfolioTransactions(
          portfolioId!,
          { limit: 10, order_by: "created_at", order: "desc" },
        );
        return Array.isArray(rows) ? rows : [];
      } catch (error) {
        console.warn("Failed to load transactions:", error);
        return [];
      }
    },
    enabled: isSet(portfolioId),
  });
}

export interface CalculationPeriod {
  period_code: string;
  period_name: string;
}

const fallbackPeriods: CalculationPeriod[] = [
  { period_code: "inception", period_name: "Since Inception" },
];

export function useCalculationPeriods() {
  return useQuery({
    queryKey: portfolioKeys.periods,
    queryFn: async (): Promise<CalculationPeriod[]> => {
      try {
        const response = await portfolioCalculationsAPI.getAvailablePeriods();
        return response.periods || [];
      } catch (error) {
        console.error("Failed to load available periods:", error);
        return fallbackPeriods;
      }
    },
    staleTime: Infinity,
  });
}

export function usePytrSyncAvailability() {
  return useQuery({
    queryKey: portfolioKeys.pytrAvailability,
    queryFn: portfolioAPI.getPytrSyncAvailability,
    refetchInterval: (query) =>
      query.state.data?.fetch_status === "running" ? 2000 : false,
  });
}

export function usePortfolioSync(portfolioId: Id | null | undefined, enabled: boolean) {
  return useQuery({
    queryKey: portfolioKeys.sync(portfolioId ?? "none"),
    queryFn: () => portfolioAPI.getSync(portfolioId as Id),
    enabled: enabled && isId(portfolioId),
  });
}

export function useInvestPlan(
  portfolioId: Id | null | undefined,
  amount: number,
  minAmount: number,
) {
  return useQuery({
    queryKey: portfolioKeys.plannerInvest(portfolioId ?? "none", amount, minAmount),
    queryFn: () => plannerAPI.invest(portfolioId!, amount, minAmount),
    enabled: isId(portfolioId) && amount > 0,
    placeholderData: keepPreviousData,
  });
}

export function useSavingsPlans(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: portfolioKeys.savingsPlans(portfolioId ?? "none"),
    queryFn: () => plannerAPI.savingsPlans(portfolioId!),
    enabled: isId(portfolioId),
  });
}

export function useDividends(portfolioId: Id | null | undefined) {
  return useQuery({
    queryKey: portfolioKeys.dividends(portfolioId ?? "none"),
    queryFn: () => dividendsAPI.get(portfolioId!),
    enabled: isId(portfolioId),
  });
}

export function useGoalProjection(
  portfolioId: Id | null | undefined,
  goal: { target: number; targetDate: string; monthly?: number | null; annualReturn?: number | null } | null,
) {
  return useQuery({
    queryKey: portfolioKeys.goal(portfolioId ?? "none", goal ?? {}),
    queryFn: () => plannerAPI.goal(portfolioId!, goal!),
    enabled: isId(portfolioId) && Boolean(goal && goal.target > 0 && goal.targetDate),
    placeholderData: keepPreviousData,
    retry: false,
  });
}
