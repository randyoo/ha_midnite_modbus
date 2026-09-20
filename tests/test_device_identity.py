"""Tests for the identity Home Assistant shows the Classic under."""

from __future__ import annotations

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

from midnite_solar.base import MidniteBaseEntityDescription
from midnite_solar.const import REGISTER_MAP

DOMAIN = "midnite_solar"


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def device_group(**extra):
    """Registers 4101-4112 for a Classic 200, PCB 3, built 2013-12-08."""
    data = {
        REGISTER_MAP["UNIT_ID"]: 200 | (3 << 8),
        REGISTER_MAP["UNIT_SW_DATE_RO"]: 2013,
        REGISTER_MAP["UNIT_SW_DATE_MONTH_DAY"]: (12 << 8) | 8,
        REGISTER_MAP["DEVICE_ID_LSW"]: 0x1111,
        REGISTER_MAP["DEVICE_ID_MSW"]: 0x0000,
    }
    data.update(extra)
    return data


class TestSerialNumber:
    """The map identifies a Classic by 28673/28674, not by the device ID."""

    def test_the_serial_is_the_32bit_pair_from_28673_and_28674(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(
            Hass(),
            api,
            {"serial": {28673: 0x00A1, 28674: 0xB2C3}},
        )
        assert MidniteBaseEntityDescription.serial_number(coordinator) == 0x00A1B2C3

    def test_the_serial_reaches_the_device_info(self, entry):
        info = MidniteBaseEntityDescription.get_device_info(
            FakeCoordinator(
                Hass(),
                FakeApi(),
                {"device_info": device_group(), "serial": {28673: 0x00A1, 28674: 0xB2C3}},
            ),
            entry,
            DOMAIN,
        )
        assert info["serial_number"] == 0x00A1B2C3

    def test_a_device_that_has_not_been_read_yet_reports_no_serial(self, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {})
        assert MidniteBaseEntityDescription.serial_number(coordinator) is None
        assert MidniteBaseEntityDescription.get_device_info(coordinator, entry, DOMAIN)[
            "serial_number"
        ] is None

    def test_half_a_serial_is_not_a_serial(self, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {"serial": {28673: 0x00A1}})
        assert MidniteBaseEntityDescription.serial_number(coordinator) is None

    def test_the_serial_also_reaches_the_fallback_info(self, entry):
        """Before 4101-4112 have been read the device still has a serial."""
        info = MidniteBaseEntityDescription.get_device_info(
            FakeCoordinator(Hass(), FakeApi(), {"serial": {28673: 1, 28674: 2}}),
            entry,
            DOMAIN,
        )
        assert info["identifiers"] == {(DOMAIN, "entry-1")}
        assert info["serial_number"] == 0x00010002


class TestDeviceIdentity:
    """The identifiers must not move, or the upgrade forks the device."""

    def test_identifiers_still_come_from_the_device_id(self, entry):
        info = MidniteBaseEntityDescription.get_device_info(
            FakeCoordinator(Hass(), FakeApi(), {"device_info": device_group()}),
            entry,
            DOMAIN,
        )
        assert info["identifiers"] == {(DOMAIN, "4369")}
        assert info["model"] == "Classic 200"
        assert info["hw_version"] == "PCB 3"
        assert info["sw_version"] == "2013-12-08"

    def test_the_static_method_is_a_plain_one(self, entry):
        """It was decorated @staticmethod twice, which only works by luck."""
        plain = MidniteBaseEntityDescription.__dict__["get_device_info"]
        assert isinstance(plain, staticmethod)
        inner = plain.__func__
        assert not isinstance(inner, staticmethod)
        coordinator = FakeCoordinator(Hass(), FakeApi(), {"device_info": device_group()})
        assert callable(inner)
        assert inner(coordinator, entry, DOMAIN)["manufacturer"] == "Midnite Solar"
