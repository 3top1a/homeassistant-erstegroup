"""Constants for ErsteGroup integration."""
DOMAIN = "erstegroup"

# Configuration keys
CONF_API_KEY = "api_key"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_API_BASE_URL = "api_base_url"
CONF_IDP_BASE_URL = "idp_base_url"
CONF_PAYDAY = "payday"

# Default URLs
DEFAULT_API_BASE_URL = "https://webapi.developers.erstegroup.com/api/csas/public/sandbox/v3/accounts"
DEFAULT_IDP_BASE_URL = "https://webapi.developers.erstegroup.com/api/csas/sandbox/v1/sandbox-idp"
DEFAULT_PAYDAY = 1

# API endpoints
API_ACCOUNTS = "/my/accounts"
API_BALANCES = "/my/accounts/{account_id}/balance"
API_TRANSACTIONS = "/my/accounts/{account_id}/transactions"

# Update interval
UPDATE_INTERVAL = 600  # 10 minutes
