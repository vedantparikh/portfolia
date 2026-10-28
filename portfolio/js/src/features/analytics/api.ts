import { api, type Id, type Params } from "../../shared/api/client";

const base = (portfolioId: Id) => `/analytics/portfolios/${portfolioId}`;

export const analyticsAPI = {
  getPortfolioAnalyticsSummary: async (portfolioId: Id) =>
    (await api.get(`${base(portfolioId)}/summary`)).data,
  setPortfolioAllocations: async (portfolioId: Id, allocations: unknown) =>
    (await api.post(`${base(portfolioId)}/allocations`, allocations)).data,
  getPortfolioAllocations: async (portfolioId: Id) =>
    (await api.get(`${base(portfolioId)}/allocations`)).data,
  updatePortfolioAllocation: async (
    portfolioId: Id,
    allocationId: Id,
    allocationData: Params,
  ) =>
    (
      await api.put(
        `${base(portfolioId)}/allocations/${allocationId}`,
        allocationData,
      )
    ).data,
  deletePortfolioAllocation: async (portfolioId: Id, allocationId: Id) =>
    (await api.delete(`${base(portfolioId)}/allocations/${allocationId}`))
      .data,
  analyzePortfolioAllocation: async (portfolioId: Id) =>
    (await api.get(`${base(portfolioId)}/allocations/analysis`)).data,
  getPortfolioRiskMetrics: async (portfolioId: Id, period = "inception") =>
    (await api.get(`${base(portfolioId)}/risk`, { params: { period } })).data,
  getPortfolioAdvanceRiskMetrics: async (
    portfolioId: Id,
    period = "inception",
  ) =>
    (
      await api.get(`${base(portfolioId)}/advance-risk`, {
        params: { period },
      })
    ).data,
  addPortfolioBenchmark: async (portfolioId: Id, benchmarkData: Params) =>
    (await api.post(`${base(portfolioId)}/benchmarks`, benchmarkData)).data,
  getPortfolioBenchmarks: async (portfolioId: Id) =>
    (await api.get(`${base(portfolioId)}/benchmarks`)).data,
  getRebalancingRecommendations: async (portfolioId: Id) =>
    (await api.get(`${base(portfolioId)}/rebalancing/recommendations`)).data,
};
