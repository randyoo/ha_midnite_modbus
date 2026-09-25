"""Tests for the set points: what each one reads, and what it puts on the wire.

The register map gives a formula per register, and a set point that misreads it is
worse than a sensor that does: it writes the wrong value to the battery. Every case
below quotes the map's row.
"""

from __future__ import annotations

import asyncio

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import REGISTER_GROUPS, REGISTER_MAP
from midnite_solar.number import (
    AbsorbTimeNumber,
    AbsorbVoltageNumber,
    BatteryCurrentLimitNumber,
    BatteryTempCompValueNumber,
    EqualizeIntervalDaysNumber,
    EqualizeRetryDaysNumber,
    EqualizeTimeNumber,
    EqualizeVoltageNumber,
    FloatVoltageNumber,
    MaxBatteryTempCompVoltageNumber,
    MinAbsorbTimeNumber,
    MinBatteryTempCompVoltageNumber,
    ModbusAddressNumber,
)
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

SPEC_ROWS = {
    4148: "Battery output Current Limit (EE) | [4148] /10) Amps",
    4149: "Absorb Set Point Voltage (EE) | ([4149] /10) Volts",
    4150: "Float Voltage Set Point (EE) | ( [4150] /10) Volts",
    4151: "Equalize Voltage Set Point (EE) | ([4151] /10) Volts",
    4153: "Minimum Absorb Time (EE) | [4153] seconds",
    4154: "Absorb Time (EE) | [4154] seconds",
    4155: "Maximum Battery Temperature Compensation Voltage (EE) | ([4155] /10) Volts",
    4156: "Minimum Battery Temperature Compensation Voltage (EE) | ([4155] /10) Volts",
    4157: "Battery Temp Comp Value for each 2V cell (EE) | -([4157] /10) mV/degree C/cell (0.5 mV steps)",
    4159: "EqualizeReTryDays (EE) | [4159] Number of days",
    4162: "Equalize Time (EE) | [4162] Seconds",
    4163: "Equalize Interval Days (EE) | [4163] Days",
    4326: "ClassicModbusAddr (EE) | 0 to 255 Classic Modbus Addr",
}


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def group_of(address):
    """The register group the real coordinator would have filled for this address."""
    return next(
        name for name, registers in REGISTER_GROUPS.items() if address in registers
    )


def build(cls, entry, address, raw, api=None):
    api = api or FakeApi()
    # Put the raw register in the group the real coordinator polls it in, so the
    # entity is exercised the way it runs - not through a group name it never sees.
    coordinator = FakeCoordinator(Hass(), api, {group_of(address): {address: raw}})
    coordinator.hass = Hass()
    entity = cls(coordinator, entry)
    entity.hass = coordinator.hass
    return entity


def written(cls, entry, address, value):
    """The register value a set point puts on the wire, and the EEPROM commit."""
    api = FakeApi()
    entity = build(cls, entry, address, 0, api)
    asyncio.run(entity.async_set_native_value(value))
    return api.writes


class TestRegisterAddresses:
    """The addresses these tests write are the ones const.py claims for them."""

    @pytest.mark.parametrize("address", sorted(SPEC_ROWS))
    def test_const_names_this_register(self, address):
        assert address in REGISTER_MAP.values(), (
            f"{address} is not a register const.py knows"
        )

    def test_the_minimum_and_maximum_temp_compensation_are_different_registers(self):
        """The map's row for 4156 quotes "[4155] /10": a typo in the document.

        The registers are separate, so each set point writes its own; only the
        formula column is wrong in the PDF.
        """
        assert REGISTER_MAP["MAX_BATTERY_TEMP_COMP_VOLTAGE"] == 4155
        assert REGISTER_MAP["MIN_BATTERY_TEMP_COMP_VOLTAGE"] == 4156

    def test_the_two_equalize_registers_are_not_the_absorb_ones(self):
        assert REGISTER_MAP["EQUALIZE_TIME_EEPROM"] == 4162
        assert REGISTER_MAP["EQUALIZE_INTERVAL_DAYS_EEPROM"] == 4163
        assert REGISTER_MAP["ABSORB_TIME_EEPROM"] == 4154


class TestVoltsAreTenths:
    @pytest.mark.parametrize(
        ("cls", "address"),
        [
            (AbsorbVoltageNumber, 4149),
            (FloatVoltageNumber, 4150),
            (EqualizeVoltageNumber, 4151),
            (MaxBatteryTempCompVoltageNumber, 4155),
            (MinBatteryTempCompVoltageNumber, 4156),
        ],
    )
    def test_a_voltage_reads_tenths(self, entry, cls, address):
        assert build(cls, entry, address, 576).native_value == 57.6

    @pytest.mark.parametrize(
        ("cls", "address"),
        [
            (AbsorbVoltageNumber, 4149),
            (FloatVoltageNumber, 4150),
            (EqualizeVoltageNumber, 4151),
            (MaxBatteryTempCompVoltageNumber, 4155),
            (MinBatteryTempCompVoltageNumber, 4156),
        ],
    )
    def test_a_voltage_writes_tenths(self, entry, cls, address):
        assert written(cls, entry, address, 57.6)[0] == (address, 576)


class TestAmpsAreTenths:
    def test_the_current_limit_reads_tenths(self, entry):
        """4148: "[4148] /10) Amps ... (eg. 23.4 A = 234)"."""
        entity = build(BatteryCurrentLimitNumber, entry, 4148, 234)
        assert entity.native_value == 23.4

    def test_the_current_limit_writes_tenths(self, entry):
        assert written(BatteryCurrentLimitNumber, entry, 4148, 23.4)[0][1] == 234


class TestTimes:
    def test_minimum_absorb_time_is_seconds(self, entry):
        """4153: "[4153] seconds (normally unused now)"."""
        entity = build(MinAbsorbTimeNumber, entry, 4153, 300)
        assert entity.native_value == 300

    def test_absorb_time_shows_minutes_and_writes_seconds(self, entry):
        """4154: "[4154] seconds"; the field is in minutes because nobody thinks in 2700."""
        entity = build(AbsorbTimeNumber, entry, 4154, 2700)
        assert entity.native_value == 45.0
        assert written(AbsorbTimeNumber, entry, 4154, 45)[0][1] == 2700

    def test_equalize_time_shows_minutes_and_writes_seconds(self, entry):
        """4162: "[4162] Seconds"."""
        entity = build(EqualizeTimeNumber, entry, 4162, 1800)
        assert entity.native_value == 30.0
        assert written(EqualizeTimeNumber, entry, 4162, 30)[0][1] == 1800


class TestDayCounts:
    """4159 and 4163 are plain day numbers: the map divides and multiplies nothing."""

    def test_equalize_retry_days_reads_days(self, entry):
        assert build(EqualizeRetryDaysNumber, entry, 4159, 5).native_value == 5

    def test_equalize_interval_days_reads_days(self, entry):
        """4163: "[4163] Days" - a Classic set to 30 days must show 30, not 3."""
        assert build(EqualizeIntervalDaysNumber, entry, 4163, 30).native_value == 30

    def test_equalize_interval_days_writes_days(self, entry):
        """Asking for 30 days used to write 300."""
        assert written(EqualizeIntervalDaysNumber, entry, 4163, 30)[0][1] == 30

    def test_the_day_fields_step_by_a_day(self, entry):
        assert build(EqualizeIntervalDaysNumber, entry, 4163, 30).native_step == 1
        assert build(EqualizeRetryDaysNumber, entry, 4159, 5).native_step == 1


class TestTemperatureCompensation:
    """4157: "-([4157] /10) mV/degree C/cell (0.5 mV steps) 0 to 10 mV per 2V cell"."""

    def test_the_value_is_negative_because_the_map_says_so(self, entry):
        """A positive register is a negative compensation: hotter battery, lower voltage."""
        assert build(BatteryTempCompValueNumber, entry, 4157, 50).native_value == -5.0

    def test_writing_a_negative_compensation_clears_the_sign(self, entry):
        assert written(BatteryTempCompValueNumber, entry, 4157, -5.0)[0][1] == 50

    def test_the_range_the_map_states(self, entry):
        entity = build(BatteryTempCompValueNumber, entry, 4157, 0)
        assert entity.native_min_value == -10.0
        assert entity.native_max_value == 0.0

    def test_the_step_the_map_states(self, entry):
        """The register counts tenths, but the Classic only moves in 0.5 mV steps."""
        assert build(BatteryTempCompValueNumber, entry, 4157, 0).native_step == 0.5

    def test_zero_is_the_top_of_the_range(self, entry):
        """0 mV/°C means no compensation, which is the highest value on a signed scale."""
        assert build(BatteryTempCompValueNumber, entry, 4157, 0).native_value == -0.0


class TestModbusAddress:
    def test_the_address_is_the_address(self, entry):
        """4326: "0 to 255 Classic Modbus Addr | Default address = 10 (ten)"."""
        assert build(ModbusAddressNumber, entry, 4326, 10).native_value == 10

    def test_it_is_not_a_tenth_of_anything(self, entry):
        assert written(ModbusAddressNumber, entry, 4326, 12)[0][1] == 12

    def test_the_address_range_the_map_states(self, entry):
        entity = build(ModbusAddressNumber, entry, 4326, 10)
        assert entity.native_max_value == 255

    def test_the_unit_of_a_modbus_address_is_nothing(self, entry):
        assert (
            build(ModbusAddressNumber, entry, 4326, 10).native_unit_of_measurement
            is None
        )


class TestEverySetPointSendsTheCommit:
    """Every set point here is (EE), so every write must be followed by the commit."""

    @pytest.mark.parametrize(
        ("cls", "address"),
        [
            (AbsorbVoltageNumber, 4149),
            (FloatVoltageNumber, 4150),
            (EqualizeVoltageNumber, 4151),
            (BatteryCurrentLimitNumber, 4148),
            (MinAbsorbTimeNumber, 4153),
            (AbsorbTimeNumber, 4154),
            (MaxBatteryTempCompVoltageNumber, 4155),
            (MinBatteryTempCompVoltageNumber, 4156),
            (BatteryTempCompValueNumber, 4157),
            (EqualizeRetryDaysNumber, 4159),
            (EqualizeTimeNumber, 4162),
            (EqualizeIntervalDaysNumber, 4163),
        ],
    )
    def test_the_write_is_followed_by_the_eeprom_commit(self, entry, cls, address):
        writes = written(cls, entry, address, 1)
        assert writes[0][0] == address
        assert (4160, 0x0004) in writes, "Table 4160-1 ForceEEpromUpdateWriteF"
