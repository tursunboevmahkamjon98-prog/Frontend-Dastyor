import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, authApi, clearToken, getRefreshToken, getToken, setRefreshToken, setToken } from "./api";
import { MESSAGES } from "./messages";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const user = { id: "u1", full_name: "Test", role: "teacher" };

describe("api request()", () => {
  beforeEach(() => {
    localStorage.clear();
    clearToken();
  });

  it("sends the access token as a Bearer header", async () => {
    setToken("access-1");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(200, user));

    await expect(authApi.me()).resolves.toEqual(user);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/me");
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer access-1");
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    setToken("old");
    setRefreshToken("refresh-1");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json(401, { detail: "expired" }))
      .mockResolvedValueOnce(json(200, { access_token: "new", refresh_token: "refresh-2" }))
      .mockResolvedValueOnce(json(200, user));

    await expect(authApi.me()).resolves.toEqual(user);

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/auth/refresh");
    expect((fetchMock.mock.calls[2][1]?.headers as Record<string, string>).Authorization).toBe("Bearer new");
    expect(getToken()).toBe("new");
    expect(getRefreshToken()).toBe("refresh-2");
  });

  it("clears the tokens when the refresh token is rejected", async () => {
    setToken("old");
    setRefreshToken("bad");
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json(401, { detail: "expired" }))
      .mockResolvedValueOnce(json(401, { detail: "invalid refresh" }));

    const err = await authApi.me().catch((e) => e);

    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(401);
    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("joins FastAPI validation messages into one error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(422, { detail: [{ msg: "phone is required" }, { msg: "password too short" }] })
    );

    await expect(authApi.me()).rejects.toThrow("phone is required\npassword too short");
  });

  it("reports a network failure in the user's language", async () => {
    localStorage.setItem("dastyor_web_locale", "en");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(authApi.me()).rejects.toThrow(MESSAGES.en["api.connectFailed"]);
  });

  it("explains a gateway timeout instead of a bare server error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("<html>504</html>", { status: 504 }));

    await expect(authApi.me()).rejects.toThrow(MESSAGES.ru["api.gatewayTimeout"]);
  });
});
