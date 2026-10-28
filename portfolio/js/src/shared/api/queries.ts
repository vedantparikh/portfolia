import { useQuery } from "@tanstack/react-query";

import { assetAPI, type AssetRecord } from "../../features/assets/api";
import { portfolioAPI } from "../../features/portfolio/api";
import { transactionAPI } from "../../features/transactions/api";
import { watchlistAPI } from "../../features/watchlist/api";
import { queryClient } from "./queryClient";

export const assetKeys = { all: ["assets"] as const };

export async function fetchAssets(): Promise<AssetRecord[]> {
  return assetAPI.getAssets({ limit: 1000 });
}

export function useAssets(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: assetKeys.all,
    queryFn: fetchAssets,
    enabled: options.enabled ?? true,
  });
}

export function prefetchAssets(): Promise<void> {
  return queryClient
    .prefetchQuery({ queryKey: assetKeys.all, queryFn: fetchAssets })
    .then(() => undefined);
}

export function filterAssets(
  assets: AssetRecord[],
  query: string,
  limit = 8,
): AssetRecord[] {
  if (!query || query.length < 2) {
    return [];
  }
  const searchTerm = query.toLowerCase();
  const filtered = assets.filter((asset) => {
    const symbol = asset.symbol?.toLowerCase() || "";
    const name = asset.name?.toLowerCase() || "";
    return symbol.includes(searchTerm) || name.includes(searchTerm);
  });
  filtered.sort((a, b) => {
    const aSymbol = a.symbol?.toLowerCase() || "";
    const bSymbol = b.symbol?.toLowerCase() || "";
    if (aSymbol === searchTerm) return -1;
    if (bSymbol === searchTerm) return 1;
    if (aSymbol.startsWith(searchTerm) && !bSymbol.startsWith(searchTerm)) {
      return -1;
    }
    if (bSymbol.startsWith(searchTerm) && !aSymbol.startsWith(searchTerm)) {
      return 1;
    }
    return aSymbol.localeCompare(bSymbol);
  });
  return filtered.slice(0, limit);
}

export function findAssetBySymbol(
  assets: AssetRecord[],
  symbol: string,
): AssetRecord | null {
  if (!symbol) return null;
  return (
    assets.find(
      (asset) => asset.symbol?.toLowerCase() === symbol.toLowerCase(),
    ) || null
  );
}

export const portfolioKeys = {
  all: ["portfolios"] as const,
  summary: (id: number | string) => ["portfolios", id, "summary"] as const,
  recentTransactions: (id: number | string) =>
    ["portfolios", id, "recent-transactions"] as const,
};

export const transactionKeys = {
  all: ["transactions"] as const,
};

export const watchlistKeys = {
  list: (includeItems: boolean) => ["watchlists", includeItems] as const,
  detail: (id: number | string, realtime = true) =>
    ["watchlists", "detail", id, realtime] as const,
  alerts: ["watchlists", "alerts"] as const,
};

const emptySummary = {
  total_value: 0,
  total_cost: 0,
  day_change: 0,
  total_assets: 0,
  total_transactions: 0,
};

export function usePortfolios() {
  return useQuery({
    queryKey: portfolioKeys.all,
    queryFn: () => portfolioAPI.getPortfolios(),
  });
}

export function usePortfolioAccountSummary(
  portfolioId: number | string | null,
) {
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
    enabled: portfolioId !== null && portfolioId !== "",
  });
}

export function useRecentPortfolioTransactions(
  portfolioId: number | string | null,
) {
  return useQuery({
    queryKey: portfolioKeys.recentTransactions(portfolioId ?? "none"),
    queryFn: async () => {
      try {
        const rows = await transactionAPI.getPortfolioTransactions(
          portfolioId!,
          {
            limit: 10,
            order_by: "created_at",
            order: "desc",
          },
        );
        return Array.isArray(rows) ? rows : [];
      } catch (error) {
        console.warn("Failed to load transactions:", error);
        return [];
      }
    },
    enabled: portfolioId !== null && portfolioId !== "",
  });
}

export function useTransactions() {
  return useQuery({
    queryKey: transactionKeys.all,
    queryFn: () =>
      transactionAPI.getTransactions({
        limit: 10000,
        order_by: "transaction_date",
        order: "desc",
      }),
  });
}

export function useWatchlists(includeItems = false) {
  return useQuery({
    queryKey: watchlistKeys.list(includeItems),
    queryFn: () => watchlistAPI.getWatchlists(includeItems),
  });
}

export function useWatchlist(
  watchlistId: number | string | null,
  options: { realtime?: boolean; refetchInterval?: number | false } = {},
) {
  const realtime = options.realtime ?? true;
  return useQuery({
    queryKey: watchlistKeys.detail(watchlistId ?? "none", realtime),
    queryFn: () => watchlistAPI.getWatchlist(watchlistId!, realtime),
    enabled: watchlistId !== null && watchlistId !== "",
    refetchInterval: options.refetchInterval,
  });
}

export function useWatchlistAlerts() {
  return useQuery({
    queryKey: watchlistKeys.alerts,
    queryFn: () => watchlistAPI.getAlerts(false, 50),
    refetchInterval: 60_000,
  });
}
