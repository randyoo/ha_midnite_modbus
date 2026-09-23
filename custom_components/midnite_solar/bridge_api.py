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

import logging
from datetime import datetime
from typing import Any, Optional, Tuple

from homeassistant.components.http import HomeAssistantView
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import bridge
from .const import BRIDGE_URL_PREFIX, DOMAIN, PIN_HEADER

_LOGGER = logging.getLogger(__name__)


class MidniteBridgeView(HomeAssistantView):
    """Shared plumbing: find the entry's coordinator, answer in JSON."""

    # Open by design: no Home Assistant token. Reads are public to the LAN;
    # every WRITE is gated on the entry's PIN (pin_gate below), so the token
    # was doing nothing the PIN does not do better and specific to the MPPT.
    requires_auth = False

    def coordinator_for(self, request: Any, entry_id: str) -> Optional[Any]:
        return request.app["hass"].data.get(DOMAIN, {}).get(entry_id)

    def missing_entry(self, entry_id: str):
        return self.json(
            {"error": f"no Midnite Solar entry {entry_id}"}, status_code=404
        )

    def refused(self, error: Exception):
        return self.json({"error": str(error)}, status_code=400)

    async def body(self, request: Any) -> Tuple[Optional[dict], Any]:
        """(body, error_response): a JSON object, or the answer to give."""
        try:
            body = await request.json()
        except Exception:
            return None, self.json(
                {"error": "the body must be a JSON object"}, status_code=400
            )
        if not isinstance(body, dict):
            return None, self.json(
                {"error": "the body must be a JSON object"}, status_code=400
            )
        return body, None

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
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        body, error = await self.body(request)
        if error is not None:
            return error
        presented = body.get("pin")
        if not isinstance(presented, str):
            # A probe with no pin field is a malformed request, not a guess:
            # answer 400 WITHOUT consulting the gate, so a client that posts
            # empty bodies cannot spend anyone's lockout ladder.
            return self.json({"error": "the probe needs a pin as text"}, status_code=400)
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
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        body, error = await self.body(request)
        if error is not None:
            return error
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


class MidniteClockView(MidniteBridgeView):
    """POST {"time": ISO 8601} - set the Classic's clock the app's way."""

    url = f"{BRIDGE_URL_PREFIX}/clock"
    name = "api:midnite:clock"

    async def post(self, request: Any, entry_id: str):
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        body, error = await self.body(request)
        if error is not None:
            return error
        raw = body.get("time")
        if not isinstance(raw, str):
            return self.json(
                {"error": "the clock needs a time as ISO 8601 text"}, status_code=400
            )
        try:
            when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return self.json(
                {"error": f"{raw!r} is not ISO 8601 time"}, status_code=400
            )
        if when.tzinfo is not None:
            when = dt_util.as_local(when)
        try:
            answer = await bridge.async_bridge_clock(request.app["hass"], coordinator, when)
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
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        refused = self.pin_gate(request, coordinator)
        if refused is not None:
            return refused
        answer = await bridge.async_bridge_datalogger(request.app["hass"], coordinator)
        return self.json(answer)


BRIDGE_VIEWS = (
    MidniteStateView,
    MidnitePinView,
    MidniteWriteView,
    MidniteClockView,
    MidniteRebootView,
    MidniteEepromSaveView,
    MidniteDataloggerView,
    MidniteDataloggerRefreshView,
)
