"""Tests for the Classic's own status values.

Every expectation is the register map's row for that register (Rev C.4/C.5):

  4135 | R     | NiteMinutesNoPwr          | [4135] minutes
  4141 | R     | PWM ReadOnly              | [4141] ( 0 to 1023)
  4142 | R     | Reason For Reset          | See Table 4142-1
  4191 | R     | VpvTargetRd               | ([4191] /10) Volts
  4244 | R     | VbattRegSetPTmpComp       | ([4244] /10) Volts
  4245 | R/W   | VbattNominal (EE)         | [4245] 12 * 1 thru 10
  4246 | R/W   | EndingAmps (EE)           | ([4246] /10) Amps
  4249 | R/W   | RebulkVolts (EE)          | ([4249] /10) Volts
  4272 | R     | Ibatt                     | ([4272] /10) Amps (peak A)
  4276 | R     | Output Vbatt              | ([4376] /10) Volts (peak V)  <- typo
  4277 | R     | Input Vpv                 | ([4377] /10) Volts (peak V)   <- typo
"""

from __future__ import annotations

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.helpers.entity import EntityCategory

from midnite_solar.const import (
    CLASSIC_STATUS_SENSORS,
    EE_BACKED_REGISTERS,
    NO_READBACK_REGISTERS,
    REGISTER_GROUPS,
    REGISTER_MAP,
)
from midnite_solar.sensor import ClassicStatusSensor

ROWS = {row[0]: row for row in CLASSIC_STATUS_SENSORS}

SPEC_ADDRESSES = {
    "VBATT_REG_SET_P_TMP_COMP": 4244,
    "VBATT_NOMINAL": 4245,
    "ENDING_AMPS": 4246,
    "REBULK_VOLTS": 4249,
    "VPV_TARGET_RD": 4191,
    "IBATT_UNFILTERED": 4272,
    "VBATT_UNFILTERED": 4276,
    "VPV_UNFILTERED": 4277,
    "REASON_FOR_RESET": 4142,
    "PWM_READ_ONLY": 4141,
    "NITE_MINUTES_NO_PWR": 4135,
}


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def sensor(key, raw, entry):
    _, group, *_ = ROWS[key]
    coordinator = FakeCoordinator(Hass(), FakeApi(), {group: {REGISTER_MAP[key]: raw}})
    return ClassicStatusSensor(coordinator, entry, ROWS[key])


class TestAddresses:
    """The registers, as the map lists them."""

    def test_every_row_is_at_the_maps_address(self):
        assert set(ROWS) == set(SPEC_ADDRESSES)
        for key, address in SPEC_ADDRESSES.items():
            assert REGISTER_MAP[key] == address, key

    def test_the_maps_typo_did_not_become_a_register(self):
        """4276 and 4277 are described by "([4376] /10)" in the map itself."""
        assert REGISTER_MAP["VBATT_UNFILTERED"] == 4276
        assert REGISTER_MAP["VPV_UNFILTERED"] == 4277
        assert 4376 not in REGISTER_MAP.values()
        assert 4377 not in REGISTER_MAP.values()

    def test_read_only_registers_were_not_made_eeprom_backed(self):
        """Only a write the map marks (EE) needs the EEPROM commit."""
        for key, address in SPEC_ADDRESSES.items():
            if key in ("VBATT_NOMINAL", "ENDING_AMPS", "REBULK_VOLTS"):
                continue  # the map marks these R/W (EE); they are read only here
            assert address not in EE_BACKED_REGISTERS, key
            assert address not in NO_READBACK_REGISTERS, key

    def test_the_new_registers_cost_no_extra_request(self):
        """4135, 4141 and 4142 sit inside blocks that were already read."""
        from midnite_solar.coordinator import register_blocks

        assert register_blocks(REGISTER_GROUPS["settings"])[0] == (4135, 4137)
        assert register_blocks(REGISTER_GROUPS["time_settings"])[0] == (4138, 4143)


class TestScales:
    """The map's formula, not a guess at it."""

    def test_the_compensated_target_is_the_absorb_target_in_force(self, entry):
        value = sensor("VBATT_REG_SET_P_TMP_COMP", 567, entry).native_value
        assert value == 56.7

    def test_ending_amperage_is_in_tenths_of_an_amp(self, entry):
        assert sensor("ENDING_AMPS", 25, entry).native_value == 2.5

    def test_rebulk_voltage_is_in_tenths_of_a_volt(self, entry):
        assert sensor("REBULK_VOLTS", 520, entry).native_value == 52.0

    def test_nominal_bank_voltage_is_twelve_times_the_register(self, entry):
        """Map: "[4245] 12 * 1 thru 10 (120 Max for 250 KS)"."""
        assert sensor("VBATT_NOMINAL", 4, entry).native_value == 48.0
        assert sensor("VBATT_NOMINAL", 10, entry).native_value == 120.0

    def test_the_unfiltered_values_are_tenths_too(self, entry):
        assert sensor("IBATT_UNFILTERED", 1234, entry).native_value == 123.4
        assert sensor("VBATT_UNFILTERED", 567, entry).native_value == 56.7
        assert sensor("VPV_UNFILTERED", 888, entry).native_value == 88.8

    def test_a_code_or_counter_is_reported_untouched(self, entry):
        assert sensor("REASON_FOR_RESET", 3, entry).native_value == 3.0
        assert sensor("PWM_READ_ONLY", 1023, entry).native_value == 1023.0
        assert sensor("NITE_MINUTES_NO_PWR", 17, entry).native_value == 17.0

    def test_a_register_that_has_not_been_read_is_unknown(self, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {})
        assert ClassicStatusSensor(coordinator, entry, ROWS["ENDING_AMPS"]).native_value is None


class TestPresentation:
    """What a user is offered, and what stays out of the way."""

    def test_the_units_come_from_the_formula(self, entry):
        assert sensor("VBATT_REG_SET_P_TMP_COMP", 0, entry).native_unit_of_measurement == "V"
        assert sensor("ENDING_AMPS", 0, entry).native_unit_of_measurement == "A"
        assert sensor("NITE_MINUTES_NO_PWR", 0, entry).native_unit_of_measurement == "min"

    def test_the_reason_for_reset_has_no_units_to_claim(self, entry):
        assert sensor("REASON_FOR_RESET", 0, entry).native_unit_of_measurement is None

    def test_the_useful_values_are_on_by_default(self, entry):
        for key in ("VBATT_REG_SET_P_TMP_COMP", "VBATT_NOMINAL", "ENDING_AMPS", "REBULK_VOLTS"):
            assert sensor(key, 0, entry).entity_registry_enabled_default is True, key
            assert sensor(key, 0, entry).entity_category == EntityCategory.CONFIG, key

    def test_the_fast_moving_and_diagnostic_values_are_off_by_default(self, entry):
        for key in (
            "IBATT_UNFILTERED",
            "VBATT_UNFILTERED",
            "VPV_UNFILTERED",
            "VPV_TARGET_RD",
            "REASON_FOR_RESET",
            "PWM_READ_ONLY",
            "NITE_MINUTES_NO_PWR",
        ):
            assert sensor(key, 0, entry).entity_registry_enabled_default is False, key
            assert sensor(key, 0, entry).entity_category == EntityCategory.DIAGNOSTIC, key

    def test_each_sensor_has_its_own_identity(self, entry):
        assert sensor("REBULK_VOLTS", 0, entry).unique_id == "entry-1_rebulk_volts"
        assert sensor("REBULK_VOLTS", 0, entry).name == "Rebulk Voltage"

    def test_the_sensors_read_the_group_they_are_polled_in(self, entry):
        """A sensor that looks in the wrong group is silently always unknown."""
        _, group, *_ = ROWS["VBATT_NOMINAL"]
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {group: {4245: 2}})
        entity = ClassicStatusSensor(coordinator, entry, ROWS["VBATT_NOMINAL"])
        assert entity.native_value == 24.0
        coordinator.data["data"][group] = {}
        assert entity.native_value is None
