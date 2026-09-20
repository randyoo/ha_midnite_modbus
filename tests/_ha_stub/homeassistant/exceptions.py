"""Home Assistant exceptions used by the integration."""


class HomeAssistantError(Exception):
    """General error to raise to the user interface."""


class ConfigEntryNotReady(HomeAssistantError):
    """Raised when a config entry cannot be set up yet."""


class ConfigEntryError(HomeAssistantError):
    """Raised when a config entry is in error."""


class ConfigEntryAuthFailed(ConfigEntryError):
    """Raised when authentication failed."""


class UpdateFailed(HomeAssistantError):
    """Raised when an update has failed, defined here as Home Assistant does."""


class NoServiceInfo(Exception):
    """Raised when a discovery has no service info."""
