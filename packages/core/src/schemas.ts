import { z } from "zod";

/** Successful login / 2FA validation: access token (memory) + the account salt.
 *  The wrapped keypair is null for legacy accounts that predate key support. */
export const loginResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  salt: z.string(),
  public_key: z.string().nullable().optional(),
  encrypted_private_key: z.string().nullable().optional(),
  private_key_iv: z.string().nullable().optional(),
});
export type LoginResponse = z.infer<typeof loginResponseSchema>;

/** An organization the current user belongs to, with their role + wrapped org key. */
export const organizationSchema = z.object({
  id: z.string(),
  name: z.string(),
  created_at: z.string(),
  role: z.string(),
  // Null while the user is pending confirmation (no org key access yet).
  wrapped_org_key: z.string().nullable().optional(),
  member_write: z.boolean(),
});
export type Organization = z.infer<typeof organizationSchema>;

export const orgMemberSchema = z.object({
  user_id: z.string(),
  email: z.string(),
  role: z.string(),
  created_at: z.string(),
  confirmed: z.boolean(),
});
export type OrgMember = z.infer<typeof orgMemberSchema>;

export const invitationSchema = z.object({
  id: z.string(),
  email: z.string(),
  role: z.string(),
  status: z.string(),
  created_at: z.string(),
  expires_at: z.string(),
});
export type Invitation = z.infer<typeof invitationSchema>;

export const collectionSchema = z.object({
  id: z.string(),
  name: z.string(),
  created_at: z.string(),
  wrapped_collection_key: z.string(),
});
export type Collection = z.infer<typeof collectionSchema>;

export const collectionMemberSchema = z.object({
  user_id: z.string(),
  email: z.string(),
  created_at: z.string(),
});
export type CollectionMember = z.infer<typeof collectionMemberSchema>;

export const orgAuditEntrySchema = z.object({
  id: z.string(),
  actor_email: z.string().nullable().optional(),
  event_type: z.string(),
  event_metadata: z.record(z.unknown()).nullable().optional(),
  created_at: z.string().nullable().optional(),
});
export type OrgAuditEntry = z.infer<typeof orgAuditEntrySchema>;

export const invitationLookupSchema = z.object({
  org_id: z.string(),
  org_name: z.string(),
  role: z.string(),
  email: z.string(),
  status: z.string(),
  expired: z.boolean(),
});
export type InvitationLookup = z.infer<typeof invitationLookupSchema>;

export const publicKeySchema = z.object({
  user_id: z.string(),
  email: z.string(),
  public_key: z.string(),
});
export type PublicKey = z.infer<typeof publicKeySchema>;

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
  org_id: z.string().nullable().optional(),
  collection_id: z.string().nullable().optional(),
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
