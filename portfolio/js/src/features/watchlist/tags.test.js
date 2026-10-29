import { describe, expect, it } from "vitest";

import { parseTags } from "./tags";

describe("parseTags", () => {
  it("trims, drops blanks and duplicates, keeps at most 10", () => {
    expect(parseTags(" growth, ,dividend,growth ")).toEqual(["growth", "dividend"]);
    expect(parseTags("")).toEqual([]);
    expect(parseTags("a,b,c,d,e,f,g,h,i,j,k")).toHaveLength(10);
  });
});
