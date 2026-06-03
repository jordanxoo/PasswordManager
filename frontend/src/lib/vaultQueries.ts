import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useAuth } from "../stores/authStore";
import {
  decodeEntry,
  draftFromItem,
  encodeDraft,
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
      const page = await api.listVault();
      const decoded = await Promise.all(
        page.items.map((entry) => decodeEntry(entry, encryptionKey!).catch(() => null)),
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
    mutationFn: async ({ id, draft, pinned }: { id: string; draft: VaultDraft; pinned: boolean }) =>
      api.updateVault(id, await encodeDraft(draft, key!, pinned)),
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
  });
}

export function useTogglePin() {
  const qc = useQueryClient();
  const key = useAuth((s) => s.encryptionKey);
  return useMutation({
    mutationFn: async (item: VaultItem) =>
      api.updateVault(item.id, await encodeDraft(draftFromItem(item), key!, !item.pinned)),
    onSuccess: () => qc.invalidateQueries({ queryKey: VAULT_KEY }),
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
