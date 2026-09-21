"""Home Assistant select platform objects."""

from homeassistant.helpers.entity import Entity


class SelectEntity(Entity):
    """Minimal select entity."""

    @property
    def current_option(self):
        return getattr(self, "_attr_current_option", None)

    @property
    def options(self):
        return getattr(self, "_attr_options", [])

    @property
    def state(self):
        # Home Assistant's real SelectEntity.state (core select/__init__.py) is
        # final and returns None unless current_option is one of options. Without
        # it the double is blinder than HA: a "display-only" current_option that is
        # not in the option list renders as `unknown` on a real dashboard, and the
        # suite has to be able to see that.
        current = self.current_option
        return current if current is not None and current in self.options else None
