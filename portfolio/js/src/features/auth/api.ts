import { api } from "../../shared/api/client";
import { tokenStore } from "../../shared/auth/tokenStore";

type Body = Record<string, unknown>;

export const authAPI = {
  register: async (userData: Body) =>
    (await api.post("/auth/register", userData)).data,
  login: async (credentials: Body) =>
    (await api.post("/auth/login", credentials)).data,
  getUserProfile: async () => (await api.get("/auth/me/profile")).data,
  getCurrentUser: async () => (await api.get("/auth/me")).data,
  logout: async () => {
    try {
      await api.post("/auth/logout");
    } catch (error) {
      console.warn("Logout API call failed:", error);
    } finally {
      tokenStore.clear();
    }
  },
  forgotPassword: async (email: string) =>
    (await api.post("/auth/forgot-password", { email })).data,
  resetPassword: async (resetData: Body) =>
    (await api.post("/auth/reset-password", resetData)).data,
  validateResetToken: async (token: string) =>
    (await api.get(`/auth/validate-reset-token/?token=${token}`)).data,
  verifyEmail: async (token: string) =>
    (await api.post("/auth/verify-email", { token })).data,
  updateProfile: async (changes: Body) =>
    (await api.put("/auth/me", changes)).data,
  changePassword: async (passwords: Body) =>
    (await api.post("/auth/change-password", passwords)).data,
  deleteAccount: async (password: string) =>
    (await api.delete("/auth/me", { data: { password } })).data,
  resendVerification: async () =>
    (await api.post("/auth/resend-verification")).data,
};
