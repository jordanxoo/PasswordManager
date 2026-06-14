import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generateOrgKey,
  importPublicKey,
  wrapOrgKey,
  unwrapOrgKey,
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
