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
from midnite_solar.const import CONF_SCAN_INTERVAL, DEFAULT_PORT, DOMAIN

HOST = "192.168.88.53"
PLATFORMS = {"sensor", "binary_sensor", "button", "number", "text", "select"}


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

    def test_all_six_platforms_are_set_up(self):
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
