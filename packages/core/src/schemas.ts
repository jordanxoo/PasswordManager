import { z } from "zod";

/** Successful login / 2FA validation: access token (memory) + the account salt. */
export const loginResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  salt: z.string(),
});
export type LoginResponse = z.infer<typeof loginResponseSchema>;

export const profileSchema = z.object({
  email: z.string(),
  created_at: z.string(),
  totp_enabled: z.boolean(),
  role: z.string(),
});
export type Profile = z.infer<typeof profileSchema>;

/** Returned by /auth/2fa/setup: the TOTP secret + a base64-encoded QR PNG. */
export const twoFactorSetupSchema = z.object({
  secret: z.string(),
  qr_code: z.string(),
});
export type TwoFactorSetup = z.infer<typeof twoFactorSetupSchema>;

/** Returned after enabling 2FA or regenerating codes: the recovery codes. */
export const recoveryCodesSchema = z.object({
  recovery_codes: z.array(z.string()),
  message: z.string().optional(),
});
export type RecoveryCodes = z.infer<typeof recoveryCodesSchema>;

/** Returned by /auth/2fa/recovery/status. */
export const recoveryStatusSchema = z.object({
  remaining: z.number(),
  total: z.number(),
});
export type RecoveryStatus = z.infer<typeof recoveryStatusSchema>;

/** A vault row as stored server-side. `encrypted`/`iv` are opaque ciphertext. */
export const vaultEntrySchema = z.object({
  id: z.string(),
  encrypted: z.string(),
  iv: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  expires_at: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  pinned: z.boolean(),
});
export type VaultEntry = z.infer<typeof vaultEntrySchema>;

export const vaultPageSchema = z.object({
  items: z.array(vaultEntrySchema),
  next_cursor: z.string().nullable().optional(),
  has_next: z.boolean(),
});
export type VaultPage = z.infer<typeof vaultPageSchema>;

export const vaultHistorySchema = z.object({
  id: z.string(),
  vault_id: z.string(),
  encrypted: z.string(),
  iv: z.string(),
  changed_at: z.string(),
});
export type VaultHistoryEntry = z.infer<typeof vaultHistorySchema>;
