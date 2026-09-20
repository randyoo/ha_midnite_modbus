"""Home Assistant data update coordinator objects."""

import logging
from typing import Any, Generic, TypeVar

from homeassistant.exceptions import UpdateFailed

from .entity import Entity

_DataT = TypeVar("_DataT")

__all__ = ["DataUpdateCoordinator", "CoordinatorEntity", "UpdateFailed"]


class DataUpdateCoordinator:
    """Minimal coordinator that only stores what the integration needs."""

    def __init__(self, hass, logger, *, name=None, update_interval=None, config_entry=None):
        self.hass = hass
        self.logger = logger or logging.getLogger(__name__)
        self.name = name
        self.update_interval = update_interval
        self.config_entry = config_entry
        self.data: Any = {}
        self.last_update_success = True

    async def async_request_refresh(self):
        """Record the refresh request."""
        self.refresh_requests = getattr(self, "refresh_requests", 0) + 1

    async def async_shutdown(self):
        """No-op shutdown."""

    async def async_add_listener(self, cb, alarm_type=None):
        """Return a callable that removes nothing."""
        return lambda: None

    async def _async_update_data(self):
        raise NotImplementedError


class CoordinatorEntity(Entity, Generic[_DataT]):
    """Entity that gets its state from a coordinator."""

    # The integration writes CoordinatorEntity[MidniteSolarUpdateCoordinator].
    __class_getitem__ = classmethod(lambda cls, item: cls)

    def __init__(self, coordinator=None):
        self.coordinator = coordinator
        self.hass = getattr(coordinator, "hass", None)

    @property
    def available(self):
        if self.coordinator is None:
            return False
        return getattr(self.coordinator, "last_update_success", True)
