import { api, type Id, type Params } from "../../shared/api/client";

export const transactionAPI = {
  getTransactions: async (params: Params = {}) => {
    const { data } = await api.get("/transactions/", { params });
    return data.transactions || data || [];
  },
  getPortfolioTransactions: async (portfolioId: Id, params: Params = {}) => {
    const { data } = await api.get(`/portfolios/${portfolioId}/transactions`, {
      params,
    });
    return data.transactions || data || [];
  },
  createTransaction: async (transactionData: Params) =>
    (await api.post("/transactions/", transactionData)).data,
  updateTransaction: async (id: Id, transactionData: Params) =>
    (await api.put(`/transactions/${id}`, transactionData)).data,
  deleteTransaction: async (id: Id) =>
    (await api.delete(`/transactions/${id}`)).data,
};

export const accountStatementsAPI = {
  getSupportedProviders: async () =>
    (await api.get("/account-statements/providers")).data,
  parseStatement: async (providerId: string, file: Blob, filename: string) => {
    const formData = new FormData();
    formData.append("provider_id", providerId);
    formData.append("file", file);
    formData.append("filename", filename);
    const response = await api.post("/account-statements/parse", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },
  resolveInstruments: async (instruments: Params[]) =>
    (
      await api.post(
        "/account-statements/instruments/resolve",
        { instruments },
        { timeout: 180000 },
      )
    ).data,
  importedTransactions: async (portfolioId: number, transactions: Params[]) =>
    (
      await api.post("/account-statements/transactions/imported", {
        portfolio_id: portfolioId,
        transactions,
      })
    ).data,
  bulkCreateTransactions: async (portfolioId: Id, transactions: Params[]) =>
    (
      await api.post("/account-statements/transactions/bulk-create", {
        portfolio_id: portfolioId,
        transactions,
      })
    ).data,
};

type ExportRequest = {
  filters: Params;
  options: Params;
  custom_filename?: string;
};

export const transactionPDFExportAPI = {
  downloadPDF: async (
    filters: Params = {},
    options: Params = {},
    customFilename: string | null = null,
  ) => {
    const requestBody: ExportRequest = { filters, options };
    if (customFilename) requestBody.custom_filename = customFilename;
    return api.post("/transactions/pdf/export/download", requestBody, {
      responseType: "blob",
    });
  },
  previewExport: async (filters: Params = {}, options: Params = {}) =>
    (await api.post("/transactions/pdf/export/preview", { filters, options }))
      .data,
};
