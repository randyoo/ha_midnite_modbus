"""Home Assistant core objects used by the integration."""


class Hass:
    """Records executor jobs so a test can assert what reached the wire."""

    def __init__(self):
        self.executor_calls = []
        # Real Home Assistant keeps integrations' data here; __init__.py stores
        # the coordinator under hass.data[DOMAIN][entry_id].
        self.data = {}

    async def async_add_executor_job(self, target, *args):
        """Run the blocking Modbus call inline and remember it."""
        self.executor_calls.append((target, args))
        return target(*args)

    def async_create_task(self, coro):
        """Return the coroutine so tests can await it themselves."""
        return coro

    class config_entries:
        @staticmethod
        async def async_forward_entry_setups(entry, platforms):
            """No-op forward."""

        @staticmethod
        async def async_unload_platforms(entry, platforms):
            """No-op unload."""


HomeAssistant = Hass
