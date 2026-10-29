import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import InfoTip from "./InfoTip";

describe("InfoTip", () => {
  it("opens the explanation and closes on Escape", async () => {
    renderWithProviders(<InfoTip id="sharpe" />);

    await userEvent.click(screen.getByRole("button", { name: "About Sharpe ratio" }));
    const tip = screen.getByRole("dialog", { name: "Sharpe ratio" });
    expect(tip).toHaveTextContent("How to read it");
    expect(tip).toHaveTextContent("What it implies");
    expect(screen.getByRole("link", { name: /How it is calculated/ })).toHaveAttribute("href", "/concepts#sharpe");

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders nothing for an unknown id", () => {
    const { container } = renderWithProviders(<InfoTip id="nope" />);
    expect(container).toBeEmptyDOMElement();
  });
});
