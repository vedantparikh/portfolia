import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import type { Params } from "../../shared/api/client";
import { queryClient } from "../../shared/api/queryClient";
import { assetAPI, type AssetRecord } from "./api";

export const ASSET_PAGE_SIZE = 8;

export const assetKeys = {
  all: ["assets"] as const,
  list: ["assets", "list"] as const,
  pages: (params: Params) => ["assets", "pages", params] as const,
  top: ["assets", "top"] as const,
};

export function fetchAssets(): Promise<AssetRecord[]> {
  return assetAPI.getAssets({ limit: 1000 });
}

export function useAssets(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: assetKeys.list,
    queryFn: fetchAssets,
    enabled: options.enabled ?? true,
  });
}

export function prefetchAssets(): Promise<void> {
  return queryClient
    .prefetchQuery({ queryKey: assetKeys.list, queryFn: fetchAssets })
    .then(() => undefined);
}

export function invalidateAssets(): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: assetKeys.all });
}

export function useAssetPages(
  params: Params,
  options: { refetchInterval?: number | false } = {},
) {
  return useInfiniteQuery({
    queryKey: assetKeys.pages(params),
    queryFn: ({ pageParam }) =>
      assetAPI
        .getAssets({
          ...params,
          limit: ASSET_PAGE_SIZE,
          skip: pageParam * ASSET_PAGE_SIZE,
        })
        .catch((error) => {
          console.error("Failed to get assets:", error);
          return [] as AssetRecord[];
        }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) =>
      lastPage.length === ASSET_PAGE_SIZE ? pages.length : undefined,
    refetchInterval: options.refetchInterval,
  });
}

export function useTopAssets() {
  return useQuery({
    queryKey: assetKeys.top,
    queryFn: () =>
      assetAPI.getAssets({
        limit: 10,
        sort: "market_cap",
        include_detail: true,
      }),
  });
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
