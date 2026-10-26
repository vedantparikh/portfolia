/**
 * API SERVICE - BACKEND COMMUNICATION LAYER
 *
 * This file handles all communication with the backend server.
 * It provides a centralized way to make HTTP requests to our API.
 *
 * What this file does:
 * 1. Creates an axios instance with base configuration
 * 2. Sets up request/response interceptors for authentication
 * 3. Handles automatic token refresh
 * 4. Provides organized API methods for different features
 * 5. Manages error handling and token storage
 *
 * Key concepts for beginners:
 * - Axios: A library for making HTTP requests (like fetch but better)
 * - Interceptors: Functions that run before requests or after responses
 * - JWT Tokens: Secure way to authenticate users
 * - Local Storage: Browser storage that persists between sessions
 * - Promise: JavaScript object representing eventual completion of async operation
 */

// Import axios library for making HTTP requests
import axios from "axios";

/**
 * API base path used by axios. Defaults to the relative path "/api/v1", which the
 * browser resolves against whatever origin the page was opened from — localhost,
 * a Tailscale IP, a domain, anything — without any hardcoded host.
 *
 * The Vite dev/preview server proxy (vite.config.js) forwards /api → the FastAPI
 * container, so no CORS or mixed-host issues arise.
 *
 * Only set VITE_API_BASE_URL when the API lives on a completely separate origin,
 * e.g. VITE_API_BASE_URL=https://api.example.com/api/v1 for a CDN-hosted SPA.
 * Never point it at a Docker service name (api, portfolia_api) — those are only
 * reachable inside Docker, not from the browser.
 */
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "/api/v1"
).replace(/\/+$/, "");

/* 
  CREATE AXIOS INSTANCE - Configure axios with default settings
  This creates a pre-configured axios instance that we can reuse throughout the app
*/
const api = axios.create({
  baseURL: API_BASE_URL, // Overridable via VITE_API_BASE_URL
  timeout: 100000, // Request timeout (100 seconds)
  headers: {
    "Content-Type": "application/json", // Tell server we're sending JSON data
  },
});

export function apiErrorMessage(error, fallback) {
  const data = error?.response?.data;
  if (typeof data?.error?.message === "string" && data.error.message) {
    return data.error.message;
  }
  if (typeof data?.detail === "string" && data.detail) {
    return data.detail;
  }
  if (typeof data?.message === "string" && data.message) {
    return data.message;
  }
  return fallback;
}

/* 
  REQUEST INTERCEPTOR - Runs before every API request
  This automatically adds the authentication token to all requests
  so we don't have to manually add it to each API call
*/
api.interceptors.request.use(
  (config) => {
    // Attach the access token, if the user is logged in
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/*
  Clear all authentication data and send the user to the login page
*/
const forceLogout = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  localStorage.removeItem("profile");
  window.location.href = "/login";
};

/*
  Refresh tokens are single-use (the server rotates them on every refresh), so
  concurrent 401s must share ONE refresh request instead of each starting their own.
*/
let refreshPromise = null;

const refreshAccessToken = () => {
  if (!refreshPromise) {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      return Promise.reject(new Error("No refresh token"));
    }
    refreshPromise = authAPI
      .refreshToken(refreshToken)
      .then(({ access_token, refresh_token }) => {
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);
        return access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

/* 
  RESPONSE INTERCEPTOR - Runs after every API response
  On a 401, refreshes the access token once and retries the original request
*/
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const message = apiErrorMessage(error, "");
    if (
      message &&
      error.response?.data &&
      typeof error.response.data === "object" &&
      typeof error.response.data.detail !== "string"
    ) {
      error.response.data.detail = message;
      if (typeof error.response.data.message !== "string") {
        error.response.data.message = message;
      }
    }
    const originalRequest = error.config;
    // Auth endpoints (login, refresh, ...) report bad credentials with 401; don't refresh for them
    const isAuthEndpoint = originalRequest?.url?.startsWith("/auth/");

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;
      try {
        const accessToken = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        forceLogout();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/* 
  AUTHENTICATION API METHODS - User authentication and account management
  These methods handle all authentication-related API calls
*/
export const authAPI = {
  /* 
      USER REGISTRATION - Create a new user account
      Parameters: userData (object with user information)
      Returns: Server response with user data
    */
  register: async (userData) => {
    const response = await api.post("/auth/register", userData);
    return response.data;
  },

  /* 
      USER LOGIN - Authenticate user and get tokens
      Parameters: credentials (object with username and password)
      Returns: Server response with access and refresh tokens
    */
  login: async (credentials) => {
    const response = await api.post("/auth/login", credentials);
    return response.data;
  },

  /* 
      GET USER PROFILE - Get detailed user profile information
      Returns: Server response with user profile data
    */
  getUserProfile: async () => {
    const response = await api.get("/auth/me/profile");
    return response.data;
  },

  /* 
      GET CURRENT USER - Get basic user information
      Returns: Server response with current user data
    */
  getCurrentUser: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  /* 
      REFRESH TOKEN - Get new access token using refresh token
      Parameters: refreshToken (string)
      Returns: Server response with new access and refresh tokens
      Note: This uses direct axios call to avoid interceptor loops
    */
  refreshToken: async (refreshToken) => {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  /* 
      LOGOUT - End user session
      Clears tokens from server and local storage
    */
  logout: async () => {
    try {
      // Try to notify server about logout
      await api.post("/auth/logout");
    } catch (error) {
      // Even if server call fails, we still want to clear local data
      console.warn("Logout API call failed:", error);
    } finally {
      // Always clear local storage regardless of server response
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
    }
  },

  /* 
      FORGOT PASSWORD - Request password reset email
      Parameters: email (string)
      Returns: Server response confirming email was sent
    */
  forgotPassword: async (email) => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
  },

  /* 
      RESET PASSWORD - Set new password using reset token
      Parameters: resetData (object with token and new password)
      Returns: Server response confirming password was reset
    */
  resetPassword: async (resetData) => {
    const response = await api.post("/auth/reset-password", resetData);
    return response.data;
  },

  /* 
      VALIDATE RESET TOKEN - Check if password reset token is valid
      Parameters: token (string)
      Returns: Server response confirming token validity
    */
  validateResetToken: async (token) => {
    const response = await api.get(
      `/auth/validate-reset-token/?token=${token}`
    );
    return response.data;
  },

  /* 
      CHANGE PASSWORD - Change password for logged-in user
      Parameters: passwordData (object with old and new passwords)
      Returns: Server response confirming password was changed
    */
  changePassword: async (passwordData) => {
    const response = await api.post("/auth/change-password", passwordData);
    return response.data;
  },

  /* 
      VERIFY EMAIL - Verify user's email address
      Parameters: token (string from verification email)
      Returns: Server response confirming email was verified
    */
  verifyEmail: async (token) => {
    const response = await api.post("/auth/verify-email", { token });
    return response.data;
  },

  /* 
      RESEND VERIFICATION - Send new verification email
      Returns: Server response confirming email was sent
    */
  resendVerification: async () => {
    const response = await api.post("/auth/resend-verification");
    return response.data;
  },
};

/* 
  PORTFOLIO API METHODS - Investment portfolio management
  These methods handle all portfolio-related API calls
*/
export const portfolioAPI = {
  /* 
      GET PORTFOLIOS - Get all portfolios for the current user
      Returns: Server response with array of portfolio objects
    */
  getPortfolios: async () => {
    const response = await api.get("/portfolios/");
    return response.data.portfolios || response.data || [];
  },

  /* 
      GET STATISTICS OVERVIEW - Totals across all of the user's portfolios
      Returns: { total_portfolios, active_portfolios, total_assets, total_value }
    */
  getStatisticsOverview: async () => {
    const response = await api.get("/portfolios/statistics/overview");
    return response.data;
  },

  /* 
      CREATE PORTFOLIO - Create a new investment portfolio
      Parameters: portfolioData (object with portfolio information)
      Returns: Server response with created portfolio data
    */
  createPortfolio: async (portfolioData) => {
    const response = await api.post("/portfolios/", portfolioData);
    return response.data;
  },

  /* 
      GET PORTFOLIO - Get a specific portfolio by ID
      Parameters: id (string or number)
      Returns: Server response with portfolio details
    */
  getPortfolio: async (id) => {
    const response = await api.get(`/portfolios/${id}`);
    return response.data;
  },

  /* 
      UPDATE PORTFOLIO - Update an existing portfolio
      Parameters: id (string or number), portfolioData (object with updated information)
      Returns: Server response with updated portfolio data
    */
  updatePortfolio: async (id, portfolioData) => {
    const response = await api.put(`/portfolios/${id}`, portfolioData);
    return response.data;
  },

  /* 
      DELETE PORTFOLIO - Delete a portfolio
      Parameters: id (string or number)
      Returns: Server response confirming deletion
    */
  deletePortfolio: async (id) => {
    const response = await api.delete(`/portfolios/${id}`);
    return response.data;
  },

  /* 
      GET PORTFOLIO SUMMARY - Get performance summary for a portfolio
      Parameters: id (string or number)
      Returns: Server response with portfolio performance data
    */
  getPortfolioSummary: async (id) => {
    const response = await api.get(`/portfolios/${id}/summary`);
    return response.data;
  },

  /* 
      GET PORTFOLIO HOLDINGS - Get detailed portfolio holdings with current values and P&L
      Parameters: id (string or number)
      Returns: Server response with portfolio holdings data
    */
  getPortfolioHoldings: async (id) => {
    const response = await api.get(`/portfolios/${id}/holdings`);
    return response.data;
  },

  /* 
      REFRESH PORTFOLIO VALUES - Refresh current values and P&L for all assets in a portfolio
      Parameters: id (string or number)
      Returns: Server response with refresh status
    */
  refreshPortfolioValues: async (id) => {
    const response = await api.post(`/portfolios/${id}/refresh`);
    return response.data;
  },

  /* 
      GET PORTFOLIO ASSETS - Get all assets in a portfolio
      Parameters: id (string or number)
      Returns: Server response with portfolio assets
    */
  getPortfolioAssets: async (id) => {
    const response = await api.get(`/portfolios/${id}/assets`);
    return response.data;
  },

  /* 
      GET PORTFOLIO ASSETS WITH DETAILS - Get portfolio assets with detailed information
      Parameters: id (string or number)
      Returns: Server response with detailed portfolio assets
    */
  getPortfolioAssetsWithDetails: async (id) => {
    const response = await api.get(`/portfolios/${id}/assets/details`);
    return response.data;
  },

  /* 
      ADD ASSET TO PORTFOLIO - Add an asset to a portfolio
      Parameters: id (string or number), assetData (object)
      Returns: Server response with added asset data
    */
  addAssetToPortfolio: async (id, assetData) => {
    const response = await api.post(`/portfolios/${id}/assets`, assetData);
    return response.data;
  },

  /* 
      REMOVE ASSET FROM PORTFOLIO - Remove an asset from a portfolio
      Parameters: portfolioId (string or number), assetId (string or number)
      Returns: Server response confirming removal
    */
  removeAssetFromPortfolio: async (portfolioId, assetId) => {
    const response = await api.delete(
      `/portfolios/${portfolioId}/assets/${assetId}`
    );
    return response.data;
  },
};

/* 
  MARKET DATA API METHODS - Stock and asset information
  These methods handle all market data and asset-related API calls
*/
export const marketAPI = {
  /*
  GET MARKET STATUS - Whether the US market is open right now
  Returns: { is_open, current_time_et, timezone }
*/
  getMarketStatus: async () => {
    const response = await api.get("/market-data/market-status");
    return response.data;
  },

  /*
  GET MAJOR INDICES - Get list of major indices
  Returns: Server response with array of major indices
*/
  getMajorIndices: async () => {
    const response = await api.get("/stock/major-indices");
    return response.data;
  },

  /* 
      GET ASSETS - Get list of available assets/stocks
      Parameters: params (object with query parameters like limit, include_detail)
      Returns: Server response with array of asset objects
    */
  getAssets: async (params = {}) => {
    const response = await api.get("/assets/", { params });
    return response.data;
  },

  /* 
      GET ASSET PRICES - Get historical price data for an asset
      Parameters: id (asset ID), params (object with date range, interval)
      Returns: Server response with price history data
    */
  getAssetPrices: async (id, params = {}) => {
    const response = await api.get(`/assets/${id}/prices`, { params });
    return response.data;
  },

  /* 
      SEARCH STOCK SYMBOLS - Search for stock symbols by company name
      Parameters: query (string to search for)
      Returns: Server response with matching stock symbols
    */
  searchSymbols: async (query) => {
    const response = await api.get("/stock/symbols", {
      params: { name: query },
    });
    return response.data;
  },

  /* 
      GET STOCK LATEST DATA - Get latest market data for symbols
      Parameters: symbols (array of strings) - Stock symbols to get data for
      Returns: Server response with latest market data
    */
  getStockLatestData: async (symbols) => {
    // Convert array to comma-separated string if needed
    const symbolsParam = Array.isArray(symbols) ? symbols.join(",") : symbols;
    const response = await api.get(`/stock/stock-latest-data`, {
      params: { symbols: symbolsParam },
    });
    return response.data;
  },

  /* 
      GET BULK PRICES - Get current prices for multiple symbols
      Parameters: symbols (array of strings) - Stock symbols to get prices for
      Returns: Server response with bulk prices data
    */
  getBulkPrices: async (symbols) => {
    const response = await api.get("/market-data/prices/bulk", {
      params: { symbols: Array.isArray(symbols) ? symbols : [symbols] },
    });
    return response.data;
  },

  /* 
      GET TICKER INFO - Get comprehensive ticker information
      Parameters: symbol (string) - Stock symbol to get info for
      Returns: Server response with ticker information
    */
  getTickerInfo: async (symbol) => {
    const response = await api.get(`/market-data/ticker/${symbol}/info`);
    return response.data;
  },

  /* 
      GET TICKER DATA - Get historical market data for a ticker
      Parameters: symbol (string), params (period, interval)
      Returns: Server response with historical data
    */
  getTickerData: async (symbol, params = {}) => {
    const response = await api.get(`/market-data/ticker/${symbol}`, { params });
    return response.data;
  },
};

/* 
  USER ASSETS API METHODS - User asset management
  These methods handle all user asset-related API calls for CRUD operations
*/
export const userAssetsAPI = {
  /* 
      GET USER ASSETS - Get all assets owned by the current user
      Parameters: params (object with query parameters like limit, category)
      Returns: Server response with array of user asset objects
    */
  getUserAssets: async (params = {}) => {
    // Get assets directly from assets API (no portfolio dependency)
    try {
      const response = await api.get("/assets/", { params });
      return { assets: response.data || [] };
    } catch (error) {
      console.error("Failed to get assets:", error);
      return { assets: [] };
    }
  },

  /* 
      CREATE USER ASSET - Add a new asset to user's portfolio
      Parameters: assetData (object with symbol etc.)
      Returns: Server response with created asset data
    */
  createUserAsset: async (assetData) => {
    // Create the asset in the system for analysis purposes only (no portfolio entry)
    try {
      // Try to find existing asset by symbol first
      const existingAssets = await api.get("/assets/", {
        params: { symbol: assetData.symbol, limit: 1 },
      });

      if (existingAssets && existingAssets.length > 0) {
        return existingAssets[0];
      } else {
        // Create new asset for analysis
        const assetResponse = await api.post("/assets/", {
          symbol: assetData.symbol,
          name: assetData.name,
          asset_type: assetData.asset_type || "EQUITY",
          exchange: assetData.exchange,
          sector: assetData.sector,
          industry: assetData.industry,
          country: assetData.country,
          description: assetData.description,
          is_active: true,
        });
        return assetResponse.data;
      }
    } catch (error) {
      console.error("Failed to create/find asset:", error);
      throw new Error("Failed to create asset");
    }
  },

  /* 
      GET USER ASSET - Get a specific user asset by ID (for analysis only)
      Parameters: id (string or number)
      Returns: Server response with user asset details
    */
  getUserAsset: async (id) => {
    // Get asset directly from assets API (no portfolio dependency)
    try {
      const response = await api.get(`/assets/${id}`);
      return response.data;
    } catch (error) {
      console.error("Failed to get asset:", error);
      throw new Error("Asset not found");
    }
  },

  /* 
      UPDATE USER ASSET - Update an existing user asset
      Parameters: id (string or number), assetData (object with updated information)
      Returns: Server response with updated asset data
    */
  updateUserAsset: async (id, assetData) => {
    // Update asset directly in assets API (no portfolio dependency)
    try {
      const response = await api.put(`/assets/${id}`, {
        symbol: assetData.symbol,
        name: assetData.name,
        asset_type: assetData.asset_type,
        exchange: assetData.exchange,
        sector: assetData.sector,
        industry: assetData.industry,
        country: assetData.country,
        description: assetData.description,
        is_active: assetData.is_active,
      });
      return response.data;
    } catch (error) {
      console.error("Failed to update asset:", error);
      throw new Error("Failed to update asset");
    }
  },

  /* 
      DELETE USER ASSET - Remove an asset from user's portfolio
      Parameters: id (string or number)
      Returns: Server response confirming deletion
    */
  deleteUserAsset: async (id) => {
    // Delete asset directly from assets API (no portfolio dependency)
    try {
      const response = await api.delete(`/assets/${id}`);
      return response.data;
    } catch (error) {
      console.error("Failed to delete asset:", error);
      throw new Error("Failed to delete asset");
    }
  },

  /* 
      BULK UPDATE USER ASSETS - Update multiple assets at once
      Parameters: updates (array of asset update objects)
      Returns: Server response with updated assets data
    */
  bulkUpdateUserAssets: async (updates) => {
    // First get all portfolios for the user
    const portfoliosResponse = await api.get("/portfolios/");
    const portfolios = portfoliosResponse.data;

    if (!portfolios || portfolios.length === 0) {
      throw new Error("No portfolios found.");
    }

    // Transform updates to portfolio asset format
    const portfolioUpdates = updates.map((update) => ({
      id: update.id,
      quantity: update.quantity,
      cost_basis: update.purchase_price,
    }));

    // Update assets in the first portfolio (in a real app, you'd handle multiple portfolios)
    const portfolioId = portfolios[0].id;
    const response = await api.put(`/portfolios/${portfolioId}/assets/bulk`, {
      updates: portfolioUpdates,
    });
    return response.data;
  },
};

/* 
  ASSET API METHODS - Asset management
  These methods handle all asset-related API calls for CRUD operations
*/
export const assetAPI = {
  /* 
      GET ASSETS - Get list of available assets/stocks
      Parameters: params (object with query parameters like limit, include_detail)
      Returns: Server response with array of asset objects
    */
  getAssets: async (params = {}) => {
    const response = await api.get("/assets/", { params });
    return response;
  },

  /* 
      CREATE ASSET - Create a new financial asset
      Parameters: assetData (object with asset information)
      Returns: Server response with created asset data
    */
  createAsset: async (assetData) => {
    const response = await api.post("/assets/", assetData);
    return response;
  },

  /* 
      GET ASSET - Get a specific asset by ID
      Parameters: id (string or number)
      Returns: Server response with asset details
    */
  getAsset: async (id) => {
    const response = await api.get(`/assets/${id}`);
    return response;
  },

  /* 
      UPDATE ASSET - Update an existing asset
      Parameters: id (string or number), assetData (object with updated information)
      Returns: Server response with updated asset data
    */
  updateAsset: async (id, assetData) => {
    const response = await api.put(`/assets/${id}`, assetData);
    return response;
  },

  /* 
      DELETE ASSET - Delete an asset
      Parameters: id (string or number)
      Returns: Server response confirming deletion
    */
  deleteAsset: async (id) => {
    const response = await api.delete(`/assets/${id}`);
    return response;
  },

  /* 
      GET ASSET PRICES - Get historical price data for an asset
      Parameters: id (asset ID), params (object with date range, interval)
      Returns: Server response with price history data
    */
  getAssetPrices: async (id, params = {}) => {
    const response = await api.get(`/assets/${id}/prices`, { params });
    return response;
  },

  createBulkAssets: async (symbols) => {
    const response = await api.post('/assets/bulk-create', { symbols });
    return response;
  },
};

/* 
  TRANSACTION API METHODS - Buy/sell transaction management
  These methods handle all transaction-related API calls
*/
export const transactionAPI = {
  /* 
      GET TRANSACTIONS - Get all transactions for the current user
      Parameters: params (object with query parameters like limit, order_by)
      Returns: Server response with array of transaction objects
    */
  getTransactions: async (params = {}) => {
    const response = await api.get("/transactions/", { params });
    return response.data.transactions || response.data || [];
  },

  /* 
      GET PORTFOLIO TRANSACTIONS - Get transactions for a specific portfolio
      Parameters: portfolioId (string or number), params (query parameters)
      Returns: Server response with array of transaction objects
    */
  getPortfolioTransactions: async (portfolioId, params = {}) => {
    const response = await api.get(`/portfolios/${portfolioId}/transactions`, {
      params,
    });
    return response.data.transactions || response.data || [];
  },

  /* 
      CREATE TRANSACTION - Record a stock purchase or sell
      Parameters: transactionData (object with portfolio_id, transaction_type, symbol, quantity, price, etc.)
      Returns: Server response with created transaction data
    */
  createTransaction: async (transactionData) => {
    const response = await api.post("/transactions/", transactionData);
    return response.data;
  },

  /* 
      GET TRANSACTION - Get a specific transaction by ID
      Parameters: id (string or number)
      Returns: Server response with transaction details
    */
  getTransaction: async (id) => {
    const response = await api.get(`/transactions/${id}`);
    return response.data;
  },

  /* 
      UPDATE TRANSACTION - Update an existing transaction
      Parameters: id (string or number), transactionData (object with updated information)
      Returns: Server response with updated transaction data
    */
  updateTransaction: async (id, transactionData) => {
    const response = await api.put(`/transactions/${id}`, transactionData);
    return response.data;
  },

  /* 
      DELETE TRANSACTION - Delete a transaction
      Parameters: id (string or number)
      Returns: Server response confirming deletion
    */
  deleteTransaction: async (id) => {
    const response = await api.delete(`/transactions/${id}`);
    return response.data;
  },

  /* 
      GET TRANSACTION SUMMARY - Get transaction summary for a portfolio
      Parameters: portfolioId (string or number), params (date range)
      Returns: Server response with transaction summary data
    */
  getTransactionSummary: async (portfolioId, params = {}) => {
    const response = await api.get(`/transactions/${portfolioId}/summary`, {
      params,
    });
    return response.data;
  },

  /* 
      BULK CREATE TRANSACTIONS - Create multiple transactions at once
      Parameters: portfolioId (string or number), transactions (array of transaction objects)
      Returns: Server response with created transactions
    */
  bulkCreateTransactions: async (portfolioId, transactions) => {
    const response = await api.post("/transactions/bulk-create", {
      portfolio_id: portfolioId,
      transactions: transactions,
    });
    return response.data;
  },
};

/* 
  ANALYTICS API METHODS - Performance and analytics data
  These methods handle analytics and performance-related API calls
*/
export const analyticsAPI = {
  /* 
      GET PORTFOLIO ANALYTICS SUMMARY - Get comprehensive portfolio analytics summary
      Parameters: portfolioId (string or number)
      Returns: Server response with analytics summary data
    */
  getPortfolioAnalyticsSummary: async (portfolioId) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/summary`
    );
    return response.data;
  },

  /* 
      GET PERFORMANCE SNAPSHOT - Get portfolio performance snapshot, auto-refreshing with yfinance if stale
      Parameters: portfolioId (string or number), forceRefresh (boolean)
      Returns: Server response with performance snapshot data
    */
  getPerformanceSnapshot: async (portfolioId, forceRefresh = true) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/performance/snapshot`,
      {
        params: { force_refresh: forceRefresh },
      }
    );
    return response.data;
  },

  /* 
      DELETE PERFORMANCE SNAPSHOT - Delete a performance snapshot
      Parameters: portfolioId (string or number), snapshotId (string or number)
      Returns: Server response with deletion confirmation
    */
  deletePerformanceSnapshot: async (portfolioId, snapshotId) => {
    const response = await api.delete(
      `/analytics/portfolios/${portfolioId}/performance/${snapshotId}`
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO PERFORMANCE HISTORY - Get portfolio performance history
      Parameters: portfolioId (string or number), days (number)
      Returns: Server response with performance history data
    */
  getPortfolioPerformanceHistory: async (portfolioId, days = 30) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/performance/history`,
      {
        params: { days },
      }
    );
    return response.data;
  },

  /* 
      SET PORTFOLIO ALLOCATIONS - Set target allocations for a portfolio
      Parameters: portfolioId (string or number), allocations (array)
      Returns: Server response with allocation data
    */
  setPortfolioAllocations: async (portfolioId, allocations) => {
    const response = await api.post(
      `/analytics/portfolios/${portfolioId}/allocations`,
      allocations
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO ALLOCATIONS - Get portfolio target allocations
      Parameters: portfolioId (string or number)
      Returns: Server response with allocation data
    */
  getPortfolioAllocations: async (portfolioId) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/allocations`
    );
    return response.data;
  },

  /* 
      UPDATE PORTFOLIO ALLOCATION - Update a specific portfolio allocation
      Parameters: portfolioId (string or number), allocationId (string or number), allocationData (object)
      Returns: Server response with updated allocation data
    */
  updatePortfolioAllocation: async (
    portfolioId,
    allocationId,
    allocationData
  ) => {
    const response = await api.put(
      `/analytics/portfolios/${portfolioId}/allocations/${allocationId}`,
      allocationData
    );
    return response.data;
  },

  /* 
      DELETE PORTFOLIO ALLOCATION - Delete a portfolio allocation
      Parameters: portfolioId (string or number), allocationId (string or number)
      Returns: Server response with deletion confirmation
    */
  deletePortfolioAllocation: async (portfolioId, allocationId) => {
    const response = await api.delete(
      `/analytics/portfolios/${portfolioId}/allocations/${allocationId}`
    );
    return response.data;
  },

  /* 
      ANALYZE PORTFOLIO ALLOCATION - Analyze portfolio allocation and detect drift
      Parameters: portfolioId (string or number)
      Returns: Server response with allocation analysis data
    */
  analyzePortfolioAllocation: async (portfolioId) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/allocations/analysis`
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO RISK METRICS - Get portfolio risk metrics
      Parameters: portfolioId (string or number)
      Returns: Server response with risk metrics data
    */
  getPortfolioRiskMetrics: async (portfolioId, period = "inception") => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/risk`,
      {
        params: {
          period: period,
        },
      }
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO Advanced RISK METRICS - Get portfolio advanced risk metrics
      Parameters: portfolioId (string or number)
      Returns: Server response with advanced risk metrics data
    */
      getPortfolioAdvanceRiskMetrics: async (portfolioId, period = "inception") => {
        const response = await api.get(
          `/analytics/portfolios/${portfolioId}/advance-risk`,
          {
            params: {
              period: period,
            },
          }
        );
        return response.data;
      },

  /* 
      ADD PORTFOLIO BENCHMARK - Add a benchmark to a portfolio
      Parameters: portfolioId (string or number), benchmarkData (object)
      Returns: Server response with benchmark data
    */
  addPortfolioBenchmark: async (portfolioId, benchmarkData) => {
    const response = await api.post(
      `/analytics/portfolios/${portfolioId}/benchmarks`,
      benchmarkData
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO BENCHMARKS - Get portfolio benchmarks
      Parameters: portfolioId (string or number)
      Returns: Server response with benchmark data
    */
  getPortfolioBenchmarks: async (portfolioId) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/benchmarks`
    );
    return response.data;
  },

  /* 
      CREATE REBALANCING EVENT - Create a rebalancing event for a portfolio
      Parameters: portfolioId (string or number), eventData (object)
      Returns: Server response with event data
    */
  createRebalancingEvent: async (portfolioId, eventData) => {
    const response = await api.post(
      `/analytics/portfolios/${portfolioId}/rebalancing/events`,
      eventData
    );
    return response.data;
  },

  /* 
      GET REBALANCING EVENTS - Get rebalancing events for a portfolio
      Parameters: portfolioId (string or number), days (number)
      Returns: Server response with rebalancing events data
    */
  getRebalancingEvents: async (portfolioId, days = 90) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/rebalancing/events`,
      {
        params: { days },
      }
    );
    return response.data;
  },

  /* 
      GET REBALANCING RECOMMENDATIONS - Get rebalancing recommendations for a portfolio
      Parameters: portfolioId (string or number)
      Returns: Server response with rebalancing recommendations
    */
  getRebalancingRecommendations: async (portfolioId) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/rebalancing/recommendations`
    );
    return response.data;
  },


  /* 
      GET PORTFOLIO PERFORMANCE COMPARISON - Get portfolio performance comparison with benchmark
      Parameters: portfolioId (string or number), benchmarkId (string or number), days (number)
      Returns: Server response with performance comparison data
    */
  getPortfolioPerformanceComparison: async (
    portfolioId,
    benchmarkId = null,
    days = 30
  ) => {
    const response = await api.get(
      `/analytics/portfolios/${portfolioId}/performance/comparison`,
      {
        params: { benchmark_id: benchmarkId, days },
      }
    );
    return response.data;
  },

  /* 
      GET USER ANALYTICS DASHBOARD - Get comprehensive analytics dashboard for the current user
      Returns: Server response with user dashboard data
    */
  getUserAnalyticsDashboard: async () => {
    const response = await api.get("/analytics/users/dashboard");
    return response.data;
  },

};

/* 
  STATISTICAL INDICATORS API METHODS - Technical analysis and statistical indicators
  These methods handle all statistical indicators and analysis configuration API calls
*/
export const statisticalIndicatorsAPI = {
  /* 
      GET AVAILABLE INDICATORS - Get all available statistical indicators
      Returns: Server response with available indicators
    */
  getAvailableIndicators: async (category = null, search = null) => {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (search) params.append("search", search);

    const response = await api.get(
      `/statistical-indicators/indicators?${params.toString()}`
    );
    return response.data;
  },

  /* 
      CALCULATE INDICATORS - Calculate indicators for a symbol
      Returns: Server response with calculated indicator data
    */
  calculateIndicators: async (requestData) => {
    const response = await api.post(
      "/statistical-indicators/calculate",
      requestData
    );
    return response.data;
  },

  /* 
      GET CONFIGURATIONS - Get analysis configurations
      Returns: Server response with configurations
    */
  getConfigurations: async (skip = 0, limit = 100, userOnly = false) => {
    const params = new URLSearchParams();
    params.append("skip", skip.toString());
    params.append("limit", limit.toString());
    params.append("user_only", userOnly.toString());

    const response = await api.get(
      `/statistical-indicators/configurations?${params.toString()}`
    );
    return response.data;
  },

  /* 
      CREATE CONFIGURATION - Create a new analysis configuration
      Returns: Server response with created configuration
    */
  createConfiguration: async (configurationData) => {
    const response = await api.post(
      "/statistical-indicators/configurations",
      configurationData
    );
    return response.data;
  },

  /* 
      GET CONFIGURATION - Get a specific configuration
      Returns: Server response with configuration details
    */
  getConfiguration: async (configId) => {
    const response = await api.get(
      `/statistical-indicators/configurations/${configId}`
    );
    return response.data;
  },

  /* 
      UPDATE CONFIGURATION - Update an analysis configuration
      Returns: Server response with updated configuration
    */
  updateConfiguration: async (configId, configurationData) => {
    const response = await api.put(
      `/statistical-indicators/configurations/${configId}`,
      configurationData
    );
    return response.data;
  },

  /* 
      DELETE CONFIGURATION - Delete an analysis configuration
      Returns: Server response with deletion confirmation
    */
  deleteConfiguration: async (configId) => {
    const response = await api.delete(
      `/statistical-indicators/configurations/${configId}`
    );
    return response.data;
  },

  /* 
      GET TEMPLATES - Get predefined analysis templates
      Returns: Server response with available templates
    */
  getTemplates: async () => {
    const response = await api.get("/statistical-indicators/templates");
    return response.data;
  },

  /* 
      CREATE FROM TEMPLATE - Create configuration from template
      Returns: Server response with created configuration
    */
  createFromTemplate: async (templateName, customName = null) => {
    const params = new URLSearchParams();
    if (customName) params.append("custom_name", customName);

    const response = await api.post(
      `/statistical-indicators/templates/${templateName}/create?${params.toString()}`
    );
    return response.data;
  },

  /* 
      VALIDATE CONFIGURATION - Validate indicator configuration
      Returns: Server response with validation results
    */
  validateConfiguration: async (configuration) => {
    const response = await api.post(
      "/statistical-indicators/validate",
      configuration
    );
    return response.data;
  },

  /* 
      DUPLICATE CONFIGURATION - Duplicate an existing configuration
      Returns: Server response with duplicated configuration
    */
  duplicateConfiguration: async (configId, newName) => {
    const params = new URLSearchParams();
    params.append("new_name", newName);

    const response = await api.post(
      `/statistical-indicators/configurations/${configId}/duplicate?${params.toString()}`
    );
    return response.data;
  },

  /* 
      SEARCH CONFIGURATIONS - Search configurations by name, description, or tags
      Returns: Server response with matching configurations
    */
  searchConfigurations: async (query, skip = 0, limit = 100) => {
    const params = new URLSearchParams();
    params.append("q", query);
    params.append("skip", skip.toString());
    params.append("limit", limit.toString());

    const response = await api.get(
      `/statistical-indicators/configurations/search?${params.toString()}`
    );
    return response.data;
  },

  /* 
      GET STATISTICS - Get user's configuration statistics
      Returns: Server response with user statistics
    */
  getStatistics: async () => {
    const response = await api.get("/statistical-indicators/statistics");
    return response.data;
  },

  /* 
      GET POPULAR CONFIGURATIONS - Get popular public configurations
      Returns: Server response with popular configurations
    */
  getPopularConfigurations: async (limit = 10) => {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());

    const response = await api.get(
      `/statistical-indicators/popular?${params.toString()}`
    );
    return response.data;
  },

  /* 
      GET ASSET ANALYSIS - Get comprehensive analysis for an asset
      Returns: Server response with asset analysis data
    */
};

/* 
  PORTFOLIO CALCULATIONS API METHODS - Performance calculations and comparisons
  These methods handle all portfolio calculation-related API calls
*/
export const portfolioCalculationsAPI = {
  /* 
      GET AVAILABLE PERIODS - Get list of available calculation periods
      Returns: Server response with available periods
    */
  getAvailablePeriods: async () => {
    const response = await api.get("/portfolios/calculations/periods");
    return response.data;
  },

  /* 
      GET PERFORMANCE SERIES - Daily value, net invested and cost basis plus the period summary
      Parameters: portfolioId (string or number), period (1m, 3m, 6m, ytd, 1y, 2y, 3y, 5y, inception)
      Returns: { points: [{ date, value, net_invested, cost_basis }], summary, error }
    */
  getPerformanceSeries: async (portfolioId, period = "1y") => {
    const response = await api.get(
      `/portfolios/calculations/portfolio/${portfolioId}/performance/series`,
      { params: { period } }
    );
    return response.data;
  },

  /* 
      CALCULATE PORTFOLIO PERFORMANCE - Calculate comprehensive portfolio performance metrics
      Parameters: portfolioId (string or number), requestData (object with period, end_date, etc.)
      Returns: Server response with portfolio performance data
    */
  calculatePortfolioPerformance: async (portfolioId, requestData) => {
    const response = await api.post(
      `/portfolios/calculations/portfolio/${portfolioId}/performance`,
      requestData
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO PERFORMANCE - Get portfolio performance metrics for a specific period
      Parameters: portfolioId (string or number), period (string), endDate (string)
      Returns: Server response with portfolio performance data
    */
  getPortfolioPerformance: async (
    portfolioId,
    period = "inception",
    endDate = null
  ) => {
    const response = await api.get(
      `/portfolios/calculations/portfolio/${portfolioId}/performance`,
      {
        params: { period, end_date: endDate },
      }
    );
    return response.data;
  },

  /* 
      GET MULTI PERIOD PERFORMANCE - Calculate portfolio performance across multiple periods
      Parameters: portfolioId (string or number), periods (array), endDate (string)
      Returns: Server response with multi-period performance data
    */
  getMultiPeriodPerformance: async (
    portfolioId,
    periods = ["3m", "6m", "ytd", "1y", "2y", "3y", "5y", "inception"],
    endDate = null
  ) => {
    // Create the params object
    const params = { periods };
    if (endDate) {
      params.end_date = endDate;
    }

    const response = await api.get(
      `/portfolios/calculations/portfolio/${portfolioId}/multi-period`,
      {
        params, // Your params object

        // --- THIS IS THE FIX ---
        // Add this serializer to force the repeated-key format
        // that FastAPI requires.
        paramsSerializer: {
          indexes: null, // This serializes to: ?periods=3m&periods=6m...
        },
      }
    );
    return response.data;
  },

  /*
      GET BENCHMARK OPTIONS - Suggested total-return benchmarks for a currency
      Returns: { currency, options: [{ symbol, name }] }
    */
  getBenchmarkOptions: async (currency) => {
    const response = await api.get("/portfolios/calculations/benchmarks", {
      params: { currency },
    });
    return response.data;
  },

  /*
      GET BENCHMARK COMPARISON - The portfolio next to the same cash flows invested in a benchmark
      Parameters: portfolioId, period (code), symbol (Yahoo ticker; null = portfolio default)
      Returns: { benchmark, points[{date, value, benchmark_value, invested}], portfolio, shadow, difference, warnings, error }
    */
  getBenchmarkComparison: async (portfolioId, period = "1y", symbol = null) => {
    const response = await api.get(
      `/portfolios/calculations/portfolio/${portfolioId}/benchmark`,
      { params: { period, symbol: symbol || undefined } }
    );
    return response.data;
  },

  /* 
      GET PORTFOLIO PERFORMANCE OVERVIEW - Get comprehensive portfolio performance overview
      Parameters: portfolioId (string or number)
      Returns: Server response with portfolio performance overview data
    */
  getPortfolioPerformanceOverview: async (portfolioId) => {
    const response = await api.get(
      `/portfolios/calculations/portfolio/${portfolioId}/overview`
    );
    return response.data;
  },
};

/* 
  ACCOUNT STATEMENTS API METHODS - PDF statement parsing and bulk transaction creation
  These methods handle all account statement-related API calls
*/
export const accountStatementsAPI = {
  /* 
      GET SUPPORTED PROVIDERS - Get list of supported account statement providers
      Returns: Server response with array of provider objects
    */
  getSupportedProviders: async () => {
    const response = await api.get("/account-statements/providers");
    return response.data;
  },

  /* 
      PARSE STATEMENT - Upload PDF and extract transaction data
      Parameters: providerId (string), file (File object), filename (string)
      Returns: Server response with parsed transaction data
    */
  parseStatement: async (providerId, file, filename) => {
    const formData = new FormData();
    formData.append("provider_id", providerId);
    formData.append("file", file);
    formData.append("filename", filename);

    const response = await api.post("/account-statements/parse", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  /*
      RESOLVE INSTRUMENTS - Suggest the Yahoo listing for up to 10 ISINs
      Parameters: instruments (array of { isin, name, transaction_count, fills })
      Returns: { results: [{ isin, status, suggested_symbol, asset_id, candidates }] }
    */
  resolveInstruments: async (instruments) => {
    const response = await api.post(
      "/account-statements/instruments/resolve",
      { instruments },
      { timeout: 180000 }
    );
    return response.data;
  },

  /*
      IMPORTED TRANSACTIONS - Which parsed rows are already in a portfolio
      Parameters: portfolioId (number), transactions (array of { source_key, transaction_date, transaction_type, isin, quantity, total_amount })
      Returns: { imported_keys: [source_key] }
    */
  importedTransactions: async (portfolioId, transactions) => {
    const response = await api.post("/account-statements/transactions/imported", {
      portfolio_id: portfolioId,
      transactions,
    });
    return response.data;
  },

  /* 
      BULK CREATE TRANSACTIONS - Create multiple transactions from parsed data
      Parameters: portfolioId (number), transactions (array of transaction objects)
      Returns: Server response with created transactions
    */
  bulkCreateTransactions: async (portfolioId, transactions) => {
    const response = await api.post(
      "/account-statements/transactions/bulk-create",
      {
        portfolio_id: portfolioId,
        transactions: transactions,
      }
    );
    return response.data;
  },
};

/* 
  TRANSACTION PDF EXPORT API METHODS - PDF report generation and download
  These methods handle all transaction PDF export-related API calls
*/
export const transactionPDFExportAPI = {
  /* 
      EXPORT PDF WITH METADATA - Generate PDF and return metadata without file
      Parameters: filters (object), options (object), customFilename (string)
      Returns: Server response with export metadata
    */
  exportPDF: async (filters = {}, options = {}, customFilename = null) => {
    const requestBody = { filters, options };
    if (customFilename) {
      requestBody.custom_filename = customFilename;
    }

    const response = await api.post("/transactions/pdf/export", requestBody);
    return response.data;
  },

  /* 
      DOWNLOAD PDF DIRECTLY - Generate and download PDF file
      Parameters: filters (object), options (object), customFilename (string)
      Returns: Binary PDF file content
    */
  downloadPDF: async (filters = {}, options = {}, customFilename = null) => {
    const requestBody = { filters, options };
    if (customFilename) {
      requestBody.custom_filename = customFilename;
    }

    const response = await api.post(
      "/transactions/pdf/export/download",
      requestBody,
      {
        responseType: "blob", // Important for binary file download
      }
    );
    return response;
  },

  /* 
      PREVIEW EXPORT - Preview what would be included in PDF without generating file
      Parameters: filters (object), options (object)
      Returns: Server response with preview data
    */
  previewExport: async (filters = {}, options = {}) => {
    const requestBody = { filters, options };
    const response = await api.post(
      "/transactions/pdf/export/preview",
      requestBody
    );
    return response.data;
  },
};

/* 
  WATCHLIST API METHODS - Stock watchlist management
  These methods handle all watchlist-related API calls
*/
export const watchlistAPI = {
  /*
      GET ALERTS - Triggered watchlist alerts (evaluated by the worker), newest first
      Returns: { unread_count, alerts: [{ id, symbol, watchlist_name, alert_type, condition, threshold_value, triggered_value, triggered_at, still_true, acknowledged_at }] }
    */
  getAlerts: async (unreadOnly = false, limit = 50) => {
    const response = await api.get("/watchlists/alerts", {
      params: { unread_only: unreadOnly, limit },
    });
    return response.data;
  },

  /*
      ACKNOWLEDGE ALERTS - Mark alerts as read (all unread when ids is null)
    */
  acknowledgeAlerts: async (alertIds = null) => {
    const response = await api.post("/watchlists/alerts/acknowledge", {
      alert_ids: alertIds,
    });
    return response.data;
  },

  /* 
      GET WATCHLISTS - Get all watchlists for the current user
      Parameters: includeItems (boolean to include watchlist items)
      Returns: Server response with array of watchlist objects
    */
  getWatchlists: async (includeItems = false) => {
    const response = await api.get("/watchlists/", {
      params: { include_items: includeItems },
    });
    return response.data.watchlists || response.data || [];
  },

  /* 
      GET WATCHLIST - Get a specific watchlist by ID
      Parameters: watchlistId (string or number), includeRealTimeData (boolean)
      Returns: Server response with watchlist details and items
    */
  getWatchlist: async (watchlistId, includeRealTimeData = false) => {
    const response = await api.get(`/watchlists/${watchlistId}`, {
      params: { include_real_time_data: includeRealTimeData },
    });
    return response.data;
  },

  /* 
      CREATE WATCHLIST - Create a new watchlist
      Parameters: watchlistData (object with name, description, etc.)
      Returns: Server response with created watchlist data
    */
  createWatchlist: async (watchlistData) => {
    const response = await api.post("/watchlists/", watchlistData);
    return response.data;
  },

  /* 
      UPDATE WATCHLIST - Update an existing watchlist
      Parameters: watchlistId (string or number), updateData (object with changes)
      Returns: Server response with updated watchlist data
    */
  updateWatchlist: async (watchlistId, updateData) => {
    const response = await api.put(`/watchlists/${watchlistId}`, updateData);
    return response.data;
  },

  /* 
      DELETE WATCHLIST - Delete a watchlist
      Parameters: watchlistId (string or number)
      Returns: Server response confirming deletion
    */
  deleteWatchlist: async (watchlistId) => {
    const response = await api.delete(`/watchlists/${watchlistId}`);
    return response.data;
  },

  /* 
      ADD ITEM TO WATCHLIST - Add a stock to a watchlist
      Parameters: watchlistId (string or number), itemData (object with symbol, notes)
      Returns: Server response with added item data
    */
  addItemToWatchlist: async (watchlistId, itemData) => {
    const response = await api.post(
      `/watchlists/${watchlistId}/items`,
      itemData
    );
    return response.data;
  },

  /* 
      BULK ADD ITEMS - Add multiple stocks to a watchlist at once
      Parameters: watchlistId (string or number), symbols (array of stock symbols)
      Returns: Server response with added items data
    */
  bulkAddItemsToWatchlist: async (watchlistId, symbols) => {
    const response = await api.post(`/watchlists/${watchlistId}/items/bulk`, {
      symbols,
    });
    return response.data;
  },

  /* 
      UPDATE WATCHLIST ITEM - Update a watchlist item (notes, target price, etc.)
      Parameters: watchlistId (string or number), itemId (string or number), updateData (object)
      Returns: Server response with updated item data
    */
  updateWatchlistItem: async (watchlistId, itemId, updateData) => {
    const response = await api.put(
      `/watchlists/${watchlistId}/items/${itemId}`,
      updateData
    );
    return response.data;
  },

  /* 
      REMOVE ITEM FROM WATCHLIST - Remove a stock from a watchlist
      Parameters: watchlistId (string or number), itemId (string or number)
      Returns: Server response confirming removal
    */
  removeItemFromWatchlist: async (watchlistId, itemId) => {
    const response = await api.delete(
      `/watchlists/${watchlistId}/items/${itemId}`
    );
    return response.data;
  },

  /* 
      REORDER WATCHLIST ITEMS - Change the order of items in a watchlist
      Parameters: watchlistId (string or number), itemIds (array of item IDs in new order)
      Returns: Server response confirming reorder
    */
  reorderWatchlistItems: async (watchlistId, itemIds) => {
    const response = await api.post(`/watchlists/${watchlistId}/reorder`, {
      item_ids: itemIds,
    });
    return response.data;
  },

  /* 
      GET PUBLIC WATCHLISTS - Get publicly shared watchlists
      Parameters: limit (number of watchlists to return)
      Returns: Server response with public watchlists
    */
  getPublicWatchlists: async (limit = 20) => {
    const response = await api.get("/watchlists/public", { params: { limit } });
    return response.data;
  },

  /* 
      GET WATCHLIST STATS - Get statistics about user's watchlists
      Returns: Server response with watchlist statistics
    */
  getWatchlistStats: async () => {
    const response = await api.get("/watchlists/stats");
    return response.data;
  },
};

/* 
  UTILITY FUNCTIONS - Helper functions for authentication
  These are utility functions that can be used throughout the app
*/
export const authUtils = {
  /* 
      IS AUTHENTICATED - Check if user is currently logged in
      Returns: boolean (true if user has access token)
    */
  isAuthenticated: () => {
    const token = localStorage.getItem("access_token");
    return !!token; // Convert to boolean (true if token exists, false if null)
  },

  /* 
      GET ACCESS TOKEN - Get the current access token
      Returns: string (access token) or null
    */
  getAccessToken: () => {
    return localStorage.getItem("access_token");
  },

  /* 
      GET REFRESH TOKEN - Get the current refresh token
      Returns: string (refresh token) or null
    */
  getRefreshToken: () => {
    return localStorage.getItem("refresh_token");
  },

  /* 
      CLEAR AUTH - Remove all authentication data from storage
      This is used when logging out or when tokens are invalid
    */
  clearAuth: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    localStorage.removeItem("profile");
  },

  /* 
      IS TOKEN EXPIRED - Check if a JWT token is expired
      Parameters: token (string) - JWT token to check
      Returns: boolean (true if expired or invalid, false if valid)
      
      Note: This is a basic check. The server should be the final authority on token validity.
    */
  isTokenExpired: (token) => {
    if (!token) return true; // No token means expired

    try {
      // JWT tokens have 3 parts separated by dots: header.payload.signature
      // We need the payload (middle part) to check expiration
      const payload = JSON.parse(atob(token.split(".")[1]));

      // Check if expiration time (in seconds) is less than current time (in milliseconds)
      return payload.exp * 1000 < Date.now();
    } catch (error) {
      // If we can't parse the token, consider it expired
      console.error("Error parsing token:", error);
      return true;
    }
  },
};

// Export the configured axios instance as default
export default api;
