"""The bridge engine: watching and writing the Classic through Home Assistant.

The Classic's Ethernet port serves one Modbus client at a time and this integration is that
client, so no other tool may hold the socket. The bridge is how anything else
gets its data: the coordinator keeps owning the connection, and the HTTP
views in bridge_api.py serve one-liners over these functions. The logic lives
here (like decoding lives in register_values.py) so it is testable against
the hardware-free doubles.

The bridge is OPEN: it carries no Home Assistant access token. Reads are public
to the LAN, and the write PIN (this module's PinGate / check_write_pin) is the
whole gate on every call that CHANGES the Classic - so there is no usable
default, and an unconfigured entry refuses writes until a real PIN is set.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
from contextlib import closing
from hmac import compare_digest
import json
import logging
import socket
import threading
import time
from typing import Any
from urllib.parse import urlparse

import zeroconf

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .base import MidniteBaseEntityDescription
from .const import (
    BRIDGE_ADS_KEY,
    BRIDGE_API_VERSION,
    BRIDGE_BEACON_INTERVAL,
    BRIDGE_BEACON_PORT,
    BRIDGE_BEACON_TYPE,
    BRIDGE_FORBIDDEN_WRITES,
    BRIDGE_MDNS_NAME,
    BRIDGE_MDNS_TYPE,
    BRIDGE_VIEWS_KEY,
    DEFAULT_WRITE_PIN,
    DEVICE_TYPES,
    DOMAIN,
    FORCE_FLAGS,
    PIN_LENGTH,
    PIN_LOCKOUT_STEPS,
    REGISTER_MAP,
)
from .datalogger import Datalogger, async_sweep
from .entity_writes import (
    async_auto_save_if_enabled,
    async_reboot_classic,
    async_set_clock,
    async_store_settings,
    async_verify_write,
    async_write_setting,
)
from .register_values import (
    clock_from_registers,
    combine32,
    force_flag_write,
    format_mac_from_registers,
    version_from_register,
)
from .text import name_from_registers

_LOGGER = logging.getLogger(__name__)

# The name a register answers to, for labels and the API's reverse table.
KEY_BY_ADDRESS = {address: key for key, address in REGISTER_MAP.items()}

# The advertised HTTP port when HA's own URL cannot be resolved; HA answers
# on 8123 unless the user moved it, in which case get_url knows.
DEFAULT_HTTP_PORT = 8123


def build_snapshot(coordinator: Any) -> dict[str, Any]:
    """What GET /state answers: the coordinator cache, JSON-shaped.

    Served from the last poll without touching the wire, so any number of
    clients may read it at any rate. Values are the RAW registers the map
    scales by tenths per its own formulas - the client divides, exactly like
    the AIR app's per-register conversions; the names table is the API's
    register dictionary so a client needs no copy of the register map.
    `last_polled` is when the CLASSIC was last successfully polled (UTC);
    a client's own fetch time says nothing about how old these numbers are,
    and a device that stopped answering makes this stamp's age grow.
    """
    data = (coordinator.data or {}).get("data", {}) if coordinator.data else {}
    last_polled = getattr(coordinator, "last_polled", None)
    return {
        "api_version": BRIDGE_API_VERSION,
        "online": bool(data),
        "last_polled": last_polled.isoformat() if last_polled is not None else None,
        "names": dict(REGISTER_MAP),
        "groups": {
            group: {str(address): value for address, value in (values or {}).items()}
            for group, values in data.items()
        },
        "identity": bridge_identity(coordinator),
        "clock": bridge_clock(coordinator),
        "firmware": bridge_firmware(coordinator),
        "auto_save_eeprom": bool(getattr(coordinator, "auto_save_eeprom", False)),
    }


def bridge_identity(coordinator: Any) -> dict[str, Any]:
    """Who this Classic is: unit name, MAC, model, serial."""
    device_info = ((coordinator.data or {}).get("data", {}) or {}).get(
        "device_info", {}
    ) or {}

    def read(key: str) -> int | None:
        return device_info.get(REGISTER_MAP[key])

    name_registers = [read(f"UNIT_NAME_{index}") for index in range(4)]
    mac_registers = [
        read("MAC_ADDRESS_PART_1"),
        read("MAC_ADDRESS_PART_2"),
        read("MAC_ADDRESS_PART_3"),
    ]
    unit_id = read("UNIT_ID")
    return {
        "name": name_from_registers(name_registers),
        "mac": format_mac_from_registers(*mac_registers),
        "unit_id": unit_id,
        "model": DEVICE_TYPES.get(unit_id & 0xFF) if unit_id is not None else None,
        "serial": MidniteBaseEntityDescription.serial_number(coordinator),
    }


def bridge_clock(coordinator: Any) -> str | None:
    """The Classic's own wall clock as ISO text, or None if unread."""
    clock = ((coordinator.data or {}).get("data", {}) or {}).get("clock", {}) or {}
    decoded = clock_from_registers(
        clock.get(REGISTER_MAP["CTIME_SECONDS_MINUTES"]),
        clock.get(REGISTER_MAP["CTIME_HOURS_WEEKDAY"]),
        clock.get(REGISTER_MAP["CTIME_DAY_MONTH"]),
        clock.get(REGISTER_MAP["CTIME_YEAR"]),
    )
    return decoded.isoformat() if decoded is not None else None


def bridge_firmware(coordinator: Any) -> dict[str, Any]:
    """The firmware block the AIR app opens every session with, decoded."""
    firmware = ((coordinator.data or {}).get("data", {}) or {}).get(
        "firmware", {}
    ) or {}

    def version(key: str) -> str | None:
        raw = firmware.get(REGISTER_MAP[key])
        return version_from_register(raw) if raw is not None else None

    def revision(low_key: str, high_key: str) -> int | None:
        low = firmware.get(REGISTER_MAP[low_key])
        high = firmware.get(REGISTER_MAP[high_key])
        return combine32(low, high)

    return {
        "app_version": version("APP_VERSION"),
        "net_version": version("NET_VERSION"),
        "app_rev": revision("APP_REV_LOW", "APP_REV_HIGH"),
        "net_rev": revision("NET_REV_LOW", "NET_REV_HIGH"),
    }


class PinGate:
    """Per-entry write-PIN check with Apple-style exponential lockout.

    It remembers how many wrong (or missing) PINs it has been shown and, once
    the ladder says so, refuses to look at ANY candidate - right or wrong -
    until the wait has run, returning an identical 429 for each. That refusal
    to compare mid-wait is what makes it a rate limiter rather than a fake
    one: a spammer gets a single comparison per rung, so guessing grows from
    seconds toward hours and a 4-digit PIN costs hours to reach
    (PIN_LOCKOUT_STEPS: 5 s, 15, 60, 300, 900, capped at 3600). A correct PIN
    clears the run, but only once its own wait has run. The comparison is
    constant-time (hmac.compare_digest) and no answer ever repeats the PIN back.
    """

    def __init__(self) -> None:
        """Start with a clean run: no misses, nothing locked."""
        self._wrong = 0
        self._locked_until = 0.0

    def check(self, presented: Any, expected: str, now: float):
        """Return None to let the write land, else (status, body) to answer.

        The lockout is checked BEFORE the PIN ever is, and while a wait runs
        the bridge does NOT look at the PIN at all: a right candidate and a
        wrong one get the identical 429 with the seconds left. That is the
        entire anti-brute-force property. If the bridge compared first (even
        to help the owner in), a spammer firing at line rate would hold a free
        oracle - every wrong guess returns 429, so the ONE response that is not
        429 would BE the correct PIN, and the ladder would slow nothing. By
        refusing to compare during the wait, each miss buys exactly one rung
        (5 s, 15, 60, 300, 900, 3600, capped) of total silence, so a guesser
        earns a single comparison per rung and a 4-digit PIN costs hours to
        reach. The right PIN only lands once its wait has run; misses during a
        wait are not even counted, so a retry-storm cannot re-extend the window
        past its own rung.

        The strict Apple trade-off this buys: after a few typos the OWNER's own
        correct PIN is refused until the current wait expires. That is intended
        - it is the rate limit doing its job - and the escapes are to wait it
        out, reload the entry, or restart Home Assistant (all clear the gate).
        """
        if now < self._locked_until:
            left = int(self._locked_until - now) + 1
            return 429, {
                "error": "too many wrong PINs; this bridge is not looking "
                "at another guess yet",
                "retry_after": left,
            }
        if isinstance(presented, str) and compare_digest(presented, expected):
            self._wrong = 0
            self._locked_until = 0.0
            return None
        self._wrong += 1
        wait = PIN_LOCKOUT_STEPS[min(self._wrong - 1, len(PIN_LOCKOUT_STEPS) - 1)]
        self._locked_until = now + wait
        return 401, {
            "error": "the write PIN is missing or wrong",
            "retry_after": wait,
        }


def write_pin_is_set(pin: Any) -> bool:
    """True only when a REAL write PIN is configured - never the placeholder.

    A real PIN is exactly PIN_LENGTH digits and is not DEFAULT_WRITE_PIN (the
    all-zeros fresh-install placeholder). This is the one rule behind "you
    cannot write through the bridge until you set a 6-digit PIN": the bridge
    carries no access token, so an unconfigured PIN must fail CLOSED (writes
    off), not fall back to a known default a stranger could guess.
    """
    return (
        isinstance(pin, str)
        and len(pin) == PIN_LENGTH
        and pin.isdigit()
        and pin != DEFAULT_WRITE_PIN
    )


def check_write_pin(coordinator: Any, presented: Any, now: float | None = None):
    """Engine call behind every mutating bridge endpoint: gate on the PIN.

    Two checks, in order. First the bridge asks whether the OWNER ever armed
    it: if the entry's PIN is unset or still the all-zeros placeholder, every
    write is refused 403 with the instruction to set one - there is no default
    that works, because the open bridge would otherwise be writable by anyone
    on the LAN who guessed the well-known placeholder. Only then does the
    PinGate run: the gate lives on the coordinator (one per entry, like
    auto_save_eeprom), so its lockout survives ordinary requests and resets
    when the entry reloads - exactly when the owner would have changed the PIN.
    Returns None to let the call proceed, or the (status, body) to answer it
    with; the thin HTTP view only maps that onto a JSON response.
    """
    expected = str(getattr(coordinator, "write_pin", "") or "")
    if not write_pin_is_set(expected):
        return 403, {
            "error": "the bridge has no write PIN set, so writes are off; "
            f"choose a {PIN_LENGTH}-digit write PIN in the Midnite Solar "
            "integration options to enable them",
        }
    gate = getattr(coordinator, "_pin_gate", None)
    if gate is None:
        gate = PinGate()
        coordinator._pin_gate = gate  # noqa: SLF001
        # (per-entry stores ride the coordinator, like write_pin and
        # datalogger; this module owns the attribute)
    return gate.check(presented, expected, time.monotonic() if now is None else now)


def resolve_register(target: Any) -> int:
    """Accept a register name or number and return the number to write.

    The API speaks the register map's own names when it can ("ABSORB_BATTERY
    _VOLTAGE" style keys as published in the snapshot), and a bare number
    otherwise - but never anything in BRIDGE_FORBIDDEN_WRITES, and never a
    number the 16-bit registers cannot hold.
    """
    if isinstance(target, str):
        key = target.strip().upper()
        if key in REGISTER_MAP:
            return REGISTER_MAP[key]
        if key.isdigit():
            target = int(key)
    if isinstance(target, bool) or not isinstance(target, int):
        raise HomeAssistantError(
            f"register {target!r} is neither a name from the register map nor a number"
        )
    if not 0 < target <= 0xFFFF:
        raise HomeAssistantError(f"register {target} is outside the addressable range")
    if target in BRIDGE_FORBIDDEN_WRITES:
        raise HomeAssistantError(
            f"register {target} cannot be written through the bridge: it belongs "
            "to the Modbus handshake itself"
        )
    return target


async def async_bridge_write(
    hass: Any, coordinator: Any, target: Any, value: Any, commit: bool = False
) -> dict[str, Any]:
    """Write one register through the bridge, with the integration's checks.

    This is the entity write path (write, read back, gated EEPROM commit)
    with the platform plumbing removed: the same async_verify_write that
    catches a write-protected or clamping Classic, and the same opt-in
    ForceEEpromUpdate, since the commit writes every pending (EE) register
    at once. `commit=True` asks for a commit this one write even with the
    auto-save switch off; the switch still commits when it is on.
    """
    address = resolve_register(target)
    if isinstance(value, bool) or not isinstance(value, int):
        raise HomeAssistantError(
            f"value {value!r} is not an integer; register values are raw "
            "integers (the map's tenths are the client's division)"
        )
    if not 0 <= value <= 0xFFFF:
        raise HomeAssistantError(f"value {value} does not fit in a 16-bit register")
    label = KEY_BY_ADDRESS.get(address, f"register {address}")
    await async_write_setting(hass, coordinator.api, address, value, label)
    await async_verify_write(hass, coordinator.api, address, value, label, str)
    committed = await async_auto_save_if_enabled(hass, coordinator, label)
    if commit and not committed:
        await async_store_settings(hass, coordinator.api, label)
        committed = True
    return {
        "register": address,
        "name": KEY_BY_ADDRESS.get(address),
        "value": value,
        "committed": committed,
    }


async def async_bridge_clock(hass: Any, coordinator: Any, when) -> dict[str, Any]:
    """Set the Classic's clock to `when`, the AIR app's file-write way."""
    await async_set_clock(hass, coordinator.api, when)
    return {"clock": when.isoformat()}


async def async_bridge_reboot(hass: Any, coordinator: Any) -> dict[str, Any]:
    """Reboot the Classic; it drops the connection as it restarts."""
    await async_reboot_classic(hass, coordinator.api)
    return {"reboot": "sent", "note": "the Classic drops the connection as it restarts"}


async def async_bridge_eeprom_save(hass: Any, coordinator: Any) -> dict[str, Any]:
    """Commit every pending (EE) setting with one ForceEEpromUpdate.

    The bridge's mirror of HA's "Save to EEPROM now" button: with the
    auto-save switch off this is the only way a written setting survives a
    restart. Honest about its one sharp edge - the commit writes ALL pending
    (EE) registers at once (that is what Table 4160-1's flag does), so it is
    a deliberate press, never a side effect of reading.
    """
    register, word = force_flag_write(1 << FORCE_FLAGS["ForceEEpromUpdate"])
    await async_write_setting(
        hass, coordinator.api, register, word, "Save to EEPROM now"
    )
    await coordinator.async_request_refresh()
    return {"committed": True}


def bridge_datalogger(coordinator: Any) -> Datalogger:
    """The per-entry datalogger store, created empty on first use."""
    store = getattr(coordinator, "datalogger", None)
    if store is None:
        store = Datalogger()
        coordinator.datalogger = store
    return store


# The background collector's rhythm. The bridge sweeps its OWN cache so a
# watching client's chart fills without anyone asking (and without a PIN:
# this is our read on our connection, on our schedule). The first pass
# waits out the entry's startup polls; after that the ring is re-read
# hourly, which is far more often than the Classic's day ring grows.
SWEEP_WARM_SECONDS = 5.0
SWEEP_RESWEEP_SECONDS = 3600.0


async def async_bridge_datalogger(hass: Any, coordinator: Any) -> dict[str, Any]:
    """One device-5 sweep at a time: run it now, or join the one running.

    The store's `sweeping` flag is the single-flight token: a caller that
    arrives while a sweep is in flight (the background collector's, or
    another PIN-gated refresh's) gets the cache AS IT STANDS - still
    flagged `sweeping` - instead of stampeding a second 96-read pass onto
    this single-connection device. The client's own reload loop picks up
    the finished answer; nobody hammers the wire twice.
    """
    store = bridge_datalogger(coordinator)
    if store.sweeping:
        return store.as_dict()
    store.sweeping = True
    try:
        await async_sweep(hass, coordinator.api, store)
    finally:
        # The flag falls BEFORE the answer is written, so the caller that
        # just completed a sweep is never told "still loading" about data
        # that is already in hand. A cancelled pass lands here too.
        store.sweeping = False
    return store.as_dict()


def async_start_sweeper(hass: Any, coordinator: Any) -> None:
    """Arm this entry's background datalogger collector (idempotent)."""
    if getattr(coordinator, "logger_sweeper", None) is not None:
        return
    coordinator.logger_sweeper = hass.async_create_task(
        async_sweeper_loop(hass, coordinator)
    )


async def async_sweeper_loop(hass: Any, coordinator: Any) -> None:
    """Sweep the bridge's own datalogger cache, unasked, for its lifetime.

    A failed pass is logged and retried on the next beat; the cache keeps
    answering from what it holds meanwhile. Stopping is `async_stop_bridge`
    cancelling the task - the sweep's own `finally` clears the flag, so a
    cancelled pass leaves no phantom "sweeping" behind.
    """
    await asyncio.sleep(SWEEP_WARM_SECONDS)
    while True:
        try:
            await async_bridge_datalogger(hass, coordinator)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            # A sweep failure must never kill the collector: the bench caught
            # a dead-forever background thread once (FINDINGS section 49) and
            # "retry on the next beat" is the whole recovery design.
            _LOGGER.warning(
                "The bridge's background datalogger sweep failed; retrying later: %s",
                e,
            )
        await asyncio.sleep(SWEEP_RESWEEP_SECONDS)


def beacon_payload(entry: Any, coordinator: Any, address: str, port: int) -> bytes:
    """The beacon datagram body: everything a listener needs to CALL us.

    Pure (no socket, no clock) so the contract is unit-testable. It repeats
    what the mDNS TXT record carries - the API version, the entry to call, the
    HA address and port to call it ON, and the Classic behind it - because the
    beacon exists precisely for the networks where the mDNS record never
    arrives. `name`/`model` are for the list label; both are optional.
    """
    identity = bridge_identity(coordinator)
    return json.dumps(
        {
            "t": BRIDGE_BEACON_TYPE,
            "api": BRIDGE_API_VERSION,
            "entry": entry.entry_id,
            "addr": address,
            "port": port,
            "name": identity.get("name") or "Classic",
            "model": identity.get("model"),
            "classic": str(entry.data.get("host", "")) or None,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def broadcast_beacon(payload: bytes, local_addr: str) -> None:
    """One fire-and-forget broadcast of the beacon to the LAN.

    Sent to both the global and the /24 directed broadcast address (home LANs
    are /24; the directed one gets through routers that drop the limited one).
    A plain datagram send - the client binds udp/BRIDGE_BEACON_PORT and
    listens, so nothing has to be reachable in HA's inbound direction, which
    is exactly what the mDNS record could not count on.
    """
    targets = {"255.255.255.255"}
    octets = local_addr.split(".")
    if len(octets) == 4 and all(o.isdigit() for o in octets):
        targets.add(f"{octets[0]}.{octets[1]}.{octets[2]}.255")
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sender:
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in targets:
            with contextlib.suppress(OSError):
                # no route for that broadcast form; the other may work
                sender.sendto(payload, (target, BRIDGE_BEACON_PORT))


class BridgeAdvertiser:
    """One mDNS record per entry, so a desktop app finds the bridge unaided.

    Blocking (the zeroconf library is), so publish/close run through the
    executor. The record carries what a client needs to talk to it with no
    prior configuration: the HA address and port, the API version, the config
    entry to call it by, and the Classic's own address behind it.

    The mDNS half is joined by a UDP beacon (see beacon_payload): a daemon
    thread beats the same facts to the LAN every BRIDGE_BEACON_INTERVAL, which
    is what actually works where the record is eaten. The thread's FIRST act
    is to wait the interval, and close() sets its stop event before anything
    else, so under the hardware-free suite - which unloads long before a beat
    is due, and never runs longer than the interval at all - no beacon socket
    is ever opened. The broadcaster is injectable for testing the beat.
    """

    def __init__(
        self,
        hass: Any,
        entry: Any,
        coordinator: Any,
        broadcaster: Callable[[bytes, str], None] | None = None,
    ) -> None:
        """Remember the entry; advertise nothing yet."""
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        # Resolved at call time (not a default arg) so a test can monkeypatch
        # bridge.broadcast_beacon and see it used.
        self._broadcaster = broadcast_beacon if broadcaster is None else broadcaster
        # All Optional and DECLARED: publish() fills them in, close()
        # unwinds them, and mypy checks both sides against these types.
        self._zeroconf: zeroconf.Zeroconf | None = None
        self._info: zeroconf.ServiceInfo | None = None
        self._beacon_thread: threading.Thread | None = None
        self._beacon_stop = threading.Event()
        self._beacon_bytes: bytes | None = None
        self._beacon_addr: str | None = None
        self._beacon_interval = BRIDGE_BEACON_INTERVAL

    def service_name(self) -> str:
        """An mDNS instance name unique on the LAN.

        Unit name where known, and the Ethernet MAC (the entry's unique id)
        as the discriminator, so two Homes serving Classics never collide on
        one record.
        """
        identity = bridge_identity(self._coordinator)
        tail = identity.get("mac") or self._entry.entry_id
        unit = identity.get("name") or "Classic"
        return f"{BRIDGE_MDNS_NAME} {unit} ({tail})"

    def _advertised_endpoint(self):
        """(ip, port) a LAN client should reach this Home Assistant on.

        Home Assistant's own idea of its external URL first (it knows about
        moved ports and the like); a route probe as the fallback, which sends
        no packet - connecting a UDP socket only asks the kernel which
        interface the default route uses.
        """
        try:
            parsed = urlparse(
                get_url(self._hass, allow_internal=True, prefer_external=True)
            )
            if parsed.hostname and self._is_ipv4(parsed.hostname):
                return parsed.hostname, parsed.port or DEFAULT_HTTP_PORT
        except NoURLAvailableError:
            pass
        return self._local_ip(), DEFAULT_HTTP_PORT

    @staticmethod
    def _local_ip() -> str:
        """Which interface the default route uses; no packet is sent.

        A UDP socket's connect() only asks the kernel to pick a route, so
        this answers even on a LAN with no 8.8.8.8 reachable - and never on
        one that has a real conversation (the suite double replaces it).
        """
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as probe:
            probe.connect(("8.8.8.8", 53))
            return probe.getsockname()[0]

    @staticmethod
    def _is_ipv4(candidate: str) -> bool:
        try:
            socket.inet_aton(candidate)
        except OSError:
            return False
        return True

    def server_name(self) -> str:
        """A mDNS host name UNIQUE to this bridge.

        One shared "midnite-bridge.local" would make every machine answer
        the A query, and a desktop app on a two-Classic LAN could resolve
        its bridge to the WRONG Home Assistant. The MAC (or the entry id
        before it is known) makes the name this card's own.
        """
        identity = bridge_identity(self._coordinator)
        tail = (identity.get("mac") or self._entry.entry_id).lower()
        dns_safe = "".join(char if char.isalnum() else "-" for char in tail).strip("-")
        return f"midnite-bridge-{dns_safe}.local."

    def publish(self) -> None:
        """Advertise; a no-op when already advertised."""
        if self._zeroconf is not None:
            return
        address, port = self._advertised_endpoint()
        # Beat the beacon first: it is the half that survives a firewall that
        # eats mDNS, and it must survive even a failed zeroconf registration.
        self._start_beacon(address, port)
        info = zeroconf.ServiceInfo(
            BRIDGE_MDNS_TYPE,
            f"{self.service_name()}.{BRIDGE_MDNS_TYPE}",
            addresses=[socket.inet_aton(address)],
            port=port,
            server=self.server_name(),
            properties={
                b"api": str(BRIDGE_API_VERSION).encode(),
                b"entry": str(self._entry.entry_id).encode(),
                b"classic": str(self._entry.data.get("host", "")).encode(),
            },
        )
        # Build locally, register, only then publish the handles: if the
        # registration raises, the attributes stay None (nothing half-buried
        # for close() to trip over) and the fresh socket is closed.
        zc = zeroconf.Zeroconf()
        try:
            zc.register_service(info)
        except Exception:
            zc.close()
            raise
        self._zeroconf = zc
        self._info = info
        _LOGGER.info(
            "Advertised the Midnite bridge as %s (mDNS + udp/%d beacon)",
            self.service_name(),
            BRIDGE_BEACON_PORT,
        )

    def _start_beacon(self, address: str, port: int) -> None:
        """Build the payload and set the beacon beating; safe if already set."""
        if self._beacon_thread is not None:
            return
        self._beacon_addr = address
        self._beacon_bytes = beacon_payload(
            self._entry, self._coordinator, address, port
        )
        self._beacon_stop.clear()
        self._beacon_thread = threading.Thread(
            target=self._beacon_loop,
            name=f"midnite-bridge-beacon-{self._entry.entry_id}",
            daemon=True,
        )
        self._beacon_thread.start()

    def _beacon_loop(self) -> None:
        """Beat every interval until close; a bad beat is SKIPPED, not fatal.

        Waits BEFORE the first send (see the class note) so the suite never
        opens a beacon socket; only a live Home Assistant ever gets here.

        The old loop answered any beat exception by ending the thread for
        good - and the bench (2026-09-24, mid router work) caught exactly
        that shape: the API stayed perfectly served while the beacon had
        beaten zero times in 14 s, because one sendto during an interface
        flap killed the beat forever and nothing ever re-published. A
        network that comes back deserves a beacon that comes back: log the
        first miss (and every twelfth), skip the beat, keep the cadence,
        and say so when the beat survives again.
        """
        misses = 0
        while not self._beacon_stop.wait(self._beacon_interval):
            payload = self._beacon_bytes
            addr = self._beacon_addr
            if payload is None or addr is None:
                # Cannot happen for a thread this module only starts after
                # _start_beacon filled both; skipping is cheaper than
                # asserting in production code.
                continue
            try:
                self._broadcaster(payload, addr)
            except Exception:
                misses += 1
                if misses == 1 or misses % 12 == 0:
                    _LOGGER.exception("The bridge beacon beat failed (keep beating)")
            else:
                if misses:
                    _LOGGER.info(
                        "The bridge beacon is beating again after %d failed beat(s)",
                        misses,
                    )
                    misses = 0

    def close(self) -> None:
        """Stop the beacon, withdraw the record, release the mDNS socket; safe twice."""
        # Stop the beacon FIRST: setting the event wakes the thread out of its
        # interval wait at once (so this never blocks for the interval) and is
        # what keeps the suite from ever letting a beat fire.
        self._beacon_stop.set()
        thread = self._beacon_thread
        self._beacon_thread = None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self._beacon_interval + 1.0)
        if self._zeroconf is None:
            return
        zeroconf_instance = self._zeroconf
        self._zeroconf = None
        try:
            if self._info is not None:
                zeroconf_instance.unregister_service(self._info)
        finally:
            zeroconf_instance.close()


def ensure_bridge_views(hass: Any) -> bool:
    """Register the API views once per Home Assistant, whatever the entries.

    The views are entry-agnostic (they look the coordinator up in hass.data
    per request), so a reload never stacks a second route onto aiohttp's
    router, and an unloaded entry answers 404 rather than serving whatever
    coordinator an earlier setup left behind.
    """
    if hass.data.get(BRIDGE_VIEWS_KEY):
        return False
    # Lazy BY DESIGN: bridge_api imports this module at its top, so a
    # top-level import here is a cycle.
    from .bridge_api import BRIDGE_VIEWS  # noqa: PLC0415

    for view in BRIDGE_VIEWS:
        hass.http.register_view(view())
    hass.data[BRIDGE_VIEWS_KEY] = True
    return True


async def async_start_bridge(hass: Any, entry: Any, coordinator: Any) -> None:
    """Bring the bridge up for this entry (call after the first refresh)."""
    ensure_bridge_views(hass)
    bridge_datalogger(coordinator)
    advertiser = BridgeAdvertiser(hass, entry, coordinator)
    # The API is the bridge; a LAN that drops mDNS (or a HA whose address
    # cannot be resolved) should not take it down.
    try:
        await hass.async_add_executor_job(advertiser.publish)
    except Exception as e:  # noqa: BLE001
        # The API IS the bridge; a broken mDNS/zeroconf stack must not take
        # it down, so any publish failure is a warning, never a setup failure.
        _LOGGER.warning("The bridge API is up but not advertised on the LAN: %s", e)
    hass.data.setdefault(BRIDGE_ADS_KEY, {})[entry.entry_id] = advertiser
    # The bridge also collects its own chart data: from here on the cache
    # fills without any client asking (the GET stays open, the POST
    # refresh stays the PIN-gated "now, please").
    async_start_sweeper(hass, coordinator)


async def async_stop_bridge(hass: Any, entry: Any) -> bool:
    """Withdraw this entry's advertisement and stop its sweeper.

    The views stay (entry-agnostic).
    """
    # The collector first: it is the one thing here that could still be
    # mid-read on the wire. Cancel it; the sweep's `finally` clears the
    # `sweeping` flag even into a CancelledError.
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    sweeper = getattr(coordinator, "logger_sweeper", None) if coordinator else None
    if sweeper is not None:
        sweeper.cancel()
        coordinator.logger_sweeper = None
    advertiser = hass.data.get(BRIDGE_ADS_KEY, {}).pop(entry.entry_id, None)
    if advertiser is None:
        return False
    try:
        await hass.async_add_executor_job(advertiser.close)
    except Exception as e:  # noqa: BLE001
        # Teardown best-effort: the entry is already unloading; a mDNS socket
        # that refuses to close cleanly must not fail the unload.
        _LOGGER.error("Error closing the bridge advertisement: %s", e)
    return True
