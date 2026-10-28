import { http, HttpResponse } from "msw";

export const API = "http://localhost/api/v1";

// Defaults: signed out. Tests override per case with server.use(...).
export const handlers = [
  http.post(`${API}/auth/refresh`, () =>
    HttpResponse.json(
      { error: { code: "unauthorized", message: "Invalid refresh token" } },
      { status: 401 },
    ),
  ),
];
