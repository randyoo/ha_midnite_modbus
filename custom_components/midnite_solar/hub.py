"""Support for Midnite Solar devices."""

import logging
import threading
import time

from pymodbus.client import ModbusTcpClient

_LOGGER = logging.getLogger(__name__)


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
    )

    def __init__(self, host: str, port: int) -> None:
        """Initialize the hub."""
        self.host = host
        self.port = port
        # RLock (re-entrant): read/write call _reconnect() while they already
        # hold the lock. A plain Lock would self-deadlock on that re-acquisition.
        self._lock = threading.RLock()
        self._client = self._make_client()

    def _make_client(self) -> ModbusTcpClient:
        """Create a fresh Modbus TCP client with bounded timeouts."""
        return ModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=self.DEFAULT_TIMEOUT,
            retries=self.DEFAULT_RETRIES,
        )

    @classmethod
    def _is_connection_error(cls, exc: Exception) -> bool:
        """Return True if the exception indicates the TCP connection is broken.

        Checks the exception's errno plus any wrapped cause/context, the message,
        and the exception type name, to be robust to how pymodbus surfaces it.
        """
        for e in (exc, getattr(exc, "__cause__", None), getattr(exc, "__context__", None)):
            if e is None:
                continue
            if getattr(e, "errno", None) in cls._CONN_ERRNOS:
                return True
        msg = str(exc).lower()
        for needle in cls._CONN_MSGS:
            if needle in msg:
                return True
        name = type(exc).__name__
        for cls_name in ("ConnectionException", "ConnectionReset", "ConnectionAborted", "BrokenPipe"):
            if cls_name in name:
                return True
        return False

    def is_still_connected(self):
        """Check if a socket object is present.

        Note: this can still return True for a *stale* socket whose peer has
        already reset. Real recovery happens when an op fails with a connection
        error (see _reconnect), not from this check.
        """
        with self._lock:
            return self._client.is_socket_open()

    def connect(self):
        """Connect to the Modbus TCP server."""
        with self._lock:
            if self._client.is_socket_open():
                return True
            _LOGGER.debug(f"Connecting to {self.host}:{self.port}")
            return self._client.connect()

    def disconnect(self):
        """Disconnect from the Modbus TCP server."""
        with self._lock:
            try:
                if self._client.is_socket_open():
                    _LOGGER.debug(f"Disconnecting from {self.host}:{self.port}")
                    return self._client.close()
            except Exception as e:
                _LOGGER.debug(f"Error during disconnect: {e}")
            return None

    def reset(self):
        """Force-close the (possibly stale) connection and start a fresh client.

        Leaves the client disconnected; the next read/write reconnects. Used as a
        recovery path after an operation wedged or timed out.
        """
        with self._lock:
            _LOGGER.debug("Resetting Modbus client (force close + delay + recreate)")
            try:
                self._client.close()
            except Exception:
                pass
            # Let the device drop the old session before we open a new one.
            time.sleep(self.RECONNECT_DELAY)
            self._client = self._make_client()

    def _reconnect(self) -> bool:
        """Fully release the connection, wait, then open ONE fresh connection.

        Called re-entrantly (while holding the RLock) when an operation fails
        with a connection-level error. Guarantees we never keep a stale socket
        and never hold two open connections at once.
        """
        with self._lock:
            _LOGGER.debug("Full reconnect: close connection, wait, open fresh")
            try:
                self._client.close()
            except Exception:
                pass
            # Let the device drop the old session before we open a new one.
            time.sleep(self.RECONNECT_DELAY)
            self._client = self._make_client()
            ok = self._client.connect()
            if ok:
                _LOGGER.info(f"Reconnected to {self.host}:{self.port}")
            else:
                _LOGGER.warning(f"Reconnect to {self.host}:{self.port} failed")
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

    def write_register(self, address: int, value: int, retries: int = 2):
        """Write a register with retry + reconnect-on-connection-error."""
        with self._lock:
            last_result = None
            for attempt in range(retries):
                if not self._ensure_connected():
                    _LOGGER.warning(f"Attempt {attempt + 1}: no connection for write to {address}")
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                try:
                    result = self._client.write_register(
                        address=address - 1,  # Modbus addresses are 0-indexed
                        value=value,
                    )
                    if result is not None and not result.isError():
                        return result
                    last_result = result
                    _LOGGER.warning(f"Attempt {attempt + 1} failed for write to {address}: {result}")
                except Exception as e:
                    last_result = e
                    _LOGGER.warning(f"Attempt {attempt + 1} exception for write to {address}: {e}")
                    if self._is_connection_error(e):
                        _LOGGER.debug(f"Connection-level error on write to {address}; full reconnect")
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
        _LOGGER.debug(f"Reading unit 1 address {address} count {count}")
        with self._lock:
            for attempt in range(retries):
                if not self._ensure_connected():
                    _LOGGER.warning(f"Attempt {attempt + 1}: no connection for address {address}")
                    if attempt < retries - 1:
                        time.sleep(0.2 * (attempt + 1))
                    continue
                try:
                    result = self._client.read_holding_registers(
                        address=address - 1,  # Modbus addresses are 0-indexed
                        count=count,
                    )
                    if result is not None and not result.isError():
                        _LOGGER.debug(f"Successfully read address {address}: {result.registers}")
                        return result
                    _LOGGER.warning(f"Attempt {attempt + 1} failed for address {address}: {result}")
                except Exception as e:
                    error_msg = str(e)
                    _LOGGER.warning(f"Attempt {attempt + 1} exception for address {address}: {e}")
                    if "Unable to decode request" in error_msg or "byte_count" in error_msg:
                        _LOGGER.debug("Modbus protocol error; dropping connection")
                        self.disconnect()
                    if self._is_connection_error(e):
                        _LOGGER.debug(f"Connection-level error reading {address}; full reconnect")
                        self._reconnect()
                if attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
            _LOGGER.error(f"All {retries} attempts failed for address {address}, count={count}")
            return None