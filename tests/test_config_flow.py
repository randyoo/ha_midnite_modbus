"""Tests for the config flow: what it asks for, and what it stores where.

The decisions worth pinning are not the widgets: they are that `scan_interval` goes
into the entry's *options* (which is where `__init__.py` reads it) and not its data,
that a DHCP-discovered Classic is identified by its MAC so it cannot be set up
twice, and that a Classic whose link dropped gets a fresh write-protect grant
rather than a second entry.
"""

from __future__ import annotations

import asyncio

import pytest
from homeassistant.config_entries import AbortFlow, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import Hass
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from midnite_solar import config_flow as flow_module
from midnite_solar.config_flow import MidniteSolarConfigFlow, async_get_options_flow
from midnite_solar.const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

ORIGINAL_CLIENT = flow_module.ModbusTcpClient


@pytest.fixture(autouse=True)
def restore_modbus_client():
    """Never leave a fake pymodbus class behind for another test module."""
    yield
    flow_module.ModbusTcpClient = ORIGINAL_CLIENT


HOST = "192.168.88.53"
MAC = "00:11:22:33:44:55"


class FakeClient:
    """Stands in for pymodbus so no test can reach the Classic."""

    clients = []

    def __init__(self, host, port=502, **kwargs):
        self.host = host
        self.port = port
        self.connected = False
        self.closed = False
        self.reads = []
        FakeClient.clients.append(self)

    def connect(self):
        self.connected = True
        return True

    def close(self):
        self.closed = True

    def read_holding_registers(self, address=0, count=1, **kwargs):
        self.reads.append((address, count))
        return FakeResult(registers=[0] * count)


class RefusingClient(FakeClient):
    def connect(self):
        return False


class ErrorReadingClient(FakeClient):
    def read_holding_registers(self, address=0, count=1, **kwargs):
        self.reads.append((address, count))
        return FakeResult(error=True)


class Classic200Client(FakeClient):
    """Answers the UNIT_ID read with a Classic 200, PCB 3."""

    def read_holding_registers(self, address=0, count=1, **kwargs):
        self.reads.append((address, count))
        return FakeResult(registers=[(3 << 8) | 200] + [0] * (count - 1))


class FakeResult:
    def __init__(self, registers=None, error=False):
        self.registers = registers or []
        self._error = error

    def isError(self):
        return self._error


def flow(client_class=FakeClient, entries=None, reconfigure_entry=None):
    """A flow with a fake Modbus client and a given set of existing entries."""
    FakeClient.clients = []
    flow_module.ModbusTcpClient = client_class
    instance = MidniteSolarConfigFlow()
    instance.hass = Hass()
    instance._entries = list(entries or [])
    instance._reconfigure_entry = reconfigure_entry
    return instance


def entry(host=HOST, port=DEFAULT_PORT, unique_id=None, options=None):
    config_entry = ConfigEntry(
        entry_id=f"entry-{host}-{port}",
        title=f"Midnite Solar @ {host}",
        data={CONF_HOST: host, CONF_PORT: port},
        options=options or {},
    )
    # Home Assistant sets this from the flow; the double has to be told.
    config_entry.unique_id = unique_id
    return config_entry


def default_for(result, key):
    """The default a form field comes with.

    Voluptuous keeps a field default behind a factory, so the value has to be
    asked for rather than read.
    """
    for marker in result["data_schema"].schema:
        if getattr(marker, "schema", marker) == key:
            default = getattr(marker, "default", None)
            return default() if callable(default) else default
    raise AssertionError(f"{key} is not in the form")


def set_up_manually(instance, host=HOST, port=DEFAULT_PORT, interval=DEFAULT_SCAN_INTERVAL):
    return asyncio.run(
        instance.async_step_user(
            {CONF_HOST: host, CONF_PORT: port, CONF_SCAN_INTERVAL: interval}
        )
    )


class TestManualEntry:
    def test_the_form_asks_for_host_port_and_interval(self):
        result = flow().async_step_user(None)
        outcome = asyncio.run(result)
        assert outcome["type"] == "form"
        assert outcome["step_id"] == "user"
        assert set(outcome["data_schema"].schema.keys()) == {CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL}

    def test_the_default_port_is_the_modbus_port(self):
        assert DEFAULT_PORT == 502

    def test_a_successful_entry_stores_host_and_port(self):
        outcome = set_up_manually(flow())
        assert outcome["type"] == "create_entry"
        assert outcome["data"] == {CONF_HOST: HOST, CONF_PORT: DEFAULT_PORT}

    def test_the_scan_interval_is_an_option_not_data(self):
        """__init__.py reads entry.options for it; storing it in data would do nothing."""
        outcome = set_up_manually(flow(), interval=45)
        assert outcome["options"] == {CONF_SCAN_INTERVAL: 45}
        assert CONF_SCAN_INTERVAL not in outcome["data"]

    def test_the_title_names_the_classic(self):
        outcome = set_up_manually(flow())
        assert outcome["title"] == f"Midnite Solar @ {HOST}"

    def test_a_device_that_refuses_the_connection_is_reported(self):
        outcome = set_up_manually(flow(RefusingClient))
        assert outcome["type"] == "form"
        assert outcome["errors"] == {"base": "cannot_connect"}

    def test_a_device_that_cannot_be_read_is_reported(self):
        outcome = set_up_manually(flow(ErrorReadingClient))
        assert outcome["type"] == "form"
        assert outcome["errors"] == {"base": "cannot_read"}

    def test_the_connection_test_reads_a_real_register(self):
        instance = flow()
        set_up_manually(instance)
        client = FakeClient.clients[-1]
        assert client.reads == [(4100, 1)], "address 4100 zero-indexed is register 4101"
        assert client.closed, "the test connection is not left open"

    def test_the_same_host_and_port_cannot_be_added_twice(self):
        instance = flow(entries=[entry()])
        with pytest.raises(AbortFlow) as err:
            set_up_manually(instance)
        assert err.value.reason == "already_configured"

    def test_a_different_port_is_a_different_device_as_far_as_the_flow_is_concerned(self):
        instance = flow(entries=[entry(port=5021)])
        outcome = set_up_manually(instance, port=502)
        assert outcome["type"] == "create_entry"


class TestDhcpDiscovery:
    def discovery(self, client_class=FakeClient, entries=None, mac=MAC, ip=HOST):
        instance = flow(client_class, entries)
        info = DhcpServiceInfo(ip=ip, macaddress=mac, hostname="Classic")
        return asyncio.run(instance.async_step_dhcp(info)), instance

    def test_the_unique_id_is_the_mac_address(self):
        _outcome, instance = self.discovery()
        assert instance.unique_id == MAC

    def test_a_discovered_classic_that_is_already_set_up_is_skipped(self):
        outcome, instance = self.discovery(entries=[entry(unique_id=MAC)])
        assert outcome["type"] == "abort"
        assert outcome["reason"] == "already_configured"
        assert instance.hass.config_entries.reloads == [], "same address, nothing to do"

    def test_a_new_ip_for_a_known_classic_updates_the_entry(self):
        """A lease renewal must not require deleting and re-adding the Classic."""
        existing = entry(unique_id=MAC)
        outcome, instance = self.discovery(entries=[existing], ip="192.168.88.77")
        assert outcome["type"] == "abort"
        assert outcome["reason"] == "already_configured"
        assert existing.data[CONF_HOST] == "192.168.88.77"
        assert instance.hass.config_entries.reloads == [existing.entry_id]

    def test_an_entry_without_a_unique_id_is_not_the_same_device(self):
        """An entry made before unique ids existed must not swallow discovery."""
        existing = entry()
        outcome, _instance = self.discovery(entries=[existing])
        assert outcome["type"] == "form"

    def test_the_badge_shows_the_model_when_the_classic_answers(self):
        outcome, instance = self.discovery(Classic200Client)
        assert outcome["type"] == "form"
        assert outcome["step_id"] == "user"
        assert instance.context["title_placeholders"]["name"] == "Classic 200"

    def test_the_model_read_is_the_unit_id_register(self):
        _outcome, _instance = self.discovery(Classic200Client)
        assert FakeClient.clients[-1].reads == [(4100, 2)]

    def test_an_unreachable_classic_is_still_offered_to_the_user(self):
        """Discovery must not fail just because the identification read failed."""
        outcome, instance = self.discovery(RefusingClient)
        assert outcome["type"] == "form"
        assert instance.context["title_placeholders"]["name"] == "Midnite Solar"

    def test_the_form_is_pre_filled_with_what_discovery_found(self):
        outcome, _instance = self.discovery()
        assert outcome["description_placeholders"] == {"ip": HOST, "mac": MAC}


class TestOptions:
    def test_the_options_flow_carries_the_entry_being_edited(self):
        existing = entry(options={CONF_SCAN_INTERVAL: 30})
        handler = asyncio.run(async_get_options_flow(existing))
        assert handler.config_entry is existing

    def test_the_form_defaults_to_the_current_interval(self):
        existing = entry(options={CONF_SCAN_INTERVAL: 30})
        handler = asyncio.run(async_get_options_flow(existing))
        outcome = asyncio.run(handler.async_step_init(None))
        assert outcome["type"] == "form"
        assert outcome["step_id"] == "init"
        assert default_for(outcome, CONF_SCAN_INTERVAL) == 30

    def test_the_default_when_nothing_was_set(self):
        handler = asyncio.run(async_get_options_flow(entry(options={})))
        outcome = asyncio.run(handler.async_step_init(None))
        assert default_for(outcome, CONF_SCAN_INTERVAL) == DEFAULT_SCAN_INTERVAL

    def test_the_chosen_interval_is_stored_as_an_option(self):
        handler = asyncio.run(async_get_options_flow(entry()))
        outcome = asyncio.run(handler.async_step_init({CONF_SCAN_INTERVAL: 60}))
        assert outcome["type"] == "create_entry"
        assert outcome["data"] == {CONF_SCAN_INTERVAL: 60}
        assert outcome["title"] == ""

    def test_the_flow_no_longer_has_the_step_that_could_only_raise(self):
        """The old step called _get_current_entries(), which Home Assistant does not do."""
        assert not hasattr(MidniteSolarConfigFlow, "async_step_options")


class TestImport:
    def test_an_import_creates_an_entry(self):
        outcome = asyncio.run(flow().async_step_import({CONF_HOST: HOST, CONF_PORT: 502}))
        assert outcome["type"] == "create_entry"
        assert outcome["data"] == {CONF_HOST: HOST, CONF_PORT: 502}

    def test_import_aborts_when_the_classic_is_down(self):
        outcome = asyncio.run(
            flow(RefusingClient).async_step_import({CONF_HOST: HOST, CONF_PORT: 502})
        )
        assert outcome == {"type": "abort", "reason": "cannot_connect"}

    def test_import_aborts_when_the_classic_cannot_be_read(self):
        outcome = asyncio.run(
            flow(ErrorReadingClient).async_step_import({CONF_HOST: HOST, CONF_PORT: 502})
        )
        assert outcome == {"type": "abort", "reason": "cannot_read"}

    def test_importing_a_device_that_is_already_set_up_is_aborted(self):
        with pytest.raises(AbortFlow) as err:
            asyncio.run(
                flow(entries=[entry()]).async_step_import({CONF_HOST: HOST, CONF_PORT: 502})
            )
        assert err.value.reason == "already_configured"


class TestReconfigure:
    def test_the_form_is_prefilled_with_the_current_values(self):
        existing = entry(options={CONF_SCAN_INTERVAL: 25})
        handler = flow(entries=[existing], reconfigure_entry=existing)
        outcome = asyncio.run(handler.async_step_reconfigure(None))
        assert default_for(outcome, CONF_HOST) == HOST
        assert default_for(outcome, CONF_PORT) == DEFAULT_PORT
        assert default_for(outcome, CONF_SCAN_INTERVAL) == 25

    def test_a_new_host_lands_in_data_and_a_new_interval_in_options(self):
        existing = entry(unique_id=MAC)
        handler = flow(entries=[existing], reconfigure_entry=existing)
        asyncio.run(
            handler.async_step_reconfigure(
                {CONF_HOST: "192.168.88.99", CONF_PORT: 5021, CONF_SCAN_INTERVAL: 30}
            )
        )
        assert existing.data == {CONF_HOST: "192.168.88.99", CONF_PORT: 5021}
        assert existing.options == {CONF_SCAN_INTERVAL: 30}
        assert handler.hass.config_entries.updates[0][0] == existing.entry_id

    def test_reconfiguring_reloads_the_entry(self):
        existing = entry()
        handler = flow(entries=[existing], reconfigure_entry=existing)
        outcome = asyncio.run(
            handler.async_step_reconfigure({CONF_HOST: HOST, CONF_PORT: 502, CONF_SCAN_INTERVAL: 20})
        )
        assert outcome["type"] == "abort"
        assert outcome["reason"] == "reconfigure_success"
