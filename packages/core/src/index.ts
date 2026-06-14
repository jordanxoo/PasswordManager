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
  organizationSchema,
  orgMemberSchema,
  publicKeySchema,
  invitationSchema,
  invitationLookupSchema,
  collectionSchema,
  collectionMemberSchema,
  orgAuditEntrySchema,
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
  Organization,
  OrgMember,
  PublicKey,
  Invitation,
  InvitationLookup,
  Collection,
  CollectionMember,
  OrgAuditEntry,
} from "./schemas";
