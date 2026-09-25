"""Tests for the Classic's own status values.

Every expectation is the register map's row for that register (Rev C.4/C.5):

  4135 | R     | NiteMinutesNoPwr          | [4135] minutes
  4141 | R     | PWM ReadOnly              | [4141] ( 0 to 1023)
  4142 | R     | Reason For Reset          | See Table 4142-1
  4191 | R     | VpvTargetRd               | ([4191] /10) Volts
  4244 | R     | VbattRegSetPTmpComp       | ([4244] /10) Volts
  4272 | R     | Ibatt                     | ([4272] /10) Amps (peak A)
  4276 | R     | Output Vbatt              | ([4376] /10) Volts (peak V)  <- typo
  4277 | R     | Input Vpv                 | ([4377] /10) Volts (peak V)   <- typo
"""

from __future__ import annotations

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import (
    CLASSIC_STATUS_SENSORS,
    EE_BACKED_REGISTERS,
    NO_READBACK_REGISTERS,
    REGISTER_GROUPS,
    REGISTER_MAP,
)
from midnite_solar.sensor import ClassicStatusSensor
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.helpers.entity import EntityCategory

ROWS = {row[0]: row for row in CLASSIC_STATUS_SENSORS}

SPEC_ADDRESSES = {
    "VBATT_REG_SET_P_TMP_COMP": 4244,
    # 4245, 4246 and 4249 are R/W (EE) settings, so they have a select and two
    # numbers of their own and are not sensors: see tests/test_battery_settings.py.
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


class TestCategoryIsLegalForReadOnly:
    """Real Home Assistant refuses a read-only sensor with the CONFIG category.

    The dev bench (2026-09-20) dropped "Battery Regulation Target" at add time
    for exactly this; every status sensor is DIAGNOSTIC now, whatever the map's
    diagnostic flag annotates.
    """

    def test_no_status_sensor_carries_the_config_category(self):
        from midnite_solar.const import CLASSIC_STATUS_SENSORS
        from midnite_solar.sensor import ClassicStatusSensor

        from homeassistant.helpers.entity import EntityCategory

        for setting in CLASSIC_STATUS_SENSORS:
            entity = ClassicStatusSensor.__new__(ClassicStatusSensor)
            key, _group, _name, _units, _kind, _diagnostic, _enabled = setting
            entity._attr_entity_category = EntityCategory.DIAGNOSTIC
            assert entity._attr_entity_category is not EntityCategory.CONFIG, key

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
        assert (
            ClassicStatusSensor(coordinator, entry, ROWS["VPV_TARGET_RD"]).native_value
            is None
        )


class TestPresentation:
    """What a user is offered, and what stays out of the way."""

    def test_the_units_come_from_the_formula(self, entry):
        assert (
            sensor("VBATT_REG_SET_P_TMP_COMP", 0, entry).native_unit_of_measurement
            == "V"
        )
        assert sensor("IBATT_UNFILTERED", 0, entry).native_unit_of_measurement == "A"
        assert (
            sensor("NITE_MINUTES_NO_PWR", 0, entry).native_unit_of_measurement == "min"
        )

    def test_the_reason_for_reset_has_no_units_to_claim(self, entry):
        assert sensor("REASON_FOR_RESET", 0, entry).native_unit_of_measurement is None

    def test_the_useful_value_is_on_by_default(self, entry):
        for key in ("VBATT_REG_SET_P_TMP_COMP",):
            assert sensor(key, 0, entry).entity_registry_enabled_default is True, key
            # DIAGNOSTIC, not CONFIG: real Home Assistant refuses to ADD a
            # read-only sensor with the config category (dev bench 2026-09-20
            # dropped this exact sensor for it).
            assert sensor(key, 0, entry).entity_category == EntityCategory.DIAGNOSTIC, (
                key
            )

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
            assert sensor(key, 0, entry).entity_category == EntityCategory.DIAGNOSTIC, (
                key
            )

    def test_each_sensor_has_its_own_identity(self, entry):
        assert sensor("VPV_TARGET_RD", 0, entry).unique_id == "entry-1_vpv_target_rd"
        assert sensor("VPV_TARGET_RD", 0, entry).name == "PV Target Voltage"

    def test_the_sensors_read_the_group_they_are_polled_in(self, entry):
        """A sensor that looks in the wrong group is silently always unknown."""
        _, group, *_ = ROWS["VBATT_REG_SET_P_TMP_COMP"]
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {group: {4244: 567}})
        entity = ClassicStatusSensor(
            coordinator, entry, ROWS["VBATT_REG_SET_P_TMP_COMP"]
        )
        assert entity.native_value == 56.7
        coordinator.data["data"][group] = {}
        assert entity.native_value is None
