import { describe, it, expect } from "vitest";
import {
  generateSalt,
  deriveAccount,
  encryptEntry,
  decryptEntry,
  base64ToBytes,
} from "./crypto";

describe("generateSalt", () => {
  it("produces a 16-byte base64 salt", () => {
    expect(base64ToBytes(generateSalt()).length).toBe(16);
  });

  it("is random across calls", () => {
    expect(generateSalt()).not.toBe(generateSalt());
  });
});

describe("deriveAccount", () => {
  it("is deterministic for the same password + salt", async () => {
    const salt = generateSalt();
    const a = await deriveAccount("correct horse battery staple", salt);
    const b = await deriveAccount("correct horse battery staple", salt);
    expect(a.authHash).toBe(b.authHash);
  });

  it("gives a different authHash for a different password", async () => {
    const salt = generateSalt();
    const a = await deriveAccount("password-one", salt);
    const b = await deriveAccount("password-two", salt);
    expect(a.authHash).not.toBe(b.authHash);
  });

  it("gives a different authHash for a different salt", async () => {
    const a = await deriveAccount("same-password", generateSalt());
    const b = await deriveAccount("same-password", generateSalt());
    expect(a.authHash).not.toBe(b.authHash);
  });
});

describe("encrypt / decrypt", () => {
  it("round-trips a vault entry", async () => {
    const { encryptionKey } = await deriveAccount("master-pw", generateSalt());
    const secret = JSON.stringify({ username: "alice", password: "s3cr3t", notes: "x" });
    const payload = await encryptEntry(secret, encryptionKey);
    expect(await decryptEntry(payload, encryptionKey)).toBe(secret);
  });

  it("uses a 16-char (12-byte) IV matching the backend validation", async () => {
    const { encryptionKey } = await deriveAccount("pw", generateSalt());
    const { iv } = await encryptEntry("data", encryptionKey);
    expect(iv).toHaveLength(16);
    expect(base64ToBytes(iv).length).toBe(12);
  });

  it("generates a unique IV per call (never reused)", async () => {
    const { encryptionKey } = await deriveAccount("pw", generateSalt());
    const a = await encryptEntry("data", encryptionKey);
    const b = await encryptEntry("data", encryptionKey);
    expect(a.iv).not.toBe(b.iv);
    expect(a.encrypted).not.toBe(b.encrypted);
  });

  it("fails to decrypt with the wrong key", async () => {
    const salt = generateSalt();
    const { encryptionKey } = await deriveAccount("right-pw", salt);
    const { encryptionKey: wrongKey } = await deriveAccount("wrong-pw", salt);
    const payload = await encryptEntry("secret", encryptionKey);
    await expect(decryptEntry(payload, wrongKey)).rejects.toThrow();
  });
});
