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
        entities.append(ErsteGroupSpendingSensor(coordinator, account_id))
        entities.append(ErsteGroupSpendingRatioSensor(coordinator, account_id))
        entities.append(ErsteGroupFinancialHealthSensor(coordinator, account_id))

    async_add_entities(entities)


class ErsteGroupBalanceSensor(CoordinatorEntity, SensorEntity):
    """Balance sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._account_id = account_id
        account_data = coordinator.data["accounts"][account_id]
        self._attr_name = f"{account_data['friendly_name']} Balance"
        self._attr_unique_id = f"{account_id}_balance"
        self._attr_native_unit_of_measurement = account_data["currency"]

    @property
    def native_value(self) -> float:
        """Return balance."""
        return self.coordinator.data["accounts"][self._account_id]["balance"]["amount"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return attributes."""
        account_data = self.coordinator.data["accounts"][self._account_id]
        return {
            "account_number": account_data["number"],
            "product": account_data.get("product", ""),
        }


class ErsteGroupSpendingSensor(CoordinatorEntity, SensorEntity):
    """Monthly spending sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash-minus"

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._account_id = account_id
        account_data = coordinator.data["accounts"][account_id]
        self._attr_name = f"{account_data['friendly_name']} Monthly Spending"
        self._attr_unique_id = f"{account_id}_spending"
        self._attr_native_unit_of_measurement = account_data["currency"]

    @property
    def native_value(self) -> float:
        """Return spending."""
        return self.coordinator.data["accounts"][self._account_id]["spending"]


class ErsteGroupSpendingRatioSensor(CoordinatorEntity, SensorEntity):
    """Spending/Income ratio sensor (last 30 days)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:percent"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._account_id = account_id
        account_data = coordinator.data["accounts"][account_id]
        self._attr_name = f"{account_data['friendly_name']} Spending Ratio"
        self._attr_unique_id = f"{account_id}_spending_ratio"

    @property
    def native_value(self) -> float:
        """Return spending/income ratio as percentage."""
        return round(self.coordinator.data["accounts"][self._account_id]["spending_ratio"], 1)

    @property
    def extra_state_attributes(self) -> dict:
        """Return attributes."""
        account_data = self.coordinator.data["accounts"][self._account_id]
        return {
            "spending_30d": account_data["spending_30d"],
            "income_30d": account_data["income_30d"],
            "currency": account_data["currency"],
        }


class ErsteGroupFinancialHealthSensor(CoordinatorEntity, SensorEntity):
    """Financial health sensor - safety margin until payday."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator, account_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._account_id = account_id
        account_data = coordinator.data["accounts"][account_id]
        self._attr_name = f"{account_data['friendly_name']} Financial Health"
        self._attr_unique_id = f"{account_id}_financial_health"

    @property
    def native_value(self) -> float:
        """Return safety margin (runway days / days until payday)."""
        account_data = self.coordinator.data["accounts"][self._account_id]
        return round(account_data["safety_margin"], 2)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on status."""
        status = self.coordinator.data["accounts"][self._account_id]["financial_health_status"]
        icons = {
            "excellent": "mdi:cash-100",
            "good": "mdi:cash-check",
            "ok": "mdi:cash",
            "warning": "mdi:alert",
            "danger": "mdi:alert-octagon",
        }
        return icons.get(status, "mdi:help-circle")

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed attributes."""
        account_data = self.coordinator.data["accounts"][self._account_id]
        emoji = account_data["financial_health_emoji"]
        status = account_data["financial_health_status"]
        message = account_data["financial_health_message"]

        return {
            "status": account_data["financial_health_status"],
            "emoji": emoji,
            "message": message,
            "full_message": f"{emoji} {status.upper()}: {message}",
            "runway_days": round(account_data["runway_days"], 1),
            "days_until_payday": account_data["days_until_payday"],
            "daily_burn_rate": round(account_data["daily_burn"], 2),
            "current_balance": account_data["balance"]["amount"],
            "currency": account_data["currency"],
        }
