"""Every entity the integration creates, checked in one pass.

This is the audit that catches the mistakes a per-platform test misses: a unique_id
that was never set, two entities that claim the same one, a sensor that looks in a
register group it is never polled into, a platform that kept its own copy of the
device identity. Each of those happened somewhere in this code before.

The trick is the zeroed Classic: every register in every polled group is given a
value of 0, and then every entity is asked for its value. An entity that reads a
register nobody polls has nothing to read and returns None - which is precisely how
the Aux thresholds stayed invisible while being read every interval.
"""

from __future__ import annotations

import asyncio
import importlib

import pytest
from fakes import FakeApi, FakeCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Hass

from midnite_solar.base import MidniteBaseEntityDescription
from midnite_solar.const import DOMAIN, REGISTER_GROUPS, REGISTER_MAP

PLATFORMS = ("sensor", "binary_sensor", "number", "select", "text", "button")

ENTITIES_PER_PLATFORM = {
    "sensor": 45,
    "binary_sensor": 27,  # 25 Info Flags + 2 Network Settings Flags
    "number": 60,
    "select": 7,
    "text": 1,
    "button": 5,
}
ENABLED_BY_DEFAULT = 65


async def _build():
    """Set up all six platforms against a zeroed Classic."""
    hass = Hass()
    entry = ConfigEntry(entry_id="entry-1", title="Classic 200")
    groups = {
        group: {address: 0 for address in registers}
        for group, registers in REGISTER_GROUPS.items()
    }
    coordinator = FakeCoordinator(hass, FakeApi(), groups)
    coordinator.hass = hass
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entities: list[tuple[str, object]] = []
    for platform in PLATFORMS:
        module = importlib.import_module(f"midnite_solar.{platform}")

        def add(new_entities, _platform=platform):
            for entity in new_entities:
                entity.hass = hass
                entities.append((_platform, entity))

        await module.async_setup_entry(hass, entry, add)
    return entities, coordinator, entry


@pytest.fixture(scope="module")
def built():
    return asyncio.run(_build())


@pytest.fixture(scope="module")
def entities(built):
    return built[0]


def value_of(platform, entity):
    """Ask an entity for whatever it shows, using that platform's property."""
    if platform == "binary_sensor":
        return entity.is_on
    if platform == "select":
        return entity.current_option
    if platform == "button":
        return "button"
    return entity.native_value


def declared_registers(entity):
    """Every register an entity declares, under whichever attribute it uses."""
    found = []
    for attribute in ("register_address", "low_address", "high_address", "version_address"):
        value = getattr(entity, attribute, None)
        if isinstance(value, int):
            found.append(value)
    return found


class TestCounts:
    """Pinned so adding or losing an entity is a decision, not an accident."""

    def test_each_platform_makes_the_entities_it_should(self, entities):
        made = {platform: 0 for platform in PLATFORMS}
        for platform, _entity in entities:
            made[platform] += 1
        assert made == ENTITIES_PER_PLATFORM

    def test_the_integration_offers_145_entities(self, entities):
        assert len(entities) == sum(ENTITIES_PER_PLATFORM.values())

    def test_65_of_them_are_on_without_being_asked_for(self, entities):
        enabled = [entity for _platform, entity in entities if entity.entity_registry_enabled_default]
        assert len(enabled) == ENABLED_BY_DEFAULT


class TestIdentity:
    def test_no_entity_is_created_without_a_unique_id(self, entities):
        missing = [
            f"{platform} {type(entity).__name__}"
            for platform, entity in entities
            if not entity.unique_id
        ]
        assert missing == [], "an entity with no unique_id cannot be renamed or enabled"

    def test_no_unique_id_is_claimed_twice(self, entities):
        seen = {}
        duplicates = []
        for platform, entity in entities:
            unique_id = entity.unique_id
            if unique_id in seen:
                duplicates.append(f"{unique_id}: {seen[unique_id]} and {platform}")
            else:
                seen[unique_id] = platform
        assert duplicates == []

    def test_every_unique_id_is_scoped_to_the_config_entry(self, entities):
        wrong = [entity.unique_id for _platform, entity in entities if not entity.unique_id.startswith("entry-1_")]
        assert wrong == [], "two Classic on one Home Assistant must not collide"

    def test_no_two_entities_share_a_name(self, entities):
        seen = {}
        duplicates = []
        for platform, entity in entities:
            if entity.name in seen:
                duplicates.append(f"{entity.name}: {seen[entity.name]} and {platform}")
            else:
                seen[entity.name] = platform
        assert duplicates == []


class TestWiring:
    """The value of an entity has to come from a register that is polled."""

    def test_every_entity_reports_something_on_a_zeroed_classic(self, entities):
        silent = [
            f"{platform} {entity.unique_id} -> {value_of(platform, entity)!r}"
            for platform, entity in entities
            if value_of(platform, entity) is None
        ]
        assert silent == [], (
            "every register the integration polls was given a value, so an entity "
            "with nothing to show is reading somewhere that is never read"
        )

    def test_every_declared_register_is_polled(self, entities):
        polled = set().union(*[set(registers) for registers in REGISTER_GROUPS.values()])
        unpolled = [
            f"{entity.unique_id} reads {address}"
            for _platform, entity in entities
            for address in declared_registers(entity)
            if address not in polled
        ]
        assert unpolled == []

    def test_every_register_an_entity_declares_is_one_const_names(self, entities):
        """An entity must not read a bare number that const.py does not name."""
        named = set(REGISTER_MAP.values())
        for _platform, entity in entities:
            for address in declared_registers(entity):
                assert address in named, f"{entity.unique_id} reads {address}, which const.py does not name"


class TestDeviceIdentity:
    def test_no_platform_keeps_its_own_copy_of_the_device_info(self, entities, built):
        _entities, coordinator, entry = built
        expected = MidniteBaseEntityDescription.get_device_info(coordinator, entry, DOMAIN)
        different = [
            entity.unique_id
            for _platform, entity in entities
            if entity.device_info != expected
        ]
        assert different == []

    def test_the_device_carries_a_serial_number(self, entities):
        info = next(entity.device_info for _platform, entity in entities)
        assert "serial_number" in info
        assert info["manufacturer"] == "Midnite Solar"


class TestFaultFlagsAreVisible:
    """The point of the binary sensors: a fault must not need a forum post to find."""

    def test_the_write_protect_sensor_is_on_by_default(self, entities):
        entity = next(
            entity for _platform, entity in entities
            if entity.unique_id == "entry-1_flag_serialwritelock"
        )
        assert entity.entity_registry_enabled_default is True

    @pytest.mark.parametrize(
        "unique_id",
        [
            "entry-1_flag_classicovertemp",
            "entry-1_flag_eepromerror",
            "entry-1_flag_groundfaultf",
            "entry-1_flag_ocp",
            "entry-1_flag_arcfaultf",
            "entry-1_flag_negbatcurrentf",
            "entry-1_flag_lowbatteryvf",
            "entry-1_flag_inputshortedf",
            "entry-1_flag_tempcompshortedf",
        ],
    )
    def test_a_fault_flag_is_enabled(self, entities, unique_id):
        entity = next(entity for _platform, entity in entities if entity.unique_id == unique_id)
        assert entity.entity_registry_enabled_default is True
