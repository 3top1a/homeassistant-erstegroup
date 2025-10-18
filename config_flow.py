"""Config flow for ErsteGroup integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any
from urllib.parse import urlencode, parse_qs, urlparse

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_API_BASE_URL,
    CONF_IDP_BASE_URL,
    DEFAULT_API_BASE_URL,
    DEFAULT_IDP_BASE_URL,
    CONF_PAYDAY,
    DEFAULT_PAYDAY,
    OAUTH_SCOPES
)

_LOGGER = logging.getLogger(__name__)

from homeassistant.helpers.selector import TextSelector

@config_entries.HANDLERS.register(DOMAIN)
class ErsteGroupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ErsteGroup."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._api_key: str | None = None
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._api_base_url: str | None = None
        self._idp_base_url: str | None = None
        self._payday: int = DEFAULT_PAYDAY

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 1: Enter credentials."""
        errors = {}

        if user_input is not None:
            # Check for existing entries with same API base URL
            self._async_abort_entries_match({
                CONF_API_BASE_URL: user_input[CONF_API_BASE_URL]
            })

            self._api_key = user_input[CONF_API_KEY]
            self._client_id = user_input[CONF_CLIENT_ID]
            self._client_secret = user_input[CONF_CLIENT_SECRET]
            self._api_base_url = user_input[CONF_API_BASE_URL]
            self._idp_base_url = user_input[CONF_IDP_BASE_URL]
            self._payday = user_input.get(CONF_PAYDAY, DEFAULT_PAYDAY)

            return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(CONF_API_BASE_URL, default=DEFAULT_API_BASE_URL): str,
                vol.Required(CONF_IDP_BASE_URL, default=DEFAULT_IDP_BASE_URL): str,
                vol.Optional(CONF_PAYDAY, default=DEFAULT_PAYDAY): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=31)
                ),
            }),
            errors=errors,
        )

    async def async_step_auth(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step 2: Authenticate and get redirect URL."""
        errors = {}

        if user_input is not None:
            redirect_url = user_input.get("redirect_url", "")

            if not redirect_url:
                errors["base"] = "no_redirect_url"
            else:
                try:
                    parsed = urlparse(redirect_url)
                    params = parse_qs(parsed.query)

                    if "code" not in params:
                        errors["base"] = "no_code_in_url"
                    else:
                        auth_code = params["code"][0]
                        return await self._exchange_token(auth_code)

                except Exception as err:
                    _LOGGER.error("Failed to parse redirect URL: %s", err)
                    errors["base"] = "invalid_url"

        # Build auth URL
        auth_params = {
            "client_id": self._client_id,
            "response_type": "code",
            "access_type": "offline",
            "scope": " ".join(OAUTH_SCOPES),
            "redirect_uri": "https://example.com",
            "prompt": "consent",
            "state": "csas-setup",
        }

        auth_url = f"{self._idp_base_url}/auth?{urlencode(auth_params)}"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({
                vol.Required("redirect_url"): TextSelector({"type": "text", "multiline": True}),
            }),
            errors=errors,
            description_placeholders={
                "oauth_url": auth_url,
            }
        )

    async def _exchange_token(self, auth_code: str) -> FlowResult:
        """Exchange auth code for tokens."""
        session = async_get_clientsession(self.hass)

        try:
            url = f"{self._idp_base_url}/token"
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": "https://example.com",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }

            async with session.post(url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Token exchange failed: %s", error_text)
                    return self.async_abort(reason="token_exchange_failed")

                token_data = await response.json()
                refresh_token = token_data.get("refresh_token")

                if not refresh_token:
                    return self.async_abort(reason="no_refresh_token")

                # Create config entry
                return self.async_create_entry(
                    title="ErsteGroup Bank",
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_CLIENT_ID: self._client_id,
                        CONF_CLIENT_SECRET: self._client_secret,
                        CONF_REFRESH_TOKEN: refresh_token,
                        CONF_API_BASE_URL: self._api_base_url,
                        CONF_IDP_BASE_URL: self._idp_base_url,
                        CONF_PAYDAY: self._payday,
                    }
                )

        except Exception as err:
            _LOGGER.error("Error during token exchange: %s", err)
            return self.async_abort(reason="unknown_error")

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth confirmation."""
        errors = {}

        if user_input is not None:
            redirect_url = user_input.get("redirect_url", "")

            if not redirect_url:
                errors["base"] = "no_redirect_url"
            else:
                try:
                    parsed = urlparse(redirect_url)
                    params = parse_qs(parsed.query)

                    if "code" not in params:
                        errors["base"] = "no_code_in_url"
                    else:
                        return await self._reauth_exchange(params["code"][0])

                except Exception as err:
                    _LOGGER.error("Failed to parse redirect URL: %s", err)
                    errors["base"] = "invalid_url"

        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        auth_params = {
            "client_id": entry.data[CONF_CLIENT_ID],
            "redirect_uri": "https://example.com",
            "response_type": "code",
            "access_type": "offline",
            "scope": " ".join(OAUTH_SCOPES),
            "prompt": "consent",
            "state": "csas-reauth",
        }

        auth_url = f"{entry.data[CONF_IDP_BASE_URL]}/auth?{urlencode(auth_params)}"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required("redirect_url"): str,
            }),
            errors=errors,
            description_placeholders={
                "auth_url": auth_url,
            }
        )

    async def _reauth_exchange(self, auth_code: str) -> FlowResult:
        """Exchange auth code during reauth."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        session = async_get_clientsession(self.hass)

        try:
            url = f"{entry.data[CONF_IDP_BASE_URL]}/token"
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": "https://example.com",
                "client_id": entry.data[CONF_CLIENT_ID],
                "client_secret": entry.data[CONF_CLIENT_SECRET],
            }

            async with session.post(url, data=data) as response:
                if response.status != 200:
                    return self.async_abort(reason="token_exchange_failed")

                token_data = await response.json()
                new_refresh_token = token_data.get("refresh_token")

                if not new_refresh_token:
                    return self.async_abort(reason="no_refresh_token")

                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_REFRESH_TOKEN: new_refresh_token,
                    }
                )

                await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reauth_successful")

        except Exception as err:
            _LOGGER.error("Error during reauth: %s", err)
            return self.async_abort(reason="unknown_error")
