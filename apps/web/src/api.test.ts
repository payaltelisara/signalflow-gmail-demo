import { afterEach, describe, expect, it, vi } from "vitest";
import { restoreCsrfFromCookie } from "./api";

describe("CSRF restoration", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("restores the non-HTTP-only CSRF token after a page reload", () => {
    vi.stubGlobal("document", { cookie: "signalflow_csrf=restored-token" });
    expect(() => restoreCsrfFromCookie()).not.toThrow();
  });
});
