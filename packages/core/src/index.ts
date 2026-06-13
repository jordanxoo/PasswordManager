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
  generatePassword,
  alphabetSize,
  entropyBits,
  strength,
  DEFAULT_GENERATOR_OPTIONS,
  MIN_LENGTH,
  MAX_LENGTH,
} from "./generator";
export type { GeneratorOptions, StrengthLevel } from "./generator";

export {
  loginResponseSchema,
  profileSchema,
  twoFactorSetupSchema,
  recoveryCodesSchema,
  recoveryStatusSchema,
  vaultEntrySchema,
  vaultPageSchema,
  vaultHistorySchema,
} from "./schemas";
export type {
  LoginResponse,
  Profile,
  TwoFactorSetup,
  RecoveryCodes,
  RecoveryStatus,
  VaultEntry,
  VaultPage,
  VaultHistoryEntry,
} from "./schemas";
