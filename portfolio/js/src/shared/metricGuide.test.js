import { describe, expect, it } from "vitest";

import { GUIDE_BY_ID, GUIDE_CATEGORIES, METRIC_GUIDE } from "./metricGuide";

const FIELDS = ["id", "name", "category", "short", "what", "formula", "example", "read", "good", "bad", "implies"];
const sources = import.meta.glob(["../**/*.jsx", "!../**/*.test.jsx"], {
  query: "?raw",
  import: "default",
  eager: true,
});

describe("metric guide", () => {
  it("has every field, a known category and a unique id for each entry", () => {
    const categories = new Set(GUIDE_CATEGORIES.map((c) => c.value));
    for (const entry of METRIC_GUIDE) {
      for (const field of FIELDS) expect(entry[field], `${entry.id}.${field}`).toBeTruthy();
      expect(categories.has(entry.category), entry.id).toBe(true);
    }
    expect(Object.keys(GUIDE_BY_ID)).toHaveLength(METRIC_GUIDE.length);
  });

  it("explains every metric the screens point at", () => {
    const used = new Set();
    for (const text of Object.values(sources)) {
      for (const match of text.matchAll(/\binfo="([a-z0-9_]+)"|<InfoTip id="([a-z0-9_]+)"|\['[A-Z][^']*', '([a-z0-9_]+)', '/g)) {
        used.add(match[1] || match[2] || match[3]);
      }
    }
    expect(used.size).toBeGreaterThan(30);
    expect([...used].filter((id) => !GUIDE_BY_ID[id])).toEqual([]);
  });
});
