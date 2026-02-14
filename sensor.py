"""Sensor platform for ErsteGroup."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import ErsteGroupConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ErsteGroupConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ErsteGroup sensors."""
    coordinator = entry.runtime_data

    # Wait for first successful update
    if not coordinator.data:
        return

    entities = []

    for account_id, account_data in coordinator.data.get("accounts", {}).items():
        entities.append(ErsteGroupBalanceSensor(coordinator, account_id))

    async_add_entities(entities)


class ErsteGroupBalanceSensor(CoordinatorEntity, SensorEntity):
    """Balance sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize."""

        # TODO Rework
        # - Make unique id actually unique for every separate bank account
        # - Do processing of data here
        # - Expose history too, not just latest number

        super().__init__(coordinator)
        self._account_id = account_id
        account_data = coordinator.data["accounts"][account_id]
        self._attr_name = f"{account_data['friendly_name']} Balance"
        self._attr_unique_id = f"{account_id}_balance"
        self._attr_native_unit_of_measurement = account_data["currency"]

    @property
    def native_value(self) -> float:
        """Return balance."""
        return self.coordinator.data["accounts"][self._account_id]["balance"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return attributes."""
        return self.coordinator.data["accounts"][self._account_id]
