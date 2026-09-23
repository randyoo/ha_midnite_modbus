"""The bridge engine: watching and writing the Classic through Home Assistant.

The Classic's Ethernet port serves one Modbus client at a time and this integration is that
client, so no other tool may hold the socket. The bridge is how anything else
gets its data: the coordinator keeps owning the connection, and the HTTP
views in bridge_api.py serve one-liners over these functions. The logic lives
here (like decoding lives in register_values.py) so it is testable against
the hardware-free doubles.

Every request carries a Home Assistant access token, so enabling the bridge
option alone opens nothing: the caller still has to present one of HA's own
long-lived tokens (or a browser session) like any other /api call.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
from contextlib import closing
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import zeroconf

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .base import MidniteBaseEntityDescription
from .const import (
    BRIDGE_API_VERSION,
    BRIDGE_ADS_KEY,
    BRIDGE_BEACON_INTERVAL,
    BRIDGE_BEACON_PORT,
    BRIDGE_BEACON_TYPE,
    BRIDGE_FORBIDDEN_WRITES,
    BRIDGE_MDNS_NAME,
    BRIDGE_MDNS_TYPE,
    BRIDGE_VIEWS_KEY,
    DEVICE_TYPES,
    FORCE_FLAGS,
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


def build_snapshot(coordinator: Any) -> Dict[str, Any]:
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


def bridge_identity(coordinator: Any) -> Dict[str, Any]:
    """Who this Classic is: unit name, MAC, model, serial."""
    device_info = ((coordinator.data or {}).get("data", {}) or {}).get("device_info", {}) or {}

    def read(key: str) -> Optional[int]:
        return device_info.get(REGISTER_MAP[key])

    name_registers = [read(f"UNIT_NAME_{index}") for index in range(4)]
    mac_registers = [
        read("MAC_ADDRESS_PART_1"),
        read("MAC_ADDRESS_PART_2"),
        read("MAC_ADDRESS_PART_3"),
    ]
    unit_id = read("UNIT_ID")
    return {
        "name": (
            name_from_registers(name_registers)
            if None not in name_registers
            else None
        ),
        "mac": (
            format_mac_from_registers(*mac_registers)
            if None not in mac_registers
            else None
        ),
        "unit_id": unit_id,
        "model": DEVICE_TYPES.get(unit_id & 0xFF) if unit_id is not None else None,
        "serial": MidniteBaseEntityDescription.serial_number(coordinator),
    }


def bridge_clock(coordinator: Any) -> Optional[str]:
    """The Classic's own wall clock as ISO text, or None if unread."""
    clock = ((coordinator.data or {}).get("data", {}) or {}).get("clock", {}) or {}
    decoded = clock_from_registers(
        clock.get(REGISTER_MAP["CTIME_SECONDS_MINUTES"]),
        clock.get(REGISTER_MAP["CTIME_HOURS_WEEKDAY"]),
        clock.get(REGISTER_MAP["CTIME_DAY_MONTH"]),
        clock.get(REGISTER_MAP["CTIME_YEAR"]),
    )
    return decoded.isoformat() if decoded is not None else None


def bridge_firmware(coordinator: Any) -> Dict[str, Any]:
    """The firmware block the AIR app opens every session with, decoded."""
    firmware = ((coordinator.data or {}).get("data", {}) or {}).get("firmware", {}) or {}

    def version(key: str) -> Optional[str]:
        raw = firmware.get(REGISTER_MAP[key])
        return version_from_register(raw) if raw is not None else None

    def revision(low_key: str, high_key: str) -> Optional[int]:
        low = firmware.get(REGISTER_MAP[low_key])
        high = firmware.get(REGISTER_MAP[high_key])
        return combine32(low, high) if None not in (low, high) else None

    return {
        "app_version": version("APP_VERSION"),
        "net_version": version("NET_VERSION"),
        "app_rev": revision("APP_REV_LOW", "APP_REV_HIGH"),
        "net_rev": revision("NET_REV_LOW", "NET_REV_HIGH"),
    }


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
) -> Dict[str, Any]:
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


async def async_bridge_clock(hass: Any, coordinator: Any, when) -> Dict[str, Any]:
    """Set the Classic's clock to `when`, the AIR app's file-write way."""
    await async_set_clock(hass, coordinator.api, when)
    return {"clock": when.isoformat()}


async def async_bridge_reboot(hass: Any, coordinator: Any) -> Dict[str, Any]:
    """Reboot the Classic; it drops the connection as it restarts."""
    await async_reboot_classic(hass, coordinator.api)
    return {"reboot": "sent", "note": "the Classic drops the connection as it restarts"}


async def async_bridge_eeprom_save(hass: Any, coordinator: Any) -> Dict[str, Any]:
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


async def async_bridge_datalogger(hass: Any, coordinator: Any) -> Dict[str, Any]:
    """Run the full device-5 sweep and answer with what it found."""
    return await async_sweep(hass, coordinator.api, bridge_datalogger(coordinator))


def beacon_payload(
    entry: Any, coordinator: Any, address: str, port: int
) -> bytes:
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
            try:
                sender.sendto(payload, (target, BRIDGE_BEACON_PORT))
            except OSError:
                pass  # no route for that broadcast form; the other may work


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
        broadcaster: Optional[Callable[[bytes, str], None]] = None,
    ) -> None:
        """Remember the entry; advertise nothing yet."""
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        # Resolved at call time (not a default arg) so a test can monkeypatch
        # bridge.broadcast_beacon and see it used.
        self._broadcaster = broadcast_beacon if broadcaster is None else broadcaster
        self._zeroconf = None
        self._info = None
        self._beacon_thread = None
        self._beacon_stop = threading.Event()
        self._beacon_bytes = None
        self._beacon_addr = None
        self._beacon_interval = BRIDGE_BEACON_INTERVAL

    def service_name(self) -> str:
        """An instance name unique on the LAN: unit name where known, and
        the Ethernet MAC (the entry's unique id) as the discriminator, so two
        Homes serving Classics never collide on one record."""
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
            parsed = urlparse(get_url(self._hass, allow_internal=True, prefer_external=True))
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
        dns_safe = "".join(
            char if char.isalnum() else "-" for char in tail
        ).strip("-")
        return f"midnite-bridge-{dns_safe}.local."

    def publish(self) -> None:
        """Advertise; a no-op when already advertised."""
        if self._zeroconf is not None:
            return
        address, port = self._advertised_endpoint()
        # Beat the beacon first: it is the half that survives a firewall that
        # eats mDNS, and it must survive even a failed zeroconf registration.
        self._start_beacon(address, port)
        self._info = zeroconf.ServiceInfo(
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
        self._zeroconf = zeroconf.Zeroconf()
        self._zeroconf.register_service(self._info)
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
        """Beat every interval until close; a bad beat logs and stops the beat.

        Waits BEFORE the first send (see the class note) so the suite never
        opens a beacon socket; only a live Home Assistant ever gets here.
        """
        while not self._beacon_stop.wait(self._beacon_interval):
            try:
                self._broadcaster(self._beacon_bytes, self._beacon_addr)
            except Exception:
                _LOGGER.exception("The bridge beacon stopped beating")
                return

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
    from .bridge_api import BRIDGE_VIEWS

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
    except Exception as e:
        _LOGGER.warning("The bridge API is up but not advertised on the LAN: %s", e)
    hass.data.setdefault(BRIDGE_ADS_KEY, {})[entry.entry_id] = advertiser


async def async_stop_bridge(hass: Any, entry: Any) -> bool:
    """Withdraw this entry's advertisement; the views stay (entry-agnostic)."""
    advertiser = hass.data.get(BRIDGE_ADS_KEY, {}).pop(entry.entry_id, None)
    if advertiser is None:
        return False
    try:
        await hass.async_add_executor_job(advertiser.close)
    except Exception as e:
        _LOGGER.error("Error closing the bridge advertisement: %s", e)
    return True
