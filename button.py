"""Button platform for ErsteGroup."""
from __future__ import annotations

import logging
from urllib.parse import urlencode

from homeassistant.components.button import ButtonEntity
from homeassistant.components.persistent_notification import async_create
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN, CONF_CLIENT_ID, OAUTH_SCOPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up ErsteGroup buttons."""
    conf = hass.data[DOMAIN]["config"]

    entities = [
        ErsteGroupReauthButton(hass, conf),
    ]

    async_add_entities(entities)


class ErsteGroupReauthButton(ButtonEntity):
    """Button to initiate re-authentication."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        """Initialize."""
        self.hass = hass
        self._config = config
        self._attr_name = "ErsteGroup Re-authenticate"
        self._attr_unique_id = "erstegroup_reauth_button"
        self._attr_icon = "mdi:key-refresh"

    async def async_press(self) -> None:
        """Handle button press - open auth URL."""
        # Build auth URL
        idp_base = self._config["idp_base_url"].rstrip("/")
        params = {
            "client_id": self._config[CONF_CLIENT_ID],
            "redirect_uri": "https://example.com",
            "response_type": "code",
            "access_type": "offline",
            "scope": " ".join(OAUTH_SCOPES),
            "prompt": "consent",
            "state": "csas-reauth",
        }

        auth_url = f"{idp_base}/auth?{urlencode(params)}"

        # Log the URL
        _LOGGER.info("Re-authentication URL: %s", auth_url)

        # Create a persistent notification with the URL
        async_create(
            self.hass,
            f"Click here to re-authenticate:\n\n[Authenticate with ErsteGroup]({auth_url})\n\n"
            f"After authentication, you'll be redirected to https://example.com. "
            f"Once you get redirected, copy the token in the URL (?code=<token>) and paste it into the configuration file.",
            title="ErsteGroup Re-authentication Required",
            notification_id="erstegroup_reauth",
        )
