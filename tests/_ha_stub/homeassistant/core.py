"""Home Assistant core objects used by the integration."""

import asyncio
import inspect

from homeassistant.components.http import Http


def callback(func):
    """Stand-in for Home Assistant's `@callback`.

    The real decorator only marks a function as an event-loop callback (and
    asserts it in debug mode); it returns the function unchanged, so integrations
    can use it on sync methods. `config_flow.async_get_options_flow` carries it,
    so the double must provide it.
    """
    return func


class ConfigEntries:
    """The part of Home Assistant that owns config entries.

    Updates and reloads are recorded so a test can assert what a flow did to an
    existing entry instead of only what it returned.
    """

    def __init__(self, hass):
        self.hass = hass
        self.updates = []
        self.reloads = []
        self.forwarded = []
        self.unloaded = []

    async def async_forward_entry_setups(self, entry, platforms):
        """Record which platforms the integration set up."""
        self.forwarded.append((entry.entry_id, tuple(platforms)))

    async def async_unload_platforms(self, entry, platforms):
        """Record the unload and report success, as Home Assistant would."""
        self.unloaded.append((entry.entry_id, tuple(platforms)))
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
        # Real Home Assistant always runs the http component; the bridge's
        # views register on it, and the double only records them.
        self.http = Http()

    async def async_add_executor_job(self, target, *args):
        """Run the blocking Modbus call inline and remember it.

        A target that returns a coroutine is awaited, the way awaiting a real
        executor job waits for the thread to finish: that is what lets
        asyncio.wait_for time out a wedged operation in a test.
        """
        self.executor_calls.append((target, args))
        result = target(*args)
        if inspect.isawaitable(result):
            result = await result
        return result

    def async_create_task(self, coro):
        """Schedule a real asyncio Task, the way Home Assistant does.

        An integration's lifetime task (the bridge's datalogger collector)
        must be cancel()'d and done()-checkable, so returning the bare
        coroutine was a lie the day the integration grew one. Tests start
        under asyncio.run; the case's loop cancels whatever is still parked
        when it ends, so a lifetime task cannot leak or put wire traffic
        into an assertion - the collector parks on its warm-up sleep.
        """
        return asyncio.ensure_future(coro)


HomeAssistant = Hass
