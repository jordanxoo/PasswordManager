/**
 * Zero-knowledge crypto layer.
 *
 * The master password NEVER leaves the client. From it we derive two
 * independent secrets:
 *
 *   masterKey      = PBKDF2-SHA256(password, salt, ITERATIONS)        [32 bytes]
 *   encryptionKey  = HKDF(masterKey, info="pm-enc-key")  -> AES-256-GCM key
 *   authHash       = HKDF(masterKey, info="pm-auth-hash") -> 32 bytes (base64)
 *
 * Only `authHash` is sent to the server (in place of the password); the server
 * stores Argon2id(authHash) and never sees the password or the encryption key.
 * `encryptionKey` is non-extractable and must be kept in memory only.
 *
 * Note: SubtleCrypto requires a secure context (https or localhost).
 */

const subtle = globalThis.crypto.subtle;

/** OWASP-recommended floor for PBKDF2-HMAC-SHA256. */
export const PBKDF2_ITERATIONS = 600_000;
const SALT_BYTES = 16;
/** 96-bit IV — standard for AES-GCM. 12 bytes encode to exactly 16 base64 chars,
 *  which is what the backend validates. */
const IV_BYTES = 12;

export interface DerivedAccount {
  /** AES-256-GCM key for vault entries. Non-extractable; keep in memory only. */
  encryptionKey: CryptoKey;
  /** The only secret sent to the server, in place of the password. Base64. */
  authHash: string;
}

export interface EncryptedPayload {
  /** Base64 ciphertext, includes the GCM auth tag. */
  encrypted: string;
  /** Base64 IV — 12 bytes => exactly 16 chars (matches backend validation). */
  iv: string;
}

// --- base64 helpers (isomorphic: browser + Node) ---

export function bytesToBase64(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

export function base64ToBytes(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

const encoder = new TextEncoder();
const decoder = new TextDecoder();

/** Random salt for a new account. Base64. Generated client-side at registration. */
export function generateSalt(): string {
  return bytesToBase64(crypto.getRandomValues(new Uint8Array(SALT_BYTES)));
}

async function pbkdf2MasterKey(password: string, salt: Uint8Array<ArrayBuffer>): Promise<ArrayBuffer> {
  const baseKey = await subtle.importKey(
    "raw",
    encoder.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  return subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    baseKey,
    256,
  );
}

async function hkdf(masterKey: ArrayBuffer, info: string, bits: number): Promise<ArrayBuffer> {
  const baseKey = await subtle.importKey("raw", masterKey, "HKDF", false, ["deriveBits"]);
  return subtle.deriveBits(
    { name: "HKDF", hash: "SHA-256", salt: new Uint8Array(0), info: encoder.encode(info) },
    baseKey,
    bits,
  );
}

/**
 * Derive the AES encryption key + the server auth hash from a master password
 * and its salt. Same (password, salt) always yields the same result.
 */
export async function deriveAccount(masterPassword: string, salt: string): Promise<DerivedAccount> {
  const masterKey = await pbkdf2MasterKey(masterPassword, base64ToBytes(salt));

  const encBits = await hkdf(masterKey, "pm-enc-key", 256);
  const encryptionKey = await subtle.importKey(
    "raw",
    encBits,
    { name: "AES-GCM", length: 256 },
    false, // non-extractable
    ["encrypt", "decrypt"],
  );

  const authBits = await hkdf(masterKey, "pm-auth-hash", 256);
  return { encryptionKey, authHash: bytesToBase64(new Uint8Array(authBits)) };
}

/** Encrypt a plaintext string into a ciphertext + unique IV. */
export async function encryptEntry(plaintext: string, key: CryptoKey): Promise<EncryptedPayload> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const ct = await subtle.encrypt({ name: "AES-GCM", iv }, key, encoder.encode(plaintext));
  return { encrypted: bytesToBase64(new Uint8Array(ct)), iv: bytesToBase64(iv) };
}

/** Decrypt a payload. Throws if the key is wrong or the data was tampered with. */
export async function decryptEntry(payload: EncryptedPayload, key: CryptoKey): Promise<string> {
  const pt = await subtle.decrypt(
    { name: "AES-GCM", iv: base64ToBytes(payload.iv) },
    key,
    base64ToBytes(payload.encrypted),
  );
  return decoder.decode(pt);
}
