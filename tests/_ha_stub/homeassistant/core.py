"""Home Assistant core objects used by the integration."""


class ConfigEntries:
    """The part of Home Assistant that owns config entries.

    Updates and reloads are recorded so a test can assert what a flow did to an
    existing entry instead of only what it returned.
    """

    def __init__(self, hass):
        self.hass = hass
        self.updates = []
        self.reloads = []

    async def async_forward_entry_setups(self, entry, platforms):
        """No-op forward."""

    async def async_unload_platforms(self, entry, platforms):
        """No-op unload."""
        return True

    async def async_update_entry(self, entry, *, data=None, options=None, unique_id=None):
        """Apply the change the way Home Assistant would."""
        if data is not None:
            entry.data = data
        if options is not None:
            entry.options = options
        if unique_id is not None:
            entry.unique_id = unique_id
        self.updates.append((entry.entry_id, data, options))
        return True

    async def async_reload(self, entry_id):
        self.reloads.append(entry_id)

    async def async_add(self, domain, **kwargs):
        """No-op add."""


class Hass:
    """Records executor jobs so a test can assert what reached the wire."""

    def __init__(self):
        self.executor_calls = []
        # Real Home Assistant keeps integrations' data here; __init__.py stores
        # the coordinator under hass.data[DOMAIN][entry_id].
        self.data = {}
        self.config_entries = ConfigEntries(self)

    async def async_add_executor_job(self, target, *args):
        """Run the blocking Modbus call inline and remember it."""
        self.executor_calls.append((target, args))
        return target(*args)

    def async_create_task(self, coro):
        """Return the coroutine so tests can await it themselves."""
        return coro


HomeAssistant = Hass
