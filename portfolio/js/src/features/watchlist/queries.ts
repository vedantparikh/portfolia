import { useQuery } from "@tanstack/react-query";

import type { Id } from "../../shared/api/client";
import { watchlistAPI } from "./api";

export const watchlistKeys = {
  list: (includeItems: boolean) => ["watchlists", includeItems] as const,
  detail: (id: Id, realtime = true) =>
    ["watchlists", "detail", id, realtime] as const,
  alerts: ["watchlists", "alerts"] as const,
  unreadAlerts: ["watchlists", "alerts", "unread"] as const,
};

export function useWatchlists(includeItems = false) {
  return useQuery({
    queryKey: watchlistKeys.list(includeItems),
    queryFn: () => watchlistAPI.getWatchlists(includeItems),
  });
}

export function useWatchlist(
  watchlistId: Id | null,
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

export function useUnreadAlertCount() {
  return useQuery({
    queryKey: watchlistKeys.unreadAlerts,
    queryFn: async (): Promise<number> => {
      try {
        return (await watchlistAPI.getAlerts(true, 1)).unread_count;
      } catch {
        return 0;
      }
    },
  });
}
