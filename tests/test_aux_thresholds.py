"""Tests for the Aux 1 / Aux 2 thresholds.

The formulas are transcribed from the Classic MODBUS register map (Rev C.4/C.5),
one register per threshold, so a wrong scale here is a test failure instead of a
wrong write to the hardware:

  4166 ([4166] /10) Volts   Aux1VoltsLoAbs (EE)   Aux 1 Low Absolute Threshold Voltage
  4167 [4167] Milliseconds  Aux1DelayT (EE)       Aux 1 Delay time before Asserting
  4168 [4168] Milliseconds  Aux1HoldT (EE)        Aux 1 Hold time before De-asserting
  4169 ([4169] /10) Volts   Aux2PwmVwidth (EE)    "0,1,2,3,4 or 5 volts"
  4172 ([4172] /10) Volts   Aux1VoltsHiAbs (EE)
  4173 ([4173] /10) Volts   Aux2VoltsHiAbs (EE)
  4174 ([4174] /10) Volts   Aux1VoltsLoRel (EE)   relative to charge stage set point V
  4175 ([4175] /10) Volts   Aux1VoltsHiRel (EE)
  4176 ([4176] /10) Volts   Aux2VoltsLoRel (EE)
  4177 ([4177] /10) Volts   Aux2VoltsHiRel (EE)
  4178 ([4178] /10) Volts   Aux1VoltsLoPv (EE)
  4179 ([4179] /10) Volts   Aux1VoltsHiPv (EE)
  4181 ([4181] /10) Volts   Aux2VoltsHiPv (EE)

Registers 4170 and 4171 are RESERVED in the map, which is why the block read of
4165-4181 has to ignore the words in between.
"""

from __future__ import annotations

import asyncio

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import (
    AUX_THRESHOLD_SETTINGS,
    EE_BACKED_REGISTERS,
    REGISTER_MAP,
)
from midnite_solar.number import AuxThresholdNumber
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.helpers.entity import EntityCategory

# (key, register, tenths) exactly as the map's own formulas have them.
SPEC_THRESHOLDS = {
    "AUX1_VOLTS_LO_ABS": (4166, True),
    "AUX1_DELAY_T_MS": (4167, False),
    "AUX1_HOLD_T_MS": (4168, False),
    "AUX2_PWM_VWIDTH": (4169, True),
    "AUX1_VOLTS_HI_ABS": (4172, True),
    "AUX2_VOLTS_HI_ABS": (4173, True),
    "AUX1_VOLTS_LO_REL": (4174, True),
    "AUX1_VOLTS_HI_REL": (4175, True),
    "AUX2_VOLTS_LO_REL": (4176, True),
    "AUX2_VOLTS_HI_REL": (4177, True),
    "AUX1_VOLTS_LO_PV_ABS": (4178, True),
    "AUX1_VOLTS_HI_PV_ABS": (4179, True),
    "AUX2_VOLTS_HI_PV_ABS": (4181, True),
}

SETTINGS = {setting[0]: setting for setting in AUX_THRESHOLD_SETTINGS}


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def threshold(key, api, raw=0, entry=None):
    setting = SETTINGS[key]
    coordinator = FakeCoordinator(
        Hass(), api, {"aux_settings": {REGISTER_MAP[key]: raw}}
    )
    coordinator.hass = Hass()
    entity = AuxThresholdNumber(coordinator, entry, setting)
    entity.hass = coordinator.hass
    return entity


class TestTable:
    """The table has to be the map's, not a guess at it."""

    def test_every_threshold_is_where_the_map_puts_it(self):
        assert set(SETTINGS) == set(SPEC_THRESHOLDS)
        for key, (register, tenths) in SPEC_THRESHOLDS.items():
            assert REGISTER_MAP[key] == register, key
            assert SETTINGS[key][3] is tenths, key

    def test_all_thirteen_are_eeprom_backed(self):
        """Every one of them is marked (EE) in the map."""
        for key in SPEC_THRESHOLDS:
            assert REGISTER_MAP[key] in EE_BACKED_REGISTERS, key

    def test_the_reserved_registers_are_not_offered(self):
        assert 4170 not in {REGISTER_MAP[key] for key in SETTINGS}
        assert 4171 not in {REGISTER_MAP[key] for key in SETTINGS}

    def test_the_units_follow_the_formula(self):
        for key, (_, tenths) in SPEC_THRESHOLDS.items():
            assert SETTINGS[key][2] == ("V" if tenths else "ms"), key

    def test_they_are_polled_in_the_group_that_is_already_read(self):
        from midnite_solar.const import REGISTER_GROUPS

        polled = set(REGISTER_GROUPS["aux_settings"])
        for key in SPEC_THRESHOLDS:
            assert REGISTER_MAP[key] in polled, key


class TestReadout:
    """The value the UI shows has to be the register's, at the right scale."""

    def test_a_voltage_threshold_reads_tenths(self, entry):
        entity = threshold("AUX1_VOLTS_HI_ABS", FakeApi(), raw=576, entry=entry)
        assert entity.native_value == 57.6
        assert entity.native_unit_of_measurement == "V"

    def test_a_time_threshold_reads_plain_milliseconds(self, entry):
        entity = threshold("AUX1_DELAY_T_MS", FakeApi(), raw=1500, entry=entry)
        assert entity.native_value == 1500.0
        assert entity.native_unit_of_measurement == "ms"

    def test_a_threshold_with_no_reading_is_unknown(self, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {})
        entity = AuxThresholdNumber(coordinator, entry, SETTINGS["AUX1_VOLTS_LO_ABS"])
        assert entity.native_value is None

    def test_each_threshold_has_its_own_identity(self, entry):
        entity = threshold("AUX2_VOLTS_HI_PV_ABS", FakeApi(), entry=entry)
        assert entity.unique_id == "entry-1_aux2_volts_hi_pv_abs"
        assert entity.name == "Aux 2 High PV Absolute Voltage"
        assert entity.entity_category == EntityCategory.CONFIG


class TestWrites:
    """A threshold change is a set point change: write, commit, read back."""

    def test_a_voltage_write_sends_tenths_then_commits(self, entry):
        api = FakeApi()
        entity = threshold("AUX1_VOLTS_LO_ABS", api, raw=520, entry=entry)
        asyncio.run(entity.async_set_native_value(48.5))
        assert api.writes == [(4166, 485), (4160, 0x0004)]

    def test_a_millisecond_write_sends_the_count_then_commits(self, entry):
        api = FakeApi()
        entity = threshold("AUX1_HOLD_T_MS", api, raw=500, entry=entry)
        asyncio.run(entity.async_set_native_value(2000))
        assert api.writes == [(4168, 2000), (4160, 0x0004)]

    def test_a_refused_write_says_so(self, entry):
        api = FakeApi(read_values={4172: 555}, stale_read=True)
        entity = threshold("AUX1_VOLTS_HI_ABS", api, raw=555, entry=entry)
        with pytest.raises(Exception) as err:
            asyncio.run(entity.async_set_native_value(57.6))
        assert "ignored or clamped" in str(err.value)

    def test_a_round_trip_returns_the_same_number(self, entry):
        api = FakeApi()
        entity = threshold("AUX1_VOLTS_HI_REL", api, raw=12, entry=entry)
        asyncio.run(entity.async_set_native_value(3.4))
        assert api.read_values[4175] == 34
        assert entity.native_value == 3.4


class TestRanges:
    """Only register 4169 states a range, so only that one has limits."""

    def test_the_pwm_width_carries_the_documented_range(self, entry):
        entity = threshold("AUX2_PWM_VWIDTH", FakeApi(), entry=entry)
        assert entity.native_min_value == 0.0
        assert entity.native_max_value == 5.0
        assert entity.native_step == 1.0

    def test_no_other_threshold_invents_a_range(self, entry):
        for key in SPEC_THRESHOLDS:
            if key == "AUX2_PWM_VWIDTH":
                continue
            entity = threshold(key, FakeApi(), entry=entry)
            assert entity.native_min_value is None, key
            assert entity.native_max_value is None, key
