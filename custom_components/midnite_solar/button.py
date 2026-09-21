"""Support for Midnite Solar button platform."""

from __future__ import annotations

import logging
from typing import Any

from .base import MidniteBaseEntityDescription

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FORCE_FLAGS, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator
from .entity_writes import async_write_setting, async_set_clock, async_reboot_classic
from .register_values import force_flag_write

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    buttons = [
        ForceEEpromUpdateButton(coordinator, entry),
        ForceEEpromInitReadButton(coordinator, entry),
        ResetInfoFlagsButton(coordinator, entry),
        ForceSweepButton(coordinator, entry),
        ResetFaultsButton(coordinator, entry),
        SetClockButton(coordinator, entry),
        RebootClassicButton(coordinator, entry),
    ]

    async_add_entities(buttons)


class MidniteSolarButton(CoordinatorEntity[MidniteSolarUpdateCoordinator], ButtonEntity):
    """Base class for all Midnite Solar buttons."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, flag: str):
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._flag = flag

        # Create device info - will be updated dynamically when data becomes available
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

    async def async_press(self) -> None:
        """Raise one Force Flag Bit.

        The flag is value `1 << bit` from Table 4160-1. Flags at or above
        0x10000 live in the high register (4161), so the register to write is
        chosen from the flag value instead of being assumed to be 4160.
        """
        flag_value = 1 << FORCE_FLAGS[self._flag]
        register, word = force_flag_write(flag_value)
        _LOGGER.info("Writing force flag %s: 0x%x to register %d", self._flag, flag_value, register)
        # A button that reports nothing and does nothing is indistinguishable from
        # a Classic that ignored the press, so the failure has to reach the UI.
        await async_write_setting(self.hass, self.coordinator.api, register, word, self.name)
        await self.coordinator.async_request_refresh()


class ForceEEpromUpdateButton(MidniteSolarButton):
    """Button to commit every pending setting to EEPROM now.

    The counterpart to the "Auto Save EEPROM" switch: with auto-save off, a
    set-point change is applied but volatile, and pressing this writes all pending
    (EE) registers to EEPROM in one ForceEEpromUpdate so they survive a restart.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "ForceEEpromUpdate")
        self._attr_name = "Save to EEPROM now"
        # unique_id kept as the original so an upgrade does not orphan the entity.
        self._attr_unique_id = f"{entry.entry_id}_force_eeprom_update"


class ForceEEpromInitReadButton(MidniteSolarButton):
    """Button to discard unsaved settings by re-reading the EEPROM."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "ForceEEpromInitRead")
        self._attr_name = "Discard Unsaved Settings"
        self._attr_unique_id = f"{entry.entry_id}_force_eeprom_init_read"
        # Table 4160-1: "Force read of EEprom (UnDo if a NV register changed
        # and has not been EEprom Updated yet)".
        self._attr_entity_registry_enabled_default = False


class ResetInfoFlagsButton(MidniteSolarButton):
    """Button to zero the read-only Info Flags."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "ForceResetInfoFlags")
        # Kept on the old unique_id so existing entities survive the rename: the
        # flag it writes was 0x100000, a reserved bit, and never did anything.
        self._attr_name = "Reset Info Flags"
        self._attr_unique_id = f"{entry.entry_id}_reset_flags"


class ForceSweepButton(MidniteSolarButton):
    """Button to force an MPPT sweep or re-track."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "ForceSweep")
        self._attr_name = "Force Sweep"
        self._attr_unique_id = f"{entry.entry_id}_force_sweep"
        self._attr_entity_registry_enabled_default = False


class ResetFaultsButton(MidniteSolarButton):
    """Button to reset all faults."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "ForceResetFaults")
        self._attr_name = "Reset Faults"
        self._attr_unique_id = f"{entry.entry_id}_reset_faults"


class SetClockButton(MidniteSolarButton):
    """Button to set the Classic's clock to Home Assistant's current time.

    The Classic has no NTP and its clock is only writable through the AIR
    app's private file command; this writes the same 20-byte payload
    (PROTOCOL.md section 4.2) so the Classic's clock tracks HA's.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "SetClock")
        self._attr_name = "Set Classic Clock"
        self._attr_unique_id = f"{entry.entry_id}_set_clock"

    async def async_press(self) -> None:
        """Set the Classic's wall clock to HA's local time now."""
        await async_set_clock(self.hass, self.coordinator.api, dt_util.now())
        await self.coordinator.async_request_refresh()


class RebootClassicButton(MidniteSolarButton):
    """Button to reboot the Classic, mirroring the AIR app's "Bully Menu".

    It enables the "AutoDlyReset" flag (4186 bit 2) and then raises ForceNite
    (4160 bit 8), the exact two writes ConfigMenuLocal.handleReboot makes. The
    Classic drops the connection as it reboots, so this is disabled by default
    and lives in Diagnostic only.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the button."""
        super().__init__(coordinator, entry, "Reboot")
        self._attr_name = "Reboot Classic"
        self._attr_unique_id = f"{entry.entry_id}_reboot_classic"
        self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        """Reboot the Classic. It will drop and come back on its own."""
        _LOGGER.info("Rebooting the Classic")
        await async_reboot_classic(self.hass, self.coordinator.api)
