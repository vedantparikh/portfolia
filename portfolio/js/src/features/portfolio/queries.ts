import { useQuery } from "@tanstack/react-query";

import type { Id } from "../../shared/api/client";
import { transactionAPI } from "../transactions/api";
import { portfolioAPI, portfolioCalculationsAPI } from "./api";

export const portfolioKeys = {
  all: ["portfolios"] as const,
  summary: (id: Id) => ["portfolios", id, "summary"] as const,
  recentTransactions: (id: Id) =>
    ["portfolios", id, "recent-transactions"] as const,
  periods: ["portfolios", "calculation-periods"] as const,
};

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
