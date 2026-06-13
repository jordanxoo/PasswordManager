export {
  generateSalt,
  deriveAccount,
  encryptEntry,
  decryptEntry,
  bytesToBase64,
  base64ToBytes,
  PBKDF2_ITERATIONS,
  generateKeypair,
  exportPublicKey,
  importPublicKey,
  wrapKeypair,
  unwrapPrivateKey,
  generateOrgKey,
  wrapOrgKey,
  unwrapOrgKey,
} from "./crypto";
export type { DerivedAccount, EncryptedPayload, WrappedKeypair } from "./crypto";

export { createApiClient, ApiError } from "./api";
export type { ApiClient, VaultInput, LoginResult } from "./api";

export {
  loginResponseSchema,
  profileSchema,
  twoFactorSetupSchema,
  recoveryCodesSchema,
  recoveryStatusSchema,
  vaultEntrySchema,
  vaultPageSchema,
  organizationSchema,
  orgMemberSchema,
  publicKeySchema,
} from "./schemas";
export type {
  LoginResponse,
  Profile,
  TwoFactorSetup,
  RecoveryCodes,
  RecoveryStatus,
  VaultEntry,
  VaultPage,
  Organization,
  OrgMember,
  PublicKey,
} from "./schemas";
