"""Tests for the three settings the map marks "R/W (EE)" that had no control.

Straight from the register map:

  4245 | R/W | VbattNominal (EE)   | [4245] 12 * 1 thru 10 (120 Max for 250 KS)
  4246 | R/W | EndingAmps (EE)     | ([4246] /10) Amps (Default = 0.0 amps)
  4249 | R/W | RebulkVolts (EE)    | ([4249] /10) Volts

4245 holds a multiplier, not volts, so it is a select: writing 48 to it would tell
the Classic the bank is 576 V.
"""

from __future__ import annotations

import asyncio

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from midnite_solar.const import (
    EE_BACKED_REGISTERS,
    NOMINAL_BATTERY_VOLTAGES,
    REGISTER_GROUPS,
    REGISTER_MAP,
)
from midnite_solar.number import EndingAmperageNumber, RebulkVoltageNumber
from midnite_solar.select import NominalBatteryVoltageSelect


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def select(api, entry, multiplier=None):
    group = {} if multiplier is None else {REGISTER_MAP["VBATT_NOMINAL"]: multiplier}
    coordinator = FakeCoordinator(Hass(), api, {"classic_status": group})
    coordinator.hass = Hass()
    entity = NominalBatteryVoltageSelect(coordinator, entry)
    entity.hass = coordinator.hass
    return entity


def number(cls, api, entry, register, raw):
    coordinator = FakeCoordinator(Hass(), api, {"classic_status": {register: raw}})
    coordinator.hass = Hass()
    entity = cls(coordinator, entry)
    entity.hass = coordinator.hass
    return entity


class TestNominalVoltageTable:
    """The multiplier, as the map gives it."""

    def test_the_ten_values_are_multiples_of_twelve(self):
        assert NOMINAL_BATTERY_VOLTAGES == {
            1: 12,
            2: 24,
            3: 36,
            4: 48,
            5: 60,
            6: 72,
            7: 84,
            8: 96,
            9: 108,
            10: 120,
        }

    def test_the_settings_are_eeprom_backed(self):
        for key in ("VBATT_NOMINAL", "ENDING_AMPS", "REBULK_VOLTS"):
            assert REGISTER_MAP[key] in EE_BACKED_REGISTERS, key

    def test_they_are_polled_in_the_group_the_entities_read(self):
        polled = set(REGISTER_GROUPS["classic_status"])
        for key in ("VBATT_NOMINAL", "ENDING_AMPS", "REBULK_VOLTS"):
            assert REGISTER_MAP[key] in polled, key


class TestNominalVoltageSelect:
    def test_the_options_are_volts_not_multipliers(self, entry):
        entity = select(FakeApi(), entry, 4)
        assert entity.options == ["12 V", "24 V", "36 V", "48 V", "60 V", "72 V", "84 V", "96 V", "108 V", "120 V"]

    def test_the_multiplier_reads_back_as_volts(self, entry):
        assert select(FakeApi(), entry, 4).current_option == "48 V"
        assert select(FakeApi(), entry, 10).current_option == "120 V"

    def test_a_multiplier_outside_the_table_is_reported_as_it_stands(self, entry):
        """A Classic configured from somewhere else should not be shown as a guess."""
        assert select(FakeApi(), entry, 0).current_option == "Unset (0)"

    def test_no_reading_is_unknown(self, entry):
        assert select(FakeApi(), entry).current_option is None

    def test_choosing_48_volts_writes_the_multiplier_4(self, entry):
        api = FakeApi(read_values={4245: 1})
        asyncio.run(select(api, entry, 1).async_select_option("48 V"))
        assert api.writes == [(4245, 4), (4160, 0x0004)]

    def test_the_multiplier_is_read_back(self, entry):
        api = FakeApi(read_values={4245: 1})
        asyncio.run(select(api, entry, 1).async_select_option("48 V"))
        assert api.reads == [4245]

    def test_a_refused_multiplier_says_so(self, entry):
        api = FakeApi(read_values={4245: 2}, stale_read=True)
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(select(api, entry, 2).async_select_option("96 V"))
        assert "ignored or clamped" in str(err.value)

    def test_a_voltage_that_is_not_a_multiple_of_twelve_cannot_be_written(self, entry):
        api = FakeApi()
        with pytest.raises(HomeAssistantError):
            asyncio.run(select(api, entry, 4).async_select_option("50 V"))
        assert api.writes == []

    def test_the_entity_is_a_config_setting(self, entry):
        entity = select(FakeApi(), entry, 4)
        assert entity.unique_id == "entry-1_nominal_battery_voltage"
        assert entity.entity_category == EntityCategory.CONFIG


class TestEndingAmperage:
    """Register 4246: "([4246] /10) Amps", the current at which a Classic gives up on absorb."""

    def test_tenths_of_an_amp(self, entry):
        entity = number(EndingAmperageNumber, FakeApi(), entry, 4246, 25)
        assert entity.native_value == 2.5
        assert entity.native_unit_of_measurement == "A"

    def test_zero_is_a_value_and_not_unknown(self, entry):
        """Map: "Default = 0.0 amps", so 0 has to be displayable and writable."""
        entity = number(EndingAmperageNumber, FakeApi(), entry, 4246, 0)
        assert entity.native_value == 0.0

    def test_writing_sends_tenths_then_commits(self, entry):
        api = FakeApi()
        asyncio.run(number(EndingAmperageNumber, api, entry, 4246, 50).async_set_native_value(3.5))
        assert api.writes == [(4246, 35), (4160, 0x0004)]
        assert api.reads == [4246]

    def test_no_range_is_invented(self, entry):
        entity = number(EndingAmperageNumber, FakeApi(), entry, 4246, 0)
        assert entity.native_min_value is None
        assert entity.native_max_value is None

    def test_the_step_is_a_tenth_of_an_amp(self, entry):
        assert number(EndingAmperageNumber, FakeApi(), entry, 4246, 0).native_step == 0.1


class TestRebulkVoltage:
    """Register 4249: "([4249] /10) Volts", "Rebulks if battery drops below this for > 90 Seconds"."""

    def test_tenths_of_a_volt(self, entry):
        assert number(RebulkVoltageNumber, FakeApi(), entry, 4249, 520).native_value == 52.0

    def test_writing_sends_tenths_then_commits(self, entry):
        api = FakeApi()
        asyncio.run(number(RebulkVoltageNumber, api, entry, 4249, 520).async_set_native_value(51.5))
        assert api.writes == [(4249, 515), (4160, 0x0004)]

    def test_a_clamped_write_is_reported(self, entry):
        api = FakeApi(read_values={4249: 520}, stale_read=True)
        with pytest.raises(HomeAssistantError):
            asyncio.run(number(RebulkVoltageNumber, api, entry, 4249, 520).async_set_native_value(60.0))

    def test_the_round_trip_returns_the_number_written(self, entry):
        entity = number(RebulkVoltageNumber, FakeApi(), entry, 4249, 520)
        asyncio.run(entity.async_set_native_value(53.3))
        assert entity.native_value == 53.3

    def test_identity(self, entry):
        entity = number(RebulkVoltageNumber, FakeApi(), entry, 4249, 520)
        assert entity.unique_id == "entry-1_rebulk_voltage"
        assert entity.name == "Rebulk Voltage"
