"""Select entities for AmpPilot."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CHARGING_MODES,
    CONF_VEHICLE_1,
    CONF_VEHICLE_2,
    CONF_VEHICLE_NAME,
    DISTRIBUTION_MODES,
    DISTRIBUTION_PRIORITY_ONLY,
    DISTRIBUTION_PRIORITY_THEN_SPLIT,
    DISTRIBUTION_SIMULTANEOUS,
    DOMAIN,
    MODE_BOOST,
    MODE_OFF,
    MODE_SCHEDULED,
    MODE_SOLAR,
)
from .coordinator import AmpPilotCoordinator

if TYPE_CHECKING:
    from . import AmpPilotConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmpPilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpPilot select entities."""
    coordinator = entry.runtime_data
    config = entry.data

    _LOGGER.debug("Setting up AmpPilot select entities")

    entities: list[SelectEntity] = [
        AmpPilotChargingModeSelect(coordinator, entry),
        AmpPilotDistributionModeSelect(coordinator, entry),
    ]

    # Add priority vehicle select if we have 2 vehicles
    if config.get(CONF_VEHICLE_2):
        entities.append(AmpPilotPriorityVehicleSelect(coordinator, entry))

    _LOGGER.info("Adding %d select entities", len(entities))
    async_add_entities(entities)


class AmpPilotSelectBase(CoordinatorEntity[AmpPilotCoordinator], SelectEntity):
    """Base class for AmpPilot select entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        select_key: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{select_key}"
        self._entry = entry
        self._select_key = select_key

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


class AmpPilotChargingModeSelect(AmpPilotSelectBase):
    """Select entity for charging mode."""

    _attr_icon = "mdi:ev-station"
    _attr_translation_key = "charging_mode"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry, "charging_mode")
        self._attr_name = "Charging Mode"
        self._attr_options = [
            MODE_OFF,
            MODE_SOLAR,
            MODE_SCHEDULED,
            MODE_BOOST,
        ]

    @property
    def current_option(self) -> str | None:
        """Return the current mode."""
        return self.coordinator.data.charging_mode

    async def async_select_option(self, option: str) -> None:
        """Set the charging mode."""
        _LOGGER.debug("Setting charging mode to %s", option)
        await self.coordinator.async_set_charging_mode(option)


class AmpPilotDistributionModeSelect(AmpPilotSelectBase):
    """Select entity for distribution mode."""

    _attr_icon = "mdi:arrow-split-vertical"
    _attr_translation_key = "distribution_mode"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry, "distribution_mode")
        self._attr_name = "Distribution Mode"
        self._attr_options = [
            DISTRIBUTION_SIMULTANEOUS,
            DISTRIBUTION_PRIORITY_THEN_SPLIT,
            DISTRIBUTION_PRIORITY_ONLY,
        ]

    @property
    def current_option(self) -> str | None:
        """Return the current mode."""
        return self.coordinator.data.distribution_mode

    async def async_select_option(self, option: str) -> None:
        """Set the distribution mode."""
        _LOGGER.debug("Setting distribution mode to %s", option)
        await self.coordinator.async_set_distribution_mode(option)


class AmpPilotPriorityVehicleSelect(AmpPilotSelectBase):
    """Select entity for priority vehicle."""

    _attr_icon = "mdi:car-electric"
    _attr_translation_key = "priority_vehicle"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry, "priority_vehicle")
        self._attr_name = "Priority Vehicle"

        # Get vehicle names from config
        v1_config = entry.data.get(CONF_VEHICLE_1, {})
        v2_config = entry.data.get(CONF_VEHICLE_2, {})
        v1_name = v1_config.get(CONF_VEHICLE_NAME, "Vehicle 1")
        v2_name = v2_config.get(CONF_VEHICLE_NAME, "Vehicle 2")

        # Map display names to internal keys and vice versa
        self._name_to_key = {
            v1_name: "vehicle_1",
            v2_name: "vehicle_2",
        }
        self._key_to_name = {
            "vehicle_1": v1_name,
            "vehicle_2": v2_name,
        }
        # Use vehicle names as display options
        self._attr_options = [v1_name, v2_name]

    @property
    def current_option(self) -> str | None:
        """Return the current priority vehicle (as display name)."""
        key = self.coordinator.data.priority_vehicle
        return self._key_to_name.get(key, key)

    async def async_select_option(self, option: str) -> None:
        """Set the priority vehicle (from display name)."""
        # Convert display name to internal key
        key = self._name_to_key.get(option, option)
        _LOGGER.debug("Setting priority vehicle to %s (from option %s)", key, option)
        await self.coordinator.async_set_priority_vehicle(key)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "vehicle_names": self._key_to_name,
        }
