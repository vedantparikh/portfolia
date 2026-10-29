import { api, type Id, type Params } from "../../shared/api/client";
import type { Schemas } from "../../shared/api/schema";

export type AssetRecord = Schemas["Asset"];

export const assetAPI = {
  getAssets: async (params: Params = {}): Promise<AssetRecord[]> =>
    (await api.get("/assets/", { params })).data || [],
  getAssetPage: async (
    params: Params = {},
  ): Promise<{ items: AssetRecord[]; total: number | null }> => {
    const response = await api.get("/assets/", { params });
    const total = Number(response.headers["x-total-count"]);
    return {
      items: response.data || [],
      total: Number.isFinite(total) ? total : null,
    };
  },
  getHighlights: async (): Promise<Schemas["AssetHighlights"]> =>
    (await api.get("/assets/highlights")).data,
  getAssetPrices: async (id: Id, params: Params = {}) =>
    (await api.get(`/assets/${id}/prices`, { params })).data,
  createAsset: async (assetData: Params) =>
    (await api.post("/assets/", assetData)).data,
  updateAsset: async (id: Id, assetData: Params) =>
    (await api.put(`/assets/${id}`, assetData)).data,
  deleteAsset: async (id: Id) => (await api.delete(`/assets/${id}`)).data,
  createBulkAssets: async (symbols: string[]) =>
    (await api.post("/assets/bulk-create", { symbols })).data,
};
