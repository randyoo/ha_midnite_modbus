"""Every conversion a sensor applies, checked against the register map's formula.

Each case quotes the map's row and pins what the sensor must show for a given
register value. This is the test that would have caught the bugs found here one
after another: absorb voltage at 10x, IP octets in reverse, lifetime energy
divided when the map does not divide it, and the status roll with its roll counter
added to its value.
"""

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

from midnite_solar.const import REGISTER_GROUPS, REGISTER_MAP
from midnite_solar.coordinator import register_blocks
from midnite_solar.number import EqualizeVoltageNumber
from midnite_solar.sensor import (
    AbsorbTimeRemainingSensor,
    BatteryCurrentSensor,
    BatteryTemperatureSensor,
    BatteryVoltageSensor,
    ChargeStageSensor,
    DailyAmpHoursSensor,
    DailyEnergySensor,
    DeviceTypeSensor,
    EqualizeTimeRemainingSensor,
    FETTemperatureSensor,
    FloatTimeTodaySensor,
    HighestInputVoltageSensor,
    LifetimeAmpHoursSensor,
    LifetimeEnergySensor,
    LoggingIntervalSensor,
    MACAddressSensor,
    MatchPointShadowSensor,
    ModbusPortSensor,
    PCBTemperatureSensor,
    PVInputCurrentSensor,
    PVoltageSensor,
    PowerWattsSensor,
    RestReasonSensor,
    RestartTimeSensor,
    StatusRollSensor,
    VOCMeasuredSensor,
)


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def sensor(cls, entry, group, values):
    """Build one sensor with only the registers it needs, all read."""
    coordinator = FakeCoordinator(Hass(), FakeApi(), {group: dict(values)})
    return cls(coordinator, entry)


def one(cls, entry, group, key, raw):
    """Build a single-register sensor by const key."""
    return sensor(cls, entry, group, {REGISTER_MAP[key]: raw})


class TestStatusRoll:
    """4113: "([4113]>>12)Count + ([4113]& 0x0fff) Value | ... Hi 4 bits = count"."""

    def test_the_value_is_the_low_twelve_bits(self, entry):
        assert one(StatusRollSensor, entry, "status", "STATUSROLL", 0x0001).native_value == 1

    def test_the_count_is_not_added_to_the_value(self, entry):
        """3 << 12 | 1 is value 1 with a count of 3, which used to read as 4."""
        entity = one(StatusRollSensor, entry, "status", "STATUSROLL", 0x3001)
        assert entity.native_value == 1
        assert entity.extra_state_attributes == {"count": 3, "raw": 0x3001}

    def test_the_biggest_value_the_field_holds(self, entry):
        assert one(StatusRollSensor, entry, "status", "STATUSROLL", 0xFFFF).native_value == 4095

    def test_no_reading_is_unknown(self, entry):
        assert StatusRollSensor(FakeCoordinator(Hass(), FakeApi(), {}), entry).native_value is None


class TestTenthsOfAVoltOrAmp:
    """The "([4nnn] /10)" family in the status block."""

    @pytest.mark.parametrize(
        ("cls", "key", "raw", "expected"),
        [
            (BatteryVoltageSensor, "DISP_AVG_VBATT", 5432, 543.2),  # "([4115] /10) Volts"
            (PVoltageSensor, "DISP_AVG_VPV", 1234, 123.4),  # "([4116] /10) Volts"
            (BatteryCurrentSensor, "IBATT_DISPLAY_S", 200, 20.0),  # "([4117] /10) Amps"
            (PVInputCurrentSensor, "PV_INPUT_CURRENT", 111, 11.1),  # "([4121] /10) Amps"
            (VOCMeasuredSensor, "VOC_LAST_MEASURED", 987, 98.7),  # "([4122] /10) Volts"
            (HighestInputVoltageSensor, "HIGHEST_VINPUT_LOG", 765, 76.5),  # "[4123] Voltage /10"
        ],
    )
    def test_tenths(self, entry, cls, key, raw, expected):
        assert one(cls, entry, "status", key, raw).native_value == expected

    def test_a_discharge_reads_negative(self, entry):
        """4117 is two's-complement tenths: -20.0 A is register 65336.

        A sign test placed after the /10 can never fire (a register divided by 10
        is at most 6553.5), so this reading used to be thrown away as "invalid".
        """
        assert one(BatteryCurrentSensor, entry, "status", "IBATT_DISPLAY_S", 65336) .native_value == pytest.approx(-20.0)

    def test_a_large_battery_current_is_not_invented_away(self, entry):
        """The map gives "[4117] /10 Amps" with no range; the old >200 A filter
        silently dropped what a Classic 250 can legitimately report."""
        assert one(BatteryCurrentSensor, entry, "status", "IBATT_DISPLAY_S", 2400).native_value == pytest.approx(240.0)

    def test_pv_input_current_reads_negative(self, entry):
        """4121 is the same two's-complement tenths as 4117."""
        assert one(PVInputCurrentSensor, entry, "status", "PV_INPUT_CURRENT", 65336).native_value == pytest.approx(-20.0)

    def test_a_large_pv_current_is_not_invented_away(self, entry):
        assert one(PVInputCurrentSensor, entry, "status", "PV_INPUT_CURRENT", 1200).native_value == pytest.approx(120.0)

    def test_no_current_is_dropped_for_a_ceiling_the_map_does_not_give(self, entry):
        """The old ">200 A is invalid" filter was itself the invented range.

        "([4117] /10) Amps" gives no limits, and FINDINGS' own rule is that a
        range the document does not give must not gate a reading: a Classic 250
        can legitimately pass 200 A, while a torn read at 3000 A is visible
        nonsense the user can see - a silently missing value hides the very
        problem the sensor exists to catch.
        """
        assert one(BatteryCurrentSensor, entry, "status", "IBATT_DISPLAY_S", 30000).native_value == pytest.approx(3000.0)

    def test_a_temperature_below_zero_reads_negative(self, entry):
        """Map: "([4132] /10) °C"; the Classic must be able to say it is freezing."""
        assert one(BatteryTemperatureSensor, entry, "temperatures", "BATT_TEMPERATURE", 0xFF9C).native_value == pytest.approx(-10.0)

    def test_the_two_internal_temperatures_read_the_same_way(self, entry):
        """4133 and 4134: "([4nnn] /10) °C"."""
        assert one(FETTemperatureSensor, entry, "temperatures", "FET_TEMPERATURE", 456).native_value == pytest.approx(45.6)
        assert one(PCBTemperatureSensor, entry, "temperatures", "PCB_TEMPERATURE", 321).native_value == pytest.approx(32.1)

    def test_the_temperatures_are_polled_together(self):
        assert register_blocks(REGISTER_GROUPS["temperatures"]) == [(4132, 4134)]


class TestPlainCounts:
    """Registers the map gives with no divisor at all."""

    def test_watts_are_watts(self, entry):
        """4119: "[4119] Watts"."""
        assert one(PowerWattsSensor, entry, "status", "WATTS", 1234).native_value == 1234

    def test_daily_amp_hours_are_amp_hours(self, entry):
        """4125: "[4125] Amp Hours | Daily Amp Hours reset at 23:59"."""
        assert one(DailyAmpHoursSensor, entry, "energy", "AMP_HOURS_DAILY", 42).native_value == 42

    def test_the_logging_interval_is_in_seconds(self, entry):
        """4136: "[4136] seconds | Minimum 60 seconds recent history data logging interval"."""
        assert one(LoggingIntervalSensor, entry, "settings", "MINUTE_LOG_INTERVAL_SEC", 300).native_value == 300

    def test_the_modbus_port_is_the_port(self, entry):
        """4137: "[4137] | 0 to 65,535. Default = 502"."""
        assert one(ModbusPortSensor, entry, "settings", "MODBUS_PORT_REGISTER", 502).native_value == 502

    def test_the_match_point_is_a_step_number(self, entry):
        """4124: "[4124] Present wind power curve step being indexed (1…16)"."""
        assert one(MatchPointShadowSensor, entry, "status", "MATCH_POINT_SHADOW", 7).native_value == 7

    def test_the_restart_timer_is_milliseconds(self, entry):
        """4114: "[4114] Milliseconds | Time after which the Classic can wake up"."""
        entity = one(RestartTimeSensor, entry, "status", "RESTART_TIME_MS", 2500)
        assert entity.native_value == 2500
        assert entity.extra_state_attributes == {"seconds": 2.5}


class TestEnergyTotals:
    """The 32-bit totals: the map combines them and divides by nothing."""

    def test_lifetime_energy_is_tenths_of_a_kilowatt_hour(self, entry):
        """4126 4127: map says "[...] kWh" with no divisor, but the Classic's own
        display shows a tenth (bench: 109917 -> 10991.7 kWh)."""
        values = {REGISTER_MAP["LIFETIME_KW_HOURS_1"]: 0x0001, REGISTER_MAP["LIFETIME_KW_HOURS_1"] + 1: 0x0000}
        assert sensor(LifetimeEnergySensor, entry, "energy", values).native_value == pytest.approx(0.1)

    def test_the_high_word_counts(self, entry):
        values = {REGISTER_MAP["LIFETIME_KW_HOURS_1"]: 0xFFFF, REGISTER_MAP["LIFETIME_KW_HOURS_1"] + 1: 0x0001}
        assert sensor(LifetimeEnergySensor, entry, "energy", values).native_value == pytest.approx(13107.1)

    def test_lifetime_amp_hours_is_the_other_pair(self, entry):
        """4128 4129: "(([4129] << 16) + [4128]) Amp Hours" - no divisor (bench 202213)."""
        values = {REGISTER_MAP["LIFETIME_AMP_HOURS_1"]: 500, REGISTER_MAP["LIFETIME_AMP_HOURS_1"] + 1: 2}
        assert sensor(LifetimeAmpHoursSensor, entry, "energy", values).native_value == 2 * 65536 + 500

    def test_daily_energy_is_tenths_of_a_kilowatt_hour(self, entry):
        """4118: "([4118] /10) kWatt-Hours | ... reset once per day"."""
        assert one(DailyEnergySensor, entry, "status", "KW_HOURS", 1234).native_value == 123.4

    def test_the_energy_registers_are_one_block(self):
        assert register_blocks(REGISTER_GROUPS["energy"]) == [(4125, 4129)]


class TestTimes:
    """4138, 4139 and 4143 are seconds; the sensors show minutes."""

    @pytest.mark.parametrize(
        ("cls", "key", "seconds", "minutes"),
        [
            (FloatTimeTodaySensor, "FLOAT_TIME_TODAY_SEC", 3600, 60.0),  # "[4138] seconds"
            (AbsorbTimeRemainingSensor, "ABSORB_TIME", 2700, 45.0),  # "[4139] seconds"
            (EqualizeTimeRemainingSensor, "EQUALIZE_TIME", 7200, 120.0),  # "[4143] Seconds"
        ],
    )
    def test_seconds_become_minutes(self, entry, cls, key, seconds, minutes):
        assert one(cls, entry, "time_settings", key, seconds).native_value == minutes

    @pytest.mark.parametrize(
        ("cls", "key"),
        [
            (FloatTimeTodaySensor, "FLOAT_TIME_TODAY_SEC"),
            (AbsorbTimeRemainingSensor, "ABSORB_TIME"),
            (EqualizeTimeRemainingSensor, "EQUALIZE_TIME"),
        ],
    )
    def test_the_raw_seconds_stay_available(self, entry, cls, key):
        entity = one(cls, entry, "time_settings", key, 90)
        assert entity.extra_state_attributes["seconds"] == 90


class TestPackedBytes:
    """Registers the map fills with more than one value."""

    def test_the_charge_stage_is_the_high_byte(self, entry):
        """4120: "Charge Stage = [4120] MSB State = [4120] LSB"."""
        assert one(ChargeStageSensor, entry, "status", "COMBO_CHARGE_STAGE", 0x0500).native_value == "Float"

    def test_the_charge_stage_is_not_confused_with_the_state(self, entry):
        """Low byte 3 is "MPPT / Regulating Voltage", high byte 0 is "Resting"."""
        assert one(ChargeStageSensor, entry, "status", "COMBO_CHARGE_STAGE", 0x0003).native_value == "Resting"

    def test_the_device_type_is_the_low_byte_of_the_unit_id(self, entry):
        """4101: "PCB revision = [4101]MSB Unit Type = [4101]LSB"."""
        assert one(DeviceTypeSensor, entry, "device_info", "UNIT_ID", (7 << 8) | 200).native_value == "Classic 200"

    def test_a_unit_type_the_table_does_not_have_is_reported_as_it_reads(self, entry):
        assert one(DeviceTypeSensor, entry, "device_info", "UNIT_ID", 999).native_value == "Unknown (231)"


class TestMACAddress:
    """4106-4108: "[4108] : [4108] : MSB LSB [4107] : [4107] : MSB LSB [4106] : [4106] MSB LSB"."""

    def _mac(self, entry, part_4106, part_4107, part_4108):
        values = {
            REGISTER_MAP["MAC_ADDRESS_PART_1"]: part_4106,
            REGISTER_MAP["MAC_ADDRESS_PART_2"]: part_4107,
            REGISTER_MAP["MAC_ADDRESS_PART_3"]: part_4108,
        }
        return sensor(MACAddressSensor, entry, "device_info", values).native_value

    def test_the_highest_register_holds_the_first_two_octets(self):
        assert self._mac(ConfigEntry(entry_id="e", title="t"), 0x0102, 0x0304, 0x00A1) == "00:a1:03:04:01:02"

    def test_a_realistic_classic_address(self):
        """Midnite's OUI is 00:00:00-ish; what matters is the byte order."""
        assert self._mac(ConfigEntry(entry_id="e", title="t"), 0x0101, 0x0202, 0x0303) == "03:03:02:02:01:01"

    def test_a_missing_register_is_not_guessed_at(self, entry):
        coordinator = FakeCoordinator(
            Hass(), FakeApi(), {"device_info": {REGISTER_MAP["MAC_ADDRESS_PART_1"]: 0x0102}}
        )
        assert MACAddressSensor(coordinator, entry).native_value is None

    def test_the_mac_is_read_in_the_block_already_polled(self):
        assert (4101, 4112) in register_blocks(REGISTER_GROUPS["device_info"])


class TestSetPointReadout:
    """The set points read tenths; the writes are covered in test_write_paths."""

    def test_equalize_voltage_is_tenths_of_a_volt(self, entry):
        assert one(EqualizeVoltageNumber, entry, "setpoints", "EQUALIZE_VOLTAGE_SETPOINT", 600).native_value == 60.0


class TestRegisterRowsAreQuoted:
    """The formulas this file pins, straight from the map, as a guard."""

    @pytest.mark.parametrize(
        ("key", "address"),
        [
            ("STATUSROLL", 4113),
            ("RESTART_TIME_MS", 4114),
            ("DISP_AVG_VBATT", 4115),
            ("DISP_AVG_VPV", 4116),
            ("IBATT_DISPLAY_S", 4117),
            ("KW_HOURS", 4118),
            ("WATTS", 4119),
            ("COMBO_CHARGE_STAGE", 4120),
            ("PV_INPUT_CURRENT", 4121),
            ("VOC_LAST_MEASURED", 4122),
            ("HIGHEST_VINPUT_LOG", 4123),
            ("MATCH_POINT_SHADOW", 4124),
            ("AMP_HOURS_DAILY", 4125),
            ("LIFETIME_KW_HOURS_1", 4126),
            ("LIFETIME_AMP_HOURS_1", 4128),
            ("BATT_TEMPERATURE", 4132),
            ("FET_TEMPERATURE", 4133),
            ("PCB_TEMPERATURE", 4134),
            ("MINUTE_LOG_INTERVAL_SEC", 4136),
            ("MODBUS_PORT_REGISTER", 4137),
            ("FLOAT_TIME_TODAY_SEC", 4138),
            ("ABSORB_TIME", 4139),
            ("EQUALIZE_TIME", 4143),
            ("MAC_ADDRESS_PART_1", 4106),
            ("MAC_ADDRESS_PART_2", 4107),
            ("MAC_ADDRESS_PART_3", 4108),
        ],
    )
    def test_the_map_puts_this_register_where_const_does(self, key, address):
        assert REGISTER_MAP[key] == address
