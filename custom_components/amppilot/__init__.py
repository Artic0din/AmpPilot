"""AmpPilot - Solar-aware dual-EV charging for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHARGER_SWITCH_ENTITY,
    CONF_VEHICLE_1,
    CONF_VEHICLE_2,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AmpPilotCoordinator

_LOGGER = logging.getLogger(__name__)

type AmpPilotConfigEntry = ConfigEntry[AmpPilotCoordinator]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version."""
    _LOGGER.debug("Migrating AmpPilot config entry from version %s", config_entry.version)

    if config_entry.version == 1:
        # Version 1 -> 2: Add charger_switch_entity to vehicle configs
        new_data = {**config_entry.data}

        # Add empty switch entity to vehicle 1 if missing
        if CONF_VEHICLE_1 in new_data:
            v1_config = {**new_data[CONF_VEHICLE_1]}
            if CONF_CHARGER_SWITCH_ENTITY not in v1_config:
                v1_config[CONF_CHARGER_SWITCH_ENTITY] = None
                _LOGGER.info(
                    "Migration: Added empty charger_switch_entity to Vehicle 1. "
                    "Please reconfigure to select your charger switch."
                )
            new_data[CONF_VEHICLE_1] = v1_config

        # Add empty switch entity to vehicle 2 if present and missing
        if CONF_VEHICLE_2 in new_data:
            v2_config = {**new_data[CONF_VEHICLE_2]}
            if CONF_CHARGER_SWITCH_ENTITY not in v2_config:
                v2_config[CONF_CHARGER_SWITCH_ENTITY] = None
                _LOGGER.info(
                    "Migration: Added empty charger_switch_entity to Vehicle 2. "
                    "Please reconfigure to select your charger switch."
                )
            new_data[CONF_VEHICLE_2] = v2_config

        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=2,
        )
        _LOGGER.info("Migration to version 2 successful")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: AmpPilotConfigEntry) -> bool:
    """Set up AmpPilot from a config entry."""
    _LOGGER.debug("Setting up AmpPilot integration")

    coordinator = AmpPilotCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("AmpPilot integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AmpPilotConfigEntry) -> bool:
    """Unload AmpPilot config entry."""
    _LOGGER.debug("Unloading AmpPilot integration")

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: AmpPilotConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Options updated, reloading AmpPilot integration")
    await hass.config_entries.async_reload(entry.entry_id)
