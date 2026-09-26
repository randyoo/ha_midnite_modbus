"""Fakes that record what the integration would send to a Classic."""

from __future__ import annotations

import logging
from typing import Any

from midnite_solar.const import REGISTER_GROUPS

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


class ModbusResult:
    """Stands in for a pymodbus response."""

    def __init__(self, registers: list[int] | None = None, error: bool = False):
        self.registers = registers or []
        self._error = error

    def isError(self) -> bool:
        return self._error


class FakeApi:
    """Records Modbus writes instead of sending them.

    The Classic is effectively single-connection and must not be talked to from
    the test suite, so this is the only "device" the tests use.
    """

    def __init__(
        self,
        read_values: dict[int, int] | None = None,
        fail_writes=False,
        error_writes=False,
        stale_read: bool = False,
        unreadable: bool = False,
        bad_blocks: set[tuple[int, int]] | None = None,
        unreadable_registers: set[int] | None = None,
    ):
        self.read_values = read_values or {}
        self.writes: list[tuple[int, int]] = []
        self.reads: list[int] = []
        # The /network door: (start, frame) per accepted atomic frame; the
        # fake CONFIRMS by default (the read-back answers the new words,
        # like a card that reprogrammed fine) unless network_never_lands.
        self.network_frames: list[tuple[int, list[int]]] = []
        self.network_error: Exception | None = None
        self.network_never_lands = False
        # Private function 104/105 "internal file" calls (the clock), recorded
        # the same way so the clock feature is testable without a Classic.
        self.internal_writes: list[tuple[int, list[int], int]] = []
        self.internal_reads: list[tuple[int, int, int]] = []
        self.fail_writes = fail_writes
        self.error_writes = error_writes
        # A Classic that accepts a write stores it, so a read-back returns it.
        # stale_read models the write-protected Classic that ignores the write
        # and keeps answering with the old value; unreadable models a register
        # that does not answer at all.
        self.stale_read = stale_read
        self.unreadable = unreadable
        # (address, count) pairs that answer with an exception, so the block
        # fallback can be exercised; and addresses that never answer at all.
        self.bad_blocks = bad_blocks or set()
        self.unreadable_registers = unreadable_registers or set()
        # Registers where a read answers with a value OTHER than what was just
        # written: a second tool (MNGP) changing the neighbour byte of a packed
        # register between the write and the read-back. The wind tables need a
        # double that can move beside them, or the suite cannot tell a shared
        # register's neighbour from a refused write.
        self.late_values: dict[int, int] = {}
        # The coordinator hands the serial number over after every update, because
        # the write-protect grant dies with the connection.
        self._serial = None
        self.serial_sets = 0

    def write_register(self, address: int, value: int, retries: int = 2):
        self.writes.append((address, value))
        if self.fail_writes:
            raise OSError("[Errno 104] Connection reset by peer")
        if not self.stale_read and not self.unreadable:
            self.read_values[address] = value
        return ModbusResult(error=self.error_writes)

    def write_network(
        self, start: int, values: list[int], confirms: int = 20
    ) -> list[int]:
        """Record one atomic Ethernet-card frame; the read-back is the verdict.

        Mirrors MidniteHub.write_network's CONTRACT (not its socket
        choreography - that has its own scripted double in
        test_network_writes): frame-shaped work, then confirmation by
        read-back. network_error models the hub's honest refusals (a
        misshapen frame, a dead static copy, a card that never read
        back) surfacing to the bridge layer as an exception.
        """
        self.network_frames.append((start, list(values)))
        if self.network_error is not None:
            raise self.network_error
        if self.network_never_lands:
            # Faithful to the hub: the read-back never matched, and the hub
            # FAILS rather than dressing an echo up as confirmation.
            raise OSError(
                f"the Ethernet card never read back the frame sent to {start}"
            )
        for i, value in enumerate(values):
            self.read_values[start + i] = value
        # Return what the card now ANSWERS, not an echo of what was sent:
        # a read-back assertion must be able to fail, or it asserts nothing.
        return [self.read_values.get(start + i, 0) for i in range(len(values))]

    def read_holding_registers(self, address: int, count: int = 1, retries: int = 5):
        self.reads.append(address)
        if self.unreadable or (address, count) in self.bad_blocks:
            return ModbusResult(error=True)
        if count == 1 and address in self.unreadable_registers:
            return ModbusResult(error=True)
        if count == 1 and address in self.late_values:
            return ModbusResult(registers=[self.late_values[address]])
        return ModbusResult(
            registers=[
                self.read_values.get(address + offset, 0) for offset in range(count)
            ]
        )

    def write_internal(self, device, data, address=0, retries: int = 2):
        """Record a private function-105 file write instead of sending it."""
        self.internal_writes.append((device, list(data), address))
        if not self.stale_read and not self.unreadable:
            return ModbusResult(error=self.error_writes)
        return ModbusResult(error=True)

    def read_internal(self, device, length, address=0, retries: int = 5):
        """Record a private function-104 file read; answer it empty."""
        self.internal_reads.append((device, length, address))
        return ModbusResult(error=self.error_writes)

    def set_serial_number(self, serial):
        self._serial = serial
        self.serial_sets += 1

    def connect(self):
        """No socket to open."""
        return True

    def disconnect(self):
        """No socket to close."""

    def reset(self):
        """No socket to reset."""


class FakeCoordinator(DataUpdateCoordinator):
    """Coordinator holding canned register data, keyed by group name."""

    def __init__(
        self,
        hass,
        api: FakeApi,
        groups: dict[str, dict[int, int]] | None = None,
        auto_save_eeprom: bool = True,
    ):
        super().__init__(hass, logging.getLogger(__name__), name="midnite_solar")
        self.api = api
        self.data = {"data": groups or {}, "groups": groups or {}}
        self.refresh_requests = 0
        # The double defaults the auto-save gate ON so the many commit-path tests
        # stay valid; the production default (OFF) and the off-path are pinned by
        # dedicated tests in test_auto_save.py.
        self.auto_save_eeprom = auto_save_eeprom

    async def async_request_refresh(self):
        """A refresh brings back what the device reports now, as a real one does."""
        self.refresh_requests += 1
        for group in self.data["data"].values():
            for address in group:
                if address in self.api.read_values:
                    group[address] = self.api.read_values[address]

    def get_register_value(self, address: int) -> Any:
        # Mirror the real coordinator: an address only reads back from the group
        # that actually polls it. A fake that searches every group would hide a
        # wrong group name in an entity, and could hand back a value that the real
        # device never polled for that register.
        for group_name, registers in REGISTER_GROUPS.items():
            if address in registers and group_name in self.data["data"]:
                return self.data["data"][group_name].get(address)
        return None

    def group(self, name: str) -> dict[int, int]:
        return self.data["data"].setdefault(name, {})


class FakeRequest:
    """Stands in for the aiohttp request the bridge views are called with.

    The view coroutines are driven directly (no server, no socket), the way
    every other double here works; `body=BAD` models a request whose body is
    not JSON, which is the one aiohttp behaviour the views branch on.
    """

    BAD = object()

    def __init__(self, hass, body=None, headers=None):
        self.app = {"hass": hass}
        self._body = body
        # The views read the write PIN off the request headers; a real aiohttp
        # request has a case-insensitive map, and `.get` is all the double has
        # to provide for the gate.
        self.headers = dict(headers or {})

    async def json(self):
        if self._body is FakeRequest.BAD:
            raise ValueError("not JSON")
        return self._body


class RecordingInternalApi(FakeApi):
    """FakeApi whose private function-104 reads ANSWER, with a canned payload.

    The base FakeApi answers internal reads with an empty payload (nothing
    to decode); the datalogger sweep tests need days that decode, so it hands
    back the same payload for every read unless `fail_addresses` says which
    file addresses answer with a Modbus exception (a day slot not there).
    """

    def __init__(self, payload: bytes = b"", fail_addresses=None, **kwargs):
        super().__init__(**kwargs)
        self.payload = payload
        self.fail_addresses = set(fail_addresses or ())
        self.internal_results = None

    def read_internal(self, device, length, address=0, retries: int = 5):
        # Records the RETRIES too: the sweep's bounded retry budget is the
        # contract under test, and a base FakeApi read never carries one.
        self.internal_reads.append((device, length, address, retries))
        result = ModbusResult(error=address in self.fail_addresses)
        result.payload = b"" if address in self.fail_addresses else self.payload
        self.internal_results = result
        return result
