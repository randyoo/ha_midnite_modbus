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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import MidniteBaseEntityDescription
from .const import DOMAIN
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutoSaveEepromSwitch(coordinator, entry)])


class AutoSaveEepromSwitch(CoordinatorEntity[MidniteSolarUpdateCoordinator], SwitchEntity):
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
        _LOGGER.info("Auto-save EEPROM disabled: setting writes stay unsaved until commit")
        self.coordinator.auto_save_eeprom = False
        self.async_write_ha_state()
