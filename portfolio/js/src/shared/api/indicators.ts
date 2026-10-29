import { api, type Id, type Params } from "./client";
import type { Schemas } from "./schema";

const base = "/statistical-indicators";

export const statisticalIndicatorsAPI = {
  getAvailableIndicators: async (
    category: string | null = null,
    search: string | null = null,
  ) => {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (search) params.append("search", search);
    return (await api.get(`${base}/indicators?${params.toString()}`)).data;
  },
  calculateIndicators: async (requestData: Params) =>
    (await api.post(`${base}/calculate`, requestData)).data,
  getConfigurations: async (skip = 0, limit = 100, userOnly = false) => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      user_only: userOnly.toString(),
    });
    return (await api.get(`${base}/configurations?${params.toString()}`)).data;
  },
  createConfiguration: async (configurationData: Params) =>
    (await api.post(`${base}/configurations`, configurationData)).data,
  updateConfiguration: async (configId: Id, configurationData: Params) =>
    (await api.put(`${base}/configurations/${configId}`, configurationData))
      .data,
  deleteConfiguration: async (configId: Id) =>
    (await api.delete(`${base}/configurations/${configId}`)).data,
  getTemplates: async () => (await api.get(`${base}/templates`)).data,
  createFromTemplate: async (templateName: string, customName?: string) =>
    (
      await api.post(`${base}/templates/${templateName}/create`, null, {
        params: customName ? { custom_name: customName } : {},
      })
    ).data,
  getStatistics: async () => (await api.get(`${base}/statistics`)).data,
  getPopular: async (limit = 10) =>
    (await api.get(`${base}/popular`, { params: { limit } })).data,
  getGfsStrategy: async (symbol: string): Promise<Schemas["GfsStrategyResponse"]> =>
    (await api.get(`${base}/strategies/gfs`, { params: { symbol } })).data,
  getMacdStrategy: async (symbol: string): Promise<Schemas["MacdStrategyResponse"]> =>
    (await api.get(`${base}/strategies/macd`, { params: { symbol } })).data,
  duplicateConfiguration: async (configId: Id, newName: string) => {
    const params = new URLSearchParams({ new_name: newName });
    return (
      await api.post(
        `${base}/configurations/${configId}/duplicate?${params.toString()}`,
      )
    ).data;
  },
};
