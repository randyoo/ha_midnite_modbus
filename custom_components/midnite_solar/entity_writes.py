"""Writing a Classic setting, in the one order the register map requires.

Number, select and text entities all have to do the same two writes: the value,
then ForceEEpromUpdateWriteF so it survives a restart, and all three have to
fail loudly rather than leave Home Assistant showing the old value. The
Ethernet write protect is released inside MidniteHub.write_register.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.exceptions import HomeAssistantError

from .const import FORCE_FLAGS, NO_READBACK_REGISTERS
from .register_values import force_flag_write

_LOGGER = logging.getLogger(__name__)

async def async_write_setting(
    hass: Any, api: Any, address: int, value: int, label: str
) -> None:
    """Write one register, raising HomeAssistantError if it does not land."""
    try:
        result = await hass.async_add_executor_job(api.write_register, address, value)
    except Exception as e:
        raise HomeAssistantError(f"Could not write {label}: {e}") from e
    if result is None or result.isError():
        raise HomeAssistantError(
            f"The Classic rejected the write of {value} to {label} (register {address})"
        )


async def async_store_settings(hass: Any, api: Any, label: str) -> None:
    """Send ForceEEpromUpdateWriteF so the setting survives a restart.

    Table 4160-1: "Write all current settings to internal EEPROM". The map notes
    that the commit stores every pending (EE) register at once.
    """
    flag_value = 1 << FORCE_FLAGS["ForceEEpromUpdate"]
    register, word = force_flag_write(flag_value)
    _LOGGER.debug("Storing %s in EEPROM: 0x%x to register %d", label, word, register)
    try:
        result = await hass.async_add_executor_job(api.write_register, register, word)
    except Exception as e:
        raise HomeAssistantError(f"{label} is active but was not saved to EEPROM: {e}") from e
    if result is None or result.isError():
        raise HomeAssistantError(
            f"{label} is active but the Classic did not accept the EEPROM commit"
        )


def register_value(data: Optional[dict], group: str, address: int) -> Optional[int]:
    """Return one register from the coordinator data, or None if unread."""
    if not data or "data" not in data:
        return None
    values = data["data"].get(group)
    if not values:
        return None
    return values.get(address)


async def async_verify_write(
    hass: Any, api: Any, address: int, value: int, label: str, display
) -> None:
    """Read the register back and say so if the Classic kept something else.

    A Classic that is write-protected, or that clamps a value to its own limits,
    accepts the write and carries on reporting the old number. Without this check
    Home Assistant just shows the value the user typed and nothing looks wrong.
    """
    if address in NO_READBACK_REGISTERS:
        return
    try:
        result = await hass.async_add_executor_job(api.read_holding_registers, address, 1)
    except Exception as e:
        raise HomeAssistantError(f"Wrote {label}, but it could not be read back: {e}") from e
    if result is None or result.isError() or not result.registers:
        raise HomeAssistantError(
            f"Wrote {label}, but the Classic did not answer the read-back of register {address}"
        )
    kept = result.registers[0]
    if kept == value:
        return
    raise HomeAssistantError(
        f"{label}: wrote {display(value)}, but the Classic reports "
        f"{display(kept)}. The write was ignored or clamped; the Classic is "
        "write-protected (see the Ethernet Writes Locked sensor) or the value is "
        "outside what the Classic allows."
    )
