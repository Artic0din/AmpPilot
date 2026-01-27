"""Sensor entities for AmpPilot."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BATTERY_SOC_ENTITY,
    CONF_VEHICLE_1,
    CONF_VEHICLE_2,
    CONF_VEHICLE_SOC_ENTITY,
    DOMAIN,
)
from .coordinator import AmpPilotCoordinator, AmpPilotData

if TYPE_CHECKING:
    from . import AmpPilotConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmpPilotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpPilot sensor entities."""
    coordinator = entry.runtime_data
    config = entry.data

    _LOGGER.debug("Setting up AmpPilot sensor entities")

    entities: list[SensorEntity] = [
        # System sensors
        AmpPilotSurplusSensor(coordinator, entry),
        AmpPilotStatusSensor(coordinator, entry),
        # Power monitoring sensors (always added for dashboard)
        AmpPilotSolarPowerSensor(coordinator, entry),
        AmpPilotGridPowerSensor(coordinator, entry),
        AmpPilotHomeLoadSensor(coordinator, entry),
        # Vehicle 1 sensors
        AmpPilotVehiclePowerSensor(coordinator, entry, "vehicle_1"),
        AmpPilotVehicleAmpsSensor(coordinator, entry, "vehicle_1"),
        AmpPilotVehicleEnergySessionSensor(coordinator, entry, "vehicle_1"),
        AmpPilotVehicleEnergyTodaySensor(coordinator, entry, "vehicle_1"),
    ]

    # Add battery sensors if battery is configured
    if config.get(CONF_BATTERY_SOC_ENTITY):
        entities.extend([
            AmpPilotBatterySocSensor(coordinator, entry),
            AmpPilotBatteryPowerSensor(coordinator, entry),
        ])

    # Add vehicle 1 SoC sensor if configured
    v1_config = config.get(CONF_VEHICLE_1, {})
    if v1_config.get(CONF_VEHICLE_SOC_ENTITY):
        entities.append(AmpPilotVehicleSocSensor(coordinator, entry, "vehicle_1"))

    # Add vehicle 2 sensors if configured
    v2_config = config.get(CONF_VEHICLE_2)
    if v2_config:
        entities.extend([
            AmpPilotVehiclePowerSensor(coordinator, entry, "vehicle_2"),
            AmpPilotVehicleAmpsSensor(coordinator, entry, "vehicle_2"),
            AmpPilotVehicleEnergySessionSensor(coordinator, entry, "vehicle_2"),
            AmpPilotVehicleEnergyTodaySensor(coordinator, entry, "vehicle_2"),
        ])
        # Add vehicle 2 SoC sensor if configured
        if v2_config.get(CONF_VEHICLE_SOC_ENTITY):
            entities.append(AmpPilotVehicleSocSensor(coordinator, entry, "vehicle_2"))

    _LOGGER.info("Adding %d sensor entities", len(entities))
    async_add_entities(entities)


class AmpPilotSensorBase(CoordinatorEntity[AmpPilotCoordinator], SensorEntity):
    """Base class for AmpPilot sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        sensor_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{sensor_key}"
        self._entry = entry
        self._sensor_key = sensor_key

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


class AmpPilotSurplusSensor(AmpPilotSensorBase):
    """Sensor for available solar surplus."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:solar-power"
    _attr_translation_key = "available_surplus"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "available_surplus")
        self._attr_name = "Available Surplus"

    @property
    def native_value(self) -> float:
        """Return the available surplus."""
        return round(self.coordinator.data.available_surplus, 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        data = self.coordinator.data
        return {
            "raw_surplus": round(data.raw_surplus, 0),
            "solar_power": round(data.solar_power, 0),
            "grid_power": round(data.grid_power, 0),
            "home_load": round(data.home_load, 0),
            "household_buffer": round(data.household_buffer, 0),
        }


class AmpPilotStatusSensor(AmpPilotSensorBase):
    """Sensor for charging status."""

    _attr_icon = "mdi:ev-station"
    _attr_translation_key = "charging_status"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "charging_status")
        self._attr_name = "Charging Status"

    @property
    def native_value(self) -> str:
        """Return the charging status."""
        return self.coordinator.data.charging_status

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        data = self.coordinator.data
        hysteresis = data.hysteresis
        return {
            "charging_mode": data.charging_mode,
            "solar_charging_enabled": data.solar_charging_enabled,
            "hysteresis_enabled": hysteresis.is_enabled,
            "enable_threshold": data.enable_threshold,
            "disable_threshold": data.disable_threshold,
        }


class AmpPilotVehiclePowerSensor(AmpPilotSensorBase):
    """Sensor for vehicle charging power."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:ev-station"
    # Don't use device name prefix - we want just the vehicle name
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, f"{vehicle}_power")
        self._vehicle = vehicle
        # Get custom vehicle name from config
        vehicle_data = getattr(coordinator.data, vehicle)
        self._vehicle_name = vehicle_data.name
        self._attr_name = f"{vehicle_data.name} Power"
        self._attr_translation_key = f"{vehicle}_power"

    @property
    def native_value(self) -> float:
        """Return the charging power."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return round(vehicle_data.current_power, 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return {
            "vehicle_name": self._vehicle_name,
            "target_amps": vehicle_data.target_amps,
            "is_connected": vehicle_data.is_connected,
            "is_charging": vehicle_data.is_charging,
            "enabled": vehicle_data.enabled,
        }


class AmpPilotVehicleAmpsSensor(AmpPilotSensorBase):
    """Sensor for vehicle charging amps."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_icon = "mdi:current-ac"
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, f"{vehicle}_amps")
        self._vehicle = vehicle
        vehicle_data = getattr(coordinator.data, vehicle)
        self._attr_name = f"{vehicle_data.name} Amps"
        self._attr_translation_key = f"{vehicle}_amps"

    @property
    def native_value(self) -> float:
        """Return the charging amps."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return round(vehicle_data.current_amps, 1)


class AmpPilotVehicleEnergySessionSensor(AmpPilotSensorBase):
    """Sensor for vehicle session energy."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:battery-charging"
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, f"{vehicle}_energy_session")
        self._vehicle = vehicle
        vehicle_data = getattr(coordinator.data, vehicle)
        self._attr_name = f"{vehicle_data.name} Session Energy"
        self._attr_translation_key = f"{vehicle}_energy_session"

    @property
    def native_value(self) -> float:
        """Return the session energy."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return round(vehicle_data.energy_session, 2)


class AmpPilotVehicleEnergyTodaySensor(AmpPilotSensorBase):
    """Sensor for vehicle today energy."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:battery-charging"
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, f"{vehicle}_energy_today")
        self._vehicle = vehicle
        vehicle_data = getattr(coordinator.data, vehicle)
        self._attr_name = f"{vehicle_data.name} Today Energy"
        self._attr_translation_key = f"{vehicle}_energy_today"

    @property
    def native_value(self) -> float:
        """Return the today energy."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return round(vehicle_data.energy_today, 2)


class AmpPilotSolarPowerSensor(AmpPilotSensorBase):
    """Sensor for solar power production."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:solar-power"
    _attr_translation_key = "solar_power"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "solar_power")
        self._attr_name = "Solar Power"

    @property
    def native_value(self) -> float:
        """Return solar power production."""
        return round(self.coordinator.data.solar_power, 0)


class AmpPilotGridPowerSensor(AmpPilotSensorBase):
    """Sensor for grid power (positive=import, negative=export)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:transmission-tower"
    _attr_translation_key = "grid_power"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "grid_power")
        self._attr_name = "Grid Power"

    @property
    def native_value(self) -> float:
        """Return grid power (positive=import, negative=export)."""
        return round(self.coordinator.data.grid_power, 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        grid_power = self.coordinator.data.grid_power
        return {
            "direction": "importing" if grid_power > 0 else "exporting" if grid_power < 0 else "balanced",
        }


class AmpPilotHomeLoadSensor(AmpPilotSensorBase):
    """Sensor for home power consumption."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:home-lightning-bolt"
    _attr_translation_key = "home_load"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "home_load")
        self._attr_name = "Home Load"

    @property
    def native_value(self) -> float:
        """Return home power consumption."""
        return round(self.coordinator.data.home_load, 0)


class AmpPilotBatterySocSensor(AmpPilotSensorBase):
    """Sensor for home battery state of charge."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "battery_soc"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "battery_soc")
        self._attr_name = "Battery SoC"

    @property
    def native_value(self) -> float | None:
        """Return battery state of charge."""
        if self.coordinator.data.battery_soc is None:
            return None
        return round(self.coordinator.data.battery_soc, 0)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on SoC level."""
        soc = self.coordinator.data.battery_soc
        if soc is None:
            return "mdi:battery-unknown"
        if soc >= 95:
            return "mdi:battery"
        if soc >= 80:
            return "mdi:battery-80"
        if soc >= 60:
            return "mdi:battery-60"
        if soc >= 40:
            return "mdi:battery-40"
        if soc >= 20:
            return "mdi:battery-20"
        return "mdi:battery-alert"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "min_soc_threshold": self.coordinator.data.min_battery_soc,
        }


class AmpPilotBatteryPowerSensor(AmpPilotSensorBase):
    """Sensor for home battery power (positive=charging, negative=discharging)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "battery_power"

    def __init__(self, coordinator: AmpPilotCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "battery_power")
        self._attr_name = "Battery Power"

    @property
    def native_value(self) -> float | None:
        """Return battery power."""
        if self.coordinator.data.battery_power is None:
            return None
        return round(self.coordinator.data.battery_power, 0)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on charging state."""
        power = self.coordinator.data.battery_power
        if power is None:
            return "mdi:battery-unknown"
        if power > 0:
            return "mdi:battery-charging"
        if power < 0:
            return "mdi:battery-minus"
        return "mdi:battery"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        power = self.coordinator.data.battery_power
        return {
            "direction": "charging" if power and power > 0 else "discharging" if power and power < 0 else "idle",
        }


class AmpPilotVehicleSocSensor(AmpPilotSensorBase):
    """Sensor for vehicle state of charge."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: AmpPilotCoordinator,
        entry: ConfigEntry,
        vehicle: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, f"{vehicle}_soc")
        self._vehicle = vehicle
        vehicle_data = getattr(coordinator.data, vehicle)
        self._attr_name = f"{vehicle_data.name} SoC"
        self._attr_translation_key = f"{vehicle}_soc"

    @property
    def native_value(self) -> float | None:
        """Return vehicle state of charge."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        if vehicle_data.soc is None:
            return None
        return round(vehicle_data.soc, 0)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on charging state and SoC level."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        soc = vehicle_data.soc
        if soc is None:
            return "mdi:car-battery"
        if vehicle_data.is_charging:
            return "mdi:battery-charging"
        if soc >= 80:
            return "mdi:battery-high"
        if soc >= 40:
            return "mdi:battery-medium"
        return "mdi:battery-low"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        vehicle_data = getattr(self.coordinator.data, self._vehicle)
        return {
            "is_connected": vehicle_data.is_connected,
            "is_charging": vehicle_data.is_charging,
        }
