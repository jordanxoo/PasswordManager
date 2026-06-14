import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useVaultContext } from "../stores/vaultContext";
import { useActiveVaultKey } from "./orgQueries";
import {
  decodeEntry,
  decodeHistory,
  encodeDraft,
  type HistoryVersion,
  type VaultDraft,
  type VaultItem,
} from "./vault";

/** Query key scoped to the active context: personal, an org's General, or a collection. */
const vaultKey = (orgId: string | null, collectionId: string | null) =>
  ["vault", orgId ?? "personal", collectionId ?? "general"] as const;

/** Fetch + decrypt the active vault (personal, org "General", or a collection).
 *  One undecryptable row won't sink the whole list. */
export function useVaultItems() {
  const orgId = useVaultContext((s) => s.orgId);
  const collectionId = useVaultContext((s) => s.collectionId);
  const { key } = useActiveVaultKey();
  return useQuery({
    queryKey: vaultKey(orgId, collectionId),
    enabled: !!key,
    queryFn: async (): Promise<VaultItem[]> => {
      const entries = await api.listAllVault(orgId ?? undefined, collectionId ?? undefined);
      const decoded = await Promise.all(
        entries.map((entry) => decodeEntry(entry, key!).catch(() => null)),
      );
      return decoded.filter((item): item is VaultItem => item !== null);
    },
  });
}

export function useCreateVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const collectionId = useVaultContext((s) => s.collectionId);
  const { key } = useActiveVaultKey();
  return useMutation({
    mutationFn: async (draft: VaultDraft) =>
      api.createVault(await encodeDraft(draft, key!), orgId ?? undefined, collectionId ?? undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId, collectionId) }),
  });
}

export function useUpdateVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const collectionId = useVaultContext((s) => s.collectionId);
  const { key } = useActiveVaultKey();
  return useMutation({
    mutationFn: async ({ id, draft }: { id: string; draft: VaultDraft }) =>
      api.updateVault(id, await encodeDraft(draft, key!)),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId, collectionId) }),
  });
}

/** Pin/unpin via the dedicated endpoint — no re-encryption, no history entry. */
export function useTogglePin() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const collectionId = useVaultContext((s) => s.collectionId);
  return useMutation({
    mutationFn: (item: VaultItem) => api.setPin(item.id, !item.pinned),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId, collectionId) }),
  });
}

/** Fetch + decrypt an entry's prior versions (newest first). Uses the active
 *  context key so it works for personal, "General" and collection entries. */
export function useVaultHistory(id: string | null) {
  const { key } = useActiveVaultKey();
  return useQuery({
    queryKey: ["vault", "history", id],
    enabled: !!id && !!key,
    queryFn: async (): Promise<HistoryVersion[]> => {
      const entries = await api.vaultHistory(id!);
      const decoded = await Promise.all(
        entries.map((e) => decodeHistory(e, key!).catch(() => null)),
      );
      return decoded.filter((v): v is HistoryVersion => v !== null);
    },
  });
}

/** Roll an entry back to one of its snapshots, then refresh the vault list. */
export function useRestoreVault(vaultId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (historyId: string) => api.restoreVault(vaultId!, historyId),
    // Invalidate every vault context (prefix match) plus this entry's history.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vault"] });
    },
  });
}

export function useDeleteVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const collectionId = useVaultContext((s) => s.collectionId);
  return useMutation({
    mutationFn: (id: string) => api.deleteVault(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId, collectionId) }),
  });
}

/** Dev helper: create several entries in the active context, then refresh once. */
export function useCreateManyVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const collectionId = useVaultContext((s) => s.collectionId);
  const { key } = useActiveVaultKey();
  return useMutation({
    mutationFn: async (drafts: VaultDraft[]) => {
      for (const draft of drafts)
        await api.createVault(await encodeDraft(draft, key!), orgId ?? undefined, collectionId ?? undefined);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId, collectionId) }),
  });
}
