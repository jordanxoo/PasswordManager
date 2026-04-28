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


