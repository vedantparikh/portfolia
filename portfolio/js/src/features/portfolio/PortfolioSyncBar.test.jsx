import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import PortfolioSyncBar from "./PortfolioSyncBar";

const portfolio = { id: 7, sync_source: "pytr", currency: "EUR" };
const status = (report) => ({
  source: "pytr",
  synced_at: "2026-10-28T10:00:00Z",
  file_updated_at: "2026-10-28T09:00:00Z",
  report,
});

describe("PortfolioSyncBar", () => {
  it("shows the last report and imports an unmapped security with a ticker", async () => {
    let mapped = null;
    let current = status({
      created: 3,
      already_imported: 10,
      failed: 0,
      errors: [],
      unmapped: [{ isin: "IE00B4NCWG09", name: "Physical Silver", rows: 58 }],
      not_imported: {},
    });
    server.use(
      http.get(`${API}/portfolios/7/sync`, () => HttpResponse.json(current)),
      http.post(`${API}/portfolios/7/sync/instruments`, async ({ request }) => {
        mapped = await request.json();
        current = status({ created: 58, already_imported: 13, failed: 0, errors: [], unmapped: [], not_imported: {} });
        return HttpResponse.json(current);
      }),
    );

    renderWithProviders(<PortfolioSyncBar portfolio={portfolio} />);

    expect(await screen.findByText(/3 new · 1 securities need a ticker/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Details/ }));
    await userEvent.type(screen.getByLabelText("Ticker for IE00B4NCWG09"), "ISLN.L");
    await userEvent.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() => expect(mapped).toEqual({ isin: "IE00B4NCWG09", symbol: "ISLN.L" }));
    expect(await screen.findByText(/58 new/)).toBeInTheDocument();
  });
});
