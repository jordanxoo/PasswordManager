import { create } from "zustand";

/**
 * Which vault is currently shown: the personal vault (`orgId === null`) or a
 * specific organization's shared vault. Kept tiny and in-memory; reset on logout.
 */
interface VaultContextState {
  orgId: string | null;
  setOrgId: (orgId: string | null) => void;
}

export const useVaultContext = create<VaultContextState>((set) => ({
  orgId: null,
  setOrgId: (orgId) => set({ orgId }),
}));
