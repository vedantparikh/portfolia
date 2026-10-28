import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatDate,
  formatPercentage,
  formatQuantity,
} from "./formatters";

describe("formatCurrency", () => {
  it("uses the given currency", () => {
    expect(formatCurrency(1234.5, { currency: "EUR" })).toBe("€1,234.50");
  });

  it("shows zero in the requested currency for a missing amount", () => {
    expect(formatCurrency(null, { currency: "EUR" })).toBe("€0.00");
    expect(formatCurrency(undefined, { defaultValue: "—" })).toBe("—");
  });

  it("falls back to USD without a currency", () => {
    expect(formatCurrency(-3)).toBe("-$3.00");
  });

  it("signs gains with exceptZero", () => {
    expect(formatCurrency(5, { currency: "USD", signDisplay: "exceptZero" })).toBe(
      "+$5.00",
    );
  });
});

describe("formatPercentage", () => {
  it("adds a sign and two decimals", () => {
    expect(formatPercentage(15)).toBe("+15.00%");
    expect(formatPercentage(-1.234, { precision: 1 })).toBe("-1.2%");
  });

  it("returns N/A for missing values", () => {
    expect(formatPercentage(null)).toBe("N/A");
    expect(formatPercentage("abc")).toBe("N/A");
  });
});

describe("formatQuantity", () => {
  it("keeps up to four decimals with separators", () => {
    expect(formatQuantity(1234.56789)).toBe("1,234.5679");
    expect(formatQuantity(2)).toBe("2");
  });
});

describe("formatDate", () => {
  it("formats a date-only value at noon so the day does not shift", () => {
    expect(formatDate("2026-01-05T12:00:00")).toBe("Jan 5, 2026");
  });

  it("returns N/A for an invalid date", () => {
    expect(formatDate("not a date")).toBe("N/A");
  });
});
