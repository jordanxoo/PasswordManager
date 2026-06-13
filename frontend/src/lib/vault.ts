import {
  encryptEntry,
  decryptEntry,
  generatePassword as generatePasswordCore,
  type VaultEntry,
  type VaultInput,
} from "@pm/core";

/** The full entry content — everything here is encrypted before it leaves the
 *  device (full zero-knowledge: the server only ever sees ciphertext). */
export interface VaultSecret {
  name: string;
  url: string;
  username: string;
  password: string;
  notes: string;
}

/** A fully decrypted entry, as used by the UI. `pinned` is a server-side
 *  column (not encrypted) so it can be toggled without re-encrypting. */
export interface VaultItem extends VaultSecret {
  id: string;
  category: string | null;
  updatedAt: string;
  pinned: boolean;
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
    category: entry.category ?? null,
    updatedAt: entry.updated_at,
    pinned: entry.pinned,
    name: secret.name ?? "",
    url: secret.url ?? "",
    username: secret.username ?? "",
    password: secret.password ?? "",
    notes: secret.notes ?? "",
  };
}

/** Encrypt a draft into the API payload — name/url/username/password/notes all
 *  go into the ciphertext; only `encrypted`+`iv` leave the device. */
export async function encodeDraft(draft: VaultDraft, key: CryptoKey): Promise<VaultInput> {
  const secret: VaultSecret = {
    name: draft.name,
    url: draft.url,
    username: draft.username,
    password: draft.password,
    notes: draft.notes,
  };
  const { encrypted, iv } = await encryptEntry(JSON.stringify(secret), key);
  return { encrypted, iv };
}

/** Quick all-classes password at the default settings — used for one-click
 *  generation and mock data. The full, configurable generator lives in
 *  `@pm/core` and is surfaced by the `<PasswordGenerator>` component. */
export function generatePassword(length = 20): string {
  return generatePasswordCore({ length });
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
