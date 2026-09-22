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
        self._on_unload = []

    def add_update_listener(self, listener):
        """Register a listener and return the unsubscribe callable, as HA does."""
        self._update_listeners.append(listener)
        return lambda: self._update_listeners.remove(listener)

    def async_on_unload(self, callback):
        """Queue a cleanup run on unload, as HA's ConfigEntry.async_on_unload does."""
        self._on_unload.append(callback)

    def async_test_unload(self):
        """Run the queued unload cleanups, the way HA does on unload/reload."""
        callbacks, self._on_unload = self._on_unload, []
        for callback in callbacks:
            callback()


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

    @staticmethod
    def async_get_options_flow(config_entry):
        """Base options-flow hook; real Home Assistant raises UnknownHandler.

        Integrations override this ON THE CLASS. Home Assistant's
        `supports_options` is `handler.async_supports_options_flow(entry)`, which
        only reports True when this hook is overridden on the subclass, so the
        double must carry the base method for the check to mean anything.
        """
        raise NotImplementedError("this handler has no options flow")

    @classmethod
    def async_supports_options_flow(cls, config_entry):
        """Mirror real Home Assistant's parity gate (config_entries.py, 2026.9).

        `supports_options` is decided here, by class identity, NOT by the presence
        of a module-level `async_get_options_flow`. An integration that only has
        the module-level function passes a double without this gate yet reports
        `supports_options=False` in real Home Assistant - the bug that hid the
        bridge toggle from the Flutter app (2026-09-22).
        """
        return cls.async_get_options_flow is not ConfigFlow.async_get_options_flow

    def _async_current_entries(self):
        """The entries Home Assistant already has for this domain."""
        return list(self._entries)

    def _async_current_ids(self):
        return {entry.unique_id for entry in self._entries if entry.unique_id}

    async def async_set_progress(self, *args, **kwargs):
        """No-op."""

    async def async_set_unique_id(self, unique_id, raise_on_progress=True):
        """Claim a unique id for the flow in progress.

        Home Assistant core RETURNS the already-configured entry with that
        unique id (None otherwise); the integration uses that return to refuse
        adding the same Classic twice, so the double has to answer too.
        """
        self.unique_id = unique_id
        if unique_id is None:
            return None
        for entry in self._entries:
            if entry.unique_id == unique_id:
                return entry
        return None

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
        """Compare the two unique ids exactly as core does.

        Core compares `entry.unique_id != self.unique_id` - it does NOT abort
        when both are None (None != None is False), which is what lets a legacy
        manual entry with no unique id still be reconfigured.
        """
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
    """Minimal options flow base class.

    Home Assistant 2026.9 makes `config_entry` a READ-ONLY property (resolved
    from `handler`). Assigning `self.config_entry = config_entry` in `__init__`
    therefore raises "property has no setter" in real Home Assistant - the exact
    cause of the options dialog's HTTP 500 (2026-09-22). The double reproduces
    that property trap so the bug can never come back unnoticed: any integration
    that assigns to `config_entry` now fails the suite the same way it fails
    live. Read it back here only via a subclass that stored its own attribute.
    """

    def __init__(self, *args, **kwargs):
        self._stub_entry = kwargs.get("config_entry") or (args[0] if args else None)

    @property
    def config_entry(self):
        return getattr(self, "_stub_entry", None)

    async def async_step_init(self, user_input=None):
        raise NotImplementedError

    def async_show_form(self, *args, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, *args, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, *args, **kwargs):
        return {"type": "abort", **kwargs}


ConfigFlowResult = dict
