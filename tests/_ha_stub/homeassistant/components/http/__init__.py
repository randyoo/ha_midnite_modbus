"""Test double for the http component's view machinery (no aiohttp, no server).

Only the surface the bridge views and bridge.ensure_bridge_views use:
the HomeAssistantView base with `requires_auth`/`url`/`name`/`json`, and a
`hass.http` object that records registered views. Nothing listens on a
socket: tests call the view coroutines directly, as every other platform
double here is driven.
"""

from __future__ import annotations

import json


class ViewResponse:
    """Stands in for the aiohttp Response `self.json` builds.

    Parity (pinned in test_fakes.py): a real Response carries the JSON body
    as text plus the status code, so this serialises eagerly - a view that
    handed back something unserialisable fails here the way aiohttp would
    fail it on the wire.
    """

    def __init__(self, body, status_code=200):
        self.body = body
        self.text = json.dumps(body)
        self.status = status_code


class HomeAssistantView:
    """The base class the bridge views subclass."""

    url = None
    name = None
    requires_auth = False

    def json(self, msg, status_code=200, **kwargs):
        return ViewResponse(msg, status_code)


class Http:
    """The `hass.http` object: a recorder of registered views."""

    def __init__(self):
        self.views = []

    def register_view(self, view):
        self.views.append(view)
