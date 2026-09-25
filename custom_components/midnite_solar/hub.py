"""Support for Midnite Solar devices."""

import contextlib
import logging
import threading
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.pdu import ModbusPDU

from .const import CLOCK_FILE_ADDRESS, REGISTER_MAP
from .private_pdu import ReadInternalPDU, WriteInternalPDU, register_private_pdus
from .register_values import unlock_values

_LOGGER = logging.getLogger(__name__)

UNLOCK_SERIAL_MSB = REGISTER_MAP["UNLOCK_SERIAL_MSB"]
UNLOCK_SERIAL_LSB = REGISTER_MAP["UNLOCK_SERIAL_LSB"]


class WriteLockedError(RuntimeError):
    """Raised when the Classic still write-protects Ethernet writes."""


class MidniteHub:
    """Midnite Hub for managing Modbus TCP connections."""

    # Bounded socket operations so a dead/unresponsive peer can never block a
    # thread indefinitely.
    DEFAULT_TIMEOUT = 3.0
    # We manage our own retry loops, so keep the client's internal retries at
    # zero (otherwise retries stack up and a dead device takes minutes).
    DEFAULT_RETRIES = 0
    # This device is effectively single-connection and is sensitive to
    # connection churn. After fully releasing a connection we wait this long
    # before opening a new one, to let the device drop the old session cleanly
    # (so it never sees two connections at once).
    RECONNECT_DELAY = 2.0

    # TCP errno values that mean the connection itself is broken (not a
    # Modbus-level "bad register" error). On any of these we force a full
    # reconnect instead of retrying the read on the same (dead) socket.
    # 32=EPIPE 103=ECONNABORTED 104=ECONNRESET 105=ENOTCONN 110=ETIMEDOUT
    # 111=ECONNREFUSED 112=EHOSTUNREACH 113=ENETUNREACH
    _CONN_ERRNOS = {32, 103, 104, 105, 110, 111, 112, 113}

    # Message fragments that indicate the connection dropped.
    _CONN_MSGS = (
        "reset by peer",
        "broken pipe",
        "connection aborted",
        "connection reset",
        "connection refused",
        "not connected",
        "no connection",
        "remote end closed",
        "socket is closed",
        # pymodbus surfaces a read timeout as ModbusIOException("...no response...").
        # On this device - which drops idle connections - a socket that answers
        # nothing is a dead socket, so it must reconnect rather than burn all its
        # retries against the same half-open pipe (which also risks exceeding the
        # coordinator's per-operation timeout).
        "no response",
        "timed out",
    )

    def __init__(self, host: str, port: int) -> None:
        """Initialize the hub."""
        self.host = host
        self.port = port
        # RLock (re-entrant): read/write call _reconnect() while they already
        # hold the lock. A plain Lock would self-deadlock on that re-acquisition.
        self._lock = threading.RLock()
        self._client = self._make_client()
        # The Classic ignores writes over Ethernet until the serial number has
        # been written to the unlock registers, and that grant ends as soon as
        # the connection drops, so both are tracked next to the socket.
        self._serial: int | None = None
        self._unlocked = False

    def _make_client(self) -> ModbusTcpClient:
        """Create a fresh Modbus TCP client with bounded timeouts.

        The Classic's private function codes are registered on THIS client's
        decoder only (see private_pdu.py), so the registration dies with the
        client and never shadows standard Write Coil decoding process-wide.
        """
        client = ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=self.DEFAULT_TIMEOUT,
            retries=self.DEFAULT_RETRIES,
        )
        register_private_pdus(client)
        return client

    @classmethod
    def _is_connection_error(cls, exc: Exception) -> bool:
        """Return True if the exception indicates the TCP connection is broken.

        Checks the exception's errno plus any wrapped cause/context, the message,
        and the exception type name, to be robust to how pymodbus surfaces it.
        """
        for e in (
            exc,
            getattr(exc, "__cause__", None),
            getattr(exc, "__context__", None),
        ):
            if e is None:
                continue
            if getattr(e, "errno", None) in cls._CONN_ERRNOS:
                return True
        msg = str(exc).lower()
        for needle in cls._CONN_MSGS:
            if needle in msg:
                return True
        name = type(exc).__name__
        for cls_name in (
            "ConnectionException",
            "ConnectionReset",
            "ConnectionAborted",
            "BrokenPipe",
        ):
            if cls_name in name:
                return True
        return False

    def connect(self):
        """Connect to the Modbus TCP server."""
        with self._lock:
            if self._client.is_socket_open():
                return True
            _LOGGER.debug("Connecting to %s:%s", self.host, self.port)
            # A new socket is a new session, so any grant from the last one is
            # worth nothing here.
            self._unlocked = False
            return self._client.connect()

    def disconnect(self):
        """Disconnect from the Modbus TCP server.

        The unlock grant is cleared whether or not the socket still looks open:
        the map says the grant lasts until the connection is dropped, and a
        Classic that is idle drops it without telling us, so by the time this is
        called the grant may already be gone. Leaving `self._unlocked` set is what
        made writes silently stop working after a reload - the next connection
        reused a grant that had died with the old socket.
        """
        with self._lock:
            self._unlocked = False
            try:
                if self._client.is_socket_open():
                    _LOGGER.debug("Disconnecting from %s:%s", self.host, self.port)
                    return self._client.close()
            except Exception as e:  # noqa: BLE001
                # A socket already dying on us is the normal case here; the
                # grant is cleared either way and the caller asked us to let
                # go, so nothing this close() throws is worth propagating.
                _LOGGER.debug("Error during disconnect: %s", e)
            return None

    def reset(self):
        """Force-close the (possibly stale) connection and start a fresh client.

        Leaves the client disconnected; the next read/write reconnects. Used as a
        recovery path after an operation wedged or timed out.
        """
        with self._lock:
            _LOGGER.debug("Resetting Modbus client (force close + delay + recreate)")
            with contextlib.suppress(Exception):
                # Force-close: the socket is already suspected dead, and the
                # fresh client built below is the point of the reset.
                self._client.close()
            # Let the device drop the old session before we open a new one.
            time.sleep(self.RECONNECT_DELAY)
            self._client = self._make_client()
            self._unlocked = False

    def _reconnect(self) -> bool:
        """Fully release the connection, wait, then open ONE fresh connection.

        Called re-entrantly (while holding the RLock) when an operation fails
        with a connection-level error. Guarantees we never keep a stale socket
        and never hold two open connections at once.
        """
        with self._lock:
            _LOGGER.debug("Full reconnect: close connection, wait, open fresh")
            with contextlib.suppress(Exception):
                # Same as reset(): the socket is being discarded, whatever it
                # says on the way out is noise.
                self._client.close()
            # Let the device drop the old session before we open a new one.
            time.sleep(self.RECONNECT_DELAY)
            self._client = self._make_client()
            self._unlocked = False
            ok = self._client.connect()
            if ok:
                _LOGGER.info("Reconnected to %s:%s", self.host, self.port)
            else:
                _LOGGER.warning("Reconnect to %s:%s failed", self.host, self.port)
            return bool(ok)

    def _ensure_connected(self) -> bool:
        """Return True if there is (probably) a connection, else reconnect.

        is_socket_open() can report True for a stale socket whose peer has
        already reset, so this is only a cheap "looks connected" gate. The real
        recovery happens when an op actually fails with a connection error.
        """
        if self._client.is_socket_open():
            return True
        return self._reconnect()

    def set_serial_number(self, serial: int | None) -> None:
        """Provide the serial number that releases the Ethernet write protect.

        The serial number is read from registers 28673/28674; the hub does not
        read them itself rather than duplicate the coordinator's polling, so the
        coordinator hands the value over. A change means the unlock is stale.
        """
        if serial == self._serial:
            return
        self._serial = serial
        self._unlocked = False

    def _ensure_unlocked(self) -> bool:
        """Write the unlock registers if the Classic is still write-protected.

        The map is explicit: "W Serial Number (Unlock Code) For writing to Classic
        modbus registers over Ethernet ... Write the Classic's serial number over
        Ethernet to unlock writing of modbus registers over Ethernet. Setting this
        will last until the TCP/IP connection is dropped". Until that write
        happens the Classic ignores setting writes, which is why the absorb
        voltage never took effect. Called with the lock held, and it writes
        straight to the client so it cannot recurse.
        """
        if self._unlocked:
            return True
        if self._serial is None:
            _LOGGER.warning(
                "Classic write protect is engaged and the serial number is not known yet"
            )
            return False
        msb, lsb = unlock_values(self._serial)
        for address, value in ((UNLOCK_SERIAL_MSB, msb), (UNLOCK_SERIAL_LSB, lsb)):
            result = self._client.write_register(address=address - 1, value=value)
            if result is None or result.isError():
                _LOGGER.error("Unlock write to register %s failed: %s", address, result)
                self._unlocked = False
                return False
        self._unlocked = True
        _LOGGER.debug("Released the Classic Ethernet write protect")
        return True

    def write_register(self, address: int, value: int, retries: int = 2):
        """Write a register with retry + reconnect-on-connection-error."""
        with self._lock:
            # The LAST event wins, of either kind: a failed PDU answer or a
            # raised exception; the tail below raises or returns whichever of
            # them landed last.
            last_result: ModbusPDU | Exception | None = None
            for attempt in range(retries):
                if not self._ensure_connected():
                    _LOGGER.warning(
                        "Attempt %s: no connection for write to %s",
                        attempt + 1,
                        address,
                    )
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                try:
                    unlocked = self._ensure_unlocked()
                except Exception as e:  # noqa: BLE001
                    # The unlock write is a write too, and a socket the device has
                    # already dropped can raise on it. Handle it like a failed
                    # setting write - reconnect and try again - instead of letting
                    # a bare connection error escape to the caller.
                    last_result = e
                    _LOGGER.warning(
                        "Attempt %s exception unlocking for write to %s: %s",
                        attempt + 1,
                        address,
                        e,
                    )
                    if self._is_connection_error(e):
                        _LOGGER.debug(
                            "Connection-level error on unlock; full reconnect"
                        )
                        self._reconnect()
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                if not unlocked:
                    raise WriteLockedError(
                        "The Classic write-protects Ethernet writes; the "
                        "serial number unlock has not succeeded yet"
                    )
                try:
                    result = self._client.write_register(
                        address=address - 1,  # Modbus addresses are 0-indexed
                        value=value,
                    )
                    if result is not None and not result.isError():
                        return result
                    last_result = result
                    _LOGGER.warning(
                        "Attempt %s failed for write to %s: %s",
                        attempt + 1,
                        address,
                        result,
                    )
                except Exception as e:  # noqa: BLE001
                    # pymodbus raises a family of its own plus raw OSError here,
                    # and the NEXT line classifies every one of them
                    # (_is_connection_error reads errno, message and type);
                    # naming subsets here would only age badly.
                    last_result = e
                    _LOGGER.warning(
                        "Attempt %s exception for write to %s: %s",
                        attempt + 1,
                        address,
                        e,
                    )
                    if self._is_connection_error(e):
                        _LOGGER.debug(
                            "Connection-level error on write to %s; full reconnect",
                            address,
                        )
                        self._reconnect()
                if attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
            if last_result is None:
                raise OSError(f"Could not write to {address} (no connection)")
            if isinstance(last_result, Exception):
                raise last_result
            return last_result

    def read_holding_registers(self, address: int, count: int = 1, retries: int = 5):
        """Read holding registers with retry + reconnect-on-connection-error."""
        _LOGGER.debug("Reading unit 1 address %s count %s", address, count)
        with self._lock:
            for attempt in range(retries):
                if not self._ensure_connected():
                    _LOGGER.warning(
                        "Attempt %s: no connection for address %s", attempt + 1, address
                    )
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                try:
                    result = self._client.read_holding_registers(
                        address=address - 1,  # Modbus addresses are 0-indexed
                        count=count,
                    )
                    if result is not None and not result.isError():
                        _LOGGER.debug(
                            "Successfully read address %s: %s",
                            address,
                            result.registers,
                        )
                        return result
                    _LOGGER.warning(
                        "Attempt %s failed for address %s: %s",
                        attempt + 1,
                        address,
                        result,
                    )
                except Exception as e:  # noqa: BLE001
                    # Same family as the write path: pymodbus + raw socket
                    # errors, classified from errno/message/type right after.
                    error_msg = str(e)
                    _LOGGER.warning(
                        "Attempt %s exception for address %s: %s",
                        attempt + 1,
                        address,
                        e,
                    )
                    if (
                        "Unable to decode request" in error_msg
                        or "byte_count" in error_msg
                    ):
                        _LOGGER.debug("Modbus protocol error; dropping connection")
                        self.disconnect()
                    if self._is_connection_error(e):
                        _LOGGER.debug(
                            "Connection-level error reading %s; full reconnect", address
                        )
                        self._reconnect()
                if attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
            _LOGGER.error(
                "All %s attempts failed for address %s, count=%s",
                retries,
                address,
                count,
            )
            return None

    def write_internal(
        self, device: int, data, address: int = CLOCK_FILE_ADDRESS, retries: int = 2
    ):
        """Write an internal file (function 105) with the write protect released.

        The clock lives here; like a settings write it goes through the
        Ethernet write protect, so the serial-number unlock is ensured first,
        exactly as write_register does. The frame's own address is used as-is
        (it is a file address, not a Modbus register). Returns the decoded
        response PDU (which echoes the request header), raising the last error
        if no attempt succeeds.
        """
        with self._lock:
            # The LAST event wins, of either kind: a failed PDU answer or a
            # raised exception; the tail below raises or returns whichever of
            # them landed last.
            last_result: ModbusPDU | Exception | None = None
            for attempt in range(retries):
                if not self._ensure_connected():
                    _LOGGER.warning(
                        "Attempt %s: no connection for internal write to file %s",
                        attempt + 1,
                        device,
                    )
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                try:
                    unlocked = self._ensure_unlocked()
                except Exception as e:  # noqa: BLE001
                    # Unlock writes fail like any other write here.
                    last_result = e
                    _LOGGER.warning(
                        "Attempt %s exception unlocking for internal write: %s",
                        attempt + 1,
                        e,
                    )
                    if self._is_connection_error(e):
                        self._reconnect()
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                if not unlocked:
                    raise WriteLockedError(
                        "The Classic write-protects Ethernet writes; the "
                        "serial number unlock has not succeeded yet"
                    )
                try:
                    result = self._client.execute(
                        False,
                        WriteInternalPDU(device=device, data=data, address=address),
                    )
                    if result is not None and not result.isError():
                        return result
                    last_result = result
                    _LOGGER.warning(
                        "Attempt %s internal write failed: %s", attempt + 1, result
                    )
                except Exception as e:  # noqa: BLE001
                    # Private-function writes throw the same family as the
                    # standard ones; _is_connection_error classifies them all.
                    last_result = e
                    _LOGGER.warning(
                        "Attempt %s internal write exception: %s", attempt + 1, e
                    )
                    if self._is_connection_error(e):
                        self._reconnect()
                if attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
            if last_result is None:
                raise OSError(f"Could not write internal file {device} (no connection)")
            if isinstance(last_result, Exception):
                raise last_result
            return last_result

    def read_internal(
        self, device: int, length: int, address: int = 0, retries: int = 5
    ):
        """Read an internal file (function 104), returning the response PDU.

        The Classic answers with the echoed header plus the raw payload bytes,
        which the response PDU exposes as `.payload`. Reads are not gated by
        the Ethernet write protect (only writes are), so this skips the unlock.
        Returns None if no attempt succeeds.
        """
        with self._lock:
            for attempt in range(retries):
                if not self._ensure_connected():
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                try:
                    result = self._client.execute(
                        False,
                        ReadInternalPDU(device=device, length=length, address=address),
                    )
                    if result is not None and not result.isError():
                        return result
                    _LOGGER.warning(
                        "Attempt %s internal read failed: %s", attempt + 1, result
                    )
                except Exception as e:  # noqa: BLE001
                    # Private-function reads throw the same family as the
                    # standard ones; classified right here by _is_connection_error.
                    _LOGGER.warning(
                        "Attempt %s internal read exception: %s", attempt + 1, e
                    )
                    if self._is_connection_error(e):
                        self._reconnect()
                if attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
            _LOGGER.error(
                "All %s attempts failed for internal read of file %s", retries, device
            )
            return None
