/** Shared, cryptographically-secure password generator.
 *
 *  Lives in `@pm/core` so the web app and the (future) browser extension
 *  generate passwords identically — locally, via `crypto.getRandomValues`, so a
 *  freshly-minted password never crosses the network (zero-knowledge by
 *  default). The character sets mirror the backend `/generator` endpoint. */

const UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const LOWERCASE = "abcdefghijklmnopqrstuvwxyz";
const NUMBERS = "0123456789";
const SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?";
/** Easy to misread in most fonts. */
const AMBIGUOUS = new Set("0O1lI");

export interface GeneratorOptions {
  length: number;
  uppercase: boolean;
  lowercase: boolean;
  numbers: boolean;
  symbols: boolean;
  /** Drop look-alike characters (0/O, 1/l/I). */
  excludeAmbiguous: boolean;
}

export const DEFAULT_GENERATOR_OPTIONS: GeneratorOptions = {
  length: 20,
  uppercase: true,
  lowercase: true,
  numbers: true,
  symbols: true,
  excludeAmbiguous: false,
};

export const MIN_LENGTH = 8;
export const MAX_LENGTH = 128;

/** Unbiased random integer in `[0, max)` via rejection sampling on a u32. */
function randomInt(max: number): number {
  if (max <= 0) throw new Error("max must be positive");
  const limit = Math.floor(0x1_0000_0000 / max) * max;
  const buf = new Uint32Array(1);
  let x: number;
  do {
    crypto.getRandomValues(buf);
    x = buf[0];
  } while (x >= limit);
  return x % max;
}

function pick(chars: string): string {
  return chars[randomInt(chars.length)];
}

function clean(chars: string, excludeAmbiguous: boolean): string {
  if (!excludeAmbiguous) return chars;
  return [...chars].filter((c) => !AMBIGUOUS.has(c)).join("");
}

/** The enabled character groups, each already filtered for ambiguity. */
function enabledGroups(o: GeneratorOptions): string[] {
  const groups: string[] = [];
  if (o.uppercase) groups.push(clean(UPPERCASE, o.excludeAmbiguous));
  if (o.lowercase) groups.push(clean(LOWERCASE, o.excludeAmbiguous));
  if (o.numbers) groups.push(clean(NUMBERS, o.excludeAmbiguous));
  if (o.symbols) groups.push(clean(SYMBOLS, o.excludeAmbiguous));
  return groups.filter((g) => g.length > 0);
}

/** Size of the pool the password is actually drawn from. */
export function alphabetSize(options: Partial<GeneratorOptions> = {}): number {
  const o = { ...DEFAULT_GENERATOR_OPTIONS, ...options };
  return enabledGroups(o).reduce((n, g) => n + g.length, 0);
}

/** Shannon entropy in bits for `length` chars drawn from `alphabet` symbols. */
export function entropyBits(length: number, alphabet: number): number {
  if (alphabet <= 1 || length <= 0) return 0;
  return Math.round(length * Math.log2(alphabet) * 10) / 10;
}

export type StrengthLevel = "weak" | "fair" | "strong" | "excellent";

/** Coarse strength bucket from entropy bits (NIST-ish thresholds). */
export function strength(bits: number): StrengthLevel {
  if (bits < 40) return "weak";
  if (bits < 60) return "fair";
  if (bits < 100) return "strong";
  return "excellent";
}

/** Generate a password. Guarantees at least one character from every enabled
 *  group, then fills the rest from the combined pool and shuffles securely.
 *  Throws if no character set is enabled. */
export function generatePassword(options: Partial<GeneratorOptions> = {}): string {
  const o = { ...DEFAULT_GENERATOR_OPTIONS, ...options };
  const length = Math.max(MIN_LENGTH, Math.min(MAX_LENGTH, Math.floor(o.length)));
  const groups = enabledGroups(o);
  if (groups.length === 0) {
    throw new Error("At least one character set must be enabled");
  }
  const alphabet = groups.join("");

  // One guaranteed pick per group (capped at length for very short passwords).
  const chars = groups.slice(0, length).map(pick);
  while (chars.length < length) chars.push(pick(alphabet));

  // Fisher-Yates shuffle so the guaranteed chars aren't stuck at the front.
  for (let i = chars.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [chars[i], chars[j]] = [chars[j], chars[i]];
  }
  return chars.join("");
}
