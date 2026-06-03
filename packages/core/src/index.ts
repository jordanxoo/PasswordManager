export {
  generateSalt,
  deriveAccount,
  encryptEntry,
  decryptEntry,
  bytesToBase64,
  base64ToBytes,
  PBKDF2_ITERATIONS,
} from "./crypto";
export type { DerivedAccount, EncryptedPayload } from "./crypto";

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
} from "./schemas";
export type {
  LoginResponse,
  Profile,
  TwoFactorSetup,
  RecoveryCodes,
  RecoveryStatus,
  VaultEntry,
  VaultPage,
} from "./schemas";
