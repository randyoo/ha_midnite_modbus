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
        self._update_listeners = []

    def add_update_listener(self, listener):
        """Register a listener and return the unsubscribe callable, as HA does."""
        self._update_listeners.append(listener)
        return lambda: self._update_listeners.remove(listener)


class AbortFlow(Exception):
    """Raised by the abort helpers, as homeassistant.data_entry_flow does."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class ConfigFlow:
    """Minimal config flow base class."""

    def __init_subclass__(cls, domain=None, **kwargs):
        """Home Assistant passes the domain to the flow class."""
        super().__init_subclass__(**kwargs)
        cls.VERSION = 1
        if domain:
            cls._hass_domain = domain

    def __init__(self, *args, **kwargs):
        self.hass = None
        self.context = {}
        self.unique_id = None
        self._entries = []
        self._reconfigure_entry = None

    def _async_current_entries(self):
        """The entries Home Assistant already has for this domain."""
        return list(self._entries)

    def _async_current_ids(self):
        return {entry.unique_id for entry in self._entries if entry.unique_id}

    async def async_set_progress(self, *args, **kwargs):
        """No-op."""

    async def async_set_unique_id(self, unique_id, raise_on_progress=True):
        """Claim a unique id for the flow in progress."""
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self, updates=None, **kwargs):
        """Abort if this device is already set up, updating its host if needed."""
        for entry in self._async_current_entries():
            if entry.unique_id != self.unique_id:
                continue
            if updates:
                entry.data.update(updates)
            raise AbortFlow("already_configured")

    def _async_abort_entries_match(self, match_dict):
        """Abort if an entry already has exactly this host and port."""
        for entry in self._async_current_entries():
            if all(entry.data.get(key) == value for key, value in match_dict.items()):
                raise AbortFlow("already_configured")

    def _abort_if_unique_id_mismatch(self, **kwargs):
        if self._reconfigure_entry is not None and self._reconfigure_entry.unique_id != self.unique_id:
            raise AbortFlow("unique_id_mismatch")

    def _get_reconfigure_entry(self):
        return self._reconfigure_entry

    def _get_current_entries(self):
        return self._async_current_entries()

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


class OptionsFlow:
    """Minimal options flow base class."""

    def __init__(self, *args, **kwargs):
        self.config_entry = kwargs.get("config_entry") or (args[0] if args else None)

    async def async_step_init(self, user_input=None):
        raise NotImplementedError

    def async_show_form(self, *args, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, *args, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, *args, **kwargs):
        return {"type": "abort", **kwargs}


ConfigFlowResult = dict
