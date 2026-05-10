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


class Role(enum.Enum):
    USER = "user"
    ADMIN = "admin"