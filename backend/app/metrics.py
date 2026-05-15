from prometheus_client import Counter


login_failures_total = Counter(
    "login_failures_total",
    "Failed login attempts"
)

vault_operations_total = Counter(
    "vault_operations_total",
    "Vault CRUD operations by type",
    ["operation"]
)

hibp_cache_hits_total = Counter(
    "hibp_cache_hits_total",
    "HIBP password range responses served from cache"
)
hibp_cache_misses_total = Counter(
    "hibp_cache_misses_total",
    "HIBP password range responses fetched from API"
)