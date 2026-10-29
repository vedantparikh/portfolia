import { api, type Id, type Params } from "../../shared/api/client";
import type { Schemas } from "../../shared/api/schema";

export const watchlistAPI = {
  getAlerts: async (unreadOnly = false, limit = 50) =>
    (
      await api.get("/watchlists/alerts", {
        params: { unread_only: unreadOnly, limit },
      })
    ).data,
  acknowledgeAlerts: async (alertIds: Id[] | null = null) =>
    (await api.post("/watchlists/alerts/acknowledge", { alert_ids: alertIds }))
      .data,
  getWatchlists: async (includeItems = false) => {
    const { data } = await api.get("/watchlists/", {
      params: { include_items: includeItems },
    });
    return data.watchlists || data || [];
  },
  getWatchlist: async (watchlistId: Id, includeRealTimeData = false) =>
    (
      await api.get(`/watchlists/${watchlistId}`, {
        params: { include_real_time_data: includeRealTimeData },
      })
    ).data,
  createWatchlist: async (watchlistData: Params) =>
    (await api.post("/watchlists/", watchlistData)).data,
  updateWatchlist: async (watchlistId: Id, updateData: Params) =>
    (await api.put(`/watchlists/${watchlistId}`, updateData)).data,
  deleteWatchlist: async (watchlistId: Id) =>
    (await api.delete(`/watchlists/${watchlistId}`)).data,
  addItemToWatchlist: async (watchlistId: Id, itemData: Params) =>
    (await api.post(`/watchlists/${watchlistId}/items`, itemData)).data,
  updateWatchlistItem: async (watchlistId: Id, itemId: Id, updateData: Params) =>
    (await api.put(`/watchlists/${watchlistId}/items/${itemId}`, updateData))
      .data,
  removeItemFromWatchlist: async (watchlistId: Id, itemId: Id) =>
    (await api.delete(`/watchlists/${watchlistId}/items/${itemId}`)).data,
  getItemHistory: async (
    watchlistId: Id,
    itemId: Id,
  ): Promise<Schemas["WatchlistPricePoint"][]> =>
    (await api.get(`/watchlists/${watchlistId}/items/${itemId}/history`)).data,
  getPublicWatchlists: async (): Promise<Schemas["WatchlistResponse"][]> =>
    (await api.get("/watchlists/public")).data,
  getPublicWatchlist: async (watchlistId: Id) =>
    (await api.get(`/watchlists/public/${watchlistId}`)).data,
  reorderWatchlistItems: async (watchlistId: Id, itemIds: Id[]) =>
    (
      await api.post(`/watchlists/${watchlistId}/reorder`, {
        item_ids: itemIds,
      })
    ).data,
};
