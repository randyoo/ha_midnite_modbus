"""Tests for the seven Enable-Flags toggles the AIR app's Features panel has.

From the decompiled app (air-app-reverse, ConfigMenuLocal.handleBtnFeaturesCommit):

  4187 Enable Flags 1: Ground Fault Enable (bit 0), Arc Fault Enable (bit 1)
  4186 Enable Flags 2: Night Auto Reset (2), Follow Master's Battery Sensor (5),
       LoMax (7), Insomnia (12), Keep Logging at Night (14)

The toggles are read-modify-write on registers that pack many bits, so the
load-bearing behaviours are: only this bit moves, only this bit is verified,
and the app's habit of hard-forcing PartialShading(true) on commit is NOT
copied (no entity may write bits the user did not touch).
"""

from __future__ import annotations

import asyncio

from fakes import FakeApi, FakeCoordinator
from midnite_solar.const import ENABLE_FLAG_TOGGLES, REGISTER_GROUPS, REGISTER_MAP
from midnite_solar.switch import EnableFlagSwitch
import pytest

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

R1, R2 = REGISTER_MAP["ENABLE_FLAGS_1"], REGISTER_MAP["ENABLE_FLAGS_2"]


def toggles():
    return {
        key: (R1 if register_key == "ENABLE_FLAGS_1" else R2, bit)
        for key, _label, register_key, bit, _tip in ENABLE_FLAG_TOGGLES
    }


def switch(api, entry, key, group_values):
    values = toggles()[key]
    register = values[0]
    coordinator = FakeCoordinator(
        Hass(), api, {"settings": {register: group_values[register]}}
    )
    coordinator.hass = Hass()
    label = next(t[1] for t in ENABLE_FLAG_TOGGLES if t[0] == key)
    reg_key = "ENABLE_FLAGS_1" if register == R1 else "ENABLE_FLAGS_2"
    bit = values[1]
    tip = next(t[4] for t in ENABLE_FLAG_TOGGLES if t[0] == key)
    entity = EnableFlagSwitch(coordinator, entry, key, label, reg_key, bit, tip)
    entity.hass = coordinator.hass
    return entity


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 250")


class TestToggleTable:
    def test_the_seven_app_toggles_are_all_there(self):
        assert set(toggles()) == {
            "ground_fault",
            "arc_fault",
            "night_auto_reset",
            "networked_batt_temp",
            "low_max_mode",
            "insomnia_mode",
            "log_at_night",
        }

    def test_the_two_registers_are_polled_where_the_switches_read(self):
        polled = set(REGISTER_GROUPS["settings"])
        assert R1 in polled and R2 in polled

    def test_both_enable_registers_are_eeprom_backed(self):
        # The app's Features commit ends with CommitSettingsToEEPROM.
        from midnite_solar.const import EE_BACKED_REGISTERS

        assert R1 in EE_BACKED_REGISTERS and R2 in EE_BACKED_REGISTERS


class TestBitStates:
    def test_the_switch_shows_the_bit_as_the_classic_reports_it(self, entry):
        # 4186 live value from the bench (2026-09-21): night reset, DefCon4,
        # LoMax, VbatRegSlow, diversion-timer and log-at-night are on.
        assert switch(FakeApi(), entry, "night_auto_reset", {R2: 0x48C4}).is_on
        assert not switch(FakeApi(), entry, "insomnia_mode", {R2: 0x48C4}).is_on

    def test_nothing_read_is_off_not_unknown(self, entry):
        entity = switch(FakeApi(), entry, "ground_fault", {R1: None})
        assert entity.is_on is False

    def test_the_entity_is_a_config_setting(self, entry):
        entity = switch(FakeApi(), entry, "arc_fault", {R1: 0})
        assert entity.unique_id == "entry-1_enable_arc_fault"
        assert entity.entity_category == EntityCategory.CONFIG
        assert isinstance(entity, SwitchEntity)


class TestToggling:
    def test_turning_on_sets_only_this_bit(self, entry):
        api = FakeApi(read_values={R2: 0x48C4})
        asyncio.run(switch(api, entry, "insomnia_mode", {R2: 0x48C4}).async_turn_on())
        assert api.writes[0] == (R2, 0x48C4 | (1 << 12))

    def test_turning_off_clears_only_this_bit(self, entry):
        api = FakeApi(read_values={R2: 0x48C4})
        asyncio.run(
            switch(api, entry, "night_auto_reset", {R2: 0x48C4}).async_turn_off()
        )
        assert api.writes[0] == (R2, 0x48C4 & ~(1 << 2))

    def test_ground_fault_is_on_4187_not_4186(self, entry):
        api = FakeApi(read_values={R1: 0x0041})
        asyncio.run(switch(api, entry, "ground_fault", {R1: 0x0041}).async_turn_off())
        assert api.writes[0] == (R1, 0x0040)

    def test_the_bit_is_read_fresh_before_writing(self, entry):
        # The register may have moved since the last poll; the toggle must
        # read the current value first so other bits survive.
        api = FakeApi(read_values={R2: 0x00C4})
        asyncio.run(switch(api, entry, "insomnia_mode", {R2: 0x0004}).async_turn_on())
        assert api.reads[0] == R2
        assert api.writes[0] == (R2, 0x10C4)

    def test_a_refused_bit_change_says_so(self, entry):
        api = FakeApi(read_values={R2: 0x0000}, stale_read=True)
        with pytest.raises(HomeAssistantError) as err:
            asyncio.run(
                switch(api, entry, "insomnia_mode", {R2: 0x0000}).async_turn_on()
            )
        assert "ignored or clamped" in str(err.value)

    def test_a_neighbour_bit_changed_by_another_tool_is_not_blamed(self, entry):
        # Write lands for OUR bit, but a second tool changed a different bit
        # between the read and the read-back; equality would false-alarm.
        api = FakeApi(read_values={R2: 0x0000})

        original = api.write_register

        def racing_write(address, value, retries=2):
            if address == R2:
                # Classic took our bit but gained an unrelated bit in between.
                api.read_values[R2] = value | 0x0001
            return original(address, value, retries)

        api.write_register = racing_write
        asyncio.run(switch(api, entry, "insomnia_mode", {R2: 0x0000}).async_turn_on())
        assert api.writes[0][1] == (1 << 12)  # only our bit was sent

    def test_turning_on_does_not_copy_the_apps_partial_shading_forcing(self, entry):
        # handleBtnFeaturesCommit passes literal true for PartialShading
        # (bit 3) on EVERY commit. That is the app's business, not a
        # requirement; our toggles must not set bits the user did not touch.
        api = FakeApi(read_values={R2: 0x0000})
        asyncio.run(switch(api, entry, "insomnia_mode", {R2: 0x0000}).async_turn_on())
        assert api.writes[0][1] == 1 << 12  # no bit 3 smuggled in


class TestCommit:
    def test_the_toggle_commits_when_auto_save_is_on(self, entry):
        api = FakeApi(read_values={R2: 0x0000})
        coordinator = FakeCoordinator(
            Hass(), api, {"settings": {R2: 0}}, auto_save_eeprom=True
        )
        coordinator.hass = Hass()
        entity = EnableFlagSwitch(
            coordinator,
            entry,
            "insomnia_mode",
            "Insomnia Mode",
            "ENABLE_FLAGS_2",
            12,
            "",
        )
        entity.hass = coordinator.hass
        asyncio.run(entity.async_turn_on())
        assert (R2, 1 << 12) in api.writes
        assert (4160, 0x0004) in api.writes  # ForceEEpromUpdate

    def test_the_toggle_does_not_commit_when_auto_save_is_off(self, entry):
        api = FakeApi(read_values={R2: 0x0000})
        coordinator = FakeCoordinator(
            Hass(), api, {"settings": {R2: 0}}, auto_save_eeprom=False
        )
        coordinator.hass = Hass()
        entity = EnableFlagSwitch(
            coordinator,
            entry,
            "insomnia_mode",
            "Insomnia Mode",
            "ENABLE_FLAGS_2",
            12,
            "",
        )
        entity.hass = coordinator.hass
        asyncio.run(entity.async_turn_off())
        assert api.writes[0] == (R2, 0)
        assert (4160, 0x0004) not in api.writes

    def test_a_toggle_that_cannot_read_the_register_says_so(self, entry):
        api = FakeApi(unreadable=True)
        coordinator = FakeCoordinator(Hass(), api, {"settings": {R2: 0}})
        coordinator.hass = Hass()
        entity = EnableFlagSwitch(
            coordinator,
            entry,
            "insomnia_mode",
            "Insomnia Mode",
            "ENABLE_FLAGS_2",
            12,
            "",
        )
        entity.hass = coordinator.hass
        with pytest.raises(HomeAssistantError):
            asyncio.run(entity.async_turn_on())
        assert api.writes == []
