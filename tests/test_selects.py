"""Tests for the selects: Aux fields as the map decodes them, MPPT off.

The register map is the source of every value here. Register 4165 is the
important one: it packs both Aux outputs, and the running copy was decoding it
with a 3-bit function field and a single on/off bit, which are not the fields
the map documents.
"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError

from midnite_solar.const import (
    AUX1_FUNCTIONS,
    AUX2_FUNCTIONS,
    AUX_FIELDS,
    AUX_OFF_AUTO_ON,
    MPPT_MODES,
    REGISTER_MAP,
)
from midnite_solar.register_values import read_field, write_field
from midnite_solar.select import (
    MPPT_OFF,
    Aux1FunctionSelector,
    Aux2FunctionSelector,
    MPPTModeSelector,
)

AUX_REGISTER = 4165


def aux_value(aux1_function=1, aux1_mode=1, aux2_function=0, aux2_mode=1):
    """Build register 4165 the way the map packs it."""
    return (
        (aux1_function & 0x3F)
        | ((aux1_mode & 0x03) << 6)
        | ((aux2_function & 0x3F) << 8)
        | ((aux2_mode & 0x03) << 14)
    )


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def selector(cls, entry, registers, group="aux_settings"):
    api = FakeApi()
    coordinator = FakeCoordinator(Hass(), api, {group: dict(registers)})
    return cls(coordinator, entry), api


class TestAuxFieldLayout:
    """The map's own decodes of register 4165."""

    SPEC_DECODES = {
        "Aux1Function = Aux12Function & 0x3f;": ("aux1_function", 0x003F, 0),
        "Aux1OffAutoOn = (((Aux12Function & 0xc0) >> 6));": ("aux1_mode", 0x00C0, 6),
        "Aux2Function = (Aux12FunctionS & 0x3f00) >> 8;": ("aux2_function", 0x3F00, 8),
        "Aux2OffAutoOn = ((Aux12FunctionS & 0xc000) >> 14);": ("aux2_mode", 0xC000, 14),
    }

    @pytest.mark.parametrize(
        ("sentence", "expected"), sorted(SPEC_DECODES.items())
    )
    def test_each_documented_decode_is_the_field_we_use(self, sentence, expected):
        name, mask, shift = expected
        assert AUX_FIELDS[name] == (mask, shift), sentence

    def test_the_four_fields_partition_the_register(self):
        """Bits 0-5, 6-7, 8-13, 14-15: nothing overlaps, nothing is left out."""
        masks = [AUX_FIELDS[name][0] for name in AUX_FIELDS]
        assert sum(masks) == 0xFFFF
        for mask in masks:
            for other in masks:
                if mask is not other:
                    assert mask & other == 0

    def test_the_running_copy_had_three_bit_fields(self):
        """It read bits 0-2 and 3-5 and an on/off bit 8: none of those fields exist."""
        assert AUX_FIELDS["aux1_function"][0] != 0x07
        assert AUX_FIELDS["aux2_function"][1] != 3
        assert not any(mask == 0x07 for mask, _ in AUX_FIELDS.values())

    def test_tables_4165_1_and_4165_2(self):
        assert AUX_OFF_AUTO_ON == {0: "Off", 1: "Auto", 2: "On", 3: "Unimplemented"}

    def test_read_and_write_field(self):
        value = aux_value(aux1_function=3, aux2_function=2)
        assert read_field(value, *AUX_FIELDS["aux1_function"]) == 3
        assert read_field(value, *AUX_FIELDS["aux2_function"]) == 2
        assert write_field(value, *AUX_FIELDS["aux1_function"], 4) & 0x3F == 4

    def test_write_field_refuses_values_that_do_not_fit(self):
        with pytest.raises(ValueError):
            write_field(0, 0x3F, 0, 64)


class TestAuxFunctionSelects:
    """Tables 4165-3 and 4165-4."""

    def test_aux1_codes_are_the_map_values(self):
        assert set(AUX1_FUNCTIONS) == {1, 2, 3, 4, 7, 8, 13, 14, 15, 16, 17, 18, 19, 20, 21}

    def test_aux1_has_no_value_zero(self):
        """Table 4165-3 starts at 1; 0 is not a function the Classic accepts."""
        assert 0 not in AUX1_FUNCTIONS

    def test_aux2_codes_are_the_map_values(self):
        assert set(AUX2_FUNCTIONS) == {0, 1, 2, 3, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18}

    def test_reserved_function_codes_are_not_offered(self):
        assert "RESERVED" not in AUX1_FUNCTIONS.values()
        assert "RESERVED" not in AUX2_FUNCTIONS.values()

    def test_current_option_reads_the_six_bit_field(self, entry):
        selector_obj, _ = selector(
            Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value(aux1_function=19)}
        )
        assert selector_obj.current_option == "Vent Fan High"

    def test_changing_aux1_leaves_aux2_and_both_modes_alone(self, entry):
        start = aux_value(aux1_function=1, aux1_mode=1, aux2_function=7, aux2_mode=2)
        selector_obj, api = selector(Aux1FunctionSelector, entry, {AUX_REGISTER: start})
        asyncio.run(selector_obj.async_select_option("Waste Not High"))
        written = api.writes[0][1]
        assert written == aux_value(
            aux1_function=3, aux1_mode=1, aux2_function=7, aux2_mode=2
        ), "only bits 0-5 may change"

    def test_changing_aux2_leaves_aux1_and_both_modes_alone(self, entry):
        start = aux_value(aux1_function=17, aux1_mode=2, aux2_function=0, aux2_mode=1)
        selector_obj, api = selector(Aux2FunctionSelector, entry, {AUX_REGISTER: start})
        asyncio.run(selector_obj.async_select_option("Waste Not High"))
        written = api.writes[0][1]
        assert written == aux_value(
            aux1_function=17, aux1_mode=2, aux2_function=2, aux2_mode=1
        ), "only bits 8-13 may change"

    def test_the_write_is_followed_by_the_eeprom_commit(self, entry):
        selector_obj, api = selector(
            Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value()}
        )
        asyncio.run(selector_obj.async_select_option("Toggle Test"))
        assert api.writes == [
            (AUX_REGISTER, aux_value(aux1_function=13)),
            (4160, 0x0004),
        ]
        assert selector_obj.coordinator.refresh_requests == 1

    def test_it_refuses_before_the_register_has_been_read(self, entry):
        """Writing blind would clobber the other Aux output."""
        selector_obj, api = selector(Aux1FunctionSelector, entry, {})
        with pytest.raises(HomeAssistantError):
            asyncio.run(selector_obj.async_select_option("Waste Not High"))
        assert api.writes == []

    def test_an_unknown_option_is_refused(self, entry):
        selector_obj, api = selector(Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value()})
        with pytest.raises(HomeAssistantError):
            asyncio.run(selector_obj.async_select_option("Off"))
        assert api.writes == []

    def test_options_come_from_the_tables(self, entry):
        aux1, _ = selector(Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value()})
        aux2, _ = selector(Aux2FunctionSelector, entry, {AUX_REGISTER: aux_value()})
        assert aux1.options == list(AUX1_FUNCTIONS.values())
        assert aux2.options == list(AUX2_FUNCTIONS.values())

    def test_an_unset_code_is_reported_not_hidden(self, entry):
        """Register left in a state the tables do not describe."""
        selector_obj, _ = selector(Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value(aux1_function=5)})
        assert selector_obj.current_option == "Unset (5)"


class TestMPPTMode:
    """Table 4164-1: "Bit 0 is the ON/OFF ... Subtract One (1) if showing mode as OFF"."""

    SPEC_VALUES = [0x0001, 0x0003, 0x0005, 0x0007, 0x0009, 0x000B, 0x000D, 0x000F]

    def test_the_mode_values_match_the_table(self):
        assert sorted(MPPT_MODES) == self.SPEC_VALUES

    def test_mode_names_match_the_table(self):
        assert [MPPT_MODES[value].replace("_", " ") for value in sorted(MPPT_MODES)] == [
            "PV Uset",
            "DYNAMIC",
            "WIND TRACK",
            "RESERVED",
            "Legacy P&O",
            "SOLAR",
            "HYDRO",
            "RESERVED",
        ]

    def test_reserved_rows_are_not_offered_as_modes(self, entry):
        selector_obj, _ = selector(MPPTModeSelector, entry, {4164: 0x0001}, group="settings")
        assert "RESERVED" not in selector_obj.options
        assert MPPT_OFF in selector_obj.options

    @pytest.mark.parametrize(("value", "expected"), [(0x000B, "SOLAR"), (0x0001, "PV_Uset")])
    def test_enabled_modes_read_back(self, entry, value, expected):
        selector_obj, _ = selector(MPPTModeSelector, entry, {4164: value}, group="settings")
        assert selector_obj.current_option == expected

    @pytest.mark.parametrize(("value", "expected"), [(0x0002, "DYNAMIC (Off)"), (0x000A, "SOLAR (Off)")])
    def test_an_even_value_is_that_mode_with_mppt_off(self, entry, value, expected):
        selector_obj, _ = selector(MPPTModeSelector, entry, {4164: value}, group="settings")
        assert selector_obj.current_option == expected

    def test_zero_is_mppt_off_altogether(self, entry):
        selector_obj, _ = selector(MPPTModeSelector, entry, {4164: 0x0000}, group="settings")
        assert selector_obj.current_option == MPPT_OFF

    def test_mppt_can_be_switched_off(self, entry):
        """The running copy could only ever write the enabled values."""
        selector_obj, api = selector(MPPTModeSelector, entry, {4164: 0x000B}, group="settings")
        asyncio.run(selector_obj.async_select_option(MPPT_OFF))
        assert api.writes == [(4164, 0x0000), (4160, 0x0004)]

    def test_selecting_a_mode_writes_the_enabled_value(self, entry):
        selector_obj, api = selector(MPPTModeSelector, entry, {4164: 0x0001}, group="settings")
        asyncio.run(selector_obj.async_select_option("SOLAR"))
        assert api.writes == [(4164, 0x000B), (4160, 0x0004)]

    def test_a_failed_mode_write_is_reported(self, entry):
        api = FakeApi(fail_writes=True)
        coordinator = FakeCoordinator(Hass(), api, {"settings": {4164: 0x0001}})
        selector_obj = MPPTModeSelector(coordinator, entry)
        with pytest.raises(HomeAssistantError):
            asyncio.run(selector_obj.async_select_option("SOLAR"))
