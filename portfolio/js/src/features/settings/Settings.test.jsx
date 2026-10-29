import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import Settings from "./Settings";

const auth = vi.hoisted(() => ({
  user: { username: "demo", email: "demo@example.com" },
  profile: { first_name: "Demo", last_name: "User", currency_preference: "USD", timezone: "UTC" },
  refreshUser: vi.fn(),
  logout: vi.fn(),
}));
const { refreshUser, logout } = auth;

vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => auth }));
const shell = vi.hoisted(() => ({ openSidebar: () => {} }));
vi.mock("../../app/chrome", () => ({ useShell: () => shell }));

describe("Settings", () => {
  it("saves only the changed profile fields", async () => {
    let sent = null;
    server.use(
      http.put(`${API}/auth/me`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({});
      }),
    );
    renderWithProviders(<Settings />);

    const first = screen.getByLabelText("First name");
    await userEvent.clear(first);
    await userEvent.type(first, "Dana");
    const currency = screen.getByLabelText("Preferred currency");
    await userEvent.clear(currency);
    await userEvent.type(currency, "eur");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => expect(sent).toEqual({ first_name: "Dana", currency_preference: "EUR" }));
    expect(refreshUser).toHaveBeenCalled();
  });

  it("closes the account with the password, then signs out", async () => {
    let sent = null;
    server.use(
      http.delete(`${API}/auth/me`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ message: "ok" });
      }),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<Settings />);

    await userEvent.type(screen.getByLabelText("Password"), "S3cret!pass");
    await userEvent.click(screen.getByRole("button", { name: "Close account" }));

    await waitFor(() => expect(logout).toHaveBeenCalled());
    expect(sent).toEqual({ password: "S3cret!pass" });
  });
});
