import type { ZodType } from "zod";
import {
  loginResponseSchema,
  profileSchema,
  twoFactorSetupSchema,
  recoveryCodesSchema,
  recoveryStatusSchema,
  vaultEntrySchema,
  vaultPageSchema,
  organizationSchema,
  orgMemberSchema,
  publicKeySchema,
  invitationSchema,
  invitationLookupSchema,
  collectionSchema,
  collectionMemberSchema,
  type LoginResponse,
  type Profile,
  type TwoFactorSetup,
  type RecoveryCodes,
  type RecoveryStatus,
  type VaultEntry,
  type VaultPage,
  type Organization,
  type OrgMember,
  type PublicKey,
  type Invitation,
  type InvitationLookup,
  type Collection,
  type CollectionMember,
} from "./schemas";
import { z } from "zod";

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

/** Wrapped keypair as sent to the server (snake_case wire format). */
export interface KeypairPayload {
  public_key: string;
  encrypted_private_key: string;
  private_key_iv: string;
}

/** Org key rotation payload (snake_case wire format). */
export interface RotateKeyPayload {
  remove_user_id?: string;
  member_keys: { user_id: string; wrapped_org_key: string }[];
  vault_items: { id: string; encrypted: string; iv: string }[];
}

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
    register(email: string, authHash: string, salt: string, keys?: KeypairPayload): Promise<void> {
      return request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password: authHash, salt, ...keys }),
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

    // --- keypair (org sharing) ---
    /** Backfill the keypair for a legacy account that has none yet. */
    uploadKeys(keys: KeypairPayload): Promise<void> {
      return request("/profile/keys", { method: "POST", body: JSON.stringify(keys) });
    },

    /** Fetch another user's public key (to wrap an org key for them). */
    getPublicKey(email: string): Promise<PublicKey> {
      return request(
        `/profile/public-key?email=${encodeURIComponent(email)}`,
        { method: "GET" },
        publicKeySchema,
      );
    },

    // --- organizations ---
    listOrgs(): Promise<Organization[]> {
      return request("/organizations/", { method: "GET" }, z.array(organizationSchema));
    },

    createOrg(name: string, wrappedOrgKey: string): Promise<Organization> {
      return request(
        "/organizations/",
        { method: "POST", body: JSON.stringify({ name, wrapped_org_key: wrappedOrgKey }) },
        organizationSchema,
      );
    },

    listMembers(orgId: string): Promise<OrgMember[]> {
      return request(`/organizations/${orgId}/members`, { method: "GET" }, z.array(orgMemberSchema));
    },

    addMember(orgId: string, email: string, role: string, wrappedOrgKey: string): Promise<OrgMember> {
      return request(
        `/organizations/${orgId}/members`,
        { method: "POST", body: JSON.stringify({ email, role, wrapped_org_key: wrappedOrgKey }) },
        orgMemberSchema,
      );
    },

    /** Hand the org to another confirmed member (owner only). */
    transferOwnership(orgId: string, userId: string): Promise<{ message: string }> {
      return request(`/organizations/${orgId}/transfer-ownership`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId }),
      });
    },

    /** Delete an organization and all its shared data (owner only). */
    deleteOrg(orgId: string): Promise<void> {
      return request(`/organizations/${orgId}`, { method: "DELETE" });
    },

    changeMemberRole(orgId: string, userId: string, role: string): Promise<OrgMember> {
      return request(
        `/organizations/${orgId}/members/${userId}`,
        { method: "PATCH", body: JSON.stringify({ role }) },
        orgMemberSchema,
      );
    },

    removeMember(orgId: string, userId: string): Promise<void> {
      return request(`/organizations/${orgId}/members/${userId}`, { method: "DELETE" });
    },

    /** Toggle whether plain members can edit the org's shared entries (owner only). */
    updateOrgSettings(orgId: string, memberWrite: boolean): Promise<Organization> {
      return request(
        `/organizations/${orgId}/settings`,
        { method: "PATCH", body: JSON.stringify({ member_write: memberWrite }) },
        organizationSchema,
      );
    },

    /** Re-key an org: new wrapped keys for remaining members + re-encrypted items,
     *  optionally removing a member in the same atomic call (admin+). */
    rotateOrgKey(orgId: string, payload: RotateKeyPayload): Promise<{ message: string }> {
      return request(`/organizations/${orgId}/rotate-key`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    /** Confirm a pending member by storing the org key wrapped for them (admin+). */
    confirmMember(orgId: string, userId: string, wrappedOrgKey: string): Promise<OrgMember> {
      return request(
        `/organizations/${orgId}/members/${userId}/confirm`,
        { method: "POST", body: JSON.stringify({ wrapped_org_key: wrappedOrgKey }) },
        orgMemberSchema,
      );
    },

    // --- invitations ---
    createInvitation(orgId: string, email: string, role: string): Promise<Invitation> {
      return request(
        `/organizations/${orgId}/invitations`,
        { method: "POST", body: JSON.stringify({ email, role }) },
        invitationSchema,
      );
    },

    listInvitations(orgId: string): Promise<Invitation[]> {
      return request(`/organizations/${orgId}/invitations`, { method: "GET" },
        z.array(invitationSchema));
    },

    revokeInvitation(orgId: string, inviteId: string): Promise<void> {
      return request(`/organizations/${orgId}/invitations/${inviteId}`, { method: "DELETE" });
    },

    lookupInvitation(token: string): Promise<InvitationLookup> {
      return request(
        `/organizations/invitations/lookup?token=${encodeURIComponent(token)}`,
        { method: "GET" },
        invitationLookupSchema,
      );
    },

    acceptInvitation(token: string): Promise<{ org_id: string }> {
      return request("/organizations/invitations/accept", {
        method: "POST",
        body: JSON.stringify({ token }),
      });
    },

    // --- collections ---
    listCollections(orgId: string): Promise<Collection[]> {
      return request(`/organizations/${orgId}/collections/`, { method: "GET" },
        z.array(collectionSchema));
    },

    createCollection(orgId: string, name: string, wrappedKey: string): Promise<Collection> {
      return request(
        `/organizations/${orgId}/collections/`,
        { method: "POST", body: JSON.stringify({ name, wrapped_collection_key: wrappedKey }) },
        collectionSchema,
      );
    },

    listCollectionMembers(orgId: string, cid: string): Promise<CollectionMember[]> {
      return request(`/organizations/${orgId}/collections/${cid}/members`, { method: "GET" },
        z.array(collectionMemberSchema));
    },

    grantCollectionAccess(orgId: string, cid: string, email: string, wrappedKey: string): Promise<CollectionMember> {
      return request(
        `/organizations/${orgId}/collections/${cid}/access`,
        { method: "POST", body: JSON.stringify({ email, wrapped_collection_key: wrappedKey }) },
        collectionMemberSchema,
      );
    },

    revokeCollectionAccess(orgId: string, cid: string, userId: string): Promise<void> {
      return request(`/organizations/${orgId}/collections/${cid}/access/${userId}`,
        { method: "DELETE" });
    },

    deleteCollection(orgId: string, cid: string): Promise<void> {
      return request(`/organizations/${orgId}/collections/${cid}`, { method: "DELETE" });
    },

    // --- vault ---
    /** Fetch every entry by following the cursor. The client decrypts and
     *  searches locally, so it needs the whole vault, not one page. `orgId`
     *  selects an organization's shared vault instead of the personal one. */
    async listAllVault(orgId?: string, collectionId?: string): Promise<VaultEntry[]> {
      const items: VaultEntry[] = [];
      let cursor: string | null = null;
      do {
        const params = new URLSearchParams({ limit: "100" });
        if (cursor) params.set("cursor", cursor);
        if (orgId) params.set("org_id", orgId);
        if (collectionId) params.set("collection_id", collectionId);
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

    createVault(input: VaultInput, orgId?: string, collectionId?: string): Promise<VaultEntry> {
      const body = {
        ...input,
        ...(orgId ? { org_id: orgId } : {}),
        ...(collectionId ? { collection_id: collectionId } : {}),
      };
      return request("/vault/", { method: "POST", body: JSON.stringify(body) }, vaultEntrySchema);
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
