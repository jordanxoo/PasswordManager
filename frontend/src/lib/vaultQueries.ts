import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useVaultContext } from "../stores/vaultContext";
import { useActiveVaultKey } from "./orgQueries";
import { decodeEntry, encodeDraft, type VaultDraft, type VaultItem } from "./vault";

/** Query key scoped to the active context so personal and each org cache apart. */
const vaultKey = (orgId: string | null) => ["vault", orgId ?? "personal"] as const;

/** Fetch + decrypt the active vault (personal or an org's shared vault).
 *  One undecryptable row won't sink the whole list. */
export function useVaultItems() {
  const orgId = useVaultContext((s) => s.orgId);
  const { key } = useActiveVaultKey();
  return useQuery({
    queryKey: vaultKey(orgId),
    enabled: !!key,
    queryFn: async (): Promise<VaultItem[]> => {
      const entries = await api.listAllVault(orgId ?? undefined);
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
  const { key } = useActiveVaultKey();
  return useMutation({
    mutationFn: async (draft: VaultDraft) =>
      api.createVault(await encodeDraft(draft, key!), orgId ?? undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId) }),
  });
}

export function useUpdateVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const { key } = useActiveVaultKey();
  return useMutation({
    mutationFn: async ({ id, draft }: { id: string; draft: VaultDraft }) =>
      api.updateVault(id, await encodeDraft(draft, key!)),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId) }),
  });
}

/** Pin/unpin via the dedicated endpoint — no re-encryption, no history entry. */
export function useTogglePin() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  return useMutation({
    mutationFn: (item: VaultItem) => api.setPin(item.id, !item.pinned),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId) }),
  });
}

export function useDeleteVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  return useMutation({
    mutationFn: (id: string) => api.deleteVault(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId) }),
  });
}

/** Dev helper: create several entries in the active context, then refresh once. */
export function useCreateManyVault() {
  const qc = useQueryClient();
  const orgId = useVaultContext((s) => s.orgId);
  const { key } = useActiveVaultKey();
  return useMutation({
    mutationFn: async (drafts: VaultDraft[]) => {
      for (const draft of drafts)
        await api.createVault(await encodeDraft(draft, key!), orgId ?? undefined);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: vaultKey(orgId) }),
  });
}
