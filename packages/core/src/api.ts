import type { ZodType } from "zod";
import {
  loginResponseSchema,
  profileSchema,
  twoFactorSetupSchema,
  recoveryCodesSchema,
  recoveryStatusSchema,
  vaultEntrySchema,
  vaultPageSchema,
  type LoginResponse,
  type Profile,
  type TwoFactorSetup,
  type RecoveryCodes,
  type RecoveryStatus,
  type VaultEntry,
  type VaultPage,
} from "./schemas";

/** Thrown for any non-2xx response. `status` is the HTTP code, `message` the
 *  server's `detail` when available. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Payload for creating/updating a vault entry. `encrypted`/`iv` come from the
 *  crypto layer; the server never sees plaintext. */
export interface VaultInput {
  encrypted: string;
  iv: string;
  category?: string | null;
  expires_at?: string | null;
}

export type LoginResult =
  | { requires2fa: true }
  | ({ requires2fa: false } & LoginResponse);

/**
 * Stateful API client. Holds the short-lived access token in memory and
 * transparently refreshes it (via the httpOnly refresh-token cookie) on 401.
 * `baseUrl` is configurable so the same client works in the SPA ("/api" proxy)
 * and in the browser extension (absolute URL).
 */
export function createApiClient(baseUrl: string) {
  let accessToken: string | null = null;
  let refreshing: Promise<boolean> | null = null;

  function refresh(): Promise<boolean> {
    refreshing ??= (async () => {
      const res = await fetch(`${baseUrl}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        accessToken = null;
        return false;
      }
      const data = (await res.json()) as { access_token?: string };
      accessToken = data.access_token ?? null;
      return accessToken !== null;
    })().finally(() => {
      refreshing = null;
    });
    return refreshing;
  }

  async function send(path: string, init: RequestInit, retry: boolean): Promise<Response> {
    const headers = new Headers(init.headers);
    if (init.body) headers.set("Content-Type", "application/json");
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

    const res = await fetch(`${baseUrl}${path}`, { ...init, headers, credentials: "include" });

    if (res.status === 401 && retry) {
      const refreshed = await refresh();
      if (refreshed) return send(path, init, false);
    }
    return res;
  }

  async function request<T>(
    path: string,
    init: RequestInit,
    schema?: ZodType<T>,
    retry = true,
  ): Promise<T> {
    const res = await send(path, init, retry);
    if (!res.ok) {
      let detail: unknown = res.statusText;
      try {
        detail = ((await res.json()) as { detail?: unknown }).detail ?? detail;
      } catch {
        /* non-JSON body */
      }
      throw new ApiError(res.status, typeof detail === "string" ? detail : "Request failed");
    }
    if (res.status === 204) return undefined as T;
    const data = await res.json();
    return schema ? schema.parse(data) : (data as T);
  }

  return {
    setAccessToken(token: string | null) {
      accessToken = token;
    },
    get hasSession() {
      return accessToken !== null;
    },

    // --- auth ---
    register(email: string, authHash: string, salt: string): Promise<void> {
      return request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password: authHash, salt }),
      });
    },

    async getSalt(email: string): Promise<string> {
      const data = await request<{ salt: string }>(
        `/auth/salt?email=${encodeURIComponent(email)}`,
        { method: "GET" },
      );
      return data.salt;
    },

    async login(email: string, authHash: string): Promise<LoginResult> {
      const res = await send(
        "/auth/login",
        { method: "POST", body: JSON.stringify({ email, password: authHash }) },
        false,
      );
      if (!res.ok) {
        let detail: unknown = res.statusText;
        try {
          detail = ((await res.json()) as { detail?: unknown }).detail ?? detail;
        } catch {
          /* ignore */
        }
        throw new ApiError(res.status, typeof detail === "string" ? detail : "Login failed");
      }
      const data = await res.json();
      if (data?.requires_2fa) return { requires2fa: true };
      const parsed = loginResponseSchema.parse(data);
      accessToken = parsed.access_token;
      return { requires2fa: false, ...parsed };
    },

    async validate2fa(code: string): Promise<LoginResponse> {
      const parsed = await request(
        "/auth/2fa/validate",
        { method: "POST", body: JSON.stringify({ code }) },
        loginResponseSchema,
        false,
      );
      accessToken = parsed.access_token;
      return parsed;
    },

    /** Complete login with a one-time recovery code instead of a TOTP code. */
    async validateRecovery(code: string): Promise<LoginResponse> {
      const parsed = await request(
        "/auth/2fa/recovery/validate",
        { method: "POST", body: JSON.stringify({ code }) },
        loginResponseSchema,
        false,
      );
      accessToken = parsed.access_token;
      return parsed;
    },

    logout(): Promise<void> {
      return request<void>("/auth/logout", { method: "POST" }, undefined, false).finally(() => {
        accessToken = null;
      });
    },

    // --- profile ---
    getProfile(): Promise<Profile> {
      return request("/profile/", { method: "GET" }, profileSchema);
    },

    // --- 2FA management (authenticated) ---
    /** Begin enrollment: returns a TOTP secret + QR. Nothing is enforced until
     *  the user confirms a code via verify2fa. */
    setup2fa(): Promise<TwoFactorSetup> {
      return request("/auth/2fa/setup", { method: "POST" }, twoFactorSetupSchema);
    },

    /** Confirm a TOTP code to switch 2FA on; returns the recovery codes. */
    verify2fa(code: string): Promise<RecoveryCodes> {
      return request(
        "/auth/2fa/verify",
        { method: "POST", body: JSON.stringify({ code }) },
        recoveryCodesSchema,
      );
    },

    /** Turn 2FA off; requires a current TOTP code. */
    disable2fa(code: string): Promise<{ message: string }> {
      return request("/auth/2fa/disable", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
    },

    /** How many one-time recovery codes are still unused. */
    recoveryStatus(): Promise<RecoveryStatus> {
      return request("/auth/2fa/recovery/status", { method: "GET" }, recoveryStatusSchema);
    },

    // --- vault ---
    listVault(cursor?: string): Promise<VaultPage> {
      const qs = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
      return request(`/vault/${qs}`, { method: "GET" }, vaultPageSchema);
    },

    /** Fetch every entry by following the cursor. The client decrypts and
     *  searches locally, so it needs the whole vault, not one page. */
    async listAllVault(): Promise<VaultEntry[]> {
      const items: VaultEntry[] = [];
      let cursor: string | null = null;
      do {
        const params = new URLSearchParams({ limit: "100" });
        if (cursor) params.set("cursor", cursor);
        const page = await request<VaultPage>(
          `/vault/?${params.toString()}`,
          { method: "GET" },
          vaultPageSchema,
        );
        items.push(...page.items);
        cursor = page.next_cursor ?? null;
      } while (cursor);
      return items;
    },

    createVault(input: VaultInput): Promise<VaultEntry> {
      return request("/vault/", { method: "POST", body: JSON.stringify(input) }, vaultEntrySchema);
    },

    updateVault(id: string, input: VaultInput): Promise<VaultEntry> {
      return request(
        `/vault/${id}`,
        { method: "PUT", body: JSON.stringify(input) },
        vaultEntrySchema,
      );
    },

    setPin(id: string, pinned: boolean): Promise<VaultEntry> {
      return request(
        `/vault/${id}/pin`,
        { method: "PATCH", body: JSON.stringify({ pinned }) },
        vaultEntrySchema,
      );
    },

    deleteVault(id: string): Promise<void> {
      return request(`/vault/${id}`, { method: "DELETE" });
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
