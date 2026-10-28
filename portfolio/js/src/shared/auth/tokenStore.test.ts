import { describe, expect, it, vi } from "vitest";

import { onSessionCleared, tokenStore } from "./tokenStore";

describe("tokenStore", () => {
  it("keeps the access token in memory only", () => {
    tokenStore.setAccess("abc");
    expect(tokenStore.getAccess()).toBe("abc");
    expect(localStorage.getItem("access_token")).toBeNull();
  });

  it("clears the token and notifies listeners", () => {
    const listener = vi.fn();
    const unsubscribe = onSessionCleared(listener);
    tokenStore.setAccess("abc");
    localStorage.setItem("user", "{}");

    tokenStore.clear();

    expect(tokenStore.getAccess()).toBeNull();
    expect(localStorage.getItem("user")).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });
});
