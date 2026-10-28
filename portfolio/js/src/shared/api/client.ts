import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { tokenStore } from "../auth/tokenStore";

export type Id = number | string;
export type Params = Record<string, unknown>;

// Relative by default, so the browser resolves it against the page's origin and
// the Vite proxy or nginx forwards /api. Set VITE_API_BASE_URL only when the API
// lives on another origin the browser can reach (never a Docker service name).
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "/api/v1"
).replace(/\/+$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 100000,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

interface ErrorBody {
  error?: { message?: unknown };
  detail?: unknown;
  message?: unknown;
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  const data = (error as AxiosError<ErrorBody> | undefined)?.response?.data;
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

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const forceLogout = () => {
  tokenStore.clear();
  window.location.href = "/login";
};

// Refresh tokens rotate on every use, so concurrent 401s share one refresh.
let refreshPromise: Promise<string> | null = null;

export function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post<{ access_token: string }>(`${API_BASE_URL}/auth/refresh`, null, {
        withCredentials: true,
      })
      .then(({ data }) => {
        tokenStore.setAccess(data.access_token);
        return data.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ErrorBody>) => {
    const message = apiErrorMessage(error, "");
    const data = error.response?.data;
    if (
      message &&
      data &&
      typeof data === "object" &&
      typeof data.detail !== "string"
    ) {
      data.detail = message;
      if (typeof data.message !== "string") {
        data.message = message;
      }
    }
    const originalRequest = error.config as RetryConfig | undefined;
    // Auth endpoints answer bad credentials with 401; never refresh for them.
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
  },
);
