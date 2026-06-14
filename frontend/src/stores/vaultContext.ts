import { create } from "zustand";

/**
 * Which vault is shown: personal (`orgId === null`), an org's "General" vault
 * (`orgId` set, `collectionId === null`), or a specific collection within an org.
 * Kept tiny and in-memory; reset on logout.
 */
interface VaultContextState {
  orgId: string | null;
  collectionId: string | null;
  /** Switch org — always resets the collection to the org's "General". */
  setOrgId: (orgId: string | null) => void;
  setCollectionId: (collectionId: string | null) => void;
}

export const useVaultContext = create<VaultContextState>((set) => ({
  orgId: null,
  collectionId: null,
  setOrgId: (orgId) => set({ orgId, collectionId: null }),
  setCollectionId: (collectionId) => set({ collectionId }),
}));
