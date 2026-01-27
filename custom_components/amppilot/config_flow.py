"""Config flow for AmpPilot integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

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
    CONF_ENABLE_SCHEDULED,
    CONF_ENABLE_THRESHOLD,
    CONF_GRID_ENTITY,
    CONF_HOME_LOAD_ENTITY,
    CONF_HOUSEHOLD_BUFFER,
    CONF_MAX_AMPS,
    CONF_MIN_AMPS,
    CONF_MIN_BATTERY_SOC,
    CONF_MIN_SURPLUS_PER_VEHICLE,
    CONF_NAME,
    CONF_PHASES,
    CONF_PRIORITY_VEHICLE,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_END,
    CONF_SCHEDULE_START,
    CONF_SOLAR_ENTITY,
    CONF_VEHICLE_1,
    CONF_VEHICLE_2,
    CONF_VEHICLE_CHARGING_AMPS_ENTITY,
    CONF_VEHICLE_CHARGING_STATE_ENTITY,
    CONF_VEHICLE_CONNECTED_ENTITY,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_VOLTAGE,
    DAYS_OF_WEEK,
    DEFAULT_DISABLE_DELAY,
    DEFAULT_DISABLE_THRESHOLD,
    DEFAULT_ENABLE_DELAY,
    DEFAULT_ENABLE_THRESHOLD,
    DEFAULT_HOUSEHOLD_BUFFER,
    DEFAULT_MAX_AMPS,
    DEFAULT_MIN_AMPS,
    DEFAULT_MIN_BATTERY_SOC,
    DEFAULT_NAME,
    DEFAULT_PHASES,
    DEFAULT_VOLTAGE,
    DISTRIBUTION_SIMULTANEOUS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class AmpPilotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AmpPilot."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AmpPilotOptionsFlow:
        """Get the options flow for this handler."""
        return AmpPilotOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self._data[CONF_NAME] = user_input[CONF_NAME]
            return await self.async_step_power_monitoring()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
        )

    async def async_step_power_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle power monitoring configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery()

        return self.async_show_form(
            step_id="power_monitoring",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOLAR_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Required(CONF_GRID_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Required(CONF_HOME_LOAD_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                }
            ),
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle home battery configuration (optional)."""
        if user_input is not None:
            # Only store battery config if entities were selected
            if user_input.get(CONF_BATTERY_SOC_ENTITY):
                self._data[CONF_BATTERY_SOC_ENTITY] = user_input[CONF_BATTERY_SOC_ENTITY]
            if user_input.get(CONF_BATTERY_POWER_ENTITY):
                self._data[CONF_BATTERY_POWER_ENTITY] = user_input[CONF_BATTERY_POWER_ENTITY]
            self._data[CONF_MIN_BATTERY_SOC] = user_input.get(
                CONF_MIN_BATTERY_SOC, DEFAULT_MIN_BATTERY_SOC
            )
            return await self.async_step_vehicle_1()

        return self.async_show_form(
            step_id="battery",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_BATTERY_SOC_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="battery",
                        )
                    ),
                    vol.Optional(CONF_BATTERY_POWER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Optional(
                        CONF_MIN_BATTERY_SOC, default=DEFAULT_MIN_BATTERY_SOC
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=100, step=5, unit_of_measurement="%"
                        )
                    ),
                }
            ),
        )

    async def _validate_entity(self, entity_id: str) -> bool:
        """Validate that an entity exists and is available."""
        if not entity_id:
            return True  # Empty is valid for optional fields
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        if state.state in ("unavailable", "unknown"):
            return False
        return True

    async def async_step_vehicle_1(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle 1 configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate required entities
            if not user_input.get(CONF_CHARGER_SWITCH_ENTITY):
                errors[CONF_CHARGER_SWITCH_ENTITY] = "switch_required"
            elif not await self._validate_entity(user_input.get(CONF_CHARGER_SWITCH_ENTITY)):
                errors[CONF_CHARGER_SWITCH_ENTITY] = "entity_unavailable"

            if not user_input.get(CONF_CHARGER_AMPS_ENTITY):
                errors[CONF_CHARGER_AMPS_ENTITY] = "amps_required"
            elif not await self._validate_entity(user_input.get(CONF_CHARGER_AMPS_ENTITY)):
                errors[CONF_CHARGER_AMPS_ENTITY] = "entity_unavailable"

            if not errors:
                self._data[CONF_VEHICLE_1] = {
                    CONF_VEHICLE_NAME: user_input.get(CONF_VEHICLE_NAME, "Vehicle 1"),
                    CONF_CHARGER_SWITCH_ENTITY: user_input[CONF_CHARGER_SWITCH_ENTITY],
                    CONF_CHARGER_AMPS_ENTITY: user_input[CONF_CHARGER_AMPS_ENTITY],
                    CONF_VEHICLE_CONNECTED_ENTITY: user_input.get(CONF_VEHICLE_CONNECTED_ENTITY),
                    CONF_CHARGER_POWER_ENTITY: user_input.get(CONF_CHARGER_POWER_ENTITY),
                    CONF_VEHICLE_CHARGING_AMPS_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY),
                    CONF_VEHICLE_CHARGING_STATE_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_STATE_ENTITY),
                    CONF_VEHICLE_SOC_ENTITY: user_input.get(CONF_VEHICLE_SOC_ENTITY),
                    CONF_MIN_AMPS: user_input.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS),
                    CONF_MAX_AMPS: user_input.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS),
                    CONF_PHASES: user_input.get(CONF_PHASES, DEFAULT_PHASES),
                    CONF_VOLTAGE: user_input.get(CONF_VOLTAGE, DEFAULT_VOLTAGE),
                }
                return await self.async_step_vehicle_2()

        return self.async_show_form(
            step_id="vehicle_1",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_VEHICLE_NAME, default="Vehicle 1"): str,
                    vol.Required(CONF_CHARGER_SWITCH_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch"])
                    ),
                    vol.Required(CONF_CHARGER_AMPS_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["number"])
                    ),
                    vol.Optional(CONF_VEHICLE_CONNECTED_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor"])
                    ),
                    vol.Optional(CONF_CHARGER_POWER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Optional(CONF_VEHICLE_CHARGING_AMPS_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="current",
                        )
                    ),
                    vol.Optional(CONF_VEHICLE_CHARGING_STATE_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["sensor"])
                    ),
                    vol.Optional(CONF_VEHICLE_SOC_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="battery",
                        )
                    ),
                    vol.Optional(CONF_MIN_AMPS, default=DEFAULT_MIN_AMPS): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=32, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(CONF_MAX_AMPS, default=DEFAULT_MAX_AMPS): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=80, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(CONF_PHASES, default=DEFAULT_PHASES): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "1", "label": "Single Phase"},
                                {"value": "3", "label": "Three Phase"},
                            ]
                        )
                    ),
                    vol.Optional(CONF_VOLTAGE, default=DEFAULT_VOLTAGE): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=100, max=480, step=10, unit_of_measurement="V"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_vehicle_2(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle 2 configuration (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Only store vehicle 2 config if switch and amps entities were selected
            if user_input.get(CONF_CHARGER_SWITCH_ENTITY) or user_input.get(CONF_CHARGER_AMPS_ENTITY):
                # If one is provided, both are required
                if not user_input.get(CONF_CHARGER_SWITCH_ENTITY):
                    errors[CONF_CHARGER_SWITCH_ENTITY] = "switch_required"
                elif not await self._validate_entity(user_input.get(CONF_CHARGER_SWITCH_ENTITY)):
                    errors[CONF_CHARGER_SWITCH_ENTITY] = "entity_unavailable"

                if not user_input.get(CONF_CHARGER_AMPS_ENTITY):
                    errors[CONF_CHARGER_AMPS_ENTITY] = "amps_required"
                elif not await self._validate_entity(user_input.get(CONF_CHARGER_AMPS_ENTITY)):
                    errors[CONF_CHARGER_AMPS_ENTITY] = "entity_unavailable"

                if not errors:
                    self._data[CONF_VEHICLE_2] = {
                        CONF_VEHICLE_NAME: user_input.get(CONF_VEHICLE_NAME, "Vehicle 2"),
                        CONF_CHARGER_SWITCH_ENTITY: user_input[CONF_CHARGER_SWITCH_ENTITY],
                        CONF_CHARGER_AMPS_ENTITY: user_input[CONF_CHARGER_AMPS_ENTITY],
                        CONF_VEHICLE_CONNECTED_ENTITY: user_input.get(CONF_VEHICLE_CONNECTED_ENTITY),
                        CONF_CHARGER_POWER_ENTITY: user_input.get(CONF_CHARGER_POWER_ENTITY),
                        CONF_VEHICLE_CHARGING_AMPS_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY),
                        CONF_VEHICLE_CHARGING_STATE_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_STATE_ENTITY),
                        CONF_VEHICLE_SOC_ENTITY: user_input.get(CONF_VEHICLE_SOC_ENTITY),
                        CONF_MIN_AMPS: user_input.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS),
                        CONF_MAX_AMPS: user_input.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS),
                        CONF_PHASES: user_input.get(CONF_PHASES, DEFAULT_PHASES),
                        CONF_VOLTAGE: user_input.get(CONF_VOLTAGE, DEFAULT_VOLTAGE),
                    }

            if not errors:
                return await self.async_step_distribution()

        return self.async_show_form(
            step_id="vehicle_2",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_VEHICLE_NAME, default="Vehicle 2"): str,
                    vol.Optional(CONF_CHARGER_SWITCH_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch"])
                    ),
                    vol.Optional(CONF_CHARGER_AMPS_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["number"])
                    ),
                    vol.Optional(CONF_VEHICLE_CONNECTED_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor"])
                    ),
                    vol.Optional(CONF_CHARGER_POWER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Optional(CONF_VEHICLE_CHARGING_AMPS_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="current",
                        )
                    ),
                    vol.Optional(CONF_VEHICLE_CHARGING_STATE_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["sensor"])
                    ),
                    vol.Optional(CONF_VEHICLE_SOC_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="battery",
                        )
                    ),
                    vol.Optional(CONF_MIN_AMPS, default=DEFAULT_MIN_AMPS): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=32, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(CONF_MAX_AMPS, default=DEFAULT_MAX_AMPS): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=80, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(CONF_PHASES, default=DEFAULT_PHASES): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "1", "label": "Single Phase"},
                                {"value": "3", "label": "Three Phase"},
                            ]
                        )
                    ),
                    vol.Optional(CONF_VOLTAGE, default=DEFAULT_VOLTAGE): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=100, max=480, step=10, unit_of_measurement="V"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_distribution(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle power distribution configuration."""
        if user_input is not None:
            self._data[CONF_DISTRIBUTION_MODE] = user_input.get(
                CONF_DISTRIBUTION_MODE, DISTRIBUTION_SIMULTANEOUS
            )
            self._data[CONF_PRIORITY_VEHICLE] = user_input.get(
                CONF_PRIORITY_VEHICLE, "vehicle_1"
            )
            self._data[CONF_MIN_SURPLUS_PER_VEHICLE] = user_input.get(
                CONF_MIN_SURPLUS_PER_VEHICLE, 1400
            )
            return await self.async_step_thresholds()

        # Only show priority options if we have 2 vehicles
        has_vehicle_2 = CONF_VEHICLE_2 in self._data

        priority_options = [
            {"value": "vehicle_1", "label": self._data[CONF_VEHICLE_1].get(CONF_VEHICLE_NAME, "Vehicle 1")},
        ]
        if has_vehicle_2:
            priority_options.append(
                {"value": "vehicle_2", "label": self._data[CONF_VEHICLE_2].get(CONF_VEHICLE_NAME, "Vehicle 2")}
            )

        return self.async_show_form(
            step_id="distribution",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DISTRIBUTION_MODE, default=DISTRIBUTION_SIMULTANEOUS
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "simultaneous_split", "label": "Simultaneous Split"},
                                {"value": "priority_then_split", "label": "Priority Then Split"},
                                {"value": "priority_only", "label": "Priority Only"},
                            ]
                        )
                    ),
                    vol.Optional(CONF_PRIORITY_VEHICLE, default="vehicle_1"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=priority_options)
                    ),
                    vol.Optional(CONF_MIN_SURPLUS_PER_VEHICLE, default=1400): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=500, max=10000, step=100, unit_of_measurement="W"
                        )
                    ),
                }
            ),
        )

    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle threshold configuration."""
        if user_input is not None:
            self._data[CONF_ENABLE_THRESHOLD] = user_input.get(
                CONF_ENABLE_THRESHOLD, DEFAULT_ENABLE_THRESHOLD
            )
            self._data[CONF_ENABLE_DELAY] = user_input.get(
                CONF_ENABLE_DELAY, DEFAULT_ENABLE_DELAY
            )
            self._data[CONF_DISABLE_THRESHOLD] = user_input.get(
                CONF_DISABLE_THRESHOLD, DEFAULT_DISABLE_THRESHOLD
            )
            self._data[CONF_DISABLE_DELAY] = user_input.get(
                CONF_DISABLE_DELAY, DEFAULT_DISABLE_DELAY
            )
            self._data[CONF_HOUSEHOLD_BUFFER] = user_input.get(
                CONF_HOUSEHOLD_BUFFER, DEFAULT_HOUSEHOLD_BUFFER
            )
            return await self.async_step_schedule()

        return self.async_show_form(
            step_id="thresholds",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_THRESHOLD, default=DEFAULT_ENABLE_THRESHOLD
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10000, step=100, unit_of_measurement="W"
                        )
                    ),
                    vol.Optional(
                        CONF_ENABLE_DELAY, default=DEFAULT_ENABLE_DELAY
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=600, step=10, unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        CONF_DISABLE_THRESHOLD, default=DEFAULT_DISABLE_THRESHOLD
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=-5000, max=5000, step=100, unit_of_measurement="W"
                        )
                    ),
                    vol.Optional(
                        CONF_DISABLE_DELAY, default=DEFAULT_DISABLE_DELAY
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=600, step=10, unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        CONF_HOUSEHOLD_BUFFER, default=DEFAULT_HOUSEHOLD_BUFFER
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=2000, step=50, unit_of_measurement="W"
                        )
                    ),
                }
            ),
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle scheduled charging configuration (optional)."""
        if user_input is not None:
            self._data[CONF_ENABLE_SCHEDULED] = user_input.get(CONF_ENABLE_SCHEDULED, False)
            if self._data[CONF_ENABLE_SCHEDULED]:
                self._data[CONF_SCHEDULE_START] = user_input.get(CONF_SCHEDULE_START)
                self._data[CONF_SCHEDULE_END] = user_input.get(CONF_SCHEDULE_END)
                self._data[CONF_SCHEDULE_DAYS] = user_input.get(CONF_SCHEDULE_DAYS, DAYS_OF_WEEK)

            # Create the config entry
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
            )

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ENABLE_SCHEDULED, default=False): selector.BooleanSelector(),
                    vol.Optional(CONF_SCHEDULE_START): selector.TimeSelector(),
                    vol.Optional(CONF_SCHEDULE_END): selector.TimeSelector(),
                    vol.Optional(CONF_SCHEDULE_DAYS, default=DAYS_OF_WEEK): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "mon", "label": "Monday"},
                                {"value": "tue", "label": "Tuesday"},
                                {"value": "wed", "label": "Wednesday"},
                                {"value": "thu", "label": "Thursday"},
                                {"value": "fri", "label": "Friday"},
                                {"value": "sat", "label": "Saturday"},
                                {"value": "sun", "label": "Sunday"},
                            ],
                            multiple=True,
                        )
                    ),
                }
            ),
        )


class AmpPilotOptionsFlow(OptionsFlow):
    """Handle AmpPilot options - goes through the full config flow."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial options step - start from power monitoring."""
        # Copy existing config as starting point
        self._data = dict(self.config_entry.data)
        return await self.async_step_power_monitoring()

    async def async_step_power_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle power monitoring configuration."""
        if user_input is not None:
            self._data[CONF_SOLAR_ENTITY] = user_input[CONF_SOLAR_ENTITY]
            self._data[CONF_GRID_ENTITY] = user_input[CONF_GRID_ENTITY]
            self._data[CONF_HOME_LOAD_ENTITY] = user_input[CONF_HOME_LOAD_ENTITY]
            return await self.async_step_battery()

        data = self._data

        return self.async_show_form(
            step_id="power_monitoring",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SOLAR_ENTITY,
                        default=data.get(CONF_SOLAR_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Required(
                        CONF_GRID_ENTITY,
                        default=data.get(CONF_GRID_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Required(
                        CONF_HOME_LOAD_ENTITY,
                        default=data.get(CONF_HOME_LOAD_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                }
            ),
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle home battery configuration (optional)."""
        if user_input is not None:
            # Clear old values first
            self._data.pop(CONF_BATTERY_SOC_ENTITY, None)
            self._data.pop(CONF_BATTERY_POWER_ENTITY, None)
            # Only store battery config if entities were selected
            if user_input.get(CONF_BATTERY_SOC_ENTITY):
                self._data[CONF_BATTERY_SOC_ENTITY] = user_input[CONF_BATTERY_SOC_ENTITY]
            if user_input.get(CONF_BATTERY_POWER_ENTITY):
                self._data[CONF_BATTERY_POWER_ENTITY] = user_input[CONF_BATTERY_POWER_ENTITY]
            self._data[CONF_MIN_BATTERY_SOC] = user_input.get(
                CONF_MIN_BATTERY_SOC, DEFAULT_MIN_BATTERY_SOC
            )
            return await self.async_step_vehicle_1()

        data = self._data

        return self.async_show_form(
            step_id="battery",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_BATTERY_SOC_ENTITY,
                        default=data.get(CONF_BATTERY_SOC_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="battery",
                        )
                    ),
                    vol.Optional(
                        CONF_BATTERY_POWER_ENTITY,
                        default=data.get(CONF_BATTERY_POWER_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Optional(
                        CONF_MIN_BATTERY_SOC,
                        default=data.get(CONF_MIN_BATTERY_SOC, DEFAULT_MIN_BATTERY_SOC),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=100, step=5, unit_of_measurement="%"
                        )
                    ),
                }
            ),
        )

    async def async_step_vehicle_1(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle 1 configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate required entities
            if not user_input.get(CONF_CHARGER_SWITCH_ENTITY):
                errors[CONF_CHARGER_SWITCH_ENTITY] = "switch_required"
            if not user_input.get(CONF_CHARGER_AMPS_ENTITY):
                errors[CONF_CHARGER_AMPS_ENTITY] = "amps_required"

            if not errors:
                self._data[CONF_VEHICLE_1] = {
                    CONF_VEHICLE_NAME: user_input.get(CONF_VEHICLE_NAME, "Vehicle 1"),
                    CONF_CHARGER_SWITCH_ENTITY: user_input[CONF_CHARGER_SWITCH_ENTITY],
                    CONF_CHARGER_AMPS_ENTITY: user_input[CONF_CHARGER_AMPS_ENTITY],
                    CONF_VEHICLE_CONNECTED_ENTITY: user_input.get(CONF_VEHICLE_CONNECTED_ENTITY),
                    CONF_CHARGER_POWER_ENTITY: user_input.get(CONF_CHARGER_POWER_ENTITY),
                    CONF_VEHICLE_CHARGING_AMPS_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY),
                    CONF_VEHICLE_CHARGING_STATE_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_STATE_ENTITY),
                    CONF_VEHICLE_SOC_ENTITY: user_input.get(CONF_VEHICLE_SOC_ENTITY),
                    CONF_MIN_AMPS: user_input.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS),
                    CONF_MAX_AMPS: user_input.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS),
                    CONF_PHASES: user_input.get(CONF_PHASES, DEFAULT_PHASES),
                    CONF_VOLTAGE: user_input.get(CONF_VOLTAGE, DEFAULT_VOLTAGE),
                }
                return await self.async_step_vehicle_2()

        v1_config = self._data.get(CONF_VEHICLE_1, {})

        return self.async_show_form(
            step_id="vehicle_1",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_VEHICLE_NAME,
                        default=v1_config.get(CONF_VEHICLE_NAME, "Vehicle 1"),
                    ): str,
                    vol.Required(
                        CONF_CHARGER_SWITCH_ENTITY,
                        default=v1_config.get(CONF_CHARGER_SWITCH_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch"])
                    ),
                    vol.Required(
                        CONF_CHARGER_AMPS_ENTITY,
                        default=v1_config.get(CONF_CHARGER_AMPS_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["number"])
                    ),
                    vol.Optional(
                        CONF_VEHICLE_CONNECTED_ENTITY,
                        default=v1_config.get(CONF_VEHICLE_CONNECTED_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor"])
                    ),
                    vol.Optional(
                        CONF_CHARGER_POWER_ENTITY,
                        default=v1_config.get(CONF_CHARGER_POWER_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Optional(
                        CONF_VEHICLE_CHARGING_AMPS_ENTITY,
                        default=v1_config.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="current",
                        )
                    ),
                    vol.Optional(
                        CONF_VEHICLE_CHARGING_STATE_ENTITY,
                        default=v1_config.get(CONF_VEHICLE_CHARGING_STATE_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["sensor"])
                    ),
                    vol.Optional(
                        CONF_VEHICLE_SOC_ENTITY,
                        default=v1_config.get(CONF_VEHICLE_SOC_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="battery",
                        )
                    ),
                    vol.Optional(
                        CONF_MIN_AMPS,
                        default=v1_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=32, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(
                        CONF_MAX_AMPS,
                        default=v1_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=80, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(
                        CONF_PHASES,
                        default=v1_config.get(CONF_PHASES, DEFAULT_PHASES),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "1", "label": "Single Phase"},
                                {"value": "3", "label": "Three Phase"},
                            ]
                        )
                    ),
                    vol.Optional(
                        CONF_VOLTAGE,
                        default=v1_config.get(CONF_VOLTAGE, DEFAULT_VOLTAGE),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=100, max=480, step=10, unit_of_measurement="V"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_vehicle_2(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle 2 configuration (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Only store vehicle 2 config if switch and amps entities were selected
            if user_input.get(CONF_CHARGER_SWITCH_ENTITY) or user_input.get(CONF_CHARGER_AMPS_ENTITY):
                # If one is provided, both are required
                if not user_input.get(CONF_CHARGER_SWITCH_ENTITY):
                    errors[CONF_CHARGER_SWITCH_ENTITY] = "switch_required"
                if not user_input.get(CONF_CHARGER_AMPS_ENTITY):
                    errors[CONF_CHARGER_AMPS_ENTITY] = "amps_required"

                if not errors:
                    self._data[CONF_VEHICLE_2] = {
                        CONF_VEHICLE_NAME: user_input.get(CONF_VEHICLE_NAME, "Vehicle 2"),
                        CONF_CHARGER_SWITCH_ENTITY: user_input[CONF_CHARGER_SWITCH_ENTITY],
                        CONF_CHARGER_AMPS_ENTITY: user_input[CONF_CHARGER_AMPS_ENTITY],
                        CONF_VEHICLE_CONNECTED_ENTITY: user_input.get(CONF_VEHICLE_CONNECTED_ENTITY),
                        CONF_CHARGER_POWER_ENTITY: user_input.get(CONF_CHARGER_POWER_ENTITY),
                        CONF_VEHICLE_CHARGING_AMPS_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY),
                        CONF_VEHICLE_CHARGING_STATE_ENTITY: user_input.get(CONF_VEHICLE_CHARGING_STATE_ENTITY),
                        CONF_VEHICLE_SOC_ENTITY: user_input.get(CONF_VEHICLE_SOC_ENTITY),
                        CONF_MIN_AMPS: user_input.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS),
                        CONF_MAX_AMPS: user_input.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS),
                        CONF_PHASES: user_input.get(CONF_PHASES, DEFAULT_PHASES),
                        CONF_VOLTAGE: user_input.get(CONF_VOLTAGE, DEFAULT_VOLTAGE),
                    }
            else:
                # No vehicle 2 configured, remove it if it existed
                self._data.pop(CONF_VEHICLE_2, None)

            if not errors:
                return await self.async_step_distribution()

        v2_config = self._data.get(CONF_VEHICLE_2, {})

        return self.async_show_form(
            step_id="vehicle_2",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_VEHICLE_NAME,
                        default=v2_config.get(CONF_VEHICLE_NAME, "Vehicle 2"),
                    ): str,
                    vol.Optional(
                        CONF_CHARGER_SWITCH_ENTITY,
                        default=v2_config.get(CONF_CHARGER_SWITCH_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch"])
                    ),
                    vol.Optional(
                        CONF_CHARGER_AMPS_ENTITY,
                        default=v2_config.get(CONF_CHARGER_AMPS_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["number"])
                    ),
                    vol.Optional(
                        CONF_VEHICLE_CONNECTED_ENTITY,
                        default=v2_config.get(CONF_VEHICLE_CONNECTED_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor"])
                    ),
                    vol.Optional(
                        CONF_CHARGER_POWER_ENTITY,
                        default=v2_config.get(CONF_CHARGER_POWER_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="power",
                        )
                    ),
                    vol.Optional(
                        CONF_VEHICLE_CHARGING_AMPS_ENTITY,
                        default=v2_config.get(CONF_VEHICLE_CHARGING_AMPS_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="current",
                        )
                    ),
                    vol.Optional(
                        CONF_VEHICLE_CHARGING_STATE_ENTITY,
                        default=v2_config.get(CONF_VEHICLE_CHARGING_STATE_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["sensor"])
                    ),
                    vol.Optional(
                        CONF_VEHICLE_SOC_ENTITY,
                        default=v2_config.get(CONF_VEHICLE_SOC_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="battery",
                        )
                    ),
                    vol.Optional(
                        CONF_MIN_AMPS,
                        default=v2_config.get(CONF_MIN_AMPS, DEFAULT_MIN_AMPS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=32, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(
                        CONF_MAX_AMPS,
                        default=v2_config.get(CONF_MAX_AMPS, DEFAULT_MAX_AMPS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=80, step=1, unit_of_measurement="A"
                        )
                    ),
                    vol.Optional(
                        CONF_PHASES,
                        default=v2_config.get(CONF_PHASES, DEFAULT_PHASES),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "1", "label": "Single Phase"},
                                {"value": "3", "label": "Three Phase"},
                            ]
                        )
                    ),
                    vol.Optional(
                        CONF_VOLTAGE,
                        default=v2_config.get(CONF_VOLTAGE, DEFAULT_VOLTAGE),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=100, max=480, step=10, unit_of_measurement="V"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_distribution(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle power distribution configuration."""
        if user_input is not None:
            self._data[CONF_DISTRIBUTION_MODE] = user_input.get(
                CONF_DISTRIBUTION_MODE, DISTRIBUTION_SIMULTANEOUS
            )
            self._data[CONF_PRIORITY_VEHICLE] = user_input.get(
                CONF_PRIORITY_VEHICLE, "vehicle_1"
            )
            self._data[CONF_MIN_SURPLUS_PER_VEHICLE] = user_input.get(
                CONF_MIN_SURPLUS_PER_VEHICLE, 1400
            )
            return await self.async_step_thresholds()

        data = self._data

        # Build priority options based on configured vehicles
        priority_options = [
            {"value": "vehicle_1", "label": self._data.get(CONF_VEHICLE_1, {}).get(CONF_VEHICLE_NAME, "Vehicle 1")},
        ]
        if CONF_VEHICLE_2 in self._data:
            priority_options.append(
                {"value": "vehicle_2", "label": self._data.get(CONF_VEHICLE_2, {}).get(CONF_VEHICLE_NAME, "Vehicle 2")}
            )

        return self.async_show_form(
            step_id="distribution",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DISTRIBUTION_MODE,
                        default=data.get(CONF_DISTRIBUTION_MODE, DISTRIBUTION_SIMULTANEOUS),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "simultaneous_split", "label": "Simultaneous Split"},
                                {"value": "priority_then_split", "label": "Priority Then Split"},
                                {"value": "priority_only", "label": "Priority Only"},
                            ]
                        )
                    ),
                    vol.Optional(
                        CONF_PRIORITY_VEHICLE,
                        default=data.get(CONF_PRIORITY_VEHICLE, "vehicle_1"),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=priority_options)
                    ),
                    vol.Optional(
                        CONF_MIN_SURPLUS_PER_VEHICLE,
                        default=data.get(CONF_MIN_SURPLUS_PER_VEHICLE, 1400),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=500, max=10000, step=100, unit_of_measurement="W"
                        )
                    ),
                }
            ),
        )

    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle threshold configuration."""
        if user_input is not None:
            self._data[CONF_ENABLE_THRESHOLD] = user_input.get(
                CONF_ENABLE_THRESHOLD, DEFAULT_ENABLE_THRESHOLD
            )
            self._data[CONF_ENABLE_DELAY] = user_input.get(
                CONF_ENABLE_DELAY, DEFAULT_ENABLE_DELAY
            )
            self._data[CONF_DISABLE_THRESHOLD] = user_input.get(
                CONF_DISABLE_THRESHOLD, DEFAULT_DISABLE_THRESHOLD
            )
            self._data[CONF_DISABLE_DELAY] = user_input.get(
                CONF_DISABLE_DELAY, DEFAULT_DISABLE_DELAY
            )
            self._data[CONF_HOUSEHOLD_BUFFER] = user_input.get(
                CONF_HOUSEHOLD_BUFFER, DEFAULT_HOUSEHOLD_BUFFER
            )
            return await self.async_step_schedule()

        data = self._data

        return self.async_show_form(
            step_id="thresholds",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_THRESHOLD,
                        default=data.get(CONF_ENABLE_THRESHOLD, DEFAULT_ENABLE_THRESHOLD),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10000, step=100, unit_of_measurement="W"
                        )
                    ),
                    vol.Optional(
                        CONF_ENABLE_DELAY,
                        default=data.get(CONF_ENABLE_DELAY, DEFAULT_ENABLE_DELAY),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=600, step=10, unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        CONF_DISABLE_THRESHOLD,
                        default=data.get(CONF_DISABLE_THRESHOLD, DEFAULT_DISABLE_THRESHOLD),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=-5000, max=5000, step=100, unit_of_measurement="W"
                        )
                    ),
                    vol.Optional(
                        CONF_DISABLE_DELAY,
                        default=data.get(CONF_DISABLE_DELAY, DEFAULT_DISABLE_DELAY),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=600, step=10, unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        CONF_HOUSEHOLD_BUFFER,
                        default=data.get(CONF_HOUSEHOLD_BUFFER, DEFAULT_HOUSEHOLD_BUFFER),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=2000, step=50, unit_of_measurement="W"
                        )
                    ),
                }
            ),
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle scheduled charging configuration (optional)."""
        if user_input is not None:
            self._data[CONF_ENABLE_SCHEDULED] = user_input.get(CONF_ENABLE_SCHEDULED, False)
            if self._data[CONF_ENABLE_SCHEDULED]:
                self._data[CONF_SCHEDULE_START] = user_input.get(CONF_SCHEDULE_START)
                self._data[CONF_SCHEDULE_END] = user_input.get(CONF_SCHEDULE_END)
                self._data[CONF_SCHEDULE_DAYS] = user_input.get(CONF_SCHEDULE_DAYS, DAYS_OF_WEEK)
            else:
                # Clear schedule data if disabled
                self._data.pop(CONF_SCHEDULE_START, None)
                self._data.pop(CONF_SCHEDULE_END, None)
                self._data.pop(CONF_SCHEDULE_DAYS, None)

            # Save and finish
            return self._save_options()

        data = self._data

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_SCHEDULED,
                        default=data.get(CONF_ENABLE_SCHEDULED, False),
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_SCHEDULE_START,
                        default=data.get(CONF_SCHEDULE_START),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_SCHEDULE_END,
                        default=data.get(CONF_SCHEDULE_END),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_SCHEDULE_DAYS,
                        default=data.get(CONF_SCHEDULE_DAYS, DAYS_OF_WEEK),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "mon", "label": "Monday"},
                                {"value": "tue", "label": "Tuesday"},
                                {"value": "wed", "label": "Wednesday"},
                                {"value": "thu", "label": "Thursday"},
                                {"value": "fri", "label": "Friday"},
                                {"value": "sat", "label": "Saturday"},
                                {"value": "sun", "label": "Sunday"},
                            ],
                            multiple=True,
                        )
                    ),
                }
            ),
        )

    def _save_options(self) -> FlowResult:
        """Save the options by updating config entry data."""
        # Update the config entry data directly
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=self._data,
        )

        return self.async_create_entry(title="", data={})
