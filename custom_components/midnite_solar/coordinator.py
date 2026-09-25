"""Define the Midnite Solar Device Update Coordinator."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import time
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_BRIDGE_ENABLED,
    DEFAULT_SENSOR_INTERVAL,
    DEFAULT_WRITE_PIN,
    DOMAIN,
    REGISTER_BY_ADDRESS,
    REGISTER_GROUPS,
    REGISTER_MAP,
)
from .hub import MidniteHub
from .register_values import serial_from_registers

if TYPE_CHECKING:
    # Declared for the attribute annotations in __init__ only. The bridge
    # owns these types and imports this module's siblings, never this
    # module, so a runtime import here would risk a cycle for nothing.
    from .bridge import PinGate
    from .datalogger import Datalogger

_LOGGER = logging.getLogger(__name__)

# One register per request means 115 requests per interval (the register groups
# total 115 addresses) on a Classic that has a single Modbus connection and is
# known to get out of sorts when it is pushed.
# The SNMP card answers up to 125 registers in one request, so neighbouring
# registers are read as blocks and these caps stay far inside that.
MAX_BLOCK_SPAN = 32
MAX_BLOCK_GAP = 6


def register_blocks(registers) -> list:
    """Contiguous (first, last) inclusive blocks covering these registers.

    A gap longer than MAX_BLOCK_GAP starts a new block, so a register the card
    will not answer cannot sit between two settings we want and black out the
    block around it. A block never grows past MAX_BLOCK_SPAN registers.

    A block may straddle registers the map marks write-only or RESERVED (the
    eeprom block spans the Force Flag Bits 4160/4161, for instance): a bench read
    of this hardware confirmed a holding-register read across those addresses
    comes back whole. The only registers that reject a read are the unlock
    registers 20492/20493, and no polled group ever covers them.
    """
    ordered = sorted(set(registers))
    if not ordered:
        return []
    blocks = []
    start = previous = ordered[0]
    for register in ordered[1:]:
        if register - previous > MAX_BLOCK_GAP or register - start + 1 > MAX_BLOCK_SPAN:
            blocks.append((start, previous))
            start = register
        previous = register
    blocks.append((start, previous))
    return blocks


# Hard cap (seconds) for a single blocking Modbus operation. The Modbus client
# already uses bounded socket timeouts; this is a final safety net so that a
# wedged operation can never hang the coordinator (and, with it, Home Assistant).
OP_TIMEOUT = 20.0
# Hard cap (seconds) for the connection reset performed after a wedged op.
RESET_TIMEOUT = 5.0
# Retries for the reads this coordinator issues. The hub's own default (5) does
# NOT fit the cap above: one attempt against a half-dead port can burn its full
# socket timeout (3 s) plus a full reconnect (2 s delay + a 3 s connect), about
# 8.4 s with backoff - and 5 such attempts are ~42 s, past OP_TIMEOUT. When the
# cap fires the executor thread cannot be recalled: it keeps holding the hub
# lock and may swap the client behind the next cycle. So the calls here state a
# retry count whose worst case fits under the cap (2 x 8.4 s < 20 s) instead of
# inheriting it, and the test suite pins that arithmetic.
READ_RETRIES = 2


class MidniteSolarUpdateCoordinator(DataUpdateCoordinator):
    """Gather data for the Midnite Solar device."""

    api: MidniteHub

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        interval: int = 15,
        sensor_interval: int = DEFAULT_SENSOR_INTERVAL,
    ) -> None:
        """Initialize Update Coordinator."""

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=interval)
        )
        self.api = MidniteHub(host, port)
        self.interval = interval
        # How often the polled values may be republished to entities (and so
        # reach the recorder). Home Assistant's base dispatches listeners on
        # EVERY poll whose data changed; async_update_listeners below thins
        # that out without ever holding data back from coordinator.data,
        # which is what the bridge cache serves.
        self.sensor_interval = sensor_interval
        # Wall time of the last fully successful Modbus poll; the bridge
        # answers GET /state with it so a client's "last update" counter
        # shows the WIRE's age, not the age of its own fetch from this cache.
        self.last_polled: datetime | None = None
        # Dispatch throttle state: 0.0 makes the very first dispatch free.
        self._dispatch_due = 0.0
        self._dispatched_success: bool | None = None
        # The attributes __init__.py (setup) and bridge.py set on this
        # coordinator, DECLARED here so both sides type-check instead of
        # throwing attr-defined at every reader. The bridge sets them after
        # construction, exactly like HA sets the config entry.
        self.write_pin: str = DEFAULT_WRITE_PIN
        self.bridge_enabled: bool = DEFAULT_BRIDGE_ENABLED
        self._pin_gate: PinGate | None = None
        self.datalogger: Datalogger | None = None
        self.logger_sweeper: asyncio.Future[None] | None = None
        # Whether a set-point write should also commit to EEPROM. Off by default:
        # the ForceEEpromUpdate commit writes every pending (EE) register at once,
        # so it is opt-in via the "Auto Save EEPROM" switch, with the "Save to
        # EEPROM now" button for one-off commits. Reset to off on reload/restart.
        self.auto_save_eeprom = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all device and sensor data from api."""
        data = {}
        unavailable_entities = {}

        # Connectivity check. The read below transparently (re)connects if the
        # socket is closed, so we never touch the Modbus client on the event
        # loop here. A blocking call on the event loop would freeze Home
        # Assistant whenever a worker thread is holding the connection lock.
        test_result = await self._safe_read(REGISTER_MAP["UNIT_ID"], 1, retries=1)
        if test_result is None or test_result.isError():
            _LOGGER.warning(
                "Connection test failed on UNIT_ID. Trying alternative register..."
            )
            # Try a different register that might be more stable
            test_result = await self._safe_read(
                REGISTER_MAP["DISP_AVG_VBATT"], 1, retries=1
            )

        if test_result is None or test_result.isError():
            _LOGGER.error("Connection tests failed. Device not responding.")
            raise UpdateFailed("Device not responding to connection tests")

        unit_id = test_result.registers[0] if test_result.registers else None
        _LOGGER.debug("Connection test successful. UNIT_ID: %s", unit_id)

        # Read all register groups. A group that fails only marks its own
        # registers unavailable; it does not fail the whole update. A wedged
        # read (UpdateFailed) fails the update so the coordinator reschedules
        # instead of stalling on every remaining group.
        for group_name, registers in REGISTER_GROUPS.items():
            try:
                result = await self._read_register_group(registers, group_name)
                if result is not None:
                    data[group_name] = result
                else:
                    _LOGGER.warning("Failed to read register group: %s", group_name)
                    # Mark all registers in this group as unavailable
                    for reg in registers:
                        unavailable_entities[str(reg)] = False
            except UpdateFailed:
                # A read wedged, which means the device went down mid-update.
                # Fail fast and let the coordinator retry on the next interval.
                raise
            except Exception:  # noqa: BLE001
                # One group's failure must not fail the whole update: whatever
                # the wire throws here only marks its group's entities
                # unavailable (UpdateFailed is caught above and still fails
                # fast, as it must).
                for reg in registers:
                    unavailable_entities[str(reg)] = False

        self._hand_over_serial_number(data)

        # Only a poll that got this far (the connection test passed; groups
        # may individually be marked unavailable) stamps the wire. A failed
        # update leaves the last good time standing, so the age a client sees
        # keeps growing over a device that stopped answering.
        self.last_polled = dt_util.utcnow()

        return {
            "data": data,
            "availability": unavailable_entities,
        }

    def async_update_listeners(self) -> None:
        """Republish to entities at the sensor interval, not every Modbus poll.

        The base coordinator calls this whenever new data differs, which at a
        fast scan rate would land every changed reading in the recorder. A
        change in the success flag ALWAYS goes through at once (entities must
        see offline and the recovery immediately); only same-status data is
        thinned. Skipped polls lose nothing: the next allowed dispatch carries
        the newest `self.data`, and readers of `self.data` directly (the
        bridge) always have the newest regardless of dispatch.
        """
        now = time.monotonic()
        if (
            self.last_update_success == self._dispatched_success
            and now < self._dispatch_due
        ):
            return
        self._dispatched_success = self.last_update_success
        self._dispatch_due = now + self.sensor_interval
        super().async_update_listeners()

    def _hand_over_serial_number(self, data: dict[str, Any]) -> None:
        """Give the hub the serial number that releases the Ethernet write protect.

        The map requires the serial number to be written to registers 20492/20493
        before the Classic accepts writes over Ethernet, and says the grant lasts
        only until the TCP/IP connection is dropped. The hub re-sends it after
        every (re)connect; here it only has to supply the value it read from
        28673/28674.
        """
        serial_group = data.get("serial")
        if not serial_group:
            return
        msb = serial_group.get(REGISTER_MAP["SERIAL_NUMBER_MSB_RO"])
        lsb = serial_group.get(REGISTER_MAP["SERIAL_NUMBER_LSB_RO"])
        if msb is None or lsb is None:
            return
        self.api.set_serial_number(serial_from_registers(msb, lsb))

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
        except TimeoutError:
            _LOGGER.error(
                "Read of address %s timed out after %ss; resetting connection",
                address,
                OP_TIMEOUT,
            )
            await self._safe_reset()
            raise UpdateFailed(
                f"Timed out communicating with device (address {address})"
            ) from None

    async def _safe_reset(self) -> None:
        """Reset the Modbus client in the executor, bounded by a timeout."""
        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(self.api.reset),
                timeout=RESET_TIMEOUT,
            )
        except Exception as e:  # noqa: BLE001
            # Recovery best-effort: a failed reset must not raise over the
            # UpdateFailed the caller is already dealing with.
            _LOGGER.error("Failed to reset Modbus connection: %s", e)

    async def _read_register_group(
        self, registers: list[int], group_name: str
    ) -> dict[int, Any] | None:
        """Read a group of registers as blocks, one request per block."""
        if not registers:
            return None

        sorted_regs = sorted(set(registers))
        wanted = set(sorted_regs)
        result_data: dict[int, Any] = {}
        failed_registers: list[int] = []

        for first, last in register_blocks(sorted_regs):
            span = last - first + 1
            block = await self._safe_read(first, span, retries=READ_RETRIES)
            if (
                block is not None
                and not block.isError()
                and len(block.registers) == span
            ):
                for offset, value in enumerate(block.registers):
                    address = first + offset
                    if address in wanted:
                        result_data[address] = value
                continue

            # The block did not come back whole. Fall back to reading it one
            # register at a time, so a single register the card will not answer
            # marks only itself unavailable instead of blacking out every
            # setting that happens to sit next to it.
            _LOGGER.debug(
                "Block %d-%d (%d registers) did not come back; reading it register by register",
                first,
                last,
                span,
            )
            for register in [r for r in sorted_regs if first <= r <= last]:
                single = await self._safe_read(register, 1, retries=READ_RETRIES)
                if single is not None and not single.isError():
                    result_data[register] = single.registers[0]
                else:
                    _LOGGER.warning(
                        "Failed to read register %s (group: %s)",
                        REGISTER_BY_ADDRESS.get(register, f"register {register}"),
                        group_name,
                    )
                    failed_registers.append(register)

        if failed_registers:
            _LOGGER.debug("Failed to read registers: %s", failed_registers)

        return result_data or None

    def get_register_value(self, address: int) -> int | None:
        """Get a specific register value from the last update."""
        if self.data is None or "data" not in self.data:
            return None

        for group_name, registers in REGISTER_GROUPS.items():
            if address in registers and group_name in self.data["data"]:
                return self.data["data"][group_name].get(address)

        return None
