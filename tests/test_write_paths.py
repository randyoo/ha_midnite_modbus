"""Tests for what the integration actually writes to the Classic.

Every expectation quotes the Classic MODBUS register map. These run against a
fake Modbus API: no sockets, and no Midnite Classic, which is single-connection
and must not be disturbed by a test run.
"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError

from midnite_solar.button import (
    ForceEEpromUpdateButton,
    ForceSweepButton,
    ResetFaultsButton,
    ResetInfoFlagsButton,
)
from midnite_solar import number as number_module
from midnite_solar.const import EE_BACKED_REGISTERS, REGISTER_MAP
# The map's own voltage example [64,68,70,72,75,78,81,83,85,87,89,91,93,98,104,112]
# packed the way the map says: "WindPowerTableV(stp 1) << 8) + WindPowerTableV(stp 0)".
WIND_STEPS = [64, 68, 70, 72, 75, 78, 81, 83, 85, 87, 89, 91, 93, 98, 104, 112]
WIND_TABLE = {
    4301 + even // 2: (WIND_STEPS[even + 1] << 8) | WIND_STEPS[even]
    for even in range(0, 16, 2)
}

from midnite_solar.number import (
    AbsorbTimeNumber,
    AbsorbVoltageNumber,
    BatteryCurrentLimitNumber,
    BatteryTempCompValueNumber,
    EqualizeTimeNumber,
    EqualizeVoltageNumber,
    FloatVoltageNumber,
    MidniteSolarNumber,
    MinAbsorbTimeNumber,
    WindPowerCurveINumber,
    WindPowerCurveVNumber,
)


@pytest.fixture
def hass():
    return Hass()


@pytest.fixture
def api():
    return FakeApi()


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def make_coordinator(hass, api, group="setpoints", registers=None):
    return FakeCoordinator(hass, api, {group: dict(registers or {})})


def absorb(hass, api, entry, value=57.6):
    coordinator = make_coordinator(hass, api, registers={REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]: int(value * 10)})
    number = AbsorbVoltageNumber(coordinator, entry)
    asyncio.run(number.async_set_native_value(value))
    return number, coordinator


class TestAbsorbVoltage:
    """The set point the register map calls "4149 R/W Absorb Set Point Voltage (EE)"."""

    def test_absorb_voltage_is_written_as_tenths_of_a_volts(self, hass, api, entry):
        """Spec: "([4149] /10) Volts ... (eg. 28.3V = 283)"."""
        absorb(hass, api, entry, value=28.3)
        assert api.writes[0] == (4149, 283)

    def test_absorb_voltage_is_committed_to_eeprom(self, hass, api, entry):
        """Spec: an (EE) value "is saved to EEprom whenever the Force write to EEprom is set"."""
        absorb(hass, api, entry, value=57.6)
        assert api.writes == [(4149, 576), (4160, 0x0004)]

    def test_commit_is_the_low_word_of_force_flag_bit_2(self, hass, api, entry):
        """Table 4160-1: ForceEEpromUpdateWriteF is 0x00000004, so it fits in 4160."""
        _, coordinator = absorb(hass, api, entry)
        assert api.writes[1][0] == REGISTER_MAP["FORCE_FLAG_BITS"] == 4160
        assert coordinator.refresh_requests == 1

    @pytest.mark.parametrize(("value", "raw"), [(13.6, 136), (28.8, 288), (48.0, 480), (57.6, 576)])
    def test_every_set_point_scales_to_tenths(self, hass, api, entry, value, raw):
        absorb(hass, api, entry, value=value)
        assert api.writes[0] == (4149, raw)

    def test_read_back_matches_the_value_written(self, hass, api, entry):
        number, _ = absorb(hass, api, entry, value=57.6)
        assert number.native_value == pytest.approx(57.6)


class TestOtherSetPoints:
    """The other numbers that write (EE) registers."""

    def test_float_voltage_is_committed(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, registers={4150: 555})
        asyncio.run(FloatVoltageNumber(coordinator, entry).async_set_native_value(55.5))
        assert api.writes == [(4150, 555), (4160, 0x0004)]

    def test_equalize_voltage_is_committed(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, registers={4151: 630})
        asyncio.run(EqualizeVoltageNumber(coordinator, entry).async_set_native_value(63.0))
        assert api.writes == [(4151, 630), (4160, 0x0004)]

    def test_battery_current_limit_follows_the_spec_example(self, hass, api, entry):
        """Spec: "e g. 23.4 A = 234" for register 4148."""
        coordinator = make_coordinator(hass, api, group="eeprom_settings", registers={4148: 234})
        asyncio.run(BatteryCurrentLimitNumber(coordinator, entry).async_set_native_value(23.4))
        assert api.writes == [(4148, 234), (4160, 0x0004)]

    def test_absorb_time_is_written_in_seconds_not_tenths(self, hass, api, entry):
        """Spec: "4154 R/W Absorb Time (EE) [4154] seconds" - the entity is in minutes."""
        coordinator = make_coordinator(hass, api, group="eeprom_settings", registers={4154: 7200})
        number = AbsorbTimeNumber(coordinator, entry)
        asyncio.run(number.async_set_native_value(120))
        assert api.writes == [(4154, 7200), (4160, 0x0004)]
        assert number.native_value == 120

    def test_min_absorb_time_is_plain_seconds(self, hass, api, entry):
        """Spec: "4153 R/W Minimum Absorb Time (EE) [4153] seconds"."""
        coordinator = make_coordinator(hass, api, group="time_settings", registers={4153: 300})
        number = MinAbsorbTimeNumber(coordinator, entry)
        asyncio.run(number.async_set_native_value(300))
        assert api.writes == [(4153, 300), (4160, 0x0004)]
        assert number.native_value == 300

    def test_equalize_time_is_written_in_seconds(self, hass, api, entry):
        """Spec: "4162 R/W Equalize Time (EE) [4162] Seconds"."""
        coordinator = make_coordinator(hass, api, group="eeprom_settings", registers={4162: 5400})
        number = EqualizeTimeNumber(coordinator, entry)
        asyncio.run(number.async_set_native_value(90))
        assert api.writes == [(4162, 5400), (4160, 0x0004)]
        assert number.native_value == 90

    def test_temp_comp_value_is_stored_as_a_magnitude(self, hass, api, entry):
        """Spec: "4157 ... -([4157] /10) mV/degree C/cell" - the register holds the magnitude."""
        coordinator = make_coordinator(hass, api, group="eeprom_settings", registers={4157: 30})
        number = BatteryTempCompValueNumber(coordinator, entry)
        assert number.native_value == pytest.approx(-3.0)
        asyncio.run(number.async_set_native_value(-3.0))
        assert api.writes == [(4157, 30), (4160, 0x0004)]

    @pytest.mark.parametrize("value", [-0.1, -3.0, -5.0, -10.0])
    def test_temp_comp_round_trips_through_the_register(self, hass, api, entry, value):
        coordinator = make_coordinator(hass, api, group="eeprom_settings", registers={})
        number = BatteryTempCompValueNumber(coordinator, entry)
        raw = number._to_register_value(value)
        assert raw > 0, "the Classic stores the magnitude, not a negative"
        assert number._from_register_value(raw) == pytest.approx(value)

    def test_a_setting_that_is_not_ee_backed_is_not_committed(self, hass, api, entry):
        """A plain (non-EE) register must not trigger an EEPROM cycle."""

        class PlainNumber(MidniteSolarNumber):
            """A setting the map lists without (EE), used to test the negative case."""

            register_address = 4238  # SiestaTime
            is_raw_value = True

        coordinator = make_coordinator(hass, api, group="time_settings", registers={4238: 300})
        number = PlainNumber(coordinator, entry)
        asyncio.run(number._async_set_value(300))
        assert api.writes == [(4238, 300)]


class TestWriteFailures:
    """A failed write has to reach the user instead of showing stale state."""

    def test_socket_error_is_raised(self, hass, entry):
        api = FakeApi(fail_writes=True)
        coordinator = make_coordinator(hass, api, registers={4149: 0})
        with pytest.raises(HomeAssistantError):
            asyncio.run(AbsorbVoltageNumber(coordinator, entry).async_set_native_value(57.6))

    def test_modbus_exception_response_is_raised(self, hass, entry):
        api = FakeApi(error_writes=True)
        coordinator = make_coordinator(hass, api, registers={4149: 0})
        with pytest.raises(HomeAssistantError):
            asyncio.run(AbsorbVoltageNumber(coordinator, entry).async_set_native_value(57.6))

    def test_no_eeprom_commit_is_sent_after_a_failed_write(self, hass, entry):
        api = FakeApi(fail_writes=True)
        coordinator = make_coordinator(hass, api, registers={4149: 0})
        with pytest.raises(HomeAssistantError):
            asyncio.run(AbsorbVoltageNumber(coordinator, entry).async_set_native_value(57.6))
        assert api.writes == [(4149, 576)]


class TestEepromBackedList:
    """Which registers need ForceEEpromUpdateWriteF to survive a restart."""

    @pytest.mark.parametrize(
        "key",
        [
            "ABSORB_SETPOINT_VOLTAGE",
            "FLOAT_VOLTAGE_SETPOINT",
            "EQUALIZE_VOLTAGE_SETPOINT",
            "BATTERY_OUTPUT_CURRENT_LIMIT",
            "ABSORB_TIME_EEPROM",
            "MIN_ABSORB_TIME",
            "EQUALIZE_TIME_EEPROM",
            "EQUALIZE_INTERVAL_DAYS_EEPROM",
            "MAX_BATTERY_TEMP_COMP_VOLTAGE",
            "MIN_BATTERY_TEMP_COMP_VOLTAGE",
            "BATTERY_TEMP_COMP_VALUE",
            "EQUALIZE_RETRY_DAYS",
            "MODBUS_PORT_REGISTER",
        ],
    )
    def test_ee_marked_settings_are_listed(self, key):
        assert REGISTER_MAP[key] in EE_BACKED_REGISTERS

    def test_read_only_and_plain_registers_are_not_listed(self):
        assert REGISTER_MAP["SLIDING_CURRENT_LIMIT"] not in EE_BACKED_REGISTERS  # 4152, read only
        assert 4238 not in EE_BACKED_REGISTERS  # SiestaTime, no (EE) marker

    def test_whole_wind_tables_are_listed(self):
        assert {REGISTER_MAP[f"WIND_POWER_TABLE_V_{step}_EEPA"] for step in range(8)} <= EE_BACKED_REGISTERS
        assert {REGISTER_MAP[f"WIND_POWER_TABLE_I_{step}_EEPA"] for step in range(8)} <= EE_BACKED_REGISTERS


class TestEveryNumberCommits:
    """A guard so no number can bypass the EEPROM commit again.

    AbsorbTimeNumber, EqualizeTimeNumber, MinAbsorbTimeNumber and
    BatteryTempCompValueNumber each carried a private copy of the write code and
    were the reason set points did not survive a restart.
    """

    @staticmethod
    def number_classes():
        """Every number class the integration defines."""
        return [
            obj
            for obj in vars(number_module).values()
            if isinstance(obj, type)
            and issubclass(obj, MidniteSolarNumber)
            and obj is not MidniteSolarNumber
        ]

    def test_all_number_classes_are_covered(self):
        assert len(self.number_classes()) == 16

    def test_every_ee_backed_setting_sends_a_commit(self, hass, entry):
        missing = []
        for cls in self.number_classes():
            api = FakeApi()
            coordinator = make_coordinator(hass, api)
            number = cls(coordinator, entry)
            asyncio.run(number._async_set_value(1))
            ee_backed = number.register_address in EE_BACKED_REGISTERS
            if ee_backed and len(api.writes) != 2:
                missing.append(cls.__name__)
            if not ee_backed and len(api.writes) != 1:
                missing.append(f"{cls.__name__} (extra commit)")
        assert not missing

    def test_commit_always_follows_the_setting(self, hass, entry):
        for cls in self.number_classes():
            api = FakeApi()
            number = cls(make_coordinator(hass, api), entry)
            asyncio.run(number._async_set_value(1))
            if number.register_address in EE_BACKED_REGISTERS:
                assert api.writes[1] == (4160, 0x0004), cls.__name__


class TestButtons:
    """Table 4160-1 flags, written to the word that can hold them."""

    @pytest.mark.parametrize(
        ("button_class", "expected"),
        [
            (ForceEEpromUpdateButton, (4160, 0x0004)),  # ForceEEpromUpdateWriteF
            (ResetInfoFlagsButton, (4160, 0x0010)),  # ForceResetInfoFlags
            (ForceSweepButton, (4160, 0x0800)),  # ForceSweepF
            (ResetFaultsButton, (4161, 0x0080)),  # ForceResetFaultsF, high word
        ],
    )
    def test_press_writes_the_documented_flag(self, hass, api, entry, button_class, expected):
        coordinator = make_coordinator(hass, api)
        asyncio.run(button_class(coordinator, entry).async_press())
        assert api.writes == [expected]

    def test_high_word_flag_survives_the_split(self, hass, api, entry):
        """ForceResetFaultsF is 0x00800000: the high word times 2**16 must be it."""
        coordinator = make_coordinator(hass, api)
        asyncio.run(ResetFaultsButton(coordinator, entry).async_press())
        register, word = api.writes[0]
        assert register == REGISTER_MAP["FORCE_FLAG_BITS_HIGH"]
        assert word << 16 == 0x00800000


class TestWindPowerTableSteps:
    """Section 1.3.3: 16 bytes per table, "0 to 255 volts" / "0 to 255 amps".

    The map packs them "WindPowerTableV(stp 1) << 8) + WindPowerTableV(stp 0)"
    into registers 4301-4308 (voltage) and 4309-4316 (current), so each write has
    to keep the neighbouring step and must not scale by ten.
    """

    @pytest.mark.parametrize(
        ("step", "address", "expected"),
        [(0, 4301, 64), (1, 4301, 68), (2, 4302, 70), (15, 4308, 112)],
    )
    def test_each_step_reads_its_own_byte(self, hass, api, entry, step, address, expected):
        api = FakeApi()
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        number = WindPowerCurveVNumber(coordinator, entry, step)
        assert number.register_address == address
        assert number.native_value == expected

    def test_writing_a_step_leaves_its_neighbour_alone(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        number = WindPowerCurveVNumber(coordinator, entry, 0)
        asyncio.run(number.async_set_native_value(70))
        # 4301 held step1 = 68 (0x44) and step0 = 64 (0x40); only the low byte moves.
        assert api.writes[0] == (4301, 0x4446)

    def test_writing_the_high_byte_step_keeps_the_low_byte(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        number = WindPowerCurveVNumber(coordinator, entry, 1)
        asyncio.run(number.async_set_native_value(75))
        assert api.writes[0] == (4301, 0x4B40)

    def test_steps_are_not_scaled_by_ten(self, hass, api, entry):
        """The running copy wrote 930 into an 8-bit field for a step of 93."""
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        number = WindPowerCurveVNumber(coordinator, entry, 10)
        assert number.register_address == 4306
        asyncio.run(number.async_set_native_value(100))
        assert api.writes[0][1] & 0xFF == 100
        assert api.writes[0][1] >> 8 == 91, "step 11 of the same register is untouched"

    def test_current_steps_live_in_the_second_table(self, hass, api, entry):
        """Spec example table I: [0,2,4,6,8,10,15,20,25,30,35,40,45,50,55,60]."""
        # Current example: [0,2,4,6,8,10,15,20,25,30,35,40,45,50,55,60]
        registers = {4309: (2 << 8) | 0, 4310: (6 << 8) | 4, 4316: (60 << 8) | 55}
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=registers)
        assert WindPowerCurveINumber(coordinator, entry, 0).native_value == 0
        assert WindPowerCurveINumber(coordinator, entry, 1).native_value == 2
        assert WindPowerCurveINumber(coordinator, entry, 15).native_value == 60

    def test_every_step_gets_an_eeprom_commit(self, hass, api, entry):
        # Current example [0,2,4,6,8,10,15,20,...]: step 6 (15 A) shares 4312 with step 7.
        registers = {4312: (20 << 8) | 15}
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=registers)
        number = WindPowerCurveINumber(coordinator, entry, 7)
        asyncio.run(number.async_set_native_value(18))
        assert api.writes == [(4312, (18 << 8) | 15), (4160, 0x0004)]

    def test_out_of_range_step_is_rejected_before_writing(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        number = WindPowerCurveVNumber(coordinator, entry, 0)
        with pytest.raises(HomeAssistantError):
            asyncio.run(number._async_set_value(300))
        assert api.writes == []

    def test_unique_ids_follow_the_step_number(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        assert WindPowerCurveVNumber(coordinator, entry, 0).unique_id == "entry-1_wind_power_curve_v0"
        assert WindPowerCurveINumber(coordinator, entry, 15).unique_id == "entry-1_wind_power_curve_i15"

    def test_step_range_is_the_byte_range(self, hass, api, entry):
        coordinator = make_coordinator(hass, api, group="wind_power_curve", registers=dict(WIND_TABLE))
        number = WindPowerCurveVNumber(coordinator, entry, 3)
        assert (number.native_min_value, number.native_max_value, number.native_step) == (0, 255, 1)
