"""Support for Midnite Solar text input platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import MidniteBaseEntityDescription

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator
from .entity_writes import (
    async_store_settings,
    async_verify_write,
    async_write_setting,
)
from .register_values import byte_of

_LOGGER = logging.getLogger(__name__)

# The register map's example for the unit name:
#   "CLASSIC" = 0x4C43, 0x5341, 0x4953, 0x0043
# The low byte of the first register is the first character, so a name is written
# two characters at a time with the earlier character in the low byte.
NAME_REGISTERS = tuple(REGISTER_MAP[f"UNIT_NAME_{index}"] for index in range(4))
MAX_NAME_LENGTH = 8


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar text inputs."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    texts = [
        HostNameText(coordinator, entry),
    ]

    async_add_entities(texts)


def name_from_registers(registers: list[int]) -> str:
    """Read the 8-character unit name out of four registers.

    Map: "4210 4211 4212 4213 | R/W | ID name (EE) … End with 0 if less than 8
    chars". A shorter name is terminated by a zero byte, so everything from the
    first zero onwards is padding.
    """
    chars = []
    for register in registers:
        for index in (0, 1):
            byte = byte_of(register, index)
            if byte == 0:
                return "".join(chars).rstrip()
            chars.append(chr(byte))
    return "".join(chars).rstrip()


def registers_for_name(value: str) -> list[int]:
    """Pack a name into the four registers, zero padded as the map says."""
    if len(value) > MAX_NAME_LENGTH:
        raise HomeAssistantError(
            f"A Classic unit name is {MAX_NAME_LENGTH} characters; {value!r} is {len(value)}"
        )
    # The map terminates a short name with a zero byte rather than spaces:
    # "End with 0 if less than 8 chars", and "CLASSIC" is 0x4C43, 0x5341,
    # 0x4953, 0x0043 - the fourth register ends in a zero, not a space.
    padded = value.ljust(MAX_NAME_LENGTH, chr(0))
    registers = []
    for index in range(4):
        low = ord(padded[index * 2])
        high = ord(padded[index * 2 + 1])
        registers.append(low | (high << 8))
    return registers


class MidniteSolarText(CoordinatorEntity[MidniteSolarUpdateCoordinator], TextEntity):
    """Base class for all Midnite Solar text inputs."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the text input."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return the device info, which the base builds for every platform."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    @property
    def _group(self) -> dict:
        """Return the register group this platform reads."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return {}
        return self.coordinator.data["data"].get("device_info") or {}


class HostNameText(MidniteSolarText):
    """Text input for the unit name, registers 4210-4213.

    The map calls it "ID name (EE)" and says it "Takes place of MODBUS Register in
    MNGP display if present", so it is the label a Midnite NPE shows.
    """

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the text input."""
        super().__init__(coordinator, entry)
        self._attr_name = "Host Name"
        self._attr_unique_id = f"{entry.entry_id}_host_name"
        self._attr_max_length = MAX_NAME_LENGTH
        self._attr_pattern = r"^[A-Za-z0-9_\-\. ]*$"

    @property
    def native_value(self) -> Optional[str]:
        """Return the unit name the Classic reports."""
        group = self._group
        registers = [group.get(address) for address in NAME_REGISTERS]
        if any(value is None for value in registers):
            return None
        return name_from_registers(registers)

    async def async_set_value(self, value: str) -> None:
        """Write the name, store it, and read it back."""
        registers = registers_for_name(value)
        for address, register_value in zip(NAME_REGISTERS, registers):
            await async_write_setting(
                self.hass, self.coordinator.api, address, register_value, self.name
            )
        # "(EE)": the name has to be committed to EEPROM or it is gone on restart.
        await async_store_settings(self.hass, self.coordinator.api, self.name)
        for address, register_value in zip(NAME_REGISTERS, registers):
            await async_verify_write(
                self.hass,
                self.coordinator.api,
                address,
                register_value,
                self.name,
                lambda raw: f"0x{raw:04X}",
            )
        await self.coordinator.async_request_refresh()
