import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

const PROFILE_KEY = ["profile"] as const;
const RECOVERY_STATUS_KEY = ["recovery-status"] as const;

/** The signed-in user's profile, including whether 2FA is enabled. */
export function useProfile() {
  return useQuery({
    queryKey: PROFILE_KEY,
    queryFn: () => api.getProfile(),
  });
}

/** Remaining one-time recovery codes. Only meaningful once 2FA is on. */
export function useRecoveryStatus(enabled: boolean) {
  return useQuery({
    queryKey: RECOVERY_STATUS_KEY,
    queryFn: () => api.recoveryStatus(),
    enabled,
  });
}

/** Confirm a TOTP code and switch 2FA on. Returns the recovery codes. */
export function useVerify2fa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.verify2fa(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROFILE_KEY });
      qc.invalidateQueries({ queryKey: RECOVERY_STATUS_KEY });
    },
  });
}

/** Turn 2FA off with a current TOTP code. */
export function useDisable2fa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.disable2fa(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROFILE_KEY });
      qc.invalidateQueries({ queryKey: RECOVERY_STATUS_KEY });
    },
  });
}
