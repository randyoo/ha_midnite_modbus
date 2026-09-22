"""Test double for homeassistant.helpers.network.

`get_url` answers with a canned address instead of reading HA's own network
settings: the advertiser's job in the suite is to prove what it puts in the
record, not to resolve a home network. Point a test at another answer by
storing `hass.data["network_stub_url"]`.
"""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

STUB_URL = "http://192.168.50.5:8123"


class NoURLAvailableError(HomeAssistantError):
    """Raised when no URL is known; core defines it under this name."""


def get_url(hass, **kwargs):
    """Return the canned URL, or the per-test override."""
    return hass.data.get("network_stub_url", STUB_URL)
