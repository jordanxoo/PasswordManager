import { create } from "zustand";
import { deriveAccount, generateSalt } from "@pm/core";
import { api } from "../lib/api";

type Status = "anonymous" | "pending2fa" | "authenticated";

/**
 * Session state. The AES encryption key lives ONLY here, in memory — it is
 * never persisted, so a page reload locks the vault (re-login required). The
 * master password is never stored at all.
 */
interface AuthState {
  status: Status;
  email: string | null;
  encryptionKey: CryptoKey | null;
  register: (email: string, masterPassword: string) => Promise<void>;
  login: (email: string, masterPassword: string) => Promise<{ requires2fa: boolean }>;
  complete2fa: (code: string) => Promise<void>;
  logout: () => Promise<void>;
}

// Transient: holds the derived key between login and 2FA confirmation.
let pendingKey: CryptoKey | null = null;

export const useAuth = create<AuthState>((set) => ({
  status: "anonymous",
  email: null,
  encryptionKey: null,

  async register(email, masterPassword) {
    const salt = generateSalt();
    const { authHash } = await deriveAccount(masterPassword, salt);
    await api.register(email, authHash, salt);
  },

  async login(email, masterPassword) {
    const salt = await api.getSalt(email);
    const { authHash, encryptionKey } = await deriveAccount(masterPassword, salt);
    const result = await api.login(email, authHash);
    if (result.requires2fa) {
      pendingKey = encryptionKey;
      set({ status: "pending2fa", email });
      return { requires2fa: true };
    }
    set({ status: "authenticated", email, encryptionKey });
    return { requires2fa: false };
  },

  async complete2fa(code) {
    await api.validate2fa(code);
    set({ status: "authenticated", encryptionKey: pendingKey });
    pendingKey = null;
  },

  async logout() {
    try {
      await api.logout();
    } catch {
      /* best-effort */
    }
    pendingKey = null;
    set({ status: "anonymous", email: null, encryptionKey: null });
  },
}));
