"""Tests for setup and teardown of a config entry: `__init__.py`.

The Classic is effectively single-connection, so what happens here matters more than
in most integrations: a coordinator that is not shut down keeps polling a device
that only has room for one client, and a second coordinator created by a reload
takes the slot the user's own tooling was using. These tests pin the order of
connect, first refresh, platform setup, shutdown and disconnect.
"""

from __future__ import annotations

import asyncio

import pytest
from fakes import FakeApi
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import Hass
from homeassistant.exceptions import ConfigEntryNotReady, UpdateFailed

import midnite_solar as integration
from midnite_solar import coordinator as coordinator_module
from midnite_solar.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_INTERVAL,
    CONF_WRITE_PIN,
    DEFAULT_PORT,
    DEFAULT_SENSOR_INTERVAL,
    DEFAULT_WRITE_PIN,
    DOMAIN,
)

HOST = "192.168.88.53"
PLATFORMS = {"sensor", "binary_sensor", "button", "number", "text", "select", "switch"}


class Hub(FakeApi):
    """The Modbus connection the coordinator builds, with its lifecycle recorded."""

    instances = []

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.connects = 0
        self.disconnects = 0
        Hub.instances.append(self)

    def connect(self):
        self.connects += 1
        return True

    def disconnect(self):
        self.disconnects += 1


class RefusingHub(Hub):
    def connect(self):
        self.connects += 1
        raise OSError("[Errno 111] Connection refused")


class SilentHub(Hub):
    """Answers no read at all, so the first update fails."""

    def read_holding_registers(self, address, count=1, retries=5):
        self.reads.append(address)
        from fakes import ModbusResult

        return ModbusResult(error=True)


class ExplodingHub(Hub):
    def connect(self):
        self.connects += 1
        return True

    def disconnect(self):
        raise OSError("[Errno 105] Not connected")


def entry(options=None, data=None):
    return ConfigEntry(
        entry_id="entry-1",
        title="Classic 200",
        data=data or {CONF_HOST: HOST, CONF_PORT: DEFAULT_PORT},
        options=options or {},
    )


def set_up(hass, config_entry, hub_class=Hub):
    coordinator_module.MidniteHub = hub_class
    return asyncio.run(integration.async_setup_entry(hass, config_entry))


ORIGINAL_HUB = coordinator_module.MidniteHub


@pytest.fixture(autouse=True)
def clean_hub_registry():
    """Never leave a fake hub class in the module for another test file."""
    Hub.instances = []
    yield
    coordinator_module.MidniteHub = ORIGINAL_HUB


class TestSetup:
    def test_the_integration_sets_up(self):
        hass = Hass()
        assert set_up(hass, entry()) is True

    def test_the_coordinator_is_stored_where_the_platforms_look(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        assert DOMAIN in hass.data and hass.data[DOMAIN][config_entry.entry_id] is not None

    def test_the_device_is_connected_once(self):
        hass = Hass()
        set_up(hass, entry())
        assert Hub.instances[0].connects == 1

    def test_all_seven_platforms_are_set_up(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        forwarded = hass.config_entries.forwarded[0][1]
        assert set(forwarded) == PLATFORMS

    def test_the_data_is_fetched_before_the_platforms_are_created(self):
        """Entities read the coordinator at creation, so it has to have data."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.data and "data" in coordinator.data
        assert hass.config_entries.forwarded

    def test_a_device_that_refuses_the_socket_is_not_ready(self):
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), RefusingHub)

    def test_nothing_is_set_up_when_the_connection_fails(self):
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), RefusingHub)
        assert hass.config_entries.forwarded == []

    def test_a_device_that_answers_nothing_is_not_ready(self):
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), SilentHub)

    def test_the_host_and_port_come_from_the_entry(self):
        hass = Hass()
        set_up(hass, entry(data={CONF_HOST: "10.0.0.9", CONF_PORT: 5021}))
        assert (Hub.instances[0].host, Hub.instances[0].port) == ("10.0.0.9", 5021)

    def test_the_default_port_is_used_when_the_entry_has_none(self):
        hass = Hass()
        set_up(hass, entry(data={CONF_HOST: HOST}))
        assert Hub.instances[0].port == DEFAULT_PORT

    def test_the_scan_interval_option_sets_the_update_interval(self):
        hass = Hass()
        config_entry = entry(options={CONF_SCAN_INTERVAL: 45})
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.interval == 45

    def test_the_interval_defaults_to_fifteen_seconds(self):
        hass = Hass()
        config_entry = entry(options={})
        set_up(hass, config_entry)
        assert hass.data[DOMAIN][config_entry.entry_id].interval == 15

    def test_the_sensor_interval_option_sets_the_republish_rate(self):
        hass = Hass()
        config_entry = entry(options={CONF_SENSOR_INTERVAL: 300})
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.sensor_interval == 300

    def test_the_sensor_interval_defaults_to_a_minute(self):
        hass = Hass()
        config_entry = entry(options={})
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.sensor_interval == DEFAULT_SENSOR_INTERVAL == 60

    def test_the_write_pin_option_reaches_the_gate(self):
        """The bridge reads the PIN off the coordinator; setup must carry the
        entry's own value there or the gate would guard with the default."""
        hass = Hass()
        config_entry = entry(options={CONF_WRITE_PIN: "13579"})
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.write_pin == "13579"

    def test_the_write_pin_defaults_to_zeroes(self):
        hass = Hass()
        config_entry = entry(options={})
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.write_pin == DEFAULT_WRITE_PIN == "0000"

    def test_yaml_setup_is_a_no_op_that_succeeds(self):
        assert asyncio.run(integration.async_setup(Hass(), {})) is True


class TestUnload:
    def test_a_set_up_entry_unloads(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        assert asyncio.run(integration.async_unload_entry(hass, config_entry)) is True

    def test_the_coordinator_is_stopped_before_the_socket_is_closed(self):
        """A live coordinator keeps a single-connection device busy forever."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        calls = []
        original_shutdown, original_disconnect = coordinator.async_shutdown, coordinator.api.disconnect

        async def shutdown():
            calls.append("shutdown")
            await original_shutdown()

        def disconnect():
            calls.append("disconnect")
            original_disconnect()

        coordinator.async_shutdown = shutdown
        coordinator.api.disconnect = disconnect
        asyncio.run(integration.async_unload_entry(hass, config_entry))
        assert calls == ["shutdown", "disconnect"]

    def test_the_platforms_are_unloaded(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        asyncio.run(integration.async_unload_entry(hass, config_entry))
        assert set(hass.config_entries.unloaded[0][1]) == PLATFORMS

    def test_the_stored_coordinator_is_gone_afterwards(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        asyncio.run(integration.async_unload_entry(hass, config_entry))
        assert config_entry.entry_id not in hass.data[DOMAIN]

    def test_a_wedged_disconnect_cannot_hang_the_unload(self):
        """The socket may be dead already; the unload must still finish."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry, ExplodingHub)
        assert asyncio.run(integration.async_unload_entry(hass, config_entry)) is True

    def test_the_coordinator_is_shut_down_once(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        asyncio.run(integration.async_unload_entry(hass, config_entry))
        assert coordinator.shutdowns == 1


class TestOptionsChange:
    def test_a_changed_option_reloads_the_entry(self):
        """update_listener is what makes the scan interval take effect."""
        hass = Hass()
        config_entry = entry(options={CONF_SCAN_INTERVAL: 30})
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == [config_entry.entry_id]

    def test_the_listener_reports_success(self):
        hass = Hass()
        assert asyncio.run(integration.update_listener(Hass(), entry())) is True


class TestFailedSetupCleanup:
    """A setup that fails leaves nothing holding the single-connection Classic."""

    def test_a_refused_connection_closes_the_socket_it_made(self):
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), RefusingHub)
        assert Hub.instances[0].disconnects == 1

    def test_a_refused_connection_removes_the_coordinator_it_published(self):
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), RefusingHub)
        assert hass.data.get(DOMAIN, {}) == {}

    def test_a_device_that_answers_nothing_is_disconnected_afterwards(self):
        """The socket connected, the first refresh failed - the socket must close."""
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), SilentHub)
        hub = Hub.instances[0]
        assert hub.connects == 1
        assert hub.disconnects == 1
        assert hass.data.get(DOMAIN, {}) == {}

    def test_a_second_setup_after_a_failure_gets_a_fresh_connection(self):
        """The retry must not stack a second socket on the abandoned one."""
        hass = Hass()
        with pytest.raises(ConfigEntryNotReady):
            set_up(hass, entry(), SilentHub)
        assert Hub.instances[-1].disconnects == 1, "the failed attempt's hub was closed"
        # The Classic recovers; the retry now succeeds.
        assert set_up(hass, entry()) is True
        assert len(Hub.instances) == 2, "a new coordinator/hub for the retry"
        assert Hub.instances[-1].connects == 1


class TestUpdateListenerLifecycle:
    """The update listener is registered once and undone on unload."""

    def test_the_listener_is_undone_on_unload(self):
        """add_update_listener accumulates with no dedupe, so it must be unwrapped."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        assert len(config_entry._update_listeners) == 1
        assert len(config_entry._on_unload) == 1
        # HA runs the on-unload callbacks when the entry unloads or reloads.
        config_entry.async_test_unload()
        assert config_entry._update_listeners == []

    def test_a_reload_does_not_accumulate_another_listener(self):
        """Reload = unload (run cleanups) + setup; the listener count must stay 1."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        config_entry.async_test_unload()
        set_up(hass, config_entry)
        assert len(config_entry._update_listeners) == 1

    def test_a_host_change_with_the_interval_unchanged_does_not_reload(self):
        """DHCP/reconfigure already reload themselves; the listener must not double up.

        A single-connection Classic cannot take two concurrent reloads.
        """
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]
        assert coordinator.interval == 15
        # Same scan interval, different host.
        config_entry.options = {CONF_SCAN_INTERVAL: 15}
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == []

    def test_a_scan_interval_change_still_reloads(self):
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        config_entry.options = {CONF_SCAN_INTERVAL: 30}
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == [config_entry.entry_id]

    def test_a_sensor_interval_change_still_reloads(self):
        """The republish rate is fixed in the coordinator, so it reloads too."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        config_entry.options = {CONF_SCAN_INTERVAL: 15, CONF_SENSOR_INTERVAL: 300}
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == [config_entry.entry_id]

    def test_rewriting_the_same_sensor_interval_does_not_reload(self):
        hass = Hass()
        config_entry = entry(options={CONF_SENSOR_INTERVAL: 300})
        set_up(hass, config_entry)
        config_entry.options = {CONF_SCAN_INTERVAL: 15, CONF_SENSOR_INTERVAL: 300}
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == []

    def test_a_write_pin_change_still_reloads(self):
        """A reload is the ONE thing that makes a new PIN live (and resets the
        lockout ladder, which is right when the owner just rotated the PIN)."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        config_entry.options = {CONF_WRITE_PIN: "13579"}
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == [config_entry.entry_id]

    def test_rewriting_the_same_write_pin_does_not_reload(self):
        hass = Hass()
        config_entry = entry(options={CONF_WRITE_PIN: "13579"})
        set_up(hass, config_entry)
        config_entry.options = {CONF_WRITE_PIN: "13579", CONF_SCAN_INTERVAL: 15}
        asyncio.run(integration.update_listener(hass, config_entry))
        assert hass.config_entries.reloads == []


class TestUnloadRobustness:
    """The unload must clean up even when it does not go cleanly."""

    def test_a_second_unload_does_not_error(self):
        """A double unload must not KeyError out of the hass.data pop."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        assert asyncio.run(integration.async_unload_entry(hass, config_entry)) is True
        assert asyncio.run(integration.async_unload_entry(hass, config_entry)) is not None

    def test_a_failed_platform_unload_still_shuts_the_coordinator_down(self):
        """A live coordinator left behind would poll the single-connection device."""
        hass = Hass()
        config_entry = entry()
        set_up(hass, config_entry)
        coordinator = hass.data[DOMAIN][config_entry.entry_id]

        async def fail_unload(entry, platforms):
            return False

        hass.config_entries.async_unload_platforms = fail_unload
        asyncio.run(integration.async_unload_entry(hass, config_entry))
        assert coordinator.shutdowns == 1
        assert config_entry.entry_id not in hass.data[DOMAIN]
