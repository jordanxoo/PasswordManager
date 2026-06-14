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

// --- Asymmetric layer for organization secret sharing ---
//
// Each user has an RSA-OAEP keypair. The PRIVATE key is wrapped (AES-GCM) with
// the user's own `encryptionKey` and stored server-side as ciphertext; the
// PUBLIC key is stored in plaintext. An organization has a random AES "org key"
// which is wrapped to each member's public key. A member unwraps it with their
// private key. The server only ever sees public keys and ciphertext.

const RSA_PARAMS = {
  name: "RSA-OAEP",
  modulusLength: 2048,
  publicExponent: new Uint8Array([1, 0, 1]),
  hash: "SHA-256",
} as const;

export interface WrappedKeypair {
  /** SPKI public key, base64. Stored in plaintext on the server. */
  publicKey: string;
  /** PKCS8 private key, AES-GCM-encrypted with the user's encryptionKey. */
  encryptedPrivateKey: string;
  /** Base64 IV for the private-key encryption. */
  privateKeyIv: string;
}

/** Generate a fresh RSA-OAEP keypair (extractable so the private key can be wrapped). */
export async function generateKeypair(): Promise<CryptoKeyPair> {
  return subtle.generateKey(RSA_PARAMS, true, ["encrypt", "decrypt"]);
}

/** Export a public key to SPKI base64. */
export async function exportPublicKey(publicKey: CryptoKey): Promise<string> {
  return bytesToBase64(new Uint8Array(await subtle.exportKey("spki", publicKey)));
}

/** Import an SPKI base64 public key (encrypt-only). */
export async function importPublicKey(spki: string): Promise<CryptoKey> {
  return subtle.importKey("spki", base64ToBytes(spki), RSA_PARAMS, true, ["encrypt"]);
}

/** Wrap (encrypt) a generated keypair's private key with the user's AES encryptionKey. */
export async function wrapKeypair(keypair: CryptoKeyPair, encryptionKey: CryptoKey): Promise<WrappedKeypair> {
  const pkcs8 = new Uint8Array(await subtle.exportKey("pkcs8", keypair.privateKey));
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const ct = await subtle.encrypt({ name: "AES-GCM", iv }, encryptionKey, pkcs8);
  return {
    publicKey: await exportPublicKey(keypair.publicKey),
    encryptedPrivateKey: bytesToBase64(new Uint8Array(ct)),
    privateKeyIv: bytesToBase64(iv),
  };
}

/** Unwrap the private key: decrypt the PKCS8 blob with the user's AES key, then import it. */
export async function unwrapPrivateKey(
  encryptedPrivateKey: string,
  privateKeyIv: string,
  encryptionKey: CryptoKey,
): Promise<CryptoKey> {
  const pkcs8 = await subtle.decrypt(
    { name: "AES-GCM", iv: base64ToBytes(privateKeyIv) },
    encryptionKey,
    base64ToBytes(encryptedPrivateKey),
  );
  return subtle.importKey("pkcs8", pkcs8, RSA_PARAMS, false, ["decrypt"]);
}

/** Generate a random AES-256 org key. Extractable so it can be wrapped per member. */
export async function generateOrgKey(): Promise<CryptoKey> {
  return subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
}

/** Wrap an org key with a recipient's RSA public key. Returns base64 ciphertext. */
export async function wrapOrgKey(orgKey: CryptoKey, recipientPublicKey: CryptoKey): Promise<string> {
  const raw = new Uint8Array(await subtle.exportKey("raw", orgKey));
  const ct = await subtle.encrypt({ name: "RSA-OAEP" }, recipientPublicKey, raw);
  return bytesToBase64(new Uint8Array(ct));
}

/** Unwrap an org key with the member's RSA private key.
 *  Imported as extractable so the holder can re-wrap it when adding new members. */
export async function unwrapOrgKey(wrapped: string, privateKey: CryptoKey): Promise<CryptoKey> {
  const raw = await subtle.decrypt({ name: "RSA-OAEP" }, privateKey, base64ToBytes(wrapped));
  return subtle.importKey("raw", raw, { name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
}
