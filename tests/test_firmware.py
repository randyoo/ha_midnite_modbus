"""Tests for the firmware version and revision sensors.

The register map's rows, verbatim:

  16385 | app version _ | Major: [16385](15…12) Minor: [16385](11…8) Release:
          [16385](8..4) | Release version of the application code
  16386 | net version, _ | Major: [16386](15…12) Minor: [16386](11…8) Release:
          [16386](8…4) | Release version of the communications stack
  16387 16388 | app rev _ | ([16388] << 16) + [16387] | Build Revision of the
          application code
  16389 16390 | net rev _ | ([16390] << 16) + [16389] | Build Revision of the
          communications code stack
"""

from __future__ import annotations

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import (
    FIRMWARE_REVISION_SENSORS,
    FIRMWARE_VERSION_SENSORS,
    REGISTER_GROUPS,
    REGISTER_MAP,
)
from midnite_solar.coordinator import register_blocks
from midnite_solar.register_values import VERSION_FIELDS, version_from_register
from midnite_solar.sensor import FirmwareRevisionSensor, FirmwareVersionSensor
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.helpers.entity import EntityCategory


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def firmware_sensor(entry, registers, key="APP_VERSION"):
    coordinator = FakeCoordinator(Hass(), FakeApi(), {"firmware": dict(registers)})
    row = next(row for row in FIRMWARE_VERSION_SENSORS if row[0] == key)
    return FirmwareVersionSensor(coordinator, entry, *row)


class TestVersionDecode:
    """Three four-bit fields, as the map splits them."""

    def test_a_version_reads_field_by_field(self):
        assert version_from_register(0x1234) == "1.2.3"

    def test_the_highest_values_the_fields_hold(self):
        assert version_from_register(0xFFFF) == "15.15.15"

    def test_a_zero_register_is_a_version_of_zero_not_unknown(self):
        assert version_from_register(0x0000) == "0.0.0"

    def test_the_fields_do_not_overlap(self):
        """The map prints "Release: [16385](8..4)" while Minor is "(11…8)".

        Taken literally bit 8 is in both fields. Bit 8 is treated as Minor's, which
        is the only reading that gives three separate fields; this test exists so
        the choice is written down somewhere that runs.
        """
        assert version_from_register(0x0100) == "0.1.0"
        assert [mask for _name, mask, _shift in VERSION_FIELDS] == [
            0xF000,
            0x0F00,
            0x00F0,
        ]


class TestFirmwareGroup:
    def test_the_six_registers_are_one_request(self):
        assert register_blocks(REGISTER_GROUPS["firmware"]) == [(16385, 16390)]

    def test_the_addresses_are_the_maps(self):
        assert REGISTER_MAP["APP_VERSION"] == 16385
        assert REGISTER_MAP["NET_VERSION"] == 16386
        assert REGISTER_MAP["APP_REV_LOW"] == 16387
        assert REGISTER_MAP["APP_REV_HIGH"] == 16388
        assert REGISTER_MAP["NET_REV_LOW"] == 16389
        assert REGISTER_MAP["NET_REV_HIGH"] == 16390


class TestVersionSensors:
    def test_the_app_version(self, entry):
        entity = firmware_sensor(entry, {16385: 0x1234})
        assert entity.native_value == "1.2.3"

    def test_each_version_reads_its_own_register(self, entry):
        coordinator = FakeCoordinator(
            Hass(), FakeApi(), {"firmware": {16385: 0x1234, 16386: 0x2345}}
        )
        app = FirmwareVersionSensor(
            coordinator, entry, "APP_VERSION", "App Version", "application code"
        )
        net = FirmwareVersionSensor(
            coordinator, entry, "NET_VERSION", "Comms Version", "communications stack"
        )
        assert app.native_value == "1.2.3"
        assert net.native_value == "2.3.4"

    def test_no_reading_is_unknown(self, entry):
        entity = firmware_sensor(entry, {})
        assert entity.native_value is None

    def test_identity_and_category(self, entry):
        entity = firmware_sensor(entry, {16385: 0x1234})
        assert entity.unique_id == "entry-1_app_version"
        assert entity.entity_category == EntityCategory.DIAGNOSTIC

    def test_it_says_which_code_it_versions(self, entry):
        entity = firmware_sensor(entry, {16385: 0x1234})
        assert entity.extra_state_attributes == {"describes": "application code"}

    def test_the_two_version_registers_are_the_two_stacks(self, entry):
        assert [row[0] for row in FIRMWARE_VERSION_SENSORS] == [
            "APP_VERSION",
            "NET_VERSION",
        ]


class TestRevisionSensors:
    """The map's pair formula: "([16388] << 16) + [16387]".

    The second register of the pair is the high word.
    """

    def revisions(self, entry, registers, index=0):
        low_key, high_key, label = FIRMWARE_REVISION_SENSORS[index]
        coordinator = FakeCoordinator(Hass(), FakeApi(), {"firmware": dict(registers)})
        return FirmwareRevisionSensor(coordinator, entry, low_key, high_key, label)

    def test_the_pair_makes_one_32_bit_number(self, entry):
        entity = self.revisions(entry, {16387: 0x5678, 16388: 0x1234})
        assert entity.native_value == 0x12345678

    def test_the_word_order_is_the_maps(self, entry):
        entity = self.revisions(entry, {16387: 0x0001, 16388: 0x0000})
        assert entity.native_value == 0x00000001, "16387 is the low word"

    def test_the_comms_stack_has_its_own_pair(self, entry):
        entity = self.revisions(entry, {16389: 0x0002, 16390: 0x0003}, index=1)
        assert entity.native_value == 0x00030002

    def test_half_a_pair_is_not_guessed_at(self, entry):
        assert self.revisions(entry, {16387: 0x5678}).native_value is None

    def test_identity(self, entry):
        entity = self.revisions(entry, {16387: 0x5678, 16388: 0x1234})
        assert entity.unique_id == "entry-1_app_rev_low"
        assert entity.name == "App Build Revision"
        assert entity.entity_category == EntityCategory.DIAGNOSTIC
