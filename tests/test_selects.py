"""Tests for the selects: Aux fields as the map decodes them, MPPT off.

The register map is the source of every value here. Register 4165 is the
important one: it packs both Aux outputs, and the running copy was decoding it
with a 3-bit function field and a single on/off bit, which are not the fields
the map documents.
"""

from __future__ import annotations

import asyncio

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import (
    AUX1_FUNCTIONS,
    AUX2_FUNCTIONS,
    AUX_FIELDS,
    AUX_OFF_AUTO_ON,
    MPPT_MODES,
)
from midnite_solar.register_values import read_field, write_field
from midnite_solar.select import (
    MPPT_OFF,
    Aux1FunctionSelector,
    Aux1StateSelect,
    Aux2FunctionSelector,
    Aux2StateSelect,
    ChargeModeSelector,
    MPPTModeSelector,
)
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError

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

    @pytest.mark.parametrize(("sentence", "expected"), sorted(SPEC_DECODES.items()))
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
        assert set(AUX1_FUNCTIONS) == {
            1,
            2,
            3,
            4,
            7,
            8,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
        }

    def test_aux1_has_no_value_zero(self):
        """Table 4165-3 starts at 1; 0 is not a function the Classic accepts."""
        assert 0 not in AUX1_FUNCTIONS

    def test_aux2_codes_are_the_map_values(self):
        assert set(AUX2_FUNCTIONS) == {
            0,
            1,
            2,
            3,
            6,
            7,
            8,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
        }

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
        selector_obj, api = selector(
            Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value()}
        )
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
        selector_obj, _ = selector(
            Aux1FunctionSelector, entry, {AUX_REGISTER: aux_value(aux1_function=5)}
        )
        assert selector_obj.current_option == "Unset (5)"


class TestMPPTMode:
    """Table 4164-1: "Bit 0 is the ON/OFF ... Subtract One (1) if showing mode as OFF"."""

    SPEC_VALUES = [0x0001, 0x0003, 0x0005, 0x0007, 0x0009, 0x000B, 0x000D, 0x000F]

    def test_the_mode_values_match_the_table(self):
        assert sorted(MPPT_MODES) == self.SPEC_VALUES

    def test_mode_names_match_the_table(self):
        """Verbatim, including "PV_Uset" with its underscore and "WIND TRACK" with its space."""
        assert [MPPT_MODES[value] for value in sorted(MPPT_MODES)] == [
            "PV_Uset",
            "DYNAMIC",
            "WIND TRACK",
            "RESERVED",
            "Legacy P&O",
            "SOLAR",
            "HYDRO",
            "RESERVED",
        ]

    def test_reserved_rows_are_not_offered_as_modes(self, entry):
        selector_obj, _ = selector(
            MPPTModeSelector, entry, {4164: 0x0001}, group="settings"
        )
        assert "RESERVED" not in selector_obj.options
        assert MPPT_OFF in selector_obj.options

    @pytest.mark.parametrize(
        ("value", "expected"), [(0x000B, "SOLAR"), (0x0001, "PV_Uset")]
    )
    def test_enabled_modes_read_back(self, entry, value, expected):
        selector_obj, _ = selector(
            MPPTModeSelector, entry, {4164: value}, group="settings"
        )
        assert selector_obj.current_option == expected

    @pytest.mark.parametrize(
        ("value", "expected"), [(0x0002, "DYNAMIC (Off)"), (0x000A, "SOLAR (Off)")]
    )
    def test_an_even_value_is_that_mode_with_mppt_off(self, entry, value, expected):
        selector_obj, _ = selector(
            MPPTModeSelector, entry, {4164: value}, group="settings"
        )
        assert selector_obj.current_option == expected

    def test_zero_is_mppt_off_altogether(self, entry):
        selector_obj, _ = selector(
            MPPTModeSelector, entry, {4164: 0x0000}, group="settings"
        )
        assert selector_obj.current_option == MPPT_OFF

    def test_mppt_can_be_switched_off(self, entry):
        """The running copy could only ever write the enabled values."""
        selector_obj, api = selector(
            MPPTModeSelector, entry, {4164: 0x000B}, group="settings"
        )
        asyncio.run(selector_obj.async_select_option(MPPT_OFF))
        assert api.writes == [(4164, 0x0000), (4160, 0x0004)]

    def test_selecting_a_mode_writes_the_enabled_value(self, entry):
        selector_obj, api = selector(
            MPPTModeSelector, entry, {4164: 0x0001}, group="settings"
        )
        asyncio.run(selector_obj.async_select_option("SOLAR"))
        assert api.writes == [(4164, 0x000B), (4160, 0x0004)]

    def test_a_failed_mode_write_is_reported(self, entry):
        api = FakeApi(fail_writes=True)
        coordinator = FakeCoordinator(Hass(), api, {"settings": {4164: 0x0001}})
        selector_obj = MPPTModeSelector(coordinator, entry)
        with pytest.raises(HomeAssistantError):
            asyncio.run(selector_obj.async_select_option("SOLAR"))


class TestAuxStateSelects:
    """Tables 4165-1 and 4165-2: the Off / Auto / On bits of each output."""

    def test_the_options_are_the_three_states_a_user_can_ask_for(self, entry):
        selector_obj, _ = selector(Aux1StateSelect, entry, {AUX_REGISTER: aux_value()})
        assert selector_obj.options == ["Off", "Auto", "On"]

    def test_unimplemented_is_reported_but_never_offered(self, entry):
        selector_obj, _ = selector(
            Aux1StateSelect, entry, {AUX_REGISTER: aux_value(aux1_mode=3)}
        )
        assert selector_obj.current_option == "Unimplemented"
        assert "Unimplemented" not in selector_obj.options
        with pytest.raises(HomeAssistantError):
            asyncio.run(selector_obj.async_select_option("Unimplemented"))

    def test_aux1_state_reads_bits_6_and_7(self, entry):
        for mode, name in ((0, "Off"), (1, "Auto"), (2, "On")):
            selector_obj, _ = selector(
                Aux1StateSelect, entry, {AUX_REGISTER: aux_value(aux1_mode=mode)}
            )
            assert selector_obj.current_option == name

    def test_aux2_state_reads_bits_14_and_15(self, entry):
        for mode, name in ((0, "Off"), (1, "Auto"), (2, "On")):
            selector_obj, _ = selector(
                Aux2StateSelect, entry, {AUX_REGISTER: aux_value(aux2_mode=mode)}
            )
            assert selector_obj.current_option == name

    def test_the_two_states_are_read_independently(self, entry):
        start = aux_value(aux1_function=19, aux1_mode=0, aux2_function=7, aux2_mode=2)
        aux1, _ = selector(Aux1StateSelect, entry, {AUX_REGISTER: start})
        aux2, _ = selector(Aux2StateSelect, entry, {AUX_REGISTER: start})
        assert aux1.current_option == "Off"
        assert aux2.current_option == "On"

    def test_aux2_state_offers_only_the_three_user_states(self, entry):
        """Aux 2 used to offer "Unimplemented", which its select_option always rejected."""
        aux2, _ = selector(Aux2StateSelect, entry, {AUX_REGISTER: aux_value()})
        assert aux2.options == ["Off", "Auto", "On"]
        assert "Unimplemented" not in aux2.options

    @pytest.mark.parametrize("cls", [Aux1StateSelect, Aux2StateSelect])
    def test_every_offered_state_option_is_selectable(self, entry, cls):
        """The gap the sweep missed: it checked the state shown, never that each
        option in the dropdown can actually be chosen without raising.
        """
        selector_obj, _ = selector(cls, entry, {AUX_REGISTER: aux_value()})
        for option in selector_obj.options:
            asyncio.run(selector_obj.async_select_option(option))

    @pytest.mark.parametrize("cls", [Aux1StateSelect, Aux2StateSelect])
    def test_an_unimplemented_state_reports_unknown_to_home_assistant(self, entry, cls):
        """Real HA's SelectEntity.state is None for a current_option outside options.

        "Unimplemented" is deliberately display-only, so on a real dashboard the
        entity shows `unknown`, not the string - the suite must record that the
        string lives in current_option, not in the rendered state.
        """
        mode_field = "aux1_mode" if cls is Aux1StateSelect else "aux2_mode"
        selector_obj, _ = selector(
            cls, entry, {AUX_REGISTER: aux_value(**{mode_field: 3})}
        )
        assert selector_obj.current_option == "Unimplemented"
        assert selector_obj.state is None

    def test_forcing_aux1_on_leaves_the_functions_and_aux2_alone(self, entry):
        start = aux_value(aux1_function=1, aux1_mode=1, aux2_function=7, aux2_mode=1)
        selector_obj, api = selector(Aux1StateSelect, entry, {AUX_REGISTER: start})
        asyncio.run(selector_obj.async_select_option("On"))
        assert api.writes[0][1] == aux_value(
            aux1_function=1, aux1_mode=2, aux2_function=7, aux2_mode=1
        ), "only bits 6-7 may change"

    def test_forcing_aux2_off_leaves_aux1_alone(self, entry):
        start = aux_value(aux1_function=17, aux1_mode=2, aux2_function=3, aux2_mode=1)
        selector_obj, api = selector(Aux2StateSelect, entry, {AUX_REGISTER: start})
        asyncio.run(selector_obj.async_select_option("Off"))
        assert api.writes[0][1] == aux_value(
            aux1_function=17, aux1_mode=2, aux2_function=3, aux2_mode=0
        ), "only bits 14-15 may change"

    def test_a_state_write_is_committed_and_read_back(self, entry):
        selector_obj, api = selector(
            Aux2StateSelect, entry, {AUX_REGISTER: aux_value()}
        )
        asyncio.run(selector_obj.async_select_option("Auto"))
        assert [address for address, _ in api.writes] == [AUX_REGISTER, 4160]
        assert api.writes[1] == (4160, 0x0004)
        assert api.reads == [AUX_REGISTER]

    def test_a_state_write_refuses_to_guess_the_other_field(self, entry):
        selector_obj, api = selector(Aux1StateSelect, entry, {})
        with pytest.raises(HomeAssistantError):
            asyncio.run(selector_obj.async_select_option("On"))
        assert api.writes == []

    def test_each_output_has_its_own_entity(self, entry):
        aux1, _ = selector(Aux1StateSelect, entry, {AUX_REGISTER: aux_value()})
        aux2, _ = selector(Aux2StateSelect, entry, {AUX_REGISTER: aux_value()})
        assert aux1.unique_id == "entry-1_aux1_state_select"
        assert aux2.unique_id == "entry-1_aux2_state_select"
        assert aux1.name == "AUX 1 State"
        assert aux2.name == "AUX 2 State"


class TestOptionsAreRealOptions:
    """A selector must not show a value it will not let you choose.

    This sweep checks current_option, which is where the integration puts what the
    Classic reports. It is not the same thing as the rendered `state`: Home
    Assistant's final SelectEntity.state is None for any current_option outside the
    option list, so the display-only forms below show as `unknown` on a real
    dashboard rather than as that text. That is accepted - the point of this sweep
    is that no *selectable* value is ever displayed as if it were an option. Three
    display-only forms are allowed:

    - "Unknown (0x…)" and "Unset (n)": a code the table has no name for.
    - "Unimplemented": Table 4165-1 gives value 3 that name, and no user can ask
      for it.
    - "SOLAR (Off)": Table 4164-1 says to "Subtract One (1) if showing mode as
      OFF", so an even register value is a mode with MPPT disabled - something the
      Classic can be in and this select cannot write.
    """

    DISPLAY_ONLY = ("Unknown (", "Unset (", "Unimplemented")
    DISPLAY_SUFFIX = (" (Off)",)

    def sweep(self, cls, register, group, values):
        bad = []
        for raw in values:
            selector_obj, _ = selector(cls, self.entry, {register: raw}, group=group)
            current = selector_obj.current_option
            if current is None:
                continue
            if (
                current not in selector_obj.options
                and not current.startswith(self.DISPLAY_ONLY)
                and not current.endswith(self.DISPLAY_SUFFIX)
            ):
                bad.append(
                    f"{cls.__name__} register {register} value {raw:#06x}: {current!r} not in {selector_obj.options}"
                )
        return bad

    @pytest.fixture
    def entry(self, request):
        self.entry = ConfigEntry(entry_id="entry-1", title="Classic 200")
        return self.entry

    def test_every_mppt_register_value_shows_a_real_option(self, entry):
        self.entry = entry
        assert self.sweep(MPPTModeSelector, 4164, "settings", range(32)) == []

    def test_every_aux1_function_code_shows_a_real_option(self, entry):
        self.entry = entry
        assert (
            self.sweep(Aux1FunctionSelector, AUX_REGISTER, "aux_settings", range(64))
            == []
        )

    def test_every_aux2_function_code_shows_a_real_option(self, entry):
        self.entry = entry
        assert (
            self.sweep(Aux2FunctionSelector, AUX_REGISTER, "aux_settings", range(64))
            == []
        )

    def test_every_aux_state_code_shows_a_real_option(self, entry):
        self.entry = entry
        # The state field is bits 6-7 of 4165; sweep the whole register.
        assert (
            self.sweep(Aux1StateSelect, AUX_REGISTER, "aux_settings", range(256)) == []
        )
        assert (
            self.sweep(
                Aux2StateSelect, AUX_REGISTER, "aux_settings", range(0, 65536, 997)
            )
            == []
        )


class TestChargeModeStageCodes:
    """The force-mode selector reads the stage-code SETS of FINDINGS 50.

    The old code compared 4120's MSB against 5, 4 and 7 alone, so a forced
    Equalize in its seek phase (EQ MPPT 18) - what the bench actually sat
    in - showed as no current option while the Classic was visibly
    equalizing. Each mode answers with its regulating code AND its MPPT
    seek code; the selector must light on all of them.
    """

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            (4, "Bulk"),
            (5, "Float"),
            (6, "Float"),  # FloatMppt: the seek phase the bench observed
            (7, "Equalize"),
            (18, "Equalize"),  # EQ MPPT: the bench's forced-Equalize answer
        ],
    )
    def test_every_proving_stage_code_lights_its_mode(self, entry, code, expected):
        selector_obj, _ = selector(
            ChargeModeSelector, entry, {4120: code << 8}, group="status"
        )
        assert selector_obj.current_option == expected

    @pytest.mark.parametrize("code", [0, 3, 10, 8, 255])
    def test_stages_that_answer_no_force_read_as_none(self, entry, code):
        selector_obj, _ = selector(
            ChargeModeSelector, entry, {4120: code << 8}, group="status"
        )
        assert selector_obj.current_option == "None"

    def test_the_low_byte_never_leaks_into_the_stage(self, entry):
        selector_obj, _ = selector(
            ChargeModeSelector, entry, {4120: (18 << 8) | 0xFF}, group="status"
        )
        assert selector_obj.current_option == "Equalize"

    def test_no_data_honestly_says_none(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {})
        assert ChargeModeSelector(coordinator, entry).current_option == "None"
