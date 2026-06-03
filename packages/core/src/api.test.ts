import { describe, it, expect, vi, afterEach } from "vitest";
import { createApiClient } from "./api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const PROFILE = {
  email: "a@a.com",
  created_at: "2026-01-01T00:00:00",
  totp_enabled: false,
  role: "user",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client token refresh", () => {
  it("refreshes on 401, then retries the original request with the new token", async () => {
    const api = createApiClient("");
    api.setAccessToken("expired");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 })) // GET /profile/ -> 401
      .mockResolvedValueOnce(jsonResponse({ access_token: "fresh" })) // POST /auth/refresh
      .mockResolvedValueOnce(jsonResponse(PROFILE)); // retry GET /profile/
    vi.stubGlobal("fetch", fetchMock);

    const profile = await api.getProfile();

    expect(profile.email).toBe("a@a.com");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1][0])).toContain("/auth/refresh");

    const retryHeaders = fetchMock.mock.calls[2][1].headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer fresh");
  });

  it("propagates the error and does not retry when refresh fails", async () => {
    const api = createApiClient("");
    api.setAccessToken("expired");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 })) // GET /profile/ -> 401
      .mockResolvedValueOnce(new Response(null, { status: 401 })); // refresh -> 401
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.getProfile()).rejects.toThrow();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not refresh when the request succeeds", async () => {
    const api = createApiClient("");
    api.setAccessToken("good");

    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(PROFILE));
    vi.stubGlobal("fetch", fetchMock);

    await api.getProfile();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
