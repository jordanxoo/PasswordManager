import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useAuth } from "../stores/authStore";
import {
  decodeEntry,
  decodeHistory,
  encodeDraft,
  type HistoryVersion,
  type VaultDraft,
  type VaultItem,
} from "./vault";

const VAULT_KEY = ["vault"] as const;

/** Fetch + decrypt the vault. One undecryptable row won't sink the whole list. */
export function useVaultItems() {
  const encryptionKey = useAuth((s) => s.encryptionKey);
  return useQuery({
    queryKey: VAULT_KEY,
    enabled: !!encryptionKey,
    queryFn: async (): Promise<VaultItem[]> => {
      const entries = await api.listAllVault();
      const decoded = await Promise.all(
        entries.map((entry) => decodeEntry(entry, encryptionKey!).catch(() => null)),
      );
      return decoded.filter((item): item is VaultItem => item !== null);
    },
  });
}

export function useCreateVault() {
  const qc = useQueryClient();
  const key = useAuth((s) => s.encryptionKey);
  return useMutation({
    mutationFn: async (draft: VaultDraft) => api.createVault(await encodeDraft(draft, key!)),
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
  });
}

export function useUpdateVault() {
  const qc = useQueryClient();
  const key = useAuth((s) => s.encryptionKey);
  return useMutation({
    mutationFn: async ({ id, draft }: { id: string; draft: VaultDraft }) =>
      api.updateVault(id, await encodeDraft(draft, key!)),
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
  });
}

/** Pin/unpin via the dedicated endpoint — no re-encryption, no history entry. */
export function useTogglePin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (item: VaultItem) => api.setPin(item.id, !item.pinned),
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
  });
}

/** Fetch + decrypt an entry's prior versions (newest first). */
export function useVaultHistory(id: string | null) {
  const key = useAuth((s) => s.encryptionKey);
  return useQuery({
    queryKey: [...VAULT_KEY, id, "history"],
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

/** Roll an entry back to one of its snapshots, then refresh list + history. */
export function useRestoreVault(vaultId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (historyId: string) => api.restoreVault(vaultId!, historyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: VAULT_KEY });
    },
  });
}

export function useDeleteVault() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteVault(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
  });
}

/** Dev helper: create several entries, then refresh the list once. */
export function useCreateManyVault() {
  const qc = useQueryClient();
  const key = useAuth((s) => s.encryptionKey);
  return useMutation({
    mutationFn: async (drafts: VaultDraft[]) => {
      for (const draft of drafts) await api.createVault(await encodeDraft(draft, key!));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
  });
}
