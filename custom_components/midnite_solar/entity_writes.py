"""Writing a Classic setting, in the one order the register map requires.

Number, select and text entities all write the value and read it back, and all
have to fail loudly rather than leave Home Assistant showing the old value. The
Ethernet write protect is released inside MidniteHub.write_register. The EEPROM
commit (ForceEEpromUpdateWriteF) is NOT automatic: it is sent only when the
"Auto Save EEPROM" switch is on (async_auto_save_if_enabled), or on a "Save to
EEPROM now" press - because the commit writes every pending (EE) register at once.
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


async def async_auto_save_if_enabled(hass: Any, coordinator: Any, label: str) -> bool:
    """Commit to EEPROM only when the 'Auto Save EEPROM' switch is on.

    The Classic's ForceEEpromUpdate commit writes EVERY pending (EE) register at
    once, so committing after every set-point write is a side effect the user did
    not always ask for. The default is off: a set-point write then takes effect
    immediately but is volatile (reverts on restart), and the "Save to EEPROM now"
    button commits on demand. Returns True if a commit was sent.
    """
    if getattr(coordinator, "auto_save_eeprom", False):
        await async_store_settings(hass, coordinator.api, label)
        return True
    _LOGGER.debug(
        "Auto-save EEPROM is off; %s is applied but not committed to EEPROM", label
    )
    return False


def register_value(data: Optional[dict], group: str, address: int) -> Optional[int]:
    """Return one register from the coordinator data, or None if unread."""
    if not data or "data" not in data:
        return None
    values = data["data"].get(group)
    if not values:
        return None
    return values.get(address)


async def async_verify_write(
    hass: Any, api: Any, address: int, value: int, label: str, display,
    compare=None,
) -> None:
    """Read the register back and say so if the Classic kept something else.

    A Classic that is write-protected, or that clamps a value to its own limits,
    accepts the write and carries on reporting the old number. Without this check
    Home Assistant just shows the value the user typed and nothing looks wrong.

    `compare(kept, written)` defaults to plain equality. It exists for registers
    shared by two entities (the wind power tables pack two steps per register):
    only the byte this write owns can be blamed on the Classic, because the
    neighbour byte may legitimately have changed on the device since the read
    that built the packed value.
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
    if (kept == value) if compare is None else compare(kept, value):
        return
    raise HomeAssistantError(
        f"{label}: wrote {display(value)}, but the Classic reports "
        f"{display(kept)}. The write was ignored or clamped; the Classic is "
        "write-protected (see the Ethernet Writes Locked sensor) or the value is "
        "outside what the Classic allows."
    )


async def async_set_clock(hass: Any, api: Any, now) -> None:
    """Write the Classic's clock to `now` (its local wall clock, no timezone).

    The AIR app sets the clock with the private function 105 "file write" of
    a 20-byte payload to internal file 7 address 0 (PROTOCOL.md section 4.2).
    The Classic takes it immediately and needs no EEPROM commit - the app
    sends nothing else.
    """
    from .const import CLOCK_FILE_ADDRESS, CLOCK_FILE_DEVICE
    from .register_values import clock_file_payload

    payload = clock_file_payload(now)
    _LOGGER.debug("Setting the Classic clock to %s", now)
    try:
        result = await hass.async_add_executor_job(
            api.write_internal, CLOCK_FILE_DEVICE, payload, CLOCK_FILE_ADDRESS
        )
    except Exception as e:
        raise HomeAssistantError(f"Could not set the Classic clock: {e}") from e
    if result is None or result.isError():
        raise HomeAssistantError("The Classic did not accept the clock write")


async def async_reboot_classic(hass: Any, api: Any) -> None:
    """Reboot the Classic the way the AIR app's "Bully Menu" does.

    Two ordinary writes, read-first so no other setting bit moves: enable the
    "AutoDlyReset" bit of 4186, then raise ForceNite (bit 8) in 4160
    (ConfigMenuLocal.as:4877-4890). The Classic drops the connection as the
    reboot starts - the app warns the same thing - so the device going
    unavailable afterwards is expected, not an error.
    """
    from .const import ENABLE_FLAGS_2_AUTO_DLY_RESET, FORCE_FLAGS, REGISTER_MAP
    from .register_values import FORCE_FLAG_BITS_LOW_REGISTER

    enable_register = REGISTER_MAP["ENABLE_FLAGS_2"]
    enable_flags = await _read_one(hass, api, enable_register, "auto-restart flags")
    await async_write_setting(
        hass,
        api,
        enable_register,
        enable_flags | ENABLE_FLAGS_2_AUTO_DLY_RESET,
        "Reboot (enable auto-restart)",
    )
    force_flags = await _read_one(hass, api, FORCE_FLAG_BITS_LOW_REGISTER, "force flags")
    await async_write_setting(
        hass,
        api,
        FORCE_FLAG_BITS_LOW_REGISTER,
        force_flags | (1 << FORCE_FLAGS["ForceNite"]),
        "Reboot (ForceNite)",
    )


async def _read_one(hass: Any, api: Any, address: int, label: str) -> int:
    """Read one register or raise; the reboot must not send half a sequence."""
    try:
        result = await hass.async_add_executor_job(api.read_holding_registers, address, 1)
    except Exception as e:
        raise HomeAssistantError(f"Could not read the Classic's {label}: {e}") from e
    if result is None or result.isError() or not result.registers:
        raise HomeAssistantError(f"Could not read the Classic's {label}")
    return result.registers[0]
