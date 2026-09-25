"""Tests for read-back verification of writes.

This is the check that settles "the number in Home Assistant never changed and
nothing said why". A write-protected or clamping Classic accepts the Modbus write
and keeps reporting the old value; without a read-back that is invisible.
"""

from __future__ import annotations

import asyncio

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import NO_READBACK_REGISTERS, REGISTER_MAP
from midnite_solar.number import (
    AbsorbVoltageNumber,
    FloatVoltageNumber,
    ModbusAddressNumber,
)
from midnite_solar.select import MPPT_OFF, Aux1FunctionSelector, MPPTModeSelector
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def number(cls, entry, api, register, group="setpoints"):
    coordinator = FakeCoordinator(Hass(), api, {group: {register: 0}})
    return cls(coordinator, entry)


class TestAbsorbReadBack:
    """The case that started this: absorb never changed, and no error appeared."""

    def test_a_write_the_classic_kept_is_accepted(self, entry):
        api = FakeApi()
        asyncio.run(
            number(AbsorbVoltageNumber, entry, api, 4149).async_set_native_value(57.6)
        )
        assert api.writes == [(4149, 576), (4160, 0x0004)]

    def test_a_write_the_classic_ignored_is_reported(self, entry):
        api = FakeApi(read_values={4149: 555}, stale_read=True)
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(
                number(AbsorbVoltageNumber, entry, api, 4149).async_set_native_value(
                    57.6
                )
            )
        assert "57.6" in str(err.value)
        assert "55.5" in str(err.value)
        assert "ignored or clamped" in str(err.value)

    def test_the_stale_value_is_reported_in_the_entity_units(self, entry):
        api = FakeApi(read_values={4149: 575}, stale_read=True)
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(
                number(AbsorbVoltageNumber, entry, api, 4149).async_set_native_value(
                    57.6
                )
            )
        assert "57.5 V" in str(err.value), "the user sees volts, not raw counts"

    def test_a_clamped_write_is_reported(self, entry):
        """The Classic limits charge voltage to its own maximum compensation."""
        api = FakeApi(read_values={4149: 580}, stale_read=True)
        with pytest.raises(HomeAssistantError):
            asyncio.run(
                number(AbsorbVoltageNumber, entry, api, 4149).async_set_native_value(
                    64.0
                )
            )

    def test_a_register_that_does_not_answer_is_not_silently_ok(self, entry):
        api = FakeApi(unreadable=True)
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(
                number(AbsorbVoltageNumber, entry, api, 4149).async_set_native_value(
                    57.6
                )
            )
        assert "did not answer the read-back" in str(err.value)

    def test_read_back_happens_after_the_eeprom_commit(self, entry):
        api = FakeApi()
        asyncio.run(
            number(AbsorbVoltageNumber, entry, api, 4149).async_set_native_value(57.6)
        )
        assert [address for address, _ in api.writes] == [4149, 4160]
        assert api.reads[0] == 4149

    def test_the_refresh_still_runs_after_a_confirmed_write(self, entry):
        entity = number(AbsorbVoltageNumber, entry, FakeApi(), 4149)
        asyncio.run(entity.async_set_native_value(57.6))
        assert entity.coordinator.refresh_requests == 1


class TestRegistersThatCannotBeReadBack:
    """Writes that change the Modbus connection cannot verify themselves."""

    def test_a_new_modbus_address_is_not_verified(self, entry):
        """Register 4326 is the Classic's own Modbus address: after the write the
        old socket is no longer where the setting lives, so no read is expected.
        """
        api = FakeApi(unreadable=True)
        entity = number(ModbusAddressNumber, entry, api, 4326, group="eeprom_settings")
        asyncio.run(entity.async_set_native_value(600))
        assert api.writes[0][0] == 4326
        assert api.reads == []

    def test_the_registers_that_cannot_answer_are_excluded(self):
        """Two move the connection, two are write-only according to the map."""
        assert (
            frozenset(
                {
                    REGISTER_MAP["MODBUS_PORT_REGISTER"],
                    REGISTER_MAP["CLASSIC_MODBUS_ADDR_EEPROM"],
                    REGISTER_MAP["FORCE_FLAG_BITS"],
                    REGISTER_MAP["FORCE_FLAG_BITS_HIGH"],
                }
            )
            == NO_READBACK_REGISTERS
        )


class TestSelectReadBack:
    """Selects write packed settings, so a silent refusal matters just as much."""

    def test_a_stale_aux_write_is_reported(self, entry):
        api = FakeApi(read_values={4165: 0x4041}, stale_read=True)
        coordinator = FakeCoordinator(Hass(), api, {"aux_settings": {4165: 0x4041}})
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(
                Aux1FunctionSelector(coordinator, entry).async_select_option(
                    "Toggle Test"
                )
            )
        assert "0x4041" in str(err.value)

    def test_a_stale_mppt_write_is_reported(self, entry):
        api = FakeApi(read_values={4164: 0x000B}, stale_read=True)
        coordinator = FakeCoordinator(Hass(), api, {"settings": {4164: 0x000B}})
        with pytest.raises(HomeAssistantError):
            asyncio.run(
                MPPTModeSelector(coordinator, entry).async_select_option(MPPT_OFF)
            )

    def test_a_confirmed_mppt_write_passes(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {"settings": {4164: 0x000B}})
        asyncio.run(MPPTModeSelector(coordinator, entry).async_select_option(MPPT_OFF))
        assert api.writes == [(4164, 0x0000), (4160, 0x0004)]
        assert api.reads == [4164]

    def test_a_write_the_classic_refused_is_not_read_back(self, entry):
        api = FakeApi(error_writes=True)
        coordinator = FakeCoordinator(Hass(), api, {"settings": {4164: 0x0001}})
        with pytest.raises(HomeAssistantError):
            asyncio.run(
                MPPTModeSelector(coordinator, entry).async_select_option("SOLAR")
            )
        assert api.reads == []


class TestOtherNumbersStillVerifyThemselves:
    """Every number goes through the same read-back."""

    def test_float_voltage_read_back(self, entry):
        api = FakeApi(read_values={4150: 555}, stale_read=True)
        with pytest.raises(HomeAssistantError):
            asyncio.run(
                number(FloatVoltageNumber, entry, api, 4150).async_set_native_value(
                    56.0
                )
            )
