"""Tests for the two sensors that report register 4120's low byte and 4275.

Transcribed from the register map:

  4120 | R | ComboChargeStage | Charge Stage = [4120] MSB  State = [4120] LSB
  Table 4120-1 Battery Charge Stage (HIGH Byte): Resting 0, Absorb 3, BulkMppt 4,
  Float 5, FloatMppt 6, Equalize 7, HyperVoc 10, EqMppt 18
  Table 4120-2 Classic States (LOWER Byte): "Internal Resting state 0" = Resting,
  "Internal state 1,2" = Waking/Starting, "Internal state 3,4,6" = MPPT or
  Regulating Voltage
  4275 | R | ReasonForResting | [4275] Reason number | See Table 4275-1
  Table 4275-1 lists reasons 1-19, 22 and 25-35; 20, 21, 23 and 24 are not listed.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.helpers.entity import EntityCategory

from midnite_solar.const import (
    CHARGE_STAGES,
    INTERNAL_STATES,
    REGISTER_MAP,
    REST_REASONS,
)
from midnite_solar.sensor import (
    ClassicDateSensor,
    ClassicTimeSensor,
    InternalStateSensor,
    RestReasonSensor,
)


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def sensors(api, entry, status=None, diagnostics=None):
    coordinator = FakeCoordinator(
        Hass(),
        api,
        {
            "status": dict(status or {}),
            "diagnostics": dict(diagnostics or {}),
        },
    )
    return (
        InternalStateSensor(coordinator, entry),
        RestReasonSensor(coordinator, entry),
    )


def combo(stage=0, state=0):
    """Register 4120 as the map packs it: stage in the high byte, state in the low."""
    return (stage << 8) | state


class TestTables:
    """The tables in const.py have to be the map's."""

    def test_charge_stage_is_table_4120_1(self):
        assert CHARGE_STAGES == {
            0: "Resting",
            3: "Absorb",
            4: "BulkMPPT",
            5: "Float",
            6: "FloatMppt",
            7: "Equalize",
            10: "HyperVoc",
            18: "EQ MPPT",
        }

    def test_classic_states_are_table_4120_2(self):
        """The map gives three names covering six values."""
        assert set(INTERNAL_STATES) == {0, 1, 2, 3, 4, 6}
        assert INTERNAL_STATES[0] == "Resting"
        assert INTERNAL_STATES[1].startswith("Waking/Starting")
        assert INTERNAL_STATES[6].startswith("MPPT / Regulating Voltage")

    def test_rest_reasons_are_table_4275_1(self):
        """Reasons 1-19, 22 and 25-35 are listed; 20, 21, 23 and 24 are not."""
        assert set(REST_REASONS) == set(range(1, 20)) | {22} | set(range(25, 36))
        assert REST_REASONS[1] == "Anti-Click. Not enough power available (Wake Up)"
        assert REST_REASONS[35].startswith("Battery voltage is less than Low Battery Disconnect")


class TestInternalState:
    def test_the_low_byte_is_the_state(self, entry):
        internal, _ = sensors(
            FakeApi(), entry, {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(5, 3)}
        )
        assert internal.native_value.startswith("MPPT / Regulating Voltage")

    def test_the_high_byte_is_left_to_the_charge_stage_sensor(self, entry):
        internal, _ = sensors(
            FakeApi(), entry, {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(7, 0)}
        )
        assert internal.native_value == "Resting"

    def test_a_state_value_the_table_does_not_list_is_said_so(self, entry):
        internal, _ = sensors(
            FakeApi(), entry, {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(0, 5)}
        )
        assert internal.native_value == "Unknown (5)"

    def test_no_reading_is_unknown(self, entry):
        internal, _ = sensors(FakeApi(), entry)
        assert internal.native_value is None

    def test_the_rest_reason_is_not_mixed_into_the_state(self, entry):
        """It used to be, which made this history a graph of something else."""
        api = FakeApi()
        internal, _ = sensors(
            api,
            entry,
            {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(0, 0)},
            {REGISTER_MAP["REASON_FOR_RESTING"]: 6},
        )
        assert internal.native_value == "Resting"

    def test_the_state_does_not_move_when_the_reason_changes(self, entry):
        coordinator = FakeCoordinator(
            Hass(),
            FakeApi(),
            {
                "status": {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(0, 0)},
                "diagnostics": {REGISTER_MAP["REASON_FOR_RESTING"]: 6},
            },
        )
        internal = InternalStateSensor(coordinator, entry)
        first = internal.native_value
        coordinator.data["data"]["diagnostics"][REGISTER_MAP["REASON_FOR_RESTING"]] = 10
        assert internal.native_value == first


class TestRestReason:
    def test_the_reason_is_decoded_while_resting(self, entry):
        _, rest = sensors(
            FakeApi(),
            entry,
            {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(0, 0)},
            {REGISTER_MAP["REASON_FOR_RESTING"]: 6},
        )
        assert rest.native_value == REST_REASONS[6]

    def test_it_says_so_when_the_classic_is_not_resting(self, entry):
        """4275 keeps the last reason after the Classic wakes; it is history then."""
        _, rest = sensors(
            FakeApi(),
            entry,
            {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(5, 3)},
            {REGISTER_MAP["REASON_FOR_RESTING"]: 6},
        )
        assert rest.native_value == "Not resting"

    def test_a_reason_the_table_does_not_list_is_reported_as_unknown(self, entry):
        _, rest = sensors(
            FakeApi(),
            entry,
            {REGISTER_MAP["COMBO_CHARGE_STAGE"]: combo(0, 0)},
            {REGISTER_MAP["REASON_FOR_RESTING"]: 21},
        )
        assert rest.native_value == "Unknown reason (21)"

    def test_no_reading_is_unknown(self, entry):
        _, rest = sensors(FakeApi(), entry)
        assert rest.native_value is None

    def test_it_is_enabled_because_it_is_the_only_entity_for_the_reason(self, entry):
        _, rest = sensors(FakeApi(), entry)
        assert rest.entity_registry_enabled_default is True
        assert rest.entity_category == EntityCategory.DIAGNOSTIC
        assert rest.unique_id == "entry-1_rest_reason"

    def test_the_reason_comes_from_4275(self, entry):
        assert REGISTER_MAP["REASON_FOR_RESTING"] == 4275
        assert REGISTER_MAP["COMBO_CHARGE_STAGE"] == 4120


def tidy(text):
    """The map's spacing and letter case, as a person would write them."""
    return (
        text.replace(" ?", "?")
        .replace("MPPT", "Mppt")
        .replace("Bridge", "bridge")
        .replace("...", "\u2026")
        .replace("off for", "off. for")
        .lower()
    )


class TestWordingIsTheMapsWording:
    """const.py's reason texts, measured against the document's.

    Every difference is letter case or punctuation, listed here so a future edit
    cannot quietly reword a reason into saying something the map does not say. The
    document is a Word export and writes some of these oddly ("off. for HI", an
    ellipsis character, "Mppt MODE"); Home Assistant shows this text to a user, so
    it was tidied - but only that much.
    """

    MAP_WORDING = {
        3: "Negative Current (load on PV input ?) (Wake Up)",
        6: "FET temperature too high (Cover is on maybe ?)",
        16: "Mppt MODE is OFF (Usually because user turned it off)",
        25: "Battery Voltage too high of Overshoot (small battery or bad cable ?)",
        27: "bridge center == 1023 (R132 might have been stuffed) This turns MPPT Mode to OFF",
        30: "PkAmpsOverLimit\u2026 Software detected too high of PEAK output current",
        32: "Aux 2 input commanded Classic off. for HI or LO (Aux2Function == 15 or 16)",
        35: "Battery voltage is less than Low Battery Disconnect (LBD) Typically Vbatt is less than 8.5 volts",
    }

    def test_the_only_differences_are_case_and_punctuation(self):
        for code, wording in self.MAP_WORDING.items():
            assert tidy(wording) == tidy(REST_REASONS[code]), code

    def test_the_meaning_words_are_untouched(self):
        assert "Anti-Click" in REST_REASONS[1]
        assert "Ground Fault" in REST_REASONS[7]
        assert "backfeed from battery" in REST_REASONS[9]
        assert "8.0 Volts" in REST_REASONS[10]
        assert "Low Light or bad connection" in REST_REASONS[11]
        assert "too high for 250V or 250KS" in REST_REASONS[19]
        assert "RELAY is not engaged" in REST_REASONS[28]
        assert "Partial Shade" not in REST_REASONS[1]

    def test_every_reason_the_map_lists_has_a_name(self):
        for code in REST_REASONS:
            assert REST_REASONS[code].strip() != ""


class TestClassicClockSensors:
    """Classic Time is a TIMESTAMP (HA 2026.9 requires an aware datetime),
    Classic Date is a DATE (a plain date). This is the corrected declaration
    after the `SensorDeviceClass.TIME` AttributeError that dropped the whole
    sensor platform; real HA hard-fails a naive value for TIMESTAMP
    ("missing timezone information"), so tagging the naive CTIME wall time
    with HA's own zone is what makes the sensor legal - and it renders the
    same wall time the Classic's LCD shows."""

    WALL = datetime(2026, 9, 21, 14, 30, 5)

    @pytest.fixture
    def entry(self):
        return ConfigEntry(entry_id="entry-1", title="Classic 200")

    def _clock_group(self):
        return {
            REGISTER_MAP["CTIME_SECONDS_MINUTES"]: (30 << 8) | 5,   # 30:05
            REGISTER_MAP["CTIME_HOURS_WEEKDAY"]: (1 << 8) | 14,     # 14:00, weekday 1
            REGISTER_MAP["CTIME_DAY_MONTH"]: (9 << 8) | 21,         # Sep 21
            REGISTER_MAP["CTIME_YEAR"]: 2026,
            REGISTER_MAP["CTIME2"]: 0,
        }

    def _pair(self, entry, clock=None):
        coordinator = FakeCoordinator(
            Hass(), FakeApi(), {"clock": dict(self._clock_group() if clock is None else clock)}
        )
        return ClassicTimeSensor(coordinator, entry), ClassicDateSensor(coordinator, entry)

    def test_classic_time_is_an_aware_timestamp_of_the_wall_clock(self, entry):
        time_sensor, _ = self._pair(entry)
        assert time_sensor._attr_device_class == SensorDeviceClass.TIMESTAMP
        value = time_sensor.native_value
        assert isinstance(value, datetime)
        assert value.tzinfo is not None, "HA 2026.9 rejects a naive TIMESTAMP"
        # tagged, not shifted: same wall time the Classic shows
        assert value.replace(tzinfo=None) == self.WALL

    def test_classic_time_and_the_host_agree_on_the_offset(self, entry):
        time_sensor, _ = self._pair(entry)
        # the sensor carries the instance's own offset (dt_util.now()'s zone)
        host_offset = datetime.now().astimezone().utcoffset()
        assert time_sensor.native_value.utcoffset() == host_offset

    def test_classic_date_is_a_plain_date(self, entry):
        _, date_sensor = self._pair(entry)
        assert date_sensor._attr_device_class == SensorDeviceClass.DATE
        assert date_sensor.native_value == date(2026, 9, 21)

    def test_an_impossible_clock_shows_nothing(self, entry):
        zeroed = {address: 0 for address in self._clock_group()}
        time_sensor, date_sensor = self._pair(entry, zeroed)
        # words 4214-4217 of 0 are the impossible year-0 date
        assert time_sensor.native_value is None
        assert date_sensor.native_value is None
