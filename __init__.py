"""The ErsteGroup integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from .const import DOMAIN
from .coordinator import ErsteGroupCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type ErsteGroupConfigEntry = ConfigEntry[ErsteGroupCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ErsteGroupConfigEntry) -> bool:
    """Set up ErsteGroup from a config entry."""
    from .coordinator import ErsteGroupCoordinator

    coordinator = ErsteGroupCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        entry.async_start_reauth(hass)
        return False

    # Use runtime_data instead of hass.data
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ErsteGroupConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
