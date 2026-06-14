import enum


class EventType(enum.Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    ACCOUNT_LOCKED = "account_locked"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    REGISTER = "register"
    
    VAULT_READ = "vault_read"
    VAULT_CREATE = "vault_create"
    VAULT_UPDATE = "vault_update"
    VAULT_DELETE =  "vault_delete"

    TWO_FA_ENABLED = "two_fa_enabled"
    TWO_FA_DISABLED = "two_fa_disabled"
    TWO_FA_FAILED = "two_fa_failed"
    TWO_FA_SUCCESS = "two_fa_success"

    EMAIL_CHANGED = "email_changed"
    PASSWORD_CHANGED = "password_changed"
    ACCOUNT_DELETED = "account_deleted"
    SESSION_REVOKED = "session_revoked"

    HIBP_PASSWORD_CHECK = "hibp_password_check"
    HIBP_EMAIl_CHECK = "hibp_email_check"

    RECOVERY_CODES_GENERATED = "recovery_codes_generated"
    RECOVERY_CODES_USED = "recovery_codes_used"
    RECOVERY_CODE_FAILED = "recovery_code_failed"

    ORG_CREATED = "org_created"
    ORG_MEMBER_ADDED = "org_member_added"
    ORG_MEMBER_REMOVED = "org_member_removed"
    ORG_ROLE_CHANGED = "org_role_changed"
    ORG_KEY_ROTATED = "org_key_rotated"

    COLLECTION_CREATED = "collection_created"
    COLLECTION_DELETED = "collection_deleted"
    COLLECTION_ACCESS_GRANTED = "collection_access_granted"
    COLLECTION_ACCESS_REVOKED = "collection_access_revoked"


class Role(enum.Enum):
    USER = "user"
    ADMIN = "admin"


class OrgRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Category(enum.Enum):
    SOCIAL = "social"
    WORK = "work"
    FINANCE = "finance"
    EMAIL = "email"
    OTHER = "other"

