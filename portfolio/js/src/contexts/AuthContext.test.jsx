import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { tokenStore } from "../shared/auth/tokenStore";
import { API } from "../test/msw/handlers";
import { server } from "../test/msw/server";
import { renderWithProviders } from "../test/renderWithProviders";
import { AuthProvider, useAuth } from "./AuthContext";

function Probe() {
  const { isInitialized, isAuthenticated, user } = useAuth();
  if (!isInitialized) return <p>loading</p>;
  return <p>{isAuthenticated ? `signed in as ${user.username}` : "signed out"}</p>;
}

const renderAuth = () =>
  renderWithProviders(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );

describe("AuthProvider start-up", () => {
  it("is signed out when the refresh cookie is missing", async () => {
    renderAuth();
    expect(await screen.findByText("signed out")).toBeInTheDocument();
    expect(tokenStore.getAccess()).toBeNull();
  });

  it("restores the session from the refresh cookie", async () => {
    let authorization = null;
    server.use(
      http.post(`${API}/auth/refresh`, () =>
        HttpResponse.json({ access_token: "fresh", token_type: "bearer", expires_in: 900 }),
      ),
      http.get(`${API}/auth/me`, ({ request }) => {
        authorization = request.headers.get("Authorization");
        return HttpResponse.json({ id: 1, username: "demo" });
      }),
      http.get(`${API}/auth/me/profile`, () => HttpResponse.json({ id: 1 })),
    );

    renderAuth();

    expect(await screen.findByText("signed in as demo")).toBeInTheDocument();
    await waitFor(() => expect(authorization).toBe("Bearer fresh"));
    expect(tokenStore.getAccess()).toBe("fresh");
  });
});
