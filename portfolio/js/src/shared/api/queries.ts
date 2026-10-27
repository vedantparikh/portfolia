import { useQuery } from "@tanstack/react-query";

import type { AssetRecord } from "../../services/api";
import {
  analyticsAPI,
  assetAPI,
  portfolioAPI,
  transactionAPI,
  userAssetsAPI,
  watchlistAPI,
} from "../../services/api";
import { queryClient } from "./queryClient";

export const assetKeys = { all: ["assets"] as const };

export async function fetchAssets(): Promise<AssetRecord[]> {
  const response = await assetAPI.getAssets({ limit: 1000 });
  return response.data || [];
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

export function usePortfolios() {
  return useQuery({
    queryKey: ["portfolios"],
    queryFn: () => portfolioAPI.getPortfolios(),
  });
}

export function useTransactions() {
  return useQuery({
    queryKey: ["transactions"],
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
    queryKey: ["watchlists", includeItems],
    queryFn: () => watchlistAPI.getWatchlists(includeItems),
  });
}

export function useUserAssets(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ["user-assets", params],
    queryFn: () => userAssetsAPI.getUserAssets(params),
  });
}

export function usePortfolioSummary(portfolioId: number | string | null) {
  return useQuery({
    queryKey: ["analytics", "summary", portfolioId],
    queryFn: () => analyticsAPI.getPortfolioAnalyticsSummary(portfolioId!),
    enabled: portfolioId !== null && portfolioId !== "",
  });
}
