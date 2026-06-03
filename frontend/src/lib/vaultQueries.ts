import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useAuth } from "../stores/authStore";
import { decodeEntry, encodeDraft, type VaultDraft, type VaultItem } from "./vault";

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
