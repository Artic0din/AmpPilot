"""Constants for AmpPilot integration."""

from typing import Final

DOMAIN: Final = "amppilot"

# Configuration keys - General
CONF_NAME: Final = "name"

# Configuration keys - Power Monitoring
CONF_SOLAR_ENTITY: Final = "solar_entity"
CONF_GRID_ENTITY: Final = "grid_entity"
CONF_HOME_LOAD_ENTITY: Final = "home_load_entity"

# Configuration keys - Home Battery
CONF_BATTERY_SOC_ENTITY: Final = "battery_soc_entity"
CONF_BATTERY_POWER_ENTITY: Final = "battery_power_entity"
CONF_MIN_BATTERY_SOC: Final = "min_battery_soc"

# Configuration keys - Vehicles
CONF_VEHICLE_1: Final = "vehicle_1"
CONF_VEHICLE_2: Final = "vehicle_2"
CONF_VEHICLE_NAME: Final = "vehicle_name"
CONF_CHARGER_SWITCH_ENTITY: Final = "charger_switch_entity"
CONF_CHARGER_AMPS_ENTITY: Final = "charger_amps_entity"
CONF_CHARGER_POWER_ENTITY: Final = "charger_power_entity"
CONF_VEHICLE_CHARGING_AMPS_ENTITY: Final = "vehicle_charging_amps_entity"
CONF_VEHICLE_CHARGING_STATE_ENTITY: Final = "vehicle_charging_state_entity"
CONF_VEHICLE_SOC_ENTITY: Final = "vehicle_soc_entity"
CONF_VEHICLE_CONNECTED_ENTITY: Final = "vehicle_connected_entity"
CONF_MIN_AMPS: Final = "min_amps"
CONF_MAX_AMPS: Final = "max_amps"
CONF_PHASES: Final = "phases"
CONF_VOLTAGE: Final = "voltage"

# Configuration keys - Distribution
CONF_DISTRIBUTION_MODE: Final = "distribution_mode"
CONF_PRIORITY_VEHICLE: Final = "priority_vehicle"
CONF_MIN_SURPLUS_PER_VEHICLE: Final = "min_surplus_per_vehicle"

# Configuration keys - Thresholds
CONF_ENABLE_THRESHOLD: Final = "enable_threshold"
CONF_ENABLE_DELAY: Final = "enable_delay"
CONF_DISABLE_THRESHOLD: Final = "disable_threshold"
CONF_DISABLE_DELAY: Final = "disable_delay"
CONF_HOUSEHOLD_BUFFER: Final = "household_buffer"

# Configuration keys - Scheduled Charging
CONF_ENABLE_SCHEDULED: Final = "enable_scheduled"
CONF_SCHEDULE_START: Final = "schedule_start"
CONF_SCHEDULE_END: Final = "schedule_end"
CONF_SCHEDULE_DAYS: Final = "schedule_days"

# Distribution modes
DISTRIBUTION_SIMULTANEOUS: Final = "simultaneous_split"
DISTRIBUTION_PRIORITY_THEN_SPLIT: Final = "priority_then_split"
DISTRIBUTION_PRIORITY_ONLY: Final = "priority_only"

DISTRIBUTION_MODES: Final = [
    DISTRIBUTION_SIMULTANEOUS,
    DISTRIBUTION_PRIORITY_THEN_SPLIT,
    DISTRIBUTION_PRIORITY_ONLY,
]

# Charging modes
MODE_OFF: Final = "off"
MODE_SOLAR: Final = "solar"
MODE_SCHEDULED: Final = "scheduled"
MODE_BOOST: Final = "boost"

CHARGING_MODES: Final = [MODE_OFF, MODE_SOLAR, MODE_SCHEDULED, MODE_BOOST]

# Days of week
DAYS_OF_WEEK: Final = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Default values
DEFAULT_NAME: Final = "AmpPilot"
DEFAULT_MIN_BATTERY_SOC: Final = 80
DEFAULT_MIN_AMPS: Final = 5
DEFAULT_MAX_AMPS: Final = 16
DEFAULT_PHASES: Final = 1
DEFAULT_VOLTAGE: Final = 230
DEFAULT_ENABLE_THRESHOLD: Final = 1400  # Watts (6A * 230V single-phase)
DEFAULT_ENABLE_DELAY: Final = 60  # seconds
DEFAULT_DISABLE_THRESHOLD: Final = 0  # Watts
DEFAULT_DISABLE_DELAY: Final = 180  # seconds
DEFAULT_HOUSEHOLD_BUFFER: Final = 200  # Watts

# Update interval
UPDATE_INTERVAL: Final = 10  # seconds

# Platforms
PLATFORMS: Final = ["sensor", "switch", "number", "select"]
