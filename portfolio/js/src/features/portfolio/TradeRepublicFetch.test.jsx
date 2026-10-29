import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import TradeRepublicFetch from "./TradeRepublicFetch";
import { fetchSummary } from "./tradeRepublic";

const idle = {
  available: true,
  connected: false,
  login_pending: false,
  session_expired: false,
  fetch_status: "idle",
  fetch_report: null,
};

describe("TradeRepublicFetch", () => {
  it("logs in with a code, then fetches and reports what was imported", async () => {
    let state = idle;
    let login = null;
    let confirmedWith = null;
    server.use(
      http.get(`${API}/portfolios/sync/pytr`, () => HttpResponse.json(state)),
      http.post(`${API}/portfolios/sync/pytr/login`, async ({ request }) => {
        login = await request.json();
        return HttpResponse.json({ needs_code: true, countdown: 60 });
      }),
      http.post(`${API}/portfolios/sync/pytr/login/confirm`, async ({ request }) => {
        confirmedWith = await request.json();
        return HttpResponse.json({ confirmed: true });
      }),
      http.post(`${API}/portfolios/sync/pytr/fetch`, () => {
        state = {
          ...idle,
          connected: true,
          fetch_status: "succeeded",
          fetch_finished_at: "2026-10-29T12:00:00Z",
          fetch_report: { events: 9, documents: 2, positions: 20, portfolios: [{ portfolio_id: 16, name: "TR", created: 3, tax_entries_created: 1, failed: 0 }] },
        };
        return HttpResponse.json({ ...idle, connected: true, fetch_status: "running" });
      }),
    );

    renderWithProviders(<TradeRepublicFetch />);
    await userEvent.click(await screen.findByRole("button", { name: /Fetch from Trade Republic/ }));
    await userEvent.type(screen.getByLabelText("Phone"), "+49 151 1234567");
    await userEvent.type(screen.getByLabelText("PIN"), "1234");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    await userEvent.type(await screen.findByLabelText(/authenticator/), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => expect(confirmedWith).toEqual({ code: "123456" }));
    expect(login).toEqual({ phone: "+491511234567", pin: "1234" });
    expect(await screen.findByText(/Fetching from Trade Republic/)).toBeInTheDocument();
    expect(
      await screen.findByText(/3 new transactions · 1 tax entry · 2 new documents/, {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("summarises an error and hides itself when not available", () => {
    expect(fetchSummary({ error: "The Trade Republic session ended: log in again" })).toMatch(/log in again/);
    expect(fetchSummary(null)).toBeNull();
  });
});
