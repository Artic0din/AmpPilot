"""Switch entities for AmpPilot."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VEHICLE_2, DOMAIN
from .coordinator import AmpPilotCoordinator

if TYPE_CHECKING:
    from . import AmpPilotConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmpPilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpPilot switch entities."""
    coordinator = entry.runtime_data
    config = entry.data

    _LOGGER.debug("Setting up AmpPilot switch entities")

    entities: list[SwitchEntity] = [
        AmpPilotSolarChargingSwitch(coordinator, entry),
        AmpPilotScheduledChargingSwitch(coordinator, entry),
        AmpPilotVehicleEnabledSwitch(coordinator, entry, "vehicle_1"),
    ]

    # Add vehicle 2 switch if configured
    if config.get(CONF_VEHICLE_2):
        entities.append(AmpPilotVehicleEnabledSwitch(coordinator, entry, "vehicle_2"))

    _LOGGER.info("Adding %d switch entities", len(entities))
    async_add_entities(entities)


class AmpPilotSwitchBase(CoordinatorEntity[AmpPilotCoordinator], SwitchEntity):
    """Base class for AmpPilot switches."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        switch_key: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{switch_key}"
        self._entry = entry
        self._switch_key = switch_key

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "AmpPilot",
            "manufacturer": "AmpPilot",
            "model": "Solar EV Charger",
            "sw_version": "0.1.0",
        }


class AmpPilotSolarChargingSwitch(AmpPilotSwitchBase):
    """Switch for enabling/disabling solar charging."""

    _attr_icon = "mdi:solar-power"
    _attr_translation_key = "solar_charging"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, "solar_charging")
        self._attr_name = "Solar Charging"

    @property
    def is_on(self) -> bool:
        """Return true if solar charging is enabled."""
        return self.coordinator.data.solar_charging_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on solar charging."""
        _LOGGER.debug("Enabling solar charging")
        await self.coordinator.async_set_solar_charging_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off solar charging."""
        _LOGGER.debug("Disabling solar charging")
        await self.coordinator.async_set_solar_charging_enabled(False)


class AmpPilotScheduledChargingSwitch(AmpPilotSwitchBase):
    """Switch for enabling/disabling scheduled charging."""

    _attr_icon = "mdi:clock-outline"
    _attr_translation_key = "scheduled_charging"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, "scheduled_charging")
        self._attr_name = "Scheduled Charging"

    @property
    def is_on(self) -> bool:
        """Return true if scheduled charging is enabled."""
        return self.coordinator.data.scheduled_charging_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on scheduled charging."""
        _LOGGER.debug("Enabling scheduled charging")
        await self.coordinator.async_set_scheduled_charging_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off scheduled charging."""
        _LOGGER.debug("Disabling scheduled charging")
        await self.coordinator.async_set_scheduled_charging_enabled(False)


class AmpPilotVehicleEnabledSwitch(AmpPilotSwitchBase):
    """Switch for enabling/disabling a vehicle."""

    _attr_icon = "mdi:car-electric"

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, f"{vehicle}_enabled")
        self._vehicle = vehicle
        vehicle_num = "1" if vehicle == "vehicle_1" else "2"
        self._attr_name = f"Vehicle {vehicle_num} Enabled"
        self._attr_translation_key = f"{vehicle}_enabled"

    @property
    def is_on(self) -> bool:
        """Return true if vehicle is enabled."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return vehicle_data.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the vehicle."""
        _LOGGER.debug("Enabling %s", self._vehicle)
        await self.coordinator.async_set_vehicle_enabled(self._vehicle, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the vehicle."""
        _LOGGER.debug("Disabling %s", self._vehicle)
        await self.coordinator.async_set_vehicle_enabled(self._vehicle, False)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return {
            "is_connected": vehicle_data.is_connected,
            "is_charging": vehicle_data.is_charging,
            "current_power": vehicle_data.current_power,
        }
