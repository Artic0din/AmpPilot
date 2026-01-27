# AmpPilot

Solar-aware dual-EV charging integration for Home Assistant. Manages charging for up to 2 EVs simultaneously using available solar surplus.

## Why AmpPilot?

Several solar EV charging solutions exist, but each has limitations that led to creating AmpPilot:

| Solution | Limitations |
|----------|-------------|
| **ChargeHQ** | Cloud-dependent, subscription pricing, single vehicle only |
| **Amber for EV** | Australia-only (Amber Electric), price-focused not solar-focused, no battery awareness |
| **EVCC** | Powerful but complex, config via YAML/evcc.yaml outside HA, single loadpoint focus |

**AmpPilot was built to be:**
- **100% Local** - No cloud dependency, works offline
- **Native Home Assistant** - Config flow UI, no YAML required
- **Dual-EV Ready** - Charge 2 vehicles simultaneously with intelligent power splitting
- **Battery Aware** - Prioritizes home battery before EV charging
- **Integration Agnostic** - Works with any solar/charger integration in HA
- **Free & Open Source** - No subscriptions, no lock-in

## Features

- **Simultaneous Dual-EV Charging** - Unlike other solutions, AmpPilot can charge 2 EVs at the same time by intelligently splitting available solar surplus
- **Solar Surplus Charging** - Automatically adjusts charging amperage based on available solar power to minimize grid import
- **Home Battery Priority** - Configurable minimum battery SoC before EV charging begins
- **Dynamic Amperage Control** - Works with any charger that exposes a controllable number entity
- **Scheduled Charging** - Time-based charging for off-peak hours
- **Integration Agnostic** - Works with any solar, battery, and EV charger integration in Home Assistant

## Requirements

- Home Assistant 2024.1.0 or newer
- Solar production sensor (any integration)
- Grid import/export sensor (any integration)
- EV charger with controllable amperage via number entity (Teslemetry, OCPP, Easee, Wallbox, etc.)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Add"
6. Search for "AmpPilot" and install
7. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/amppilot` folder to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

AmpPilot uses a config flow wizard - no YAML configuration required.

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "AmpPilot"
4. Follow the setup wizard:

### Step 1: Power Monitoring
Select your power sensors:
- **Solar production** - Sensor showing current solar generation (W)
- **Grid import/export** - Sensor showing grid power (positive = importing, negative = exporting) (W)
- **Home load** - Sensor showing home consumption (W)

### Step 2: Home Battery (Optional)
If you have a home battery:
- **Battery SoC** - Battery state of charge sensor (%)
- **Battery power** - Battery charging/discharging power (W)
- **Minimum SoC** - Don't charge EVs until battery reaches this level

### Step 3 & 4: Vehicle Configuration
For each vehicle:
- **Vehicle name** - Friendly name for the vehicle
- **Charger switch** - Switch entity to enable/disable the charger (required)
- **Charger amperage control** - Number entity to control charging amps (required)
- **Vehicle connected sensor** - Binary sensor for plug-in detection (optional)
- **Charger power sensor** - Sensor showing current charging power (optional)
- **Vehicle charging state sensor** - Binary sensor for vehicle's charging state (optional)
- **Vehicle charging amps sensor** - Sensor for vehicle's charging current (optional)
- **Vehicle SoC sensor** - Vehicle battery level (optional)
- **Min/Max amps** - Amperage limits
- **Phases** - Single or three-phase charging
- **Voltage** - Line voltage (default 230V)

### Step 5: Power Distribution
- **Distribution mode**:
  - `simultaneous_split` - Split power evenly between both vehicles
  - `priority_then_split` - Priority vehicle charges first, then split remainder
  - `priority_only` - Only charge priority vehicle
- **Priority vehicle** - Which vehicle has priority when power is limited

### Step 6: Thresholds
- **Enable threshold** - Surplus required to start charging (W)
- **Enable delay** - How long surplus must be sustained before starting (seconds)
- **Disable threshold** - Surplus level to stop charging (W)
- **Disable delay** - How long before stopping when surplus drops (seconds)
- **Household buffer** - Power reserved for household (W)

### Step 7: Scheduled Charging (Optional)
- Configure time windows for scheduled charging

## Entities

### Sensors
| Entity | Description |
|--------|-------------|
| `sensor.amppilot_available_surplus` | Current surplus available for EVs (W) |
| `sensor.amppilot_charging_status` | Status text |
| `sensor.amppilot_solar_power` | Solar production (W) |
| `sensor.amppilot_grid_power` | Grid import/export (W) |
| `sensor.amppilot_home_load` | Home consumption (W) |
| `sensor.amppilot_battery_soc` | Home battery SoC (%) |
| `sensor.amppilot_battery_power` | Home battery power (W) |
| `sensor.amppilot_vehicle_1_power` | Vehicle 1 charging power (W) |
| `sensor.amppilot_vehicle_1_amps` | Vehicle 1 charging current (A) |
| `sensor.amppilot_vehicle_1_energy_session` | Session energy (kWh) |
| `sensor.amppilot_vehicle_1_energy_today` | Today's energy (kWh) |
| `sensor.amppilot_vehicle_2_*` | Same for vehicle 2 |

### Switches
| Entity | Description |
|--------|-------------|
| `switch.amppilot_solar_charging` | Enable/disable solar mode |
| `switch.amppilot_scheduled_charging` | Enable/disable schedules |
| `switch.amppilot_vehicle_1_enabled` | Include vehicle 1 |
| `switch.amppilot_vehicle_2_enabled` | Include vehicle 2 |

### Selects
| Entity | Description |
|--------|-------------|
| `select.amppilot_charging_mode` | off / solar / scheduled / boost |
| `select.amppilot_distribution_mode` | How to split power |
| `select.amppilot_priority_vehicle` | Priority vehicle |

### Numbers
| Entity | Description |
|--------|-------------|
| `number.amppilot_enable_threshold` | Surplus to start (W) |
| `number.amppilot_disable_threshold` | Surplus to stop (W) |
| `number.amppilot_enable_delay` | Delay before enabling (s) |
| `number.amppilot_disable_delay` | Delay before disabling (s) |
| `number.amppilot_household_buffer` | Reserved household power (W) |
| `number.amppilot_min_battery_soc` | Battery priority threshold (%) |
| `number.amppilot_vehicle_1_min_amps` | Vehicle 1 minimum amps |
| `number.amppilot_vehicle_1_max_amps` | Vehicle 1 maximum amps |
| `number.amppilot_vehicle_2_min_amps` | Vehicle 2 minimum amps |
| `number.amppilot_vehicle_2_max_amps` | Vehicle 2 maximum amps |

## Dashboard

A sample dashboard configuration is included in `dashboards/amppilot-dashboard.yaml`.

**Required HACS Frontend Cards:**
- power-flow-card-plus
- mushroom cards
- stack-in-card
- apexcharts-card (optional)

Copy the contents into your Lovelace dashboard configuration.

## Charging Modes

- **Off** - No charging
- **Solar** - Charge using available solar surplus only
- **Scheduled** - Charge during configured time windows
- **Boost** - Charge at maximum rate regardless of solar

## Distribution Logic

When both vehicles are connected:

1. **Enough surplus for both**: Split power evenly between vehicles
2. **Only enough for one**: Priority vehicle charges, secondary pauses
3. **Surplus drops mid-charge**: Secondary pauses first, priority continues at reduced rate

## Hysteresis

To prevent rapid on/off cycling:
- Charging only **starts** when surplus exceeds threshold for the configured delay
- Charging only **stops** when surplus drops below threshold for the configured delay

This prevents the charger from cycling on cloudy days.

## Debugging

Enable debug logging by adding to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.amppilot: debug
```

## Compatibility

AmpPilot is integration-agnostic and works with any Home Assistant setup that provides:

- **Solar/Grid sensors** - Any integration exposing power sensors (W)
- **Chargers** - Any charger with a controllable amperage number entity and on/off switch
- **Vehicles** - Any vehicle integration exposing SoC/charging state sensors (optional)

If your equipment exposes the right entities in Home Assistant, AmpPilot can use it.

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

MIT License
