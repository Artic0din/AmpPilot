"""DataUpdateCoordinator for AmpPilot."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_CHARGER_AMPS_ENTITY,
    CONF_CHARGER_POWER_ENTITY,
    CONF_CHARGER_SWITCH_ENTITY,
    CONF_DISABLE_DELAY,
    CONF_DISABLE_THRESHOLD,
    CONF_DISTRIBUTION_MODE,
    CONF_ENABLE_DELAY,
    CONF_ENABLE_THRESHOLD,
    CONF_GRID_ENTITY,
    CONF_HOME_LOAD_ENTITY,
    CONF_HOUSEHOLD_BUFFER,
    CONF_MAX_AMPS,
    CONF_MIN_AMPS,
    CONF_MIN_BATTERY_SOC,
    CONF_PHASES,
    CONF_PRIORITY_VEHICLE,
    CONF_SOLAR_ENTITY,
    CONF_VEHICLE_1,
    CONF_VEHICLE_2,
    CONF_VEHICLE_CHARGING_AMPS_ENTITY,
    CONF_VEHICLE_CHARGING_STATE_ENTITY,
    CONF_VEHICLE_CONNECTED_ENTITY,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_VOLTAGE,
    DEFAULT_DISABLE_DELAY,
    DEFAULT_DISABLE_THRESHOLD,
    DEFAULT_ENABLE_DELAY,
    DEFAULT_ENABLE_THRESHOLD,
    DEFAULT_HOUSEHOLD_BUFFER,
    DEFAULT_MAX_AMPS,
    DEFAULT_MIN_AMPS,
    DEFAULT_MIN_BATTERY_SOC,
    DEFAULT_PHASES,
    DEFAULT_VOLTAGE,
    DISTRIBUTION_PRIORITY_ONLY,
    DISTRIBUTION_PRIORITY_THEN_SPLIT,
    DISTRIBUTION_SIMULTANEOUS,
    DOMAIN,
    MODE_BOOST,
    MODE_OFF,
    MODE_SCHEDULED,
    MODE_SOLAR,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VehicleState:
    """State for a single vehicle."""

    name: str = "Vehicle"
    is_connected: bool = False
    is_charging: bool = False
    current_amps: float = 0
    current_power: float = 0
    soc: float | None = None
    target_amps: float = 0
    energy_session: float = 0  # kWh
    energy_today: float = 0  # kWh
    enabled: bool = True
    session_start: datetime | None = None
    last_power_reading: float = 0
    last_update: datetime | None = None
    # Track last commanded state to avoid duplicate commands
    last_commanded_on: bool | None = None
    last_commanded_amps: float | None = None
    last_command_time: datetime | None = None  # Cooldown tracking


@dataclass
class HysteresisState:
    """State for hysteresis control."""

    enable_condition_since: datetime | None = None
    disable_condition_since: datetime | None = None
    is_enabled: bool = False


@dataclass
class AmpPilotData:
    """Data class for AmpPilot coordinator."""

    # Power readings
    solar_power: float = 0
    grid_power: float = 0
    home_load: float = 0
    battery_soc: float | None = None
    battery_power: float | None = None

    # Calculated values
    available_surplus: float = 0
    raw_surplus: float = 0

    # State
    charging_mode: str = MODE_SOLAR
    charging_status: str = "Idle"
    solar_charging_enabled: bool = True
    scheduled_charging_enabled: bool = False

    # Vehicle states
    vehicle_1: VehicleState = field(default_factory=VehicleState)
    vehicle_2: VehicleState = field(default_factory=VehicleState)

    # Hysteresis
    hysteresis: HysteresisState = field(default_factory=HysteresisState)

    # Configuration (runtime adjustable)
    enable_threshold: float = DEFAULT_ENABLE_THRESHOLD
    disable_threshold: float = DEFAULT_DISABLE_THRESHOLD
    enable_delay: int = DEFAULT_ENABLE_DELAY
    disable_delay: int = DEFAULT_DISABLE_DELAY
    household_buffer: float = DEFAULT_HOUSEHOLD_BUFFER
    min_battery_soc: float = DEFAULT_MIN_BATTERY_SOC
    distribution_mode: str = DISTRIBUTION_SIMULTANEOUS
    priority_vehicle: str = "vehicle_1"


class AmpPilotCoordinator(DataUpdateCoordinator[AmpPilotData]):
    """Coordinator for AmpPilot integration."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.config_entry = entry
        self._config = entry.data
        self._options = entry.options

        # Initialize data
        self.data = AmpPilotData()
        self._init_from_config()

    def _init_from_config(self) -> None:
        """Initialize data from config."""
        config = self._config

        # Load threshold settings
        self.data.enable_threshold = config.get(CONF_ENABLE_THRESHOLD, DEFAULT_ENABLE_THRESHOLD)
        self.data.disable_threshold = config.get(CONF_DISABLE_THRESHOLD, DEFAULT_DISABLE_THRESHOLD)
        self.data.enable_delay = config.get(CONF_ENABLE_DELAY, DEFAULT_ENABLE_DELAY)
        self.data.disable_delay = config.get(CONF_DISABLE_DELAY, DEFAULT_DISABLE_DELAY)
        self.data.household_buffer = config.get(CONF_HOUSEHOLD_BUFFER, DEFAULT_HOUSEHOLD_BUFFER)
        self.data.min_battery_soc = config.get(CONF_MIN_BATTERY_SOC, DEFAULT_MIN_BATTERY_SOC)
        self.data.distribution_mode = config.get(CONF_DISTRIBUTION_MODE, DISTRIBUTION_SIMULTANEOUS)
        self.data.priority_vehicle = config.get(CONF_PRIORITY_VEHICLE, "vehicle_1")

        # Initialize vehicle 1
        v1_config = config.get(CONF_VEHICLE_1, {})
        self.data.vehicle_1 = VehicleState(
            name=v1_config.get(CONF_VEHICLE_NAME, "Vehicle 1"),
        )

        # Initialize vehicle 2 (if configured)
        v2_config = config.get(CONF_VEHICLE_2)
        if v2_config:
            self.data.vehicle_2 = VehicleState(
                name=v2_config.get(CONF_VEHICLE_NAME, "Vehicle 2"),
            )

        # Apply options overrides if present
        if self._options:
            self._apply_options(self._options)

    def _apply_options(self, options: dict[str, Any]) -> None:
        """Apply options to data."""
        if CONF_ENABLE_THRESHOLD in options:
            self.data.enable_threshold = options[CONF_ENABLE_THRESHOLD]
        if CONF_DISABLE_THRESHOLD in options:
            self.data.disable_threshold = options[CONF_DISABLE_THRESHOLD]
        if CONF_ENABLE_DELAY in options:
            self.data.enable_delay = options[CONF_ENABLE_DELAY]
        if CONF_DISABLE_DELAY in options:
            self.data.disable_delay = options[CONF_DISABLE_DELAY]
        if CONF_HOUSEHOLD_BUFFER in options:
            self.data.household_buffer = options[CONF_HOUSEHOLD_BUFFER]
        if CONF_MIN_BATTERY_SOC in options:
            self.data.min_battery_soc = options[CONF_MIN_BATTERY_SOC]
        if CONF_DISTRIBUTION_MODE in options:
            self.data.distribution_mode = options[CONF_DISTRIBUTION_MODE]
        if CONF_PRIORITY_VEHICLE in options:
            self.data.priority_vehicle = options[CONF_PRIORITY_VEHICLE]

    def _get_entity_value(self, entity_id: str | None, convert_to_watts: bool = False) -> float | None:
        """Get numeric value from a Home Assistant entity.

        Args:
            entity_id: The entity ID to read from
            convert_to_watts: If True, converts kW to W based on unit_of_measurement
        """
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", "none"):
            return None
        try:
            value = float(state.state)

            # Convert kW to W if needed
            if convert_to_watts:
                unit = state.attributes.get("unit_of_measurement", "").lower()
                if unit in ("kw", "kilowatt", "kilowatts"):
                    value = value * 1000
                    _LOGGER.debug(
                        "Converted %s from kW to W: %.1f kW -> %.0f W",
                        entity_id, value / 1000, value
                    )

            return value
        except (ValueError, TypeError):
            return None

    def _get_entity_bool(self, entity_id: str | None) -> bool:
        """Get boolean value from a binary sensor entity."""
        if not entity_id:
            return False
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        return state.state == "on"

    async def _async_update_data(self) -> AmpPilotData:
        """Fetch data and run charging algorithm."""
        try:
            now = datetime.now()
            _LOGGER.debug("Starting coordinator update cycle")

            # Read power sensors (convert kW to W if needed)
            self.data.solar_power = self._get_entity_value(
                self._config.get(CONF_SOLAR_ENTITY), convert_to_watts=True
            ) or 0
            self.data.grid_power = self._get_entity_value(
                self._config.get(CONF_GRID_ENTITY), convert_to_watts=True
            ) or 0
            self.data.home_load = self._get_entity_value(
                self._config.get(CONF_HOME_LOAD_ENTITY), convert_to_watts=True
            ) or 0

            _LOGGER.debug(
                "Power readings - Solar: %.0fW, Grid: %.0fW, Home: %.0fW",
                self.data.solar_power,
                self.data.grid_power,
                self.data.home_load,
            )

            # Read battery sensors (optional)
            self.data.battery_soc = self._get_entity_value(
                self._config.get(CONF_BATTERY_SOC_ENTITY)
            )
            # Tesla reports positive battery_power for discharging (power leaving battery)
            # We negate it so positive = charging (power entering battery) for flow card
            raw_battery_power = self._get_entity_value(
                self._config.get(CONF_BATTERY_POWER_ENTITY), convert_to_watts=True
            )
            if raw_battery_power is not None:
                self.data.battery_power = -raw_battery_power
                _LOGGER.debug(
                    "Battery power sign inverted: %.0fW -> %.0fW (positive=charging)",
                    raw_battery_power,
                    self.data.battery_power,
                )
            else:
                self.data.battery_power = None

            # Read vehicle states
            await self._update_vehicle_state(self.data.vehicle_1, CONF_VEHICLE_1)
            if self._config.get(CONF_VEHICLE_2):
                await self._update_vehicle_state(self.data.vehicle_2, CONF_VEHICLE_2)

            # Calculate surplus
            self._calculate_surplus()
            _LOGGER.debug(
                "Surplus calculation - Raw: %.0fW, Available: %.0fW (buffer: %.0fW)",
                self.data.raw_surplus,
                self.data.available_surplus,
                self.data.household_buffer,
            )

            # Check battery priority
            battery_has_priority = self._check_battery_priority()
            if battery_has_priority:
                _LOGGER.debug(
                    "Battery has priority - SoC: %.0f%% (min: %.0f%%)",
                    self.data.battery_soc or 0,
                    self.data.min_battery_soc,
                )

            # Determine charging based on mode
            if self.data.charging_mode == MODE_OFF:
                self.data.charging_status = "Off"
                await self._set_charging(0, 0)
            elif self.data.charging_mode == MODE_BOOST:
                self.data.charging_status = "Boost charging"
                await self._boost_charge()
            elif self.data.charging_mode == MODE_SOLAR:
                if battery_has_priority:
                    self.data.charging_status = f"Waiting for battery ({self.data.battery_soc:.0f}%)"
                    await self._set_charging(0, 0)
                else:
                    await self._solar_charge(now)
            elif self.data.charging_mode == MODE_SCHEDULED:
                await self._scheduled_charge(now)

            return self.data

        except Exception as err:
            _LOGGER.exception("Error updating AmpPilot data")
            raise UpdateFailed(f"Error updating data: {err}") from err

    def _get_charging_state_from_entity(self, entity_id: str | None) -> str | None:
        """Get charging state string from a state entity (e.g., sensor.slater_charging)."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        return state.state

    async def _update_vehicle_state(self, vehicle: VehicleState, config_key: str) -> None:
        """Update state for a vehicle.

        Priority for determining charging state and power:
        1. Vehicle charging state sensor (sensor.X_charging) - most reliable
        2. Vehicle charging amps sensor (sensor.X_charger_current) - calculates power
        3. Charger power sensor (sensor.X_charger_power) - may not work for Mobile Connector
        4. Switch state (switch.X_charge) - fallback
        """
        v_config = self._config.get(config_key, {})
        if not v_config:
            return

        phases = int(v_config.get(CONF_PHASES, DEFAULT_PHASES))
        voltage = v_config.get(CONF_VOLTAGE, DEFAULT_VOLTAGE)
        was_charging = vehicle.is_charging

        # Check if connected
        connected_entity = v_config.get(CONF_VEHICLE_CONNECTED_ENTITY)
        if connected_entity:
            vehicle.is_connected = self._get_entity_bool(connected_entity)
        else:
            # Assume connected if no sensor configured
            vehicle.is_connected = True

        # === Determine charging state and power ===
        # Priority 1: Vehicle charging state sensor (e.g., sensor.slater_charging)
        charging_state_entity = v_config.get(CONF_VEHICLE_CHARGING_STATE_ENTITY)
        charging_state = self._get_charging_state_from_entity(charging_state_entity)

        # Priority 2: Vehicle charging amps sensor (e.g., sensor.slater_charger_current)
        charging_amps_entity = v_config.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY)
        vehicle_amps = self._get_entity_value(charging_amps_entity)

        # Priority 3: Charger power sensor (e.g., sensor.slater_charger_power)
        power_entity = v_config.get(CONF_CHARGER_POWER_ENTITY)
        charger_power = self._get_entity_value(power_entity, convert_to_watts=True)

        # Determine is_charging based on available sensors
        if charging_state is not None:
            # Use charging state sensor - most reliable
            vehicle.is_charging = charging_state == "charging"
            _LOGGER.debug(
                "%s charging state from sensor: %s (is_charging=%s)",
                vehicle.name, charging_state, vehicle.is_charging
            )
        elif vehicle_amps is not None and vehicle_amps > 0:
            vehicle.is_charging = True
        elif charger_power is not None and charger_power > 100:
            vehicle.is_charging = True
        else:
            # Fallback to switch state
            switch_entity = v_config.get(CONF_CHARGER_SWITCH_ENTITY)
            if switch_entity:
                vehicle.is_charging = self._get_entity_bool(switch_entity)
            else:
                vehicle.is_charging = False

        # Determine current_amps and current_power
        if vehicle_amps is not None and vehicle_amps > 0:
            # Calculate power from vehicle-reported amps (most accurate for Mobile Connector)
            vehicle.current_amps = vehicle_amps
            vehicle.current_power = vehicle_amps * voltage * phases
            _LOGGER.debug(
                "%s power calculated from vehicle amps: %.1fA × %dV × %d phases = %.0fW",
                vehicle.name, vehicle_amps, voltage, phases, vehicle.current_power
            )
        elif charger_power is not None and charger_power > 0:
            # Use charger power sensor and calculate amps
            vehicle.current_power = charger_power
            vehicle.current_amps = charger_power / (voltage * phases)
        elif vehicle.is_charging:
            # Charging but no power reading - estimate from target amps
            target = vehicle.target_amps if vehicle.target_amps > 0 else v_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS)
            vehicle.current_amps = target
            vehicle.current_power = target * voltage * phases
            _LOGGER.debug(
                "%s power estimated from target amps: %.1fA × %dV = %.0fW",
                vehicle.name, target, voltage, vehicle.current_power
            )
        else:
            vehicle.current_amps = 0
            vehicle.current_power = 0

        # Sync last_commanded_on with actual state to handle external changes
        # (e.g., user manually started/stopped via Tesla app)
        if vehicle.is_charging != was_charging:
            _LOGGER.debug(
                "Vehicle %s charging state changed externally: %s -> %s",
                vehicle.name,
                was_charging,
                vehicle.is_charging,
            )
            vehicle.last_commanded_on = vehicle.is_charging

        # Read vehicle SoC
        soc_entity = v_config.get(CONF_VEHICLE_SOC_ENTITY)
        if soc_entity:
            vehicle.soc = self._get_entity_value(soc_entity)

        # Log final state
        if vehicle.is_charging or vehicle.current_power > 0:
            _LOGGER.debug(
                "%s state: charging=%s, power=%.0fW, amps=%.1fA",
                vehicle.name, vehicle.is_charging, vehicle.current_power, vehicle.current_amps
            )

    def _calculate_surplus(self) -> None:
        """Calculate available solar surplus.

        With a home battery, surplus solar charges the battery first, so grid
        export may be ~0 even when there's excess solar. We include battery
        charging power as available surplus (if battery is above min SoC).

        Formula: surplus = grid_export + current_EV_power + divertable_battery_power - buffer
        """
        # Get current EV power
        current_ev_power = self.data.vehicle_1.current_power
        if self._config.get(CONF_VEHICLE_2):
            current_ev_power += self.data.vehicle_2.current_power

        # Battery charging power that could be diverted to EVs
        # Only count if battery is above minimum SoC threshold
        # Note: battery_power is now positive for charging, negative for discharging
        battery_charge_power = 0
        if self.data.battery_power is not None and self.data.battery_power > 0:
            # Battery is charging (positive = charging) - this power could go to EVs instead
            if self.data.battery_soc is None or self.data.battery_soc >= self.data.min_battery_soc:
                battery_charge_power = self.data.battery_power
                _LOGGER.debug(
                    "Battery above min SoC (%.0f%% >= %.0f%%), adding %.0fW battery charging to surplus",
                    self.data.battery_soc or 100,
                    self.data.min_battery_soc,
                    battery_charge_power,
                )
            else:
                _LOGGER.debug(
                    "Battery below min SoC (%.0f%% < %.0f%%), not diverting battery charging power",
                    self.data.battery_soc,
                    self.data.min_battery_soc,
                )

        # Calculate raw surplus:
        # - Negative grid = export (we're sending power to grid)
        # - Plus current EV power (would become available if we stopped)
        # - Plus battery charging (can be diverted if battery above min SoC)
        self.data.raw_surplus = -self.data.grid_power + current_ev_power + battery_charge_power

        # Subtract household buffer
        self.data.available_surplus = max(
            0, self.data.raw_surplus - self.data.household_buffer
        )

    def _check_battery_priority(self) -> bool:
        """Check if home battery should have priority."""
        if self.data.battery_soc is None:
            return False

        # Battery has priority if below threshold AND charging
        # Note: battery_power is positive for charging (after sign inversion)
        if self.data.battery_soc < self.data.min_battery_soc:
            # Check if battery is charging (positive power = charging)
            if self.data.battery_power is not None and self.data.battery_power > 0:
                return True
        return False

    async def _solar_charge(self, now: datetime) -> None:
        """Handle solar surplus charging."""
        if not self.data.solar_charging_enabled:
            self.data.charging_status = "Solar charging disabled"
            await self._set_charging(0, 0)
            return

        surplus = self.data.available_surplus
        hysteresis = self.data.hysteresis

        # Apply hysteresis logic
        if hysteresis.is_enabled:
            # Check disable condition
            if surplus < self.data.disable_threshold:
                if hysteresis.disable_condition_since is None:
                    hysteresis.disable_condition_since = now
                elif (now - hysteresis.disable_condition_since).total_seconds() >= self.data.disable_delay:
                    hysteresis.is_enabled = False
                    hysteresis.disable_condition_since = None
                    _LOGGER.info("Disabling solar charging - surplus below threshold")
            else:
                hysteresis.disable_condition_since = None
        else:
            # Check enable condition
            if surplus >= self.data.enable_threshold:
                if hysteresis.enable_condition_since is None:
                    hysteresis.enable_condition_since = now
                elif (now - hysteresis.enable_condition_since).total_seconds() >= self.data.enable_delay:
                    hysteresis.is_enabled = True
                    hysteresis.enable_condition_since = None
                    _LOGGER.info("Enabling solar charging - surplus above threshold")
            else:
                hysteresis.enable_condition_since = None

        if not hysteresis.is_enabled:
            self.data.charging_status = "Waiting for surplus"
            await self._set_charging(0, 0)
            return

        # Distribute power
        v1_amps, v2_amps = self._distribute_power(surplus)

        self.data.charging_status = f"Solar charging ({surplus:.0f}W surplus)"
        await self._set_charging(v1_amps, v2_amps)

    def _distribute_power(self, surplus: float) -> tuple[float, float]:
        """Distribute surplus power between vehicles."""
        _LOGGER.debug(
            "Distributing %.0fW surplus (mode: %s, priority: %s)",
            surplus,
            self.data.distribution_mode,
            self.data.priority_vehicle,
        )
        v1_config = self._config.get(CONF_VEHICLE_1, {})
        v2_config = self._config.get(CONF_VEHICLE_2)

        v1_min_amps = v1_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS)
        v1_max_amps = v1_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS)
        v1_phases = int(v1_config.get(CONF_PHASES, DEFAULT_PHASES))
        v1_voltage = v1_config.get(CONF_VOLTAGE, DEFAULT_VOLTAGE)
        v1_min_power = v1_min_amps * v1_voltage * v1_phases

        # Check if vehicle 1 is available
        v1_available = (
            self.data.vehicle_1.enabled and
            self.data.vehicle_1.is_connected
        )

        # If no vehicle 2, give all to vehicle 1
        if not v2_config:
            if not v1_available or surplus < v1_min_power:
                return (0, 0)
            v1_amps = min(surplus / (v1_voltage * v1_phases), v1_max_amps)
            return (int(v1_amps), 0)

        v2_min_amps = v2_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS)
        v2_max_amps = v2_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS)
        v2_phases = int(v2_config.get(CONF_PHASES, DEFAULT_PHASES))
        v2_voltage = v2_config.get(CONF_VOLTAGE, DEFAULT_VOLTAGE)
        v2_min_power = v2_min_amps * v2_voltage * v2_phases

        v2_available = (
            self.data.vehicle_2.enabled and
            self.data.vehicle_2.is_connected
        )

        # Determine which vehicles can charge
        can_v1 = v1_available and surplus >= v1_min_power
        can_v2 = v2_available and surplus >= v2_min_power
        can_both = v1_available and v2_available and surplus >= (v1_min_power + v2_min_power)

        # Determine priority
        priority_is_v1 = self.data.priority_vehicle == "vehicle_1"

        # Distribution based on mode
        if self.data.distribution_mode == DISTRIBUTION_SIMULTANEOUS:
            if can_both:
                # Split evenly
                half = surplus / 2
                v1_power = max(v1_min_power, min(half, v1_max_amps * v1_voltage * v1_phases))
                v2_power = max(v2_min_power, min(half, v2_max_amps * v2_voltage * v2_phases))

                # Redistribute excess
                v1_excess = half - v1_power if half > v1_power else 0
                v2_excess = half - v2_power if half > v2_power else 0

                v1_power = min(v1_power + v2_excess, v1_max_amps * v1_voltage * v1_phases)
                v2_power = min(v2_power + v1_excess, v2_max_amps * v2_voltage * v2_phases)

                v1_amps = v1_power / (v1_voltage * v1_phases)
                v2_amps = v2_power / (v2_voltage * v2_phases)
                return (int(v1_amps), int(v2_amps))
            elif can_v1 and priority_is_v1:
                v1_amps = min(surplus / (v1_voltage * v1_phases), v1_max_amps)
                return (int(v1_amps), 0)
            elif can_v2 and not priority_is_v1:
                v2_amps = min(surplus / (v2_voltage * v2_phases), v2_max_amps)
                return (0, int(v2_amps))
            elif can_v1:
                v1_amps = min(surplus / (v1_voltage * v1_phases), v1_max_amps)
                return (int(v1_amps), 0)
            elif can_v2:
                v2_amps = min(surplus / (v2_voltage * v2_phases), v2_max_amps)
                return (0, int(v2_amps))

        elif self.data.distribution_mode == DISTRIBUTION_PRIORITY_THEN_SPLIT:
            if priority_is_v1:
                if can_v1:
                    v1_power = min(surplus, v1_max_amps * v1_voltage * v1_phases)
                    v1_amps = v1_power / (v1_voltage * v1_phases)
                    remaining = surplus - v1_power
                    if can_v2 and remaining >= v2_min_power:
                        v2_power = min(remaining, v2_max_amps * v2_voltage * v2_phases)
                        v2_amps = v2_power / (v2_voltage * v2_phases)
                        return (int(v1_amps), int(v2_amps))
                    return (int(v1_amps), 0)
                elif can_v2:
                    v2_amps = min(surplus / (v2_voltage * v2_phases), v2_max_amps)
                    return (0, int(v2_amps))
            else:
                if can_v2:
                    v2_power = min(surplus, v2_max_amps * v2_voltage * v2_phases)
                    v2_amps = v2_power / (v2_voltage * v2_phases)
                    remaining = surplus - v2_power
                    if can_v1 and remaining >= v1_min_power:
                        v1_power = min(remaining, v1_max_amps * v1_voltage * v1_phases)
                        v1_amps = v1_power / (v1_voltage * v1_phases)
                        return (int(v1_amps), int(v2_amps))
                    return (0, int(v2_amps))
                elif can_v1:
                    v1_amps = min(surplus / (v1_voltage * v1_phases), v1_max_amps)
                    return (int(v1_amps), 0)

        elif self.data.distribution_mode == DISTRIBUTION_PRIORITY_ONLY:
            if priority_is_v1 and can_v1:
                v1_amps = min(surplus / (v1_voltage * v1_phases), v1_max_amps)
                return (int(v1_amps), 0)
            elif not priority_is_v1 and can_v2:
                v2_amps = min(surplus / (v2_voltage * v2_phases), v2_max_amps)
                return (0, int(v2_amps))

        return (0, 0)

    async def _set_charging(self, v1_amps: float, v2_amps: float) -> None:
        """Set charging amperage for vehicles.

        Uses switch entity for start/stop control and number entity for amperage.
        Commands go to the Tesla vehicles (not wall/mobile connectors directly).

        IMPORTANT: Only sends commands when:
        - The desired state differs from the last commanded state
        - The amp change is significant (>= MIN_AMP_CHANGE_THRESHOLD)
        - Enough time has passed since last command (COMMAND_COOLDOWN_SECONDS)
        This avoids API rate limiting and conserves Tesla API credits.
        """
        # Minimum amp change to trigger a command (avoids tiny fluctuations)
        MIN_AMP_CHANGE_THRESHOLD = 2
        # Minimum seconds between commands to same vehicle
        COMMAND_COOLDOWN_SECONDS = 30

        now = datetime.now()

        _LOGGER.debug(
            "Target charging - V1 (%s): %.0fA, V2 (%s): %.0fA",
            self.data.vehicle_1.name, v1_amps,
            self.data.vehicle_2.name, v2_amps,
        )
        v1_config = self._config.get(CONF_VEHICLE_1, {})
        v2_config = self._config.get(CONF_VEHICLE_2)

        # Set vehicle 1
        v1_switch = v1_config.get(CONF_CHARGER_SWITCH_ENTITY)
        v1_amps_entity = v1_config.get(CONF_CHARGER_AMPS_ENTITY)

        self.data.vehicle_1.target_amps = v1_amps
        v1_should_charge = v1_amps > 0

        # Check cooldown for vehicle 1
        v1_cooldown_ok = (
            self.data.vehicle_1.last_command_time is None or
            (now - self.data.vehicle_1.last_command_time).total_seconds() >= COMMAND_COOLDOWN_SECONDS
        )

        if v1_should_charge:
            # Set amps first, then start charging
            v1_min = v1_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS)
            v1_max = v1_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS)
            target = int(max(v1_min, min(v1_amps, v1_max)))

            # Check if amp change is significant enough
            last_amps = self.data.vehicle_1.last_commanded_amps
            amp_change = abs(target - (last_amps or 0))
            should_update_amps = (
                v1_amps_entity and
                v1_cooldown_ok and
                (last_amps is None or amp_change >= MIN_AMP_CHANGE_THRESHOLD)
            )

            if should_update_amps:
                _LOGGER.info(
                    "API CALL: %s amps %s -> %s (change: %dA)",
                    self.data.vehicle_1.name,
                    last_amps,
                    target,
                    amp_change,
                )
                await self._set_entity_value(v1_amps_entity, target)
                self.data.vehicle_1.last_commanded_amps = target
                self.data.vehicle_1.last_command_time = now
            elif v1_amps_entity and not v1_cooldown_ok:
                _LOGGER.debug(
                    "Skipping %s amp change (cooldown: %ds remaining)",
                    self.data.vehicle_1.name,
                    COMMAND_COOLDOWN_SECONDS - (now - self.data.vehicle_1.last_command_time).total_seconds(),
                )
            elif v1_amps_entity and amp_change < MIN_AMP_CHANGE_THRESHOLD and last_amps is not None:
                _LOGGER.debug(
                    "Skipping %s amp change (too small: %dA < %dA threshold)",
                    self.data.vehicle_1.name,
                    amp_change,
                    MIN_AMP_CHANGE_THRESHOLD,
                )

            # Only turn on if not already commanded on
            if v1_switch and self.data.vehicle_1.last_commanded_on is not True and v1_cooldown_ok:
                _LOGGER.info("API CALL: Starting charge on %s", self.data.vehicle_1.name)
                await self._turn_on_switch(v1_switch)
                self.data.vehicle_1.last_commanded_on = True
                self.data.vehicle_1.last_command_time = now
            elif v1_switch and self.data.vehicle_1.last_commanded_on is True:
                _LOGGER.debug("Skipping %s start (already charging)", self.data.vehicle_1.name)
        else:
            # Stop charging - only if not already commanded off
            if v1_switch and self.data.vehicle_1.last_commanded_on is not False and v1_cooldown_ok:
                _LOGGER.info("API CALL: Stopping charge on %s", self.data.vehicle_1.name)
                await self._turn_off_switch(v1_switch)
                self.data.vehicle_1.last_commanded_on = False
                self.data.vehicle_1.last_command_time = now
            elif v1_switch and self.data.vehicle_1.last_commanded_on is False:
                _LOGGER.debug("Skipping %s stop (already stopped)", self.data.vehicle_1.name)

        # Set vehicle 2
        if v2_config:
            v2_switch = v2_config.get(CONF_CHARGER_SWITCH_ENTITY)
            v2_amps_entity = v2_config.get(CONF_CHARGER_AMPS_ENTITY)

            self.data.vehicle_2.target_amps = v2_amps
            v2_should_charge = v2_amps > 0

            # Check cooldown for vehicle 2
            v2_cooldown_ok = (
                self.data.vehicle_2.last_command_time is None or
                (now - self.data.vehicle_2.last_command_time).total_seconds() >= COMMAND_COOLDOWN_SECONDS
            )

            if v2_should_charge:
                # Set amps first, then start charging
                v2_min = v2_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS)
                v2_max = v2_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS)
                target = int(max(v2_min, min(v2_amps, v2_max)))

                # Check if amp change is significant enough
                last_amps = self.data.vehicle_2.last_commanded_amps
                amp_change = abs(target - (last_amps or 0))
                should_update_amps = (
                    v2_amps_entity and
                    v2_cooldown_ok and
                    (last_amps is None or amp_change >= MIN_AMP_CHANGE_THRESHOLD)
                )

                if should_update_amps:
                    _LOGGER.info(
                        "API CALL: %s amps %s -> %s (change: %dA)",
                        self.data.vehicle_2.name,
                        last_amps,
                        target,
                        amp_change,
                    )
                    await self._set_entity_value(v2_amps_entity, target)
                    self.data.vehicle_2.last_commanded_amps = target
                    self.data.vehicle_2.last_command_time = now
                elif v2_amps_entity and not v2_cooldown_ok:
                    _LOGGER.debug(
                        "Skipping %s amp change (cooldown: %ds remaining)",
                        self.data.vehicle_2.name,
                        COMMAND_COOLDOWN_SECONDS - (now - self.data.vehicle_2.last_command_time).total_seconds(),
                    )
                elif v2_amps_entity and amp_change < MIN_AMP_CHANGE_THRESHOLD and last_amps is not None:
                    _LOGGER.debug(
                        "Skipping %s amp change (too small: %dA < %dA threshold)",
                        self.data.vehicle_2.name,
                        amp_change,
                        MIN_AMP_CHANGE_THRESHOLD,
                    )

                # Only turn on if not already commanded on
                if v2_switch and self.data.vehicle_2.last_commanded_on is not True and v2_cooldown_ok:
                    _LOGGER.info("API CALL: Starting charge on %s", self.data.vehicle_2.name)
                    await self._turn_on_switch(v2_switch)
                    self.data.vehicle_2.last_commanded_on = True
                    self.data.vehicle_2.last_command_time = now
                elif v2_switch and self.data.vehicle_2.last_commanded_on is True:
                    _LOGGER.debug("Skipping %s start (already charging)", self.data.vehicle_2.name)
            else:
                # Stop charging - only if not already commanded off
                if v2_switch and self.data.vehicle_2.last_commanded_on is not False and v2_cooldown_ok:
                    _LOGGER.info("API CALL: Stopping charge on %s", self.data.vehicle_2.name)
                    await self._turn_off_switch(v2_switch)
                    self.data.vehicle_2.last_commanded_on = False
                    self.data.vehicle_2.last_command_time = now
                elif v2_switch and self.data.vehicle_2.last_commanded_on is False:
                    _LOGGER.debug("Skipping %s stop (already stopped)", self.data.vehicle_2.name)

    async def _turn_on_switch(self, entity_id: str) -> None:
        """Turn on a switch entity to start charging."""
        # Check if entity exists
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning(
                "Cannot turn on %s - entity does not exist or is unavailable",
                entity_id,
            )
            return

        try:
            _LOGGER.info("Turning on switch: %s", entity_id)
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": entity_id},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to turn on %s: %s", entity_id, err)

    async def _turn_off_switch(self, entity_id: str) -> None:
        """Turn off a switch entity to stop charging."""
        # Check if entity exists
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning(
                "Cannot turn off %s - entity does not exist or is unavailable",
                entity_id,
            )
            return

        try:
            _LOGGER.info("Turning off switch: %s", entity_id)
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": entity_id},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to turn off %s: %s", entity_id, err)

    async def _set_entity_value(self, entity_id: str, value: float) -> None:
        """Set value on a number entity."""
        # Check if entity exists
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning(
                "Cannot set %s to %s - entity does not exist or is unavailable",
                entity_id, value,
            )
            return

        try:
            _LOGGER.info("Setting %s to %s", entity_id, value)
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": entity_id, "value": value},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.error("Failed to set %s to %s: %s", entity_id, value, err)

    async def _boost_charge(self) -> None:
        """Charge at maximum rate."""
        v1_config = self._config.get(CONF_VEHICLE_1, {})
        v2_config = self._config.get(CONF_VEHICLE_2)

        v1_max = v1_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS)
        v2_max = v2_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS) if v2_config else 0

        await self._set_charging(v1_max, v2_max)

    async def _scheduled_charge(self, now: datetime) -> None:
        """Handle scheduled charging."""
        # TODO: Implement schedule checking
        if self.data.scheduled_charging_enabled:
            self.data.charging_status = "Scheduled charging"
            await self._boost_charge()
        else:
            self.data.charging_status = "Outside schedule"
            await self._set_charging(0, 0)

    # Public methods for entity control
    async def async_set_charging_mode(self, mode: str) -> None:
        """Set the charging mode."""
        if mode in (MODE_OFF, MODE_SOLAR, MODE_SCHEDULED, MODE_BOOST):
            self.data.charging_mode = mode
            await self.async_refresh()

    async def async_set_solar_charging_enabled(self, enabled: bool) -> None:
        """Enable or disable solar charging."""
        self.data.solar_charging_enabled = enabled
        await self.async_refresh()

    async def async_set_scheduled_charging_enabled(self, enabled: bool) -> None:
        """Enable or disable scheduled charging."""
        self.data.scheduled_charging_enabled = enabled
        await self.async_refresh()

    async def async_set_vehicle_enabled(self, vehicle: str, enabled: bool) -> None:
        """Enable or disable a vehicle."""
        if vehicle == "vehicle_1":
            self.data.vehicle_1.enabled = enabled
        elif vehicle == "vehicle_2":
            self.data.vehicle_2.enabled = enabled
        await self.async_refresh()

    async def async_set_threshold(self, threshold_type: str, value: float) -> None:
        """Set a threshold value."""
        if threshold_type == "enable":
            self.data.enable_threshold = value
        elif threshold_type == "disable":
            self.data.disable_threshold = value
        elif threshold_type == "enable_delay":
            self.data.enable_delay = int(value)
        elif threshold_type == "disable_delay":
            self.data.disable_delay = int(value)
        elif threshold_type == "household_buffer":
            self.data.household_buffer = value
        elif threshold_type == "min_battery_soc":
            self.data.min_battery_soc = value
        await self.async_refresh()

    async def async_set_distribution_mode(self, mode: str) -> None:
        """Set the distribution mode."""
        if mode in (DISTRIBUTION_SIMULTANEOUS, DISTRIBUTION_PRIORITY_THEN_SPLIT, DISTRIBUTION_PRIORITY_ONLY):
            self.data.distribution_mode = mode
            await self.async_refresh()

    async def async_set_priority_vehicle(self, vehicle: str) -> None:
        """Set the priority vehicle."""
        if vehicle in ("vehicle_1", "vehicle_2"):
            self.data.priority_vehicle = vehicle
            await self.async_refresh()

    def reset_session_stats(self, vehicle: str) -> None:
        """Reset session statistics for a vehicle."""
        if vehicle == "vehicle_1":
            self.data.vehicle_1.energy_session = 0
            self.data.vehicle_1.session_start = datetime.now()
        elif vehicle == "vehicle_2":
            self.data.vehicle_2.energy_session = 0
            self.data.vehicle_2.session_start = datetime.now()
