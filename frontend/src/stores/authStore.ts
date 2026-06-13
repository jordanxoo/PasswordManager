import { create } from "zustand";
import {
  deriveAccount,
  generateSalt,
  generateKeypair,
  wrapKeypair,
  unwrapPrivateKey,
  type LoginResponse,
} from "@pm/core";
import { api } from "../lib/api";
import { queryClient } from "../lib/queryClient";

type Status = "anonymous" | "pending2fa" | "authenticated";

/**
 * Session state. The AES encryption key and the unwrapped RSA private key live
 * ONLY here, in memory — never persisted, so a page reload locks the vault
 * (re-login required). The master password is never stored at all.
 */
interface AuthState {
  status: Status;
  email: string | null;
  encryptionKey: CryptoKey | null;
  /** RSA private key for unwrapping organization keys. */
  privateKey: CryptoKey | null;
  /** Own SPKI public key (base64), used to wrap org keys for self. */
  publicKey: string | null;
  register: (email: string, masterPassword: string) => Promise<void>;
  login: (email: string, masterPassword: string) => Promise<{ requires2fa: boolean }>;
  complete2fa: (code: string) => Promise<void>;
  completeRecovery: (code: string) => Promise<void>;
  logout: () => Promise<void>;
}

interface ResolvedKeys {
  privateKey: CryptoKey;
  publicKey: string;
}

/**
 * Turn a login response into usable keys. If the account already has a wrapped
 * keypair, unwrap the private key with the AES key. Otherwise (legacy account)
 * generate a keypair now, wrap it, and upload it — a one-time migration that
 * lets the account take part in organizations.
 */
async function resolveKeys(resp: LoginResponse, encryptionKey: CryptoKey): Promise<ResolvedKeys> {
  if (resp.public_key && resp.encrypted_private_key && resp.private_key_iv) {
    const privateKey = await unwrapPrivateKey(
      resp.encrypted_private_key,
      resp.private_key_iv,
      encryptionKey,
    );
    return { privateKey, publicKey: resp.public_key };
  }

  const keypair = await generateKeypair();
  const wrapped = await wrapKeypair(keypair, encryptionKey);
  await api.uploadKeys({
    public_key: wrapped.publicKey,
    encrypted_private_key: wrapped.encryptedPrivateKey,
    private_key_iv: wrapped.privateKeyIv,
  });
  return { privateKey: keypair.privateKey, publicKey: wrapped.publicKey };
}

// Transient: holds the derived AES key between login and 2FA confirmation.
let pendingKey: CryptoKey | null = null;

export const useAuth = create<AuthState>((set) => ({
  status: "anonymous",
  email: null,
  encryptionKey: null,
  privateKey: null,
  publicKey: null,

  async register(email, masterPassword) {
    const salt = generateSalt();
    const { authHash, encryptionKey } = await deriveAccount(masterPassword, salt);
    // Generate the keypair up front so new accounts are org-ready immediately.
    const keypair = await generateKeypair();
    const wrapped = await wrapKeypair(keypair, encryptionKey);
    await api.register(email, authHash, salt, {
      public_key: wrapped.publicKey,
      encrypted_private_key: wrapped.encryptedPrivateKey,
      private_key_iv: wrapped.privateKeyIv,
    });
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
    const { privateKey, publicKey } = await resolveKeys(result, encryptionKey);
    // Drop any cached data from a previous account before this one becomes active.
    queryClient.clear();
    set({ status: "authenticated", email, encryptionKey, privateKey, publicKey });
    return { requires2fa: false };
  },

  async complete2fa(code) {
    const resp = await api.validate2fa(code);
    const { privateKey, publicKey } = await resolveKeys(resp, pendingKey!);
    queryClient.clear();
    set({ status: "authenticated", encryptionKey: pendingKey, privateKey, publicKey });
    pendingKey = null;
  },

  async completeRecovery(code) {
    const resp = await api.validateRecovery(code);
    const { privateKey, publicKey } = await resolveKeys(resp, pendingKey!);
    queryClient.clear();
    set({ status: "authenticated", encryptionKey: pendingKey, privateKey, publicKey });
    pendingKey = null;
  },

  async logout() {
    try {
      await api.logout();
    } catch {
      /* best-effort */
    }
    pendingKey = null;
    // Clear cached vault/org data so it never leaks into the next session.
    queryClient.clear();
    set({ status: "anonymous", email: null, encryptionKey: null, privateKey: null, publicKey: null });
  },
}));
