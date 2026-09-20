"""Tests for the Classic's Ethernet write protect (registers 20492/20493).

This is why "absorb never worked at all". The map says, of 20492/20493:
"W Serial Number (Unlock Code) For writing to Classic modbus registers over
Ethernet ... Write the Classic's serial number over Ethernet to unlock writing of
modbus registers over Ethernet. Setting this will last until the TCP/IP connection
is dropped". This integration is Modbus TCP, so every write was ignored.
"""

from __future__ import annotations

import pytest

from fakes import FakeApi, FakeCoordinator, ModbusResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

from midnite_solar.binary_sensor import InfoFlagBinarySensor
from midnite_solar.const import INFO_FLAGS, REGISTER_GROUPS, REGISTER_MAP
from midnite_solar.coordinator import MidniteSolarUpdateCoordinator
from midnite_solar.hub import MidniteHub, WriteLockedError
from midnite_solar.register_values import (
    info_flag_set,
    serial_from_registers,
    unlock_values,
)

# The map's own worked example: "the serial number is: 0x12345678 (hex)".
SERIAL = 0x12345678


class FakeClient:
    """Stands in for the pymodbus client, recording protocol-level writes."""

    def __init__(self, fail_unlock=False):
        self.writes = []
        self.open = True
        self.fail_unlock = fail_unlock

    def is_socket_open(self):
        return self.open

    def connect(self):
        self.open = True
        return True

    def close(self):
        self.open = False

    def write_register(self, address, value, **kwargs):
        unlock_addresses = (
            REGISTER_MAP["UNLOCK_SERIAL_MSB"] - 1,
            REGISTER_MAP["UNLOCK_SERIAL_LSB"] - 1,
        )
        if self.fail_unlock and address in unlock_addresses:
            return ModbusResult(error=True)
        self.writes.append((address, value))
        return ModbusResult()

    def read_holding_registers(self, address, count=1, **kwargs):
        return ModbusResult(registers=[0] * count)


def make_hub(monkeypatch, fail_unlock=False):
    """A hub whose Modbus client is replaced by a recorder."""
    monkeypatch.setattr(MidniteHub, "RECONNECT_DELAY", 0)
    hub = MidniteHub("127.0.0.1", 502)
    clients = []

    def factory():
        client = FakeClient(fail_unlock=fail_unlock)
        clients.append(client)
        return client

    monkeypatch.setattr(hub, "_make_client", factory)
    hub._client = factory()
    return hub, clients


class TestUnlockValues:
    """The map's example: "20492 = MSB (Serial number) 0x1234, 20493 = LSB 0x5678"."""

    def test_the_map_example_splits_as_documented(self):
        assert unlock_values(SERIAL) == (0x1234, 0x5678)

    def test_the_serial_reads_msb_first(self):
        assert serial_from_registers(0x1234, 0x5678) == SERIAL

    def test_round_trip(self):
        msb, lsb = unlock_values(SERIAL)
        assert serial_from_registers(msb, lsb) == SERIAL

    def test_the_register_numbers(self):
        assert REGISTER_MAP["UNLOCK_SERIAL_MSB"] == 20492
        assert REGISTER_MAP["UNLOCK_SERIAL_LSB"] == 20493
        assert REGISTER_MAP["SERIAL_NUMBER_MSB_RO"] == 28673
        assert REGISTER_MAP["SERIAL_NUMBER_LSB_RO"] == 28674

    def test_both_are_polled(self):
        """The serial group must be read or no write can ever be unlocked."""
        assert REGISTER_GROUPS["serial"] == [28673, 28674]
        assert REGISTER_GROUPS["info_flags"] == [4130, 4131]


class TestHubUnlock:
    """What the hub puts on the wire before a setting write."""

    def test_the_unlock_precedes_the_setting_write(self, monkeypatch):
        hub, clients = make_hub(monkeypatch)
        hub.set_serial_number(SERIAL)
        hub.write_register(4149, 576)
        # The hub addresses the wire as register - 1, as it does for reads.
        assert clients[0].writes == [(20491, 0x1234), (20492, 0x5678), (4148, 576)]

    def test_the_unlock_is_written_once_per_connection(self, monkeypatch):
        hub, clients = make_hub(monkeypatch)
        hub.set_serial_number(SERIAL)
        hub.write_register(4149, 576)
        hub.write_register(4150, 555)
        assert clients[0].writes.count((20491, 0x1234)) == 1
        assert len(clients[0].writes) == 4

    def test_nothing_is_written_while_locked_and_the_serial_is_unknown(self, monkeypatch):
        hub, clients = make_hub(monkeypatch)
        with pytest.raises(WriteLockedError):
            hub.write_register(4149, 576)
        assert clients[0].writes == []

    def test_a_dropped_connection_takes_the_unlock_with_it(self, monkeypatch):
        """The map: "Setting this will last until the TCP/IP connection is dropped"."""
        hub, clients = make_hub(monkeypatch)
        hub.set_serial_number(SERIAL)
        hub.write_register(4149, 576)
        clients[0].open = False
        hub.write_register(4149, 576)
        assert len(clients) > 1
        assert clients[-1].writes[:2] == [(20491, 0x1234), (20492, 0x5678)]

    def test_disconnect_clears_the_unlock(self, monkeypatch):
        hub, clients = make_hub(monkeypatch)
        hub.set_serial_number(SERIAL)
        hub.write_register(4149, 576)
        hub.disconnect()
        hub._client.open = True
        hub.write_register(4149, 576)
        assert clients[0].writes.count((20491, 0x1234)) == 2

    def test_a_failing_unlock_is_not_treated_as_success(self, monkeypatch):
        hub, clients = make_hub(monkeypatch, fail_unlock=True)
        hub.set_serial_number(SERIAL)
        with pytest.raises(WriteLockedError):
            hub.write_register(4149, 576)
        assert (4148, 576) not in clients[0].writes

    def test_a_new_serial_number_needs_a_new_unlock(self, monkeypatch):
        hub, clients = make_hub(monkeypatch)
        hub.set_serial_number(SERIAL)
        hub.write_register(4149, 576)
        hub.set_serial_number(0x00010002)
        hub.write_register(4149, 576)
        assert clients[0].writes.count((20491, 0x1234)) == 1
        assert (20491, 0x0001) in clients[0].writes

    def test_the_hub_never_connects_to_a_real_device(self, monkeypatch):
        """The tests must not be able to reach the Classic."""
        hub, clients = make_hub(monkeypatch)
        assert isinstance(clients[0], FakeClient)
        hub.set_serial_number(SERIAL)
        hub.write_register(4149, 576)
        assert clients[0].writes


class TestCoordinatorHandsOverTheSerial:
    """28673/28674 are read by the coordinator, which feeds the hub."""

    def test_the_serial_reaches_the_hub(self):
        coordinator = MidniteSolarUpdateCoordinator(Hass(), "127.0.0.1", 502)
        coordinator._hand_over_serial_number({"serial": {28673: 0x1234, 28674: 0x5678}})
        assert coordinator.api._serial == SERIAL

    def test_missing_registers_leave_the_hub_alone(self):
        coordinator = MidniteSolarUpdateCoordinator(Hass(), "127.0.0.1", 502)
        coordinator._hand_over_serial_number({})
        coordinator._hand_over_serial_number({"serial": {28673: 0x1234}})
        assert coordinator.api._serial is None


class TestInfoFlagsTable:
    """Table 4130-1 "Info Flag Bits: READ ONLY (can read single 16 bit words)"."""

    SPEC_FLAGS = {
        "ClassicOverTemp": 0x00000001,
        "EepromError": 0x00000002,
        "SerialWriteLock": 0x00000004,
        "EqualizeInProgress": 0x00000008,
        "EQMppt": 0x00000080,
        "InVLowerThanOut": 0x00000100,
        "CurrentLimit": 0x00000200,
        "HyperVoc": 0x00000400,
        "BattTempSensorInstalled": 0x00002000,
        "Aux1StateOn": 0x00004000,
        "Aux2StateOn": 0x00008000,
        "GroundFaultF": 0x00010000,
        "OCP": 0x00020000,
        "ArcFaultF": 0x00040000,
        "NegBatCurrentF": 0x00080000,
        "XtraInfo2DsplayF": 0x00200000,
        "PvPartialShadeF": 0x00400000,
        "WatchdogResetF": 0x00800000,
        "LowBatteryVF": 0x01000000,
        "StackumperF": 0x02000000,
        "EqDoneF": 0x04000000,
        "TempCompShortedF": 0x08000000,
        "UNLockJumperF": 0x10000000,
        "XtraJumperF": 0x20000000,
        "InputShortedF": 0x40000000,
    }

    def test_every_documented_flag_has_the_documented_value(self):
        assert INFO_FLAGS == self.SPEC_FLAGS

    def test_the_write_lock_flags_are_present(self):
        """The two bits that explain why writes were ignored."""
        assert INFO_FLAGS["SerialWriteLock"] == 0x00000004
        assert INFO_FLAGS["UNLockJumperF"] == 0x10000000

    def test_no_two_flags_share_a_bit(self):
        values = list(INFO_FLAGS.values())
        assert len(values) == len(set(values))
        assert all(value & (value - 1) == 0 for value in values), "each flag is one bit"


class TestInfoFlagSensors:
    """The flags must be readable in Home Assistant, not buried in a bit field."""

    @pytest.fixture
    def entry(self):
        return ConfigEntry(entry_id="entry-1", title="Classic 200")

    def sensor(self, entry, flag, low, high):
        coordinator = FakeCoordinator(
            Hass(), FakeApi(), {"info_flags": {4130: low, 4131: high}}
        )
        return InfoFlagBinarySensor(coordinator, entry, flag)

    def test_words_combine_as_the_map_says(self, entry):
        """([4131] << 16) + [4130]"""
        sensor_obj = self.sensor(entry, "GroundFaultF", 0x0200, 0x0001)
        assert sensor_obj.info_flags == 0x00010200

    def test_a_fault_flag_turns_the_sensor_on(self, entry):
        assert self.sensor(entry, "GroundFaultF", 0x0200, 0x0001).is_on is True
        assert self.sensor(entry, "ArcFaultF", 0x0200, 0x0001).is_on is False

    def test_the_write_lock_is_visible(self, entry):
        assert self.sensor(entry, "SerialWriteLock", 0x0004, 0x0000).is_on is True
        assert self.sensor(entry, "SerialWriteLock", 0x0000, 0x0000).is_on is False

    def test_flags_in_the_high_word_are_reachable(self, entry):
        assert self.sensor(entry, "LowBatteryVF", 0x0000, 0x0100).is_on is True
        assert self.sensor(entry, "InputShortedF", 0x0000, 0x4000).is_on is True

    def test_no_data_means_no_state(self, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {})
        assert InfoFlagBinarySensor(coordinator, entry, "ArcFaultF").is_on is None

    def test_the_raw_flags_are_exposed_for_debugging(self, entry):
        sensor_obj = self.sensor(entry, "ArcFaultF", 0x0040, 0x0000)
        assert sensor_obj.extra_state_attributes == {"info_flags": 0x00000040}

    def test_every_flag_has_an_entity(self, entry):
        from midnite_solar.binary_sensor import FLAG_ENTITIES

        assert set(FLAG_ENTITIES) == set(INFO_FLAGS)

    def test_flag_helper(self):
        assert info_flag_set(0x00010200, 0x00010000) is True
        assert info_flag_set(0x00010200, 0x00020000) is False
