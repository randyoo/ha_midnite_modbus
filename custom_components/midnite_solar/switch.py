"""Support for the Midnite Solar switch platform.

One switch today: "Auto Save EEPROM". The Classic has a single ForceEEpromUpdate
force flag that writes EVERY pending (EE) register to EEPROM at once, so
committing after every set-point write is a side effect the user does not always
want (it wears the EEPROM and can persist a value that was only meant to be
temporary). This switch turns that auto-commit on or off; the default is off, so a
set-point write is volatile until it is committed with the "Save to EEPROM now"
button or this switch is enabled.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import MidniteBaseEntityDescription
from .const import DOMAIN, EE_BACKED_REGISTERS, ENABLE_FLAG_TOGGLES, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator
from .entity_writes import (
    async_auto_save_if_enabled,
    async_verify_write,
    async_write_setting,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list = [AutoSaveEepromSwitch(coordinator, entry)]
    entities += [
        EnableFlagSwitch(coordinator, entry, key, label, register_key, bit, tooltip)
        for key, label, register_key, bit, tooltip in ENABLE_FLAG_TOGGLES
    ]
    async_add_entities(entities)


class AutoSaveEepromSwitch(
    CoordinatorEntity[MidniteSolarUpdateCoordinator], SwitchEntity
):
    """Enable or disable the automatic EEPROM commit after a setting write."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Auto Save EEPROM"
        self._attr_unique_id = f"{entry.entry_id}_auto_save_eeprom"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:content-save-cog"

        # Static device info until the coordinator reports the real model.
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    @property
    def is_on(self) -> bool:
        """Whether setting writes are being committed to EEPROM automatically."""
        return bool(getattr(self.coordinator, "auto_save_eeprom", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start committing every setting write to EEPROM."""
        _LOGGER.info("Auto-save EEPROM enabled: setting writes will be committed")
        self.coordinator.auto_save_eeprom = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop committing setting writes; they become volatile again."""
        _LOGGER.info(
            "Auto-save EEPROM disabled: setting writes stay unsaved until commit"
        )
        self.coordinator.auto_save_eeprom = False
        self.async_write_ha_state()


class EnableFlagSwitch(CoordinatorEntity[MidniteSolarUpdateCoordinator], SwitchEntity):
    """One enable bit of Enable Flags 1/2 (4187/4186), as the AIR app exposes.

    These registers pack many bits, so toggling must read the current register
    immediately before writing it, and the read-back may legitimately show
    OTHER bits changed by another tool - only this bit is verified. The app
    writes both registers plus 4183/4182 in one Features commit and ends with
    an EEPROM commit; here one switch toggles one bit and the Auto Save EEPROM
    switch decides whether to commit.
    """

    def __init__(self, coordinator, entry, key, label, register_key, bit, tooltip):
        """Initialize the switch for one enable bit."""
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._bit = bit
        self._mask = 1 << bit
        self._tooltip = tooltip  # what the app's checkbox said; kept for docs
        self.register_address = REGISTER_MAP[register_key]
        self._attr_name = label
        self._attr_unique_id = f"{entry.entry_id}_enable_{key}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:electric-switch"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    @property
    def is_on(self) -> bool:
        """Whether the Classic reports this enable bit set."""
        raw = self.coordinator.get_register_value(self.register_address)
        if raw is None:
            return False
        return bool(raw & self._mask)

    async def _async_set_bit(self, on: bool) -> None:
        """Read-modify-write just this bit; verify only this bit came back."""
        try:
            result = await self.hass.async_add_executor_job(
                self.coordinator.api.read_holding_registers, self.register_address, 1
            )
        except Exception as e:
            raise HomeAssistantError(
                f"Could not read register {self.register_address} to change it: {e}"
            ) from e
        if result is None or result.isError() or not result.registers:
            raise HomeAssistantError(
                f"The Classic did not answer the read of register {self.register_address}"
            )
        current = result.registers[0]
        value = (current | self._mask) if on else (current & ~self._mask)
        label = f"{self.name} {'on' if on else 'off'}"
        await async_write_setting(
            self.hass, self.coordinator.api, self.register_address, value, label
        )
        if self.register_address in EE_BACKED_REGISTERS:
            await async_auto_save_if_enabled(self.hass, self.coordinator, label)
        await async_verify_write(
            self.hass,
            self.coordinator.api,
            self.register_address,
            value,
            label,
            display=lambda v: f"0x{v:04X}",
            compare=lambda kept, want: (kept & self._mask) == (want & self._mask),
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the enable bit."""
        _LOGGER.info(
            "Enabling %s (register %d bit %d)",
            self.name,
            self.register_address,
            self._bit,
        )
        await self._async_set_bit(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the enable bit."""
        _LOGGER.info(
            "Disabling %s (register %d bit %d)",
            self.name,
            self.register_address,
            self._bit,
        )
        await self._async_set_bit(False)
