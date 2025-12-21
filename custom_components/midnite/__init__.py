"""The Midnite Solar custom component for Home Assistant."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.TEXT,
    Platform.SELECT,
]


async def async_setup(hass: HomeAssistant, config: Any) -> bool:
    """Set up the Midnite Solar component from YAML configuration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Midnite Solar from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    interval = entry.options.get("scan_interval", 15)

    _LOGGER.info(f"Setting up Midnite Solar at {host}:{port}")

    # Create coordinator for data updates
    coordinator = MidniteSolarUpdateCoordinator(hass, host, port, interval)

    # Connect to the device and read initial data
    try:
        await hass.async_add_executor_job(coordinator.api.connect)
        _LOGGER.info("Successfully connected to Midnite Solar device")
    except Exception as e:
        _LOGGER.error(f"Failed to connect to Midnite Solar device: {e}")
        raise ConfigEntryNotReady("Could not connect to Midnite Solar device") from e

    # Store the coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    # Register update listener to handle options changes
    entry.add_update_listener(update_listener)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Disconnecting from Modbus device...")
        await hass.async_add_executor_job(coordinator.api.disconnect)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle options updates."""
    _LOGGER.info("Options updated, reloading Midnite Solar integration")
    
    await hass.config_entries.async_reload(entry.entry_id)
    return True
