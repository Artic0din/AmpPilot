"""Number entities for AmpPilot."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfTime, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_VEHICLE_1,
    CONF_VEHICLE_2,
    CONF_MIN_AMPS,
    CONF_MAX_AMPS,
    DEFAULT_MIN_AMPS,
    DEFAULT_MAX_AMPS,
    DOMAIN,
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
    """Set up AmpPilot number entities."""
    coordinator = entry.runtime_data
    config = entry.data

    _LOGGER.debug("Setting up AmpPilot number entities")

    entities: list[NumberEntity] = [
        AmpPilotEnableThresholdNumber(coordinator, entry),
        AmpPilotDisableThresholdNumber(coordinator, entry),
        AmpPilotEnableDelayNumber(coordinator, entry),
        AmpPilotDisableDelayNumber(coordinator, entry),
        AmpPilotHouseholdBufferNumber(coordinator, entry),
        AmpPilotMinBatterySocNumber(coordinator, entry),
        AmpPilotVehicleMinAmpsNumber(coordinator, entry, "vehicle_1"),
        AmpPilotVehicleMaxAmpsNumber(coordinator, entry, "vehicle_1"),
    ]

    # Add vehicle 2 numbers if configured
    if config.get(CONF_VEHICLE_2):
        entities.extend([
            AmpPilotVehicleMinAmpsNumber(coordinator, entry, "vehicle_2"),
            AmpPilotVehicleMaxAmpsNumber(coordinator, entry, "vehicle_2"),
        ])

    _LOGGER.info("Adding %d number entities", len(entities))
    async_add_entities(entities)


class AmpPilotNumberBase(CoordinatorEntity[AmpPilotCoordinator], NumberEntity):
    """Base class for AmpPilot number entities."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        number_key: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{number_key}"
        self._entry = entry
        self._number_key = number_key

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


class AmpPilotEnableThresholdNumber(AmpPilotNumberBase):
    """Number entity for enable threshold."""

    _attr_native_min_value = 0
    _attr_native_max_value = 10000
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:flash"
    _attr_translation_key = "enable_threshold"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, "enable_threshold")
        self._attr_name = "Enable Threshold"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.enable_threshold

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting enable threshold to %.0f W", value)
        await self.coordinator.async_set_threshold("enable", value)


class AmpPilotDisableThresholdNumber(AmpPilotNumberBase):
    """Number entity for disable threshold."""

    _attr_native_min_value = -5000
    _attr_native_max_value = 5000
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:flash-off"
    _attr_translation_key = "disable_threshold"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, "disable_threshold")
        self._attr_name = "Disable Threshold"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.disable_threshold

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting disable threshold to %.0f W", value)
        await self.coordinator.async_set_threshold("disable", value)


class AmpPilotEnableDelayNumber(AmpPilotNumberBase):
    """Number entity for enable delay."""

    _attr_native_min_value = 0
    _attr_native_max_value = 600
    _attr_native_step = 10
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer"
    _attr_translation_key = "enable_delay"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, "enable_delay")
        self._attr_name = "Enable Delay"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.enable_delay

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting enable delay to %.0f s", value)
        await self.coordinator.async_set_threshold("enable_delay", value)


class AmpPilotDisableDelayNumber(AmpPilotNumberBase):
    """Number entity for disable delay."""

    _attr_native_min_value = 0
    _attr_native_max_value = 600
    _attr_native_step = 10
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-off"
    _attr_translation_key = "disable_delay"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, "disable_delay")
        self._attr_name = "Disable Delay"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.disable_delay

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting disable delay to %.0f s", value)
        await self.coordinator.async_set_threshold("disable_delay", value)


class AmpPilotHouseholdBufferNumber(AmpPilotNumberBase):
    """Number entity for household buffer."""

    _attr_native_min_value = 0
    _attr_native_max_value = 2000
    _attr_native_step = 50
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:home-lightning-bolt"
    _attr_translation_key = "household_buffer"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, "household_buffer")
        self._attr_name = "Household Buffer"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.household_buffer

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting household buffer to %.0f W", value)
        await self.coordinator.async_set_threshold("household_buffer", value)


class AmpPilotMinBatterySocNumber(AmpPilotNumberBase):
    """Number entity for minimum battery SoC."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:battery-charging-50"
    _attr_translation_key = "min_battery_soc"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, "min_battery_soc")
        self._attr_name = "Min Battery SoC"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data.min_battery_soc

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting min battery SoC to %.0f%%", value)
        await self.coordinator.async_set_threshold("min_battery_soc", value)


class AmpPilotVehicleMinAmpsNumber(AmpPilotNumberBase):
    """Number entity for vehicle minimum amps."""

    _attr_native_min_value = 1
    _attr_native_max_value = 32
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:current-ac"

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, f"{vehicle}_min_amps")
        self._vehicle = vehicle
        vehicle_num = "1" if vehicle == "vehicle_1" else "2"
        self._attr_name = f"Vehicle {vehicle_num} Min Amps"
        self._attr_translation_key = f"{vehicle}_min_amps"

        # Get current config value
        config_key = CONF_VEHICLE_1 if vehicle == "vehicle_1" else CONF_VEHICLE_2
        v_config = entry.data.get(config_key, {})
        self._config_value = v_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS)

    @property
    def native_value(self) -> float:
        """Return the current value."""
        # For now, return config value since we don't have runtime storage for this
        return self._config_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting %s min amps to %.0f A", self._vehicle, value)
        self._config_value = value
        # Note: This would need to persist to config entry for permanent change


class AmpPilotVehicleMaxAmpsNumber(AmpPilotNumberBase):
    """Number entity for vehicle maximum amps."""

    _attr_native_min_value = 1
    _attr_native_max_value = 80
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:current-ac"

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, f"{vehicle}_max_amps")
        self._vehicle = vehicle
        vehicle_num = "1" if vehicle == "vehicle_1" else "2"
        self._attr_name = f"Vehicle {vehicle_num} Max Amps"
        self._attr_translation_key = f"{vehicle}_max_amps"

        # Get current config value
        config_key = CONF_VEHICLE_1 if vehicle == "vehicle_1" else CONF_VEHICLE_2
        v_config = entry.data.get(config_key, {})
        self._config_value = v_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS)

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._config_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.debug("Setting %s max amps to %.0f A", self._vehicle, value)
        self._config_value = value
        # Note: This would need to persist to config entry for permanent change
