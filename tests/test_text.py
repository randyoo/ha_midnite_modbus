"""Tests for the unit name text input, registers 4210-4213.

The register map gives the packing and an example, which is the golden case here:

  "4210 4211 4212 4213 | R/W | ID name (EE) | [4210] || [4210] || LSB MSB
   [4211] || [4211] || LSB MSB [4212] || [4212] || LSB MSB [4213] || [4213] LSB
   MSB End with 0 if less than 8 chars | Unit Name. 8 characters max. ASCII.
   Takes place of MODBUS Register in MNGP display if present. Example: "CLASSIC" =
   0x4C43, 0x5341, 0x4953, 0x0043"
"""

from __future__ import annotations

import asyncio

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError

from midnite_solar.const import DOMAIN, REGISTER_MAP
from midnite_solar.text import (
    NAME_REGISTERS,
    HostNameText,
    name_from_registers,
    registers_for_name,
)

MAP_EXAMPLE = [0x4C43, 0x5341, 0x4953, 0x0043]


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def text_entity(api, registers=None, entry=None):
    group = {} if registers is None else {address: value for address, value in zip(NAME_REGISTERS, registers)}
    coordinator = FakeCoordinator(Hass(), api, {"device_info": group})
    coordinator.hass = Hass()
    entity = HostNameText(coordinator, entry)
    entity.hass = coordinator.hass
    return entity


class TestTheMapsOwnExample:
    """The example is the specification: get it wrong and the name is garbage."""

    def test_the_maps_example_decodes_to_the_maps_name(self):
        assert name_from_registers(MAP_EXAMPLE) == "CLASSIC"

    def test_the_maps_name_packs_to_the_maps_example(self):
        assert registers_for_name("CLASSIC") == MAP_EXAMPLE

    def test_the_low_byte_is_the_earlier_character(self):
        """0x4C43 is 'C' (0x43) then 'L' (0x4C), not the other way round."""
        assert MAP_EXAMPLE[0] & 0xFF == ord("C")
        assert MAP_EXAMPLE[0] >> 8 == ord("L")

    def test_a_full_eight_characters_need_no_terminator(self):
        assert registers_for_name("CLASSIC1") == [0x4C43, 0x5341, 0x4953, 0x3143]
        assert name_from_registers(registers_for_name("CLASSIC1")) == "CLASSIC1"

    def test_the_four_registers_are_the_ones_the_map_names(self):
        assert NAME_REGISTERS == (4210, 4211, 4212, 4213)
        assert tuple(REGISTER_MAP[f"UNIT_NAME_{i}"] for i in range(4)) == NAME_REGISTERS


class TestPacking:
    """Edge cases around the 8-character limit."""

    def test_a_name_longer_than_the_classic_holds_is_refused(self):
        with pytest.raises(HomeAssistantError):
            registers_for_name("CLASSICEXTRA")

    def test_a_short_name_ends_with_zero(self):
        """Map: "End with 0 if less than 8 chars"."""
        registers = registers_for_name("A")
        assert registers[0] & 0xFF == ord("A")
        assert registers[0] >> 8 == 0

    def test_padding_after_the_terminator_is_not_part_of_the_name(self):
        assert name_from_registers(registers_for_name("Roof")) == "Roof"

    def test_a_name_padded_with_spaces_instead_of_zeros_still_reads(self):
        """Some firmware space-pads instead of zero-terminating; hide the padding."""
        registers = [0x5948, 0x5244, 0x204F, 0x2020]  # "HYDRO   "
        assert name_from_registers(registers) == "HYDRO"

    def test_an_all_zero_name_is_empty_not_error(self):
        assert name_from_registers([0, 0, 0, 0]) == ""


class TestReadout:
    def test_the_name_the_classic_reports(self, entry):
        entity = text_entity(FakeApi(), MAP_EXAMPLE, entry)
        assert entity.native_value == "CLASSIC"

    def test_no_reading_yet_is_unknown(self, entry):
        assert text_entity(FakeApi(), None, entry).native_value is None

    def test_a_partial_reading_is_not_guessed_at(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(
            Hass(), api, {"device_info": {4210: 0x4C43, 4211: 0x5341}}
        )
        assert HostNameText(coordinator, entry).native_value is None

    def test_the_input_is_eight_characters_of_name(self, entry):
        entity = text_entity(FakeApi(), MAP_EXAMPLE, entry)
        assert entity.max_length == 8
        assert entity.name == "Host Name"
        assert entity.unique_id == "entry-1_host_name"


class TestWrites:
    """A rename that silently failed is worse than one that errors."""

    def test_a_rename_writes_four_registers_and_commits(self, entry):
        api = FakeApi()
        asyncio.run(text_entity(api, MAP_EXAMPLE, entry).async_set_value("HYDRO 1"))
        written = dict(api.writes[:-1])
        assert written == dict(zip(NAME_REGISTERS, registers_for_name("HYDRO 1")))
        assert api.writes[-1] == (4160, 0x0004), "the map marks ID name (EE)"

    def test_every_written_register_is_read_back(self, entry):
        api = FakeApi()
        asyncio.run(text_entity(api, MAP_EXAMPLE, entry).async_set_value("PUMP"))
        assert api.reads == list(NAME_REGISTERS)

    def test_a_refused_write_is_reported(self, entry):
        api = FakeApi(error_writes=True)
        with pytest.raises(HomeAssistantError):
            asyncio.run(text_entity(api, MAP_EXAMPLE, entry).async_set_value("PUMP"))

    def test_a_write_the_classic_ignored_is_reported(self, entry):
        api = FakeApi(read_values={4210: 0x4C43}, stale_read=True)
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(text_entity(api, MAP_EXAMPLE, entry).async_set_value("HYDRO"))
        assert "ignored or clamped" in str(err.value)

    def test_the_commit_is_not_sent_before_the_registers_are_written(self, entry):
        api = FakeApi()
        asyncio.run(text_entity(api, MAP_EXAMPLE, entry).async_set_value("HYDRO"))
        assert [address for address, _ in api.writes] == [4210, 4211, 4212, 4213, 4160]

    def test_the_value_shows_the_new_name_after_a_successful_write(self, entry):
        entity = text_entity(FakeApi(), MAP_EXAMPLE, entry)
        asyncio.run(entity.async_set_value("HYDRO"))
        assert entity.native_value == "HYDRO"

    def test_the_refresh_runs_after_a_write(self, entry):
        entity = text_entity(FakeApi(), MAP_EXAMPLE, entry)
        asyncio.run(entity.async_set_value("HYDRO"))
        assert entity.coordinator.refresh_requests == 1


class TestDeviceInfo:
    """The name input shares the device identity with every other platform."""

    def test_the_serial_number_is_present(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(
            Hass(),
            api,
            {"device_info": {address: value for address, value in zip(NAME_REGISTERS, MAP_EXAMPLE)}, "serial": {28673: 0x11, 28674: 0x22}},
        )
        info = HostNameText(coordinator, entry).device_info
        assert info["serial_number"] == "1114146"  # 0x00110022; the registry takes text

    def test_the_platform_does_not_keep_its_own_copy_of_the_identity(self, entry):
        """It used to: 50 lines duplicated from base.py, without the serial."""
        from midnite_solar.base import MidniteBaseEntityDescription

        entity = text_entity(FakeApi(), MAP_EXAMPLE, entry)
        assert entity.device_info == MidniteBaseEntityDescription.get_device_info(
            entity.coordinator, entry, DOMAIN
        )
