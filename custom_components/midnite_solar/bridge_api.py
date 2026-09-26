"""The HTTP face of the bridge: what a desktop app calls.

Every answer here is one engine call in bridge.py, the way a platform file
is one entity_writes call: no decoding and no register maths in the view.
The views are registered once per Home Assistant (see
bridge.ensure_bridge_views) and look the entry's coordinator up per request,
so a reload never stacks a second route and an unloaded entry gets a clean
404.

The bridge needs NO Home Assistant token (`requires_auth = False`): watching
is open to any device that can reach the port, by design. That makes the write
PIN the ONLY thing on the write path, so it is load-bearing and strict: every
call that CHANGES the Classic (write, clock, reboot, EEPROM save, the /pin
probe, and the expensive datalogger sweep) is gated on the entry's 6-digit
write PIN, and an owner who never set one (the all-zeros placeholder) is
refused until they do. A wrong or missing PIN is refused and a strict lockout
ladder makes guessing cost exponentially longer waits (see bridge.PinGate);
reads of state/datalogger change nothing and stay open.

The seconds and weekday the Classic's clock carries are not settable (the
firmware derives them, and the payload's seconds byte is a manual-set
marker, not a value - see register_values.clock_file_payload), so the clock
call takes no seconds field and the Classic may still republish its own
time a moment later (FINDINGS section 40: the Classic Ethernet stack owns the clock).
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import bridge
from .const import BRIDGE_URL_PREFIX, DOMAIN, PIN_HEADER

_LOGGER = logging.getLogger(__name__)


class _BodyError(Exception):
    """Internal plumbing: carries a prepared 400 answer out of body().

    It exists so body() can have ONE honest return type (the JSON object)
    instead of a tuple whose None-ness mypy cannot correlate across the
    call sites.
    """

    def __init__(self, answer: Any) -> None:
        """Carry the view's prepared JSON answer."""
        super().__init__("the request body was not a JSON object")
        self.answer = answer


class MidniteBridgeView(HomeAssistantView):
    """Shared plumbing: find the entry's coordinator, answer in JSON."""

    # Open by design: no Home Assistant token. Reads are public to the LAN;
    # every WRITE is gated on the entry's PIN (pin_gate below), so the token
    # was doing nothing the PIN does not do better and specific to the MPPT.
    requires_auth = False

    def coordinator_for(self, request: Any, entry_id: str) -> Any | None:
        """Look the entry's coordinator up fresh, so a reload never stacks."""
        return request.app["hass"].data.get(DOMAIN, {}).get(entry_id)

    def missing_entry(self, entry_id: str):
        """404 for an entry this HA does not (or no longer) serves."""
        return self.json(
            {"error": f"no Midnite Solar entry {entry_id}"}, status_code=404
        )

    def refused(self, error: Exception):
        """400 with the integration's own wording, kept verbatim."""
        return self.json({"error": str(error)}, status_code=400)

    async def body(self, request: Any) -> dict:
        """The request's JSON object, or _BodyError carrying the 400 answer."""
        try:
            body = await request.json()
        except Exception as e:
            # Anything aiohttp can throw for a body it cannot turn into a
            # JSON object (not JSON, gzip surprise, size limit) gets the
            # same 400 answer: the client wrote the body wrong.
            raise _BodyError(
                self.json({"error": "the body must be a JSON object"}, status_code=400)
            ) from e
        if not isinstance(body, dict):
            raise _BodyError(
                self.json({"error": "the body must be a JSON object"}, status_code=400)
            )
        return body

    def pin_gate(self, request: Any, coordinator: Any):
        """The write-PIN gate in front of every call that changes the Classic.

        None lets the call proceed; anything else is the answer to give. Three
        refusals: 403 when the owner has not set a 6-digit PIN at all (writes
        are simply not armed - no default works), 401 for a wrong or absent PIN
        which starts the lockout ladder, and 429 while a lockout runs (during
        which the bridge compares NOTHING, so brute force buys exponentially
        longer waits instead of answers). This is the whole write protection:
        the bridge carries no token, so this gate is load-bearing.
        """
        refused = bridge.check_write_pin(coordinator, request.headers.get(PIN_HEADER))
        if refused is None:
            return None
        status, body = refused
        return self.json(body, status_code=status)


class MidniteStateView(MidniteBridgeView):
    """GET /api/midnite/{entry_id}/state - the last poll, no wire touched."""

    url = f"{BRIDGE_URL_PREFIX}/state"
    name = "api:midnite:state"

    async def get(self, request: Any, entry_id: str):
        """Answer the last poll, verbatim, without touching the wire."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        return self.json(bridge.build_snapshot(coordinator))


class MidnitePinView(MidniteBridgeView):
    """POST {"pin": text} - checks a write PIN without changing the Classic.

    How the desktop app validates the PIN it just typed the moment the write
    switch is flipped: right, and the app arms; wrong or absent, and the SAME
    refusal as a write comes back. It runs through the same gate, so the
    lockout ladder counts guesses here too - there is no cheaper endpoint to
    brute the PIN against, and no PIN set at all is refused the same way a
    write would be.
    """

    url = f"{BRIDGE_URL_PREFIX}/pin"
    name = "api:midnite:pin"

    async def post(self, request: Any, entry_id: str):
        """Check a PIN against the gate WITHOUT changing the Classic."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        try:
            body = await self.body(request)
        except _BodyError as bad:
            return bad.answer
        presented = body.get("pin")
        if not isinstance(presented, str):
            # A probe with no pin field is a malformed request, not a guess:
            # answer 400 WITHOUT consulting the gate, so a client that posts
            # empty bodies cannot spend anyone's lockout ladder.
            return self.json(
                {"error": "the probe needs a pin as text"}, status_code=400
            )
        refused = bridge.check_write_pin(coordinator, presented)
        if refused is not None:
            status, message = refused
            return self.json(message, status_code=status)
        return self.json({"pin": "accepted"})


class MidniteWriteView(MidniteBridgeView):
    """POST {"register": name|number, "value": int, "commit": bool}.

    The reply is the write with the read-back verdict; a Classic that was
    write-protected or clamped answers 400 with the same wording the number
    entities raise, and a 400 NEVER means the register landed.
    """

    url = f"{BRIDGE_URL_PREFIX}/write"
    name = "api:midnite:write"

    async def post(self, request: Any, entry_id: str):
        """Write one register through the PIN gate and the read-back check."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        try:
            body = await self.body(request)
        except _BodyError as bad:
            return bad.answer
        if "register" not in body or "value" not in body:
            return self.json(
                {"error": "the write needs a register and a value"}, status_code=400
            )
        try:
            answer = await bridge.async_bridge_write(
                request.app["hass"],
                coordinator,
                body["register"],
                body["value"],
                bool(body.get("commit", False)),
            )
        except HomeAssistantError as e:
            return self.refused(e)
        return self.json(answer)


class MidniteNetworkView(MidniteBridgeView):
    """POST {"start": name, "values": [words]} - reprogram the Ethernet card.

    The controlled door (NETWORK_CHOREOGRAPHY.md): the PIN gate rides like
    every mutating call, the frame must be atomic (the hub refuses lone
    words), and the answer waits for the card's READ-BACK - the ack proves
    nothing on this block. While the card reprograms, Home Assistant's own
    connection drops with it and the integration looks briefly offline;
    that is the truth, and the hub is back on it inside a second.
    """

    url = f"{BRIDGE_URL_PREFIX}/network"
    name = "api:midnite:network"

    async def post(self, request: Any, entry_id: str):
        """Send one atomic frame through the PIN gate and the read-back."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        try:
            body = await self.body(request)
        except _BodyError as bad:
            return bad.answer
        try:
            answer = await bridge.async_bridge_network_write(
                request.app["hass"],
                coordinator,
                body.get("start"),
                body.get("values"),
            )
        except HomeAssistantError as e:
            return self.refused(e)
        return self.json(answer)


class MidniteClockView(MidniteBridgeView):
    """POST {"time": ISO 8601} - set the Classic's clock the app's way."""

    url = f"{BRIDGE_URL_PREFIX}/clock"
    name = "api:midnite:clock"

    async def post(self, request: Any, entry_id: str):
        """Reboot the Classic; it drops the connection as it restarts."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        try:
            body = await self.body(request)
        except _BodyError as bad:
            return bad.answer
        raw = body.get("time")
        if not isinstance(raw, str):
            return self.json(
                {"error": "the clock needs a time as ISO 8601 text"}, status_code=400
            )
        try:
            when = datetime.fromisoformat(raw)  # 3.11+ parses the Z suffix
        except ValueError:
            return self.json(
                {"error": f"{raw!r} is not ISO 8601 time"}, status_code=400
            )
        if when.tzinfo is not None:
            when = dt_util.as_local(when)
        try:
            answer = await bridge.async_bridge_clock(
                request.app["hass"], coordinator, when
            )
        except HomeAssistantError as e:
            return self.refused(e)
        return self.json(answer)


class MidniteRebootView(MidniteBridgeView):
    """POST - the app's "Bully Menu": reboot, and hold on to your hat.

    The Classic drops the Modbus connection as it restarts, so the next
    state answer will be offline for a moment; that is the reboot working,
    not the bridge breaking.
    """

    url = f"{BRIDGE_URL_PREFIX}/reboot"
    name = "api:midnite:reboot"

    async def post(self, request: Any, entry_id: str):
        """Commit every pending (EE) setting with one ForceEEpromUpdate."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        try:
            answer = await bridge.async_bridge_reboot(request.app["hass"], coordinator)
        except HomeAssistantError as e:
            return self.refused(e)
        return self.json(answer)


class MidniteEepromSaveView(MidniteBridgeView):
    """POST - "Save to EEPROM now": one ForceEEpromUpdate, no setting sent.

    With the auto-save switch off, pending (EE) settings only survive a
    restart when something commits them; this is that something, exactly
    like the HA button the register map's flag was designed for.
    """

    url = f"{BRIDGE_URL_PREFIX}/save"
    name = "api:midnite:save"

    async def post(self, request: Any, entry_id: str):
        """Sweep the Classic's whole year of stored days onto the one wire."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        try:
            answer = await bridge.async_bridge_eeprom_save(
                request.app["hass"], coordinator
            )
        except HomeAssistantError as e:
            return self.refused(e)
        return self.json(answer)


class MidniteDataloggerView(MidniteBridgeView):
    """GET - the last swept days, plus the `sweeping` flag.

    Open and cheap by design: the bridge sweeps this cache itself in the
    background, so a watching client can fill its chart on connect without
    a PIN, without ever POSTing, and without touching the wire.
    """

    url = f"{BRIDGE_URL_PREFIX}/datalogger"
    name = "api:midnite:datalogger"

    async def get(self, request: Any, entry_id: str):
        """Answer the last swept days from the cache; no PIN, no wire."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        return self.json(bridge.bridge_datalogger(coordinator).as_dict())


class MidniteDataloggerRefreshView(MidniteBridgeView):
    """POST - read the Classic's whole year of days (96 paced private reads).

    A sweep shares the one connection with the live poll, one read at a
    time, so this takes minutes and the state never goes stale over it; the
    reply is the full dated answer. It READS, but it is a minutes-long
    monopoly on the Classic's single Modbus connection, so an open bridge
    would let any LAN device stall the live poll and every write by spamming
    it - which is a way to change the Classic's behaviour without writing a
    register. So it is PIN-gated like a write, not open like the cheap state
    read. The datalogger GET (the cache) stays open - and nobody needs to
    POST this at all for the chart to fill: the bridge's own background
    collector keeps the cache fresh. A POST that arrives while a sweep is
    already in flight JOINS it (answers the cache, flagged `sweeping`)
    instead of stampeding a second pass onto the one connection.
    """

    url = f"{BRIDGE_URL_PREFIX}/datalogger/refresh"
    name = "api:midnite:datalogger-refresh"

    async def post(self, request: Any, entry_id: str):
        """Answer the reboot endpoint through the PIN gate."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        answer = await bridge.async_bridge_datalogger(request.app["hass"], coordinator)
        return self.json(answer)


class MidniteRecentHistoryView(MidniteBridgeView):
    """GET - the collected recent-history samples, plus `collecting`.

    Open and cheap by design, like the day-log cache: the bridge collects
    this from the Classic's device-6 ring in the background, so a watching
    client can fill its current-day histogram on connect without a PIN,
    without ever POSTing, and without touching the wire. `collecting` is the
    in-progress signal: true while a walk or tick holds the one connection,
    with the cache answering as it stands underneath it.
    """

    url = f"{BRIDGE_URL_PREFIX}/recenthistory"
    name = "api:midnite:recenthistory"

    async def get(self, request: Any, entry_id: str):
        """Answer the collected samples from the cache; no PIN, no wire."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        return self.json(bridge.bridge_recent_history(coordinator).as_dict())


class MidniteRecentHistoryRefreshView(MidniteBridgeView):
    """POST - "collect now": a tick on the Classic's one connection.

    It READS, but every collection is a monopoly (however brief) on the
    single Modbus connection the live poll and every write share, so an open
    bridge would let any LAN device stall the poll by spamming it - the
    datalogger refresh's reasoning, verbatim. The background collector beats
    without anyone asking and the GET answers from the cache meanwhile, so
    nobody needs to POST this for the chart to fill. A POST that arrives
    while a collection is in flight JOINS it (answers the cache, flagged
    `collecting`) instead of stampeding a second one onto the wire.
    """

    url = f"{BRIDGE_URL_PREFIX}/recenthistory/refresh"
    name = "api:midnite:recenthistory-refresh"

    async def post(self, request: Any, entry_id: str):
        """Answer the collection through the PIN gate."""
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        answer = await bridge.async_bridge_recent_history(
            request.app["hass"], coordinator
        )
        return self.json(answer)


BRIDGE_VIEWS = (
    MidniteStateView,
    MidnitePinView,
    MidniteWriteView,
    MidniteNetworkView,
    MidniteClockView,
    MidniteRebootView,
    MidniteEepromSaveView,
    MidniteDataloggerView,
    MidniteDataloggerRefreshView,
    MidniteRecentHistoryView,
    MidniteRecentHistoryRefreshView,
)
