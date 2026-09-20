"""Home Assistant config entry objects used by the integration."""


class ConfigEntry:
    """Minimal config entry."""

    def __init__(self, entry_id="entry", title="Classic", data=None, options=None):
        self.entry_id = entry_id
        self.title = title
        self.data = data or {}
        self.options = options or {}
        self.unique_id = entry_id
        self.version = 1
        self.runtime_data = None


class ConfigFlow:
    """Minimal config flow base class."""

    def __init__(self, *args, **kwargs):
        self.hass = None
        self._async_current_ids = lambda: set()
        self._async_current_entries = lambda: []

    async def async_set_progress(self, *args, **kwargs):
        """No-op."""

    def async_show_form(self, *args, **kwargs):
        return {"type": "form", **kwargs}

    def async_show_progress(self, *args, **kwargs):
        return {"type": "progress", **kwargs}

    def async_create_entry(self, *args, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, *args, **kwargs):
        return {"type": "abort", **kwargs}

    async def async_update_reload_and_abort(self, *args, **kwargs):
        """No-op."""


ConfigFlowResult = dict
