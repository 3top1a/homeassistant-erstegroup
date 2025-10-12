"""The ErsteGroup integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType
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
    DEFAULT_PAYDAY
)
from .coordinator import ErsteGroupCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
                vol.Required(CONF_REFRESH_TOKEN): cv.string,
                vol.Optional(CONF_API_BASE_URL, default=DEFAULT_API_BASE_URL): cv.string,
                vol.Optional(CONF_IDP_BASE_URL, default=DEFAULT_IDP_BASE_URL): cv.string,
                vol.Optional(CONF_PAYDAY, default=DEFAULT_PAYDAY): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=31)
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ErsteGroup component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    coordinator = ErsteGroupCoordinator(
        hass,
        api_key=conf[CONF_API_KEY],
        api_base_url=conf[CONF_API_BASE_URL],
        idp_base_url=conf[CONF_IDP_BASE_URL],
        client_id=conf[CONF_CLIENT_ID],
        client_secret=conf[CONF_CLIENT_SECRET],
        refresh_token=conf[CONF_REFRESH_TOKEN],
        payday=conf[CONF_PAYDAY],
    )

    # Use async_refresh for YAML-only integrations
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["coordinator"] = coordinator

    # Load sensor platform
    await async_load_platform(hass, "sensor", DOMAIN, {}, config)

    return True
