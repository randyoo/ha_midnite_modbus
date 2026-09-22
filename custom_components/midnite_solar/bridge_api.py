"""The HTTP face of the bridge: what a desktop app calls.

Every answer here is one engine call in bridge.py, the way a platform file
is one entity_writes call: no decoding and no register maths in the view.
The views are registered once per Home Assistant (see
bridge.ensure_bridge_views) and look the entry's coordinator up per request,
so a reload never stacks a second route and an unloaded entry gets a clean
404.

Auth is Home Assistant's own: `requires_auth` makes the core middleware
check the Authorization header, so a desktop app signs its calls with a
long-lived access token from the user's HA profile page - the same
credential every other /api caller uses. Enabling the bridge option opens
nothing that a token cannot also close.

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
from .const import BRIDGE_URL_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MidniteBridgeView(HomeAssistantView):
    """Shared plumbing: find the entry's coordinator, answer in JSON."""

    # No anonymous MPPT writes on the LAN, ever.
    requires_auth = True

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


class MidniteStateView(MidniteBridgeView):
    """GET /api/midnite/{entry_id}/state - the last poll, no wire touched."""

    url = f"{BRIDGE_URL_PREFIX}/state"
    name = "api:midnite:state"

    async def get(self, request: Any, entry_id: str):
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        return self.json(bridge.build_snapshot(coordinator))


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
        try:
            answer = await bridge.async_bridge_eeprom_save(
                request.app["hass"], coordinator
            )
        except HomeAssistantError as e:
            return self.refused(e)
        return self.json(answer)


class MidniteDataloggerView(MidniteBridgeView):
    """GET - the last swept days (empty until the first refresh)."""

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
    time, so this takes a few seconds and the state never goes stale over
    it; the reply is the full dated answer.
    """

    url = f"{BRIDGE_URL_PREFIX}/datalogger/refresh"
    name = "api:midnite:datalogger-refresh"

    async def post(self, request: Any, entry_id: str):
        coordinator = self.coordinator_for(request, entry_id)
        if coordinator is None:
            return self.missing_entry(entry_id)
        answer = await bridge.async_bridge_datalogger(request.app["hass"], coordinator)
        return self.json(answer)


BRIDGE_VIEWS = (
    MidniteStateView,
    MidniteWriteView,
    MidniteClockView,
    MidniteRebootView,
    MidniteEepromSaveView,
    MidniteDataloggerView,
    MidniteDataloggerRefreshView,
)
