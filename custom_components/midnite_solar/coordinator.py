"""Define the Midnite Solar Device Update Coordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import pymodbus

if "3.7.0" <= pymodbus.__version__ <= "3.7.4":
    from pymodbus.pdu.register_read_message import ReadHoldingRegistersResponse
else:
    from pymodbus.pdu.register_message import ReadHoldingRegistersResponse

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, REGISTER_GROUPS, REGISTER_MAP
from .hub import MidniteHub

_LOGGER = logging.getLogger(__name__)

# Hard cap (seconds) for a single blocking Modbus operation. The Modbus client
# already uses bounded socket timeouts; this is a final safety net so that a
# wedged operation can never hang the coordinator (and, with it, Home Assistant).
OP_TIMEOUT = 20.0
# Hard cap (seconds) for the connection reset performed after a wedged op.
RESET_TIMEOUT = 5.0


class MidniteSolarUpdateCoordinator(DataUpdateCoordinator):
    """Gather data for the Midnite Solar device."""

    api: MidniteHub

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        interval: int = 15,
    ) -> None:
        """Initialize Update Coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval)
        )
        self.api = MidniteHub(host, port)
        self.interval = interval
        self.device_info = {}

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch all device and sensor data from api."""
        data = {}
        unavailable_entities = {}

        # Connectivity check. The read below transparently (re)connects if the
        # socket is closed, so we never touch the Modbus client on the event
        # loop here. A blocking call on the event loop would freeze Home
        # Assistant whenever a worker thread is holding the connection lock.
        test_result = await self._safe_read(REGISTER_MAP["UNIT_ID"], 1, retries=1)
        if test_result is None or test_result.isError():
            _LOGGER.warning("Connection test failed on UNIT_ID. Trying alternative register...")
            # Try a different register that might be more stable
            test_result = await self._safe_read(REGISTER_MAP["DISP_AVG_VBATT"], 1, retries=1)

        if test_result is None or test_result.isError():
            _LOGGER.error("Connection tests failed. Device not responding.")
            raise UpdateFailed("Device not responding to connection tests")

        unit_id = test_result.registers[0] if test_result.registers else None
        _LOGGER.debug(f"Connection test successful. UNIT_ID: {unit_id}")

        # Read all register groups. A group that fails only marks its own
        # registers unavailable; it does not fail the whole update. A wedged
        # read (UpdateFailed) fails the update so the coordinator reschedules
        # instead of stalling on every remaining group.
        for group_name, registers in REGISTER_GROUPS.items():
            try:
                result = await self._read_register_group(registers)
                if result is not None:
                    data[group_name] = result
                else:
                    _LOGGER.warning(f"Failed to read register group: {group_name}")
                    # Mark all registers in this group as unavailable
                    for reg in registers:
                        unavailable_entities[str(reg)] = False
            except UpdateFailed:
                # A read wedged, which means the device went down mid-update.
                # Fail fast and let the coordinator retry on the next interval.
                raise
            except Exception as e:
                _LOGGER.error(f"Error reading register group {group_name}: {e}")
                for reg in registers:
                    unavailable_entities[str(reg)] = False

        return {
            "data": data,
            "availability": unavailable_entities,
        }

    async def _safe_read(self, address: int, count: int, retries: int):
        """Read registers in the executor with a hard timeout.

        Returns the Modbus response (which may itself be an error response), or
        None if the read completed without usable data. Raises UpdateFailed if
        the operation wedged (timed out), after resetting the client so a stuck
        socket cannot wedge the next update either.
        """
        try:
            return await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    self.api.read_holding_registers, address, count, retries
                ),
                timeout=OP_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.error(f"Read of address {address} timed out after {OP_TIMEOUT}s; resetting connection")
            await self._safe_reset()
            raise UpdateFailed(f"Timed out communicating with device (address {address})") from None

    async def _safe_reset(self) -> None:
        """Reset the Modbus client in the executor, bounded by a timeout."""
        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(self.api.reset),
                timeout=RESET_TIMEOUT,
            )
        except Exception as e:
            _LOGGER.error(f"Failed to reset Modbus connection: {e}")

    async def _read_register_group(self, registers: List[int]) -> Optional[Dict[int, Any]]:
        """Read a group of registers."""
        if not registers:
            return None

        # Sort and deduplicate registers
        sorted_regs = sorted(set(registers))
        result_data = {}
        failed_registers = []

        for reg in sorted_regs:
            value_result = await self._safe_read(reg, 1, retries=5)
            if value_result is not None and not value_result.isError():
                result_data[reg] = value_result.registers[0]
            else:
                _LOGGER.warning(f"Failed to read register {reg} (group: {REGISTER_MAP.get(reg, 'unknown')})")
                failed_registers.append(reg)

        if failed_registers:
            _LOGGER.debug(f"Failed to read registers: {failed_registers}")

        return result_data if result_data else None

    def get_register_value(self, address: int) -> Optional[int]:
        """Get a specific register value from the last update."""
        if self.data is None or "data" not in self.data:
            return None

        for group_name, registers in REGISTER_GROUPS.items():
            if address in registers and group_name in self.data["data"]:
                return self.data["data"][group_name].get(address)

        return None

    def get_32bit_value(self, low_address: int, high_address: int) -> Optional[int]:
        """Get a 32-bit value from two registers."""
        if self.data is None or "data" not in self.data:
            return None

        for group_name, registers in REGISTER_GROUPS.items():
            if low_address in registers and high_address in registers:
                data = self.data["data"].get(group_name)
                if data is not None:
                    low_value = data.get(low_address)
                    high_value = data.get(high_address)
                    if low_value is not None and high_value is not None:
                        return (high_value << 16) | low_value

        return None