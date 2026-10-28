import { api } from "./client";

export const marketAPI = {
  getMarketStatus: async () =>
    (await api.get("/market-data/market-status")).data,
  searchSymbols: async (query: string) =>
    (await api.get("/stock/symbols", { params: { name: query } })).data,
  getStockLatestData: async (symbols: string | string[]) =>
    (
      await api.get("/stock/stock-latest-data", {
        params: {
          symbols: Array.isArray(symbols) ? symbols.join(",") : symbols,
        },
      })
    ).data,
};
