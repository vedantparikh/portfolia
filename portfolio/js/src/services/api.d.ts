export interface AssetRecord {
  id?: number;
  symbol?: string;
  name?: string;
}

export const assetAPI: {
  getAssets(params?: { limit?: number }): Promise<{ data: AssetRecord[] }>;
};

export const portfolioAPI: {
  getPortfolios(): Promise<unknown[]>;
  getPortfolioSummary(id: number | string): Promise<unknown>;
};

export const transactionAPI: {
  getTransactions(params?: Record<string, unknown>): Promise<unknown[]>;
  getPortfolioTransactions(
    portfolioId: number | string,
    params?: Record<string, unknown>,
  ): Promise<unknown>;
};

export const watchlistAPI: {
  getWatchlists(includeItems?: boolean): Promise<unknown[]>;
  getWatchlist(
    watchlistId: number | string,
    includeRealTimeData?: boolean,
  ): Promise<unknown>;
  getAlerts(unreadOnly?: boolean, limit?: number): Promise<unknown>;
};

export const analyticsAPI: {
  getPortfolioAnalyticsSummary(portfolioId: number | string): Promise<unknown>;
};

export const userAssetsAPI: {
  getUserAssets(params?: Record<string, unknown>): Promise<{ assets: unknown[] }>;
};
