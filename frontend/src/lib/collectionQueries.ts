import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generateOrgKey,
  importPublicKey,
  wrapOrgKey,
  unwrapOrgKey,
  encryptEntry,
  decryptEntry,
  type Collection,
} from "@pm/core";
import { api } from "./api";
import { useAuth } from "../stores/authStore";

const collectionsKey = (orgId: string) => ["collections", orgId] as const;
const collMembersKey = (orgId: string, cid: string) =>
  ["collections", orgId, cid, "members"] as const;

/** Collections in the org the current user has access to (with wrapped keys). */
export function useCollections(orgId: string | null) {
  const encryptionKey = useAuth((s) => s.encryptionKey);
  return useQuery({
    queryKey: collectionsKey(orgId ?? ""),
    enabled: !!orgId && !!encryptionKey,
    queryFn: () => api.listCollections(orgId!),
  });
}

/** Create a collection: generate a fresh key, wrap it with the creator's own key. */
export function useCreateCollection(orgId: string) {
  const qc = useQueryClient();
  const publicKey = useAuth((s) => s.publicKey);
  return useMutation({
    mutationFn: async (name: string) => {
      const key = await generateOrgKey();
      const wrapped = await wrapOrgKey(key, await importPublicKey(publicKey!));
      return api.createCollection(orgId, name, wrapped);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: collectionsKey(orgId) }),
  });
}

export function useCollectionMembers(orgId: string, cid: string) {
  return useQuery({
    queryKey: collMembersKey(orgId, cid),
    queryFn: () => api.listCollectionMembers(orgId, cid),
  });
}

/**
 * Grant a member access: unwrap our copy of the collection key, re-wrap it with
 * their public key. The plaintext collection key never leaves the browser.
 */
export function useGrantCollectionAccess(orgId: string, collection: Collection | undefined) {
  const qc = useQueryClient();
  const privateKey = useAuth((s) => s.privateKey);
  return useMutation({
    mutationFn: async (email: string) => {
      if (!collection) throw new Error("Collection not loaded yet — try again in a moment.");
      if (!privateKey) throw new Error("Session locked. Please sign in again.");
      const key = await unwrapOrgKey(collection.wrapped_collection_key, privateKey);
      const target = await api.getPublicKey(email);
      const wrapped = await wrapOrgKey(key, await importPublicKey(target.public_key));
      return api.grantCollectionAccess(orgId, collection.id, email, wrapped);
    },
    onSuccess: () =>
      collection && qc.invalidateQueries({ queryKey: collMembersKey(orgId, collection.id) }),
  });
}

export function useRevokeCollectionAccess(orgId: string, cid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.revokeCollectionAccess(orgId, cid, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: collMembersKey(orgId, cid) }),
  });
}

export function useDeleteCollection(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cid: string) => api.deleteCollection(orgId, cid),
    onSuccess: () => qc.invalidateQueries({ queryKey: collectionsKey(orgId) }),
  });
}

/**
 * Rotate a collection's key: generate a fresh key, re-encrypt every item with
 * it, re-wrap it for every remaining member with access — optionally revoking a
 * member atomically. Invalidates the old key a removed member may have cached.
 */
export function useRotateCollectionKey(orgId: string, collection: Collection | undefined) {
  const qc = useQueryClient();
  const privateKey = useAuth((s) => s.privateKey);
  return useMutation({
    mutationFn: async ({ removeUserId }: { removeUserId?: string }) => {
      if (!collection) throw new Error("Collection not loaded yet — try again in a moment.");
      if (!privateKey) throw new Error("Session locked. Please sign in again.");
      const oldKey = await unwrapOrgKey(collection.wrapped_collection_key, privateKey);
      const newKey = await generateOrgKey();

      // Re-encrypt every item in the collection with the new key.
      const items = await api.listAllVault(orgId, collection.id);
      const vault_items = await Promise.all(
        items.map(async (it) => {
          const plain = await decryptEntry({ encrypted: it.encrypted, iv: it.iv }, oldKey);
          const enc = await encryptEntry(plain, newKey);
          return { id: it.id, encrypted: enc.encrypted, iv: enc.iv };
        }),
      );

      // Re-wrap the new key for every remaining member with access.
      const members = await api.listCollectionMembers(orgId, collection.id);
      const remaining = members.filter((m) => m.user_id !== removeUserId);
      const member_keys = await Promise.all(
        remaining.map(async (m) => {
          const pk = await api.getPublicKey(m.email);
          const pub = await importPublicKey(pk.public_key);
          return { user_id: m.user_id, wrapped_collection_key: await wrapOrgKey(newKey, pub) };
        }),
      );

      return api.rotateCollectionKey(orgId, collection.id, { remove_user_id: removeUserId, member_keys, vault_items });
    },
    onSuccess: () => {
      if (!collection) return;
      qc.invalidateQueries({ queryKey: collectionsKey(orgId) });
      qc.invalidateQueries({ queryKey: collMembersKey(orgId, collection.id) });
      // Re-derive the unwrapped collection key + refetch the collection vault.
      qc.invalidateQueries({ queryKey: ["orgKey", orgId] });
      qc.invalidateQueries({ queryKey: ["vault", orgId, collection.id] });
    },
  });
}
