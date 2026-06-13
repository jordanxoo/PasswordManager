import { describe, it, expect } from "vitest";
import {
  generateSalt,
  deriveAccount,
  encryptEntry,
  decryptEntry,
  generateKeypair,
  exportPublicKey,
  importPublicKey,
  wrapKeypair,
  unwrapPrivateKey,
  generateOrgKey,
  wrapOrgKey,
  unwrapOrgKey,
} from "./crypto";

describe("keypair wrap / unwrap", () => {
  it("round-trips the private key through the user's AES key", async () => {
    const { encryptionKey } = await deriveAccount("master-pw", generateSalt());
    const keypair = await generateKeypair();
    const wrapped = await wrapKeypair(keypair, encryptionKey);

    // Unwrapped private key must decrypt what the public key encrypts.
    const priv = await unwrapPrivateKey(wrapped.encryptedPrivateKey, wrapped.privateKeyIv, encryptionKey);
    const pub = await importPublicKey(wrapped.publicKey);
    const orgKey = await generateOrgKey();
    const wrappedOrg = await wrapOrgKey(orgKey, pub);
    await expect(unwrapOrgKey(wrappedOrg, priv)).resolves.toBeDefined();
  });

  it("cannot unwrap the private key with the wrong AES key", async () => {
    const salt = generateSalt();
    const { encryptionKey } = await deriveAccount("right-pw", salt);
    const { encryptionKey: wrongKey } = await deriveAccount("wrong-pw", salt);
    const wrapped = await wrapKeypair(await generateKeypair(), encryptionKey);
    await expect(
      unwrapPrivateKey(wrapped.encryptedPrivateKey, wrapped.privateKeyIv, wrongKey),
    ).rejects.toThrow();
  });
});

describe("org key sharing", () => {
  it("two members both decrypt the same shared secret", async () => {
    const orgKey = await generateOrgKey();
    const secret = JSON.stringify({ username: "team", password: "shared-s3cret" });
    const payload = await encryptEntry(secret, orgKey);

    // Each member has their own keypair; the org key is wrapped to each.
    const alice = await generateKeypair();
    const bob = await generateKeypair();
    const aliceWrap = await wrapOrgKey(orgKey, await importPublicKey(await exportPublicKey(alice.publicKey)));
    const bobWrap = await wrapOrgKey(orgKey, await importPublicKey(await exportPublicKey(bob.publicKey)));

    const aliceKey = await unwrapOrgKey(aliceWrap, alice.privateKey);
    const bobKey = await unwrapOrgKey(bobWrap, bob.privateKey);

    expect(await decryptEntry(payload, aliceKey)).toBe(secret);
    expect(await decryptEntry(payload, bobKey)).toBe(secret);
  });

  it("an unwrapped org key can be re-wrapped for a new member (add-member flow)", async () => {
    // Owner creates the org key and a secret, then adds a member: the owner must
    // UNWRAP their own copy and RE-WRAP it for the newcomer. This requires the
    // unwrapped key to stay extractable.
    const orgKey = await generateOrgKey();
    const secret = JSON.stringify({ password: "team-secret" });
    const payload = await encryptEntry(secret, orgKey);

    const owner = await generateKeypair();
    const ownerWrap = await wrapOrgKey(orgKey, owner.publicKey);

    // Owner re-derives the org key from their wrapped copy, then wraps for a new member.
    const ownerOrgKey = await unwrapOrgKey(ownerWrap, owner.privateKey);
    const newMember = await generateKeypair();
    const memberWrap = await wrapOrgKey(ownerOrgKey, newMember.publicKey);

    const memberOrgKey = await unwrapOrgKey(memberWrap, newMember.privateKey);
    expect(await decryptEntry(payload, memberOrgKey)).toBe(secret);
  });

  it("a non-member cannot unwrap the org key", async () => {
    const orgKey = await generateOrgKey();
    const member = await generateKeypair();
    const outsider = await generateKeypair();
    const wrap = await wrapOrgKey(orgKey, member.publicKey);
    await expect(unwrapOrgKey(wrap, outsider.privateKey)).rejects.toThrow();
  });
});
