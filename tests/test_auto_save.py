"""The "Auto Save EEPROM" switch and "Save to EEPROM now" button.

The Classic has ONE ForceEEpromUpdate force flag that commits EVERY pending (EE)
register at once, so the integration must not fire it after every set-point write.
The commit is opt-in: off by default (writes are volatile, revert on restart), on
when the switch is enabled, or once per press of the button.
"""

from __future__ import annotations

import asyncio

from fakes import FakeApi, FakeCoordinator
from midnite_solar.button import ForceEEpromUpdateButton
from midnite_solar.const import REGISTER_MAP
from midnite_solar.coordinator import MidniteSolarUpdateCoordinator
from midnite_solar.number import AbsorbVoltageNumber
from midnite_solar.select import Aux1StateSelect, NominalBatteryVoltageSelect
from midnite_solar.switch import AutoSaveEepromSwitch
from midnite_solar.text import NAME_REGISTERS, HostNameText
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

COMMIT = (REGISTER_MAP["FORCE_FLAG_BITS"], 0x0004)  # ForceEEpromUpdateWriteF
ABSORB = REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"]


@pytest.fixture
def entry():
    return ConfigEntry(entry_id="entry-1", title="Classic 200")


def number_write(auto_save, entry, value=57.6):
    api = FakeApi()
    coordinator = FakeCoordinator(
        Hass(),
        api,
        {"setpoints": {ABSORB: int(value * 10)}},
        auto_save_eeprom=auto_save,
    )
    entity = AbsorbVoltageNumber(coordinator, entry)
    asyncio.run(entity.async_set_native_value(value))
    return api


class TestProductionDefaultIsOff:
    def test_a_real_coordinator_defaults_auto_save_off(self):
        # The double defaults on for convenience; the class Home Assistant builds
        # must default off, or every set-point write would silently commit.
        coordinator = MidniteSolarUpdateCoordinator(
            Hass(), "192.168.88.53", 502, interval=15
        )
        assert coordinator.auto_save_eeprom is False


class TestCommitIsGated:
    def test_number_write_does_not_commit_when_auto_save_is_off(self, entry):
        api = number_write(False, entry)
        assert api.writes[0] == (ABSORB, 576)
        assert COMMIT not in api.writes, "nothing should be written to EEPROM"

    def test_number_write_commits_when_auto_save_is_on(self, entry):
        api = number_write(True, entry)
        assert api.writes == [(ABSORB, 576), COMMIT]

    def test_select_write_does_not_commit_when_auto_save_is_off(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(
            Hass(),
            api,
            {"classic_status": {REGISTER_MAP["VBATT_NOMINAL"]: 48}},
            auto_save_eeprom=False,
        )
        asyncio.run(
            NominalBatteryVoltageSelect(coordinator, entry).async_select_option("24 V")
        )
        assert api.writes[0] == (REGISTER_MAP["VBATT_NOMINAL"], 24)
        assert COMMIT not in api.writes

    def test_aux_select_write_does_not_commit_when_auto_save_is_off(self, entry):
        api = FakeApi()
        start = (
            (1 & 0x3F) | (0 << 6) | (0 << 8) | (2 << 14)
        )  # aux1 func 1, aux1 off, aux2 on
        coordinator = FakeCoordinator(
            Hass(), api, {"aux_settings": {4165: start}}, auto_save_eeprom=False
        )
        asyncio.run(Aux1StateSelect(coordinator, entry).async_select_option("On"))
        assert api.writes and api.writes[0][0] == 4165
        assert COMMIT not in api.writes

    def test_name_write_does_not_commit_when_auto_save_is_off(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(
            Hass(),
            api,
            {"device_info": dict(zip(NAME_REGISTERS, [0] * 4, strict=True))},
            auto_save_eeprom=False,
        )
        asyncio.run(HostNameText(coordinator, entry).async_set_value("CLASSIC"))
        assert [a for a, _ in api.writes][:4] == list(NAME_REGISTERS)
        assert COMMIT not in api.writes


class TestSwitch:
    def _switch(self, auto_save, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {}, auto_save_eeprom=auto_save)
        return AutoSaveEepromSwitch(coordinator, entry), coordinator

    def test_the_switch_reflects_the_coordinator_flag(self, entry):
        on, _ = self._switch(True, entry)
        off, _ = self._switch(False, entry)
        assert on.is_on is True
        assert off.is_on is False

    def test_turning_the_switch_on_enables_commits(self, entry):
        switch, coordinator = self._switch(False, entry)
        asyncio.run(switch.async_turn_on())
        assert coordinator.auto_save_eeprom is True
        assert switch.is_on is True

    def test_turning_the_switch_off_disables_commits(self, entry):
        switch, coordinator = self._switch(True, entry)
        asyncio.run(switch.async_turn_off())
        assert coordinator.auto_save_eeprom is False
        assert switch.is_on is False

    def test_enabling_the_switch_makes_the_next_write_commit(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(
            Hass(), api, {"setpoints": {ABSORB: 576}}, auto_save_eeprom=False
        )
        asyncio.run(AutoSaveEepromSwitch(coordinator, entry).async_turn_on())
        asyncio.run(
            AbsorbVoltageNumber(coordinator, entry).async_set_native_value(57.6)
        )
        assert COMMIT in api.writes


class TestSaveToEepromNowButton:
    def test_the_button_always_commits_regardless_of_auto_save(self, entry):
        api = FakeApi()
        coordinator = FakeCoordinator(Hass(), api, {}, auto_save_eeprom=False)
        asyncio.run(ForceEEpromUpdateButton(coordinator, entry).async_press())
        assert COMMIT in api.writes, (
            "an explicit press must commit even with auto-save off"
        )

    def test_the_button_name_is_save_to_eeprom_now_and_keeps_its_unique_id(self, entry):
        coordinator = FakeCoordinator(Hass(), FakeApi(), {})
        button = ForceEEpromUpdateButton(coordinator, entry)
        assert button.name == "Save to EEPROM now"
        assert button.unique_id == f"{entry.entry_id}_force_eeprom_update"
