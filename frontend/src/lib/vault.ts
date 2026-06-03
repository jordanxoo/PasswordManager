import { encryptEntry, decryptEntry, type VaultEntry, type VaultInput } from "@pm/core";

/** The secret half of an entry — encrypted before it leaves the device.
 *  `pinned` lives here (the backend has no such column) so it stays private
 *  and syncs across devices without any API change. */
export interface VaultSecret {
  username: string;
  password: string;
  notes: string;
  pinned: boolean;
}

/** A fully decrypted entry, as used by the UI. */
export interface VaultItem extends VaultSecret {
  id: string;
  name: string;
  url: string;
  category: string | null;
  updatedAt: string;
}

/** Form values for create & edit. */
export interface VaultDraft {
  name: string;
  url: string;
  username: string;
  password: string;
  notes: string;
}

/** Decrypt a stored entry into a usable item. Throws if the key is wrong. */
export async function decodeEntry(entry: VaultEntry, key: CryptoKey): Promise<VaultItem> {
  const json = await decryptEntry({ encrypted: entry.encrypted, iv: entry.iv }, key);
  const secret = JSON.parse(json) as Partial<VaultSecret>;
  return {
    id: entry.id,
    name: entry.name,
    url: entry.url,
    category: entry.category ?? null,
    updatedAt: entry.updated_at,
    username: secret.username ?? "",
    password: secret.password ?? "",
    notes: secret.notes ?? "",
    pinned: secret.pinned ?? false,
  };
}

/** Encrypt a draft into the payload the API expects (name/url stay plaintext). */
export async function encodeDraft(
  draft: VaultDraft,
  key: CryptoKey,
  pinned = false,
): Promise<VaultInput> {
  const secret: VaultSecret = {
    username: draft.username,
    password: draft.password,
    notes: draft.notes,
    pinned,
  };
  const { encrypted, iv } = await encryptEntry(JSON.stringify(secret), key);
  return { name: draft.name, url: draft.url, encrypted, iv };
}

export function draftFromItem(item: VaultItem): VaultDraft {
  return {
    name: item.name,
    url: item.url,
    username: item.username,
    password: item.password,
    notes: item.notes,
  };
}

const ALPHABET =
  "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*-_=+";

/** Cryptographically-random password using a no-modulo-bias rejection sampler. */
export function generatePassword(length = 20): string {
  const max = Math.floor(256 / ALPHABET.length) * ALPHABET.length;
  let out = "";
  while (out.length < length) {
    const bytes = crypto.getRandomValues(new Uint8Array(length));
    for (let i = 0; i < bytes.length && out.length < length; i++) {
      if (bytes[i] < max) out += ALPHABET[bytes[i] % ALPHABET.length];
    }
  }
  return out;
}

// --- dev only: realistic-ish mock entries for testing ---
const MOCK_SITES: ReadonlyArray<[string, string]> = [
  ["GitHub", "github.com"],
  ["Google", "google.com"],
  ["Amazon", "amazon.com"],
  ["Netflix", "netflix.com"],
  ["Spotify", "spotify.com"],
  ["Reddit", "reddit.com"],
  ["LinkedIn", "linkedin.com"],
  ["Dropbox", "dropbox.com"],
  ["Slack", "slack.com"],
  ["Notion", "notion.so"],
  ["Figma", "figma.com"],
  ["Steam", "store.steampowered.com"],
];
const MOCK_USERS = ["alice", "bob", "carol", "dave", "erin", "frank"];

export function generateMockDrafts(count = 8): VaultDraft[] {
  const shuffled = [...MOCK_SITES].sort(() => Math.random() - 0.5);
  return Array.from({ length: Math.min(count, shuffled.length) }, (_, i) => {
    const [name, url] = shuffled[i];
    const user = MOCK_USERS[Math.floor(Math.random() * MOCK_USERS.length)];
    return {
      name,
      url,
      username: `${user}@example.com`,
      password: generatePassword(16),
      notes: Math.random() > 0.6 ? "Recovery email: backup@example.com" : "",
    };
  });
}
