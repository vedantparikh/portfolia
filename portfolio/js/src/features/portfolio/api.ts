import { api, type Id, type Params } from "../../shared/api/client";

export const portfolioAPI = {
  getPortfolios: async () => {
    const { data } = await api.get("/portfolios/");
    return data.portfolios || data || [];
  },
  getStatisticsOverview: async () =>
    (await api.get("/portfolios/statistics/overview")).data,
  createPortfolio: async (portfolioData: Params) =>
    (await api.post("/portfolios/", portfolioData)).data,
  updatePortfolio: async (id: Id, portfolioData: Params) =>
    (await api.put(`/portfolios/${id}`, portfolioData)).data,
  deletePortfolio: async (id: Id) =>
    (await api.delete(`/portfolios/${id}`)).data,
  getPortfolioSummary: async (id: Id) =>
    (await api.get(`/portfolios/${id}/summary`)).data,
  getPortfolioHoldings: async (id: Id) =>
    (await api.get(`/portfolios/${id}/holdings`)).data,
  getPytrSyncAvailability: async () =>
    (await api.get("/portfolios/sync/pytr")).data,
  getSync: async (id: Id) => (await api.get(`/portfolios/${id}/sync`)).data,
  setSync: async (id: Id, source: "pytr" | null) =>
    (await api.put(`/portfolios/${id}/sync`, { source })).data,
  runSync: async (id: Id) => (await api.post(`/portfolios/${id}/sync`)).data,
  mapSyncInstrument: async (id: Id, isin: string, symbol: string) =>
    (await api.post(`/portfolios/${id}/sync/instruments`, { isin, symbol }))
      .data,
};

const calc = (portfolioId: Id) =>
  `/portfolios/calculations/portfolio/${portfolioId}`;

export const portfolioCalculationsAPI = {
  getAvailablePeriods: async () =>
    (await api.get("/portfolios/calculations/periods")).data,
  getPerformanceSeries: async (portfolioId: Id, period = "1y") =>
    (
      await api.get(`${calc(portfolioId)}/performance/series`, {
        params: { period },
      })
    ).data,
  getPortfolioPerformance: async (
    portfolioId: Id,
    period = "inception",
    endDate: string | null = null,
  ) =>
    (
      await api.get(`${calc(portfolioId)}/performance`, {
        params: { period, end_date: endDate },
      })
    ).data,
  getMultiPeriodPerformance: async (
    portfolioId: Id,
    periods = ["3m", "6m", "ytd", "1y", "2y", "3y", "5y", "inception"],
    endDate: string | null = null,
  ) => {
    const params: Params = { periods };
    if (endDate) params.end_date = endDate;
    // FastAPI wants repeated keys: ?periods=3m&periods=6m
    const response = await api.get(`${calc(portfolioId)}/multi-period`, {
      params,
      paramsSerializer: { indexes: null },
    });
    return response.data;
  },
  getBenchmarkOptions: async (currency: string) =>
    (
      await api.get("/portfolios/calculations/benchmarks", {
        params: { currency },
      })
    ).data,
  getBenchmarkComparison: async (
    portfolioId: Id,
    period = "1y",
    symbol: string | null = null,
  ) =>
    (
      await api.get(`${calc(portfolioId)}/benchmark`, {
        params: { period, symbol: symbol || undefined },
      })
    ).data,
};
