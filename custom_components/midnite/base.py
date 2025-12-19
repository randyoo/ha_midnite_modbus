"""Module defines entity descriptions for Midnite Solar components."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.typing import StateType


@dataclass
class MidniteBaseEntityDescription(EntityDescription):
    """An extension of EntityDescription for Midnite Solar components."""

    @staticmethod
    def lambda_func():
        """Return an entitydescription."""
        return lambda coordinator, address: coordinator.get_register_value(address)

    value_fn: Callable[[dict], StateType] = lambda_func()
