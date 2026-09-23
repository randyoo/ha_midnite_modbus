"""The Midnite Solar custom component for Home Assistant."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .bridge import async_start_bridge, async_stop_bridge
from .const import (
    CONF_BRIDGE_ENABLED,
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_INTERVAL,
    DEFAULT_BRIDGE_ENABLED,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SENSOR_INTERVAL,
    DOMAIN,
)
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.TEXT,
    Platform.SELECT,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: Any) -> bool:
    """Set up the Midnite Solar component from YAML configuration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Midnite Solar from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    sensor_interval = entry.options.get(CONF_SENSOR_INTERVAL, DEFAULT_SENSOR_INTERVAL)

    _LOGGER.info(
        f"Setting up Midnite Solar at {host}:{port} (Classic polled every "
        f"{interval}s, sensors republished at most every {sensor_interval}s)"
    )

    # Create coordinator for data updates
    coordinator = MidniteSolarUpdateCoordinator(hass, host, port, interval, sensor_interval)

    # Publish the coordinator before the first refresh so the teardown below can
    # always find and undo it, and store it before connect so a failed connect
    # still leaves the socket to close.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Connect to the device and read initial data. If any of it fails the entry is
    # retried later, and Home Assistant never unloads an entry that failed setup -
    # the coordinator's socket is ours to close. On a device this integration
    # itself calls effectively single-connection, leaving an abandoned coordinator
    # holding the Classic's one session is what keeps a half-dead Classic wedged:
    # each retry opens a second connection on top of the first.
    try:
        connected = await hass.async_add_executor_job(coordinator.api.connect)
        # connect() answers with a bool; a refused-but-no-exception connect must not
        # be logged as a success and carried on from.
        if not connected:
            raise OSError("the device refused the Modbus connection")
        _LOGGER.info("Successfully connected to Midnite Solar device")
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        await _teardown_coordinator(hass, entry, coordinator)
        raise ConfigEntryNotReady("Could not connect to Midnite Solar device") from e

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    # The bridge (LAN API + mDNS record) comes up after the first refresh so
    # the identity it advertises is the Classic's own, and only when the
    # options say so; the record is withdrawn on every teardown path.
    bridge_enabled = bool(entry.options.get(CONF_BRIDGE_ENABLED, DEFAULT_BRIDGE_ENABLED))
    coordinator.bridge_enabled = bridge_enabled
    if bridge_enabled:
        await async_start_bridge(hass, entry, coordinator)

    # Register update listener to handle options changes, and undo it on unload.
    # add_update_listener appends to a list with no dedupe, so an unwrapped listener
    # accumulates one per reload and every later entry update fires all of them.
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def _teardown_coordinator(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: MidniteSolarUpdateCoordinator
) -> None:
    """Undo a coordinator we published but could not finish setting up."""
    # Drop it from hass.data first so nothing else can pick it up.
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    try:
        await coordinator.async_shutdown()
    except Exception as e:
        _LOGGER.error(f"Error shutting down coordinator after a failed setup: {e}")
    # Guarded so a socket that is already wedged cannot turn the cleanup into a
    # hang (which would block the retry Home Assistant is about to schedule).
    try:
        await hass.async_add_executor_job(coordinator.api.disconnect)
    except Exception as e:
        _LOGGER.error(f"Error disconnecting after a failed setup: {e}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

    # Pop with a default so a second unload cannot KeyError, and clean the
    # coordinator up whether or not the platforms reported success - otherwise a
    # failed platform unload leaves a live coordinator polling the single-connection
    # Classic forever.
    # Withdraw the advertisement before the socket closes, so no client is
    # sent to an address that just went quiet. Guarded: an entry that never
    # started its bridge has nothing to withdraw.
    try:
        await async_stop_bridge(hass, entry)
    except Exception as e:
        _LOGGER.error("Error stopping the bridge: %s", e)

    coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if coordinator is not None:
        _LOGGER.info("Disconnecting from Modbus device...")
        # Stop the coordinator first so its scheduled update can't keep polling
        # (and leave a second coordinator alive) after a reload.
        try:
            await coordinator.async_shutdown()
        except Exception as e:
            _LOGGER.error(f"Error shutting down coordinator: {e}")
        # Disconnect in the executor; guard it so a wedged socket can't block
        # the unload (which would make reload/delete hang).
        try:
            await hass.async_add_executor_job(coordinator.api.disconnect)
        except Exception as e:
            _LOGGER.error(f"Error disconnecting from Modbus device: {e}")

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle options updates."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    new_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    new_sensor = entry.options.get(CONF_SENSOR_INTERVAL, DEFAULT_SENSOR_INTERVAL)
    new_bridge = bool(entry.options.get(CONF_BRIDGE_ENABLED, DEFAULT_BRIDGE_ENABLED))
    # Reload only for the changes this integration actually acts on: the two
    # intervals and the bridge toggle. The listener fires on every
    # async_update_entry - including the ones the DHCP and reconfigure flows
    # make while they are already reloading the entry themselves. Reloading on
    # those too turns a single address change into concurrent reloads of a
    # single-connection Classic.
    if (
        coordinator is not None
        and getattr(coordinator, "interval", None) == new_interval
        and getattr(coordinator, "sensor_interval", DEFAULT_SENSOR_INTERVAL) == new_sensor
        and getattr(coordinator, "bridge_enabled", DEFAULT_BRIDGE_ENABLED) == new_bridge
    ):
        _LOGGER.debug(
            "Config entry updated but neither the poll interval (%s s), the "
            "sensor interval (%s s) nor the bridge (%s) changed; not reloading",
            new_interval,
            new_sensor,
            new_bridge,
        )
        return True

    _LOGGER.info("Options updated, reloading Midnite Solar integration")
    await hass.config_entries.async_reload(entry.entry_id)
    return True
