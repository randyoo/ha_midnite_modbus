"""Support for the Midnite Solar binary_sensor platform: the read-only Info Flags.

The map gives "4130 4131 R InfoFlagsBits (InfoFlagsBits2) ([4131] << 16) + [4130],
See Table 4130-1 (read as 32 bits or singly)". Each flag becomes an entity so a
fault is visible in the dashboard and in automations instead of being buried in a
bit field nobody reads.

One of them matters more than the others: SerialWriteLock means the Classic is
ignoring the writes this integration sends, and UNLockJumperF says whether the
hardware jumper that bypasses the Ethernet write protect is missing.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import MidniteBaseEntityDescription
from .const import DOMAIN, INFO_FLAGS, NETWORK_FLAGS, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator
from .register_values import combine32, info_flag_set

_LOGGER = logging.getLogger(__name__)

# Table 4130-1 flag -> (entity name, enabled by default, is a fault).
# Faults are enabled because nobody wants to learn about an arc fault by
# digging through disabled entities; the rest are diagnostics that can be
# switched on where they are wanted.
FLAG_ENTITIES = {
    "ClassicOverTemp": ("Classic Over Temperature", True, True),
    "EepromError": ("EEPROM Error", True, True),
    "SerialWriteLock": ("Ethernet Writes Locked", True, True),
    "EqualizeInProgress": ("Equalizing", False, False),
    "EQMppt": ("EQ MPPT", False, False),
    "InVLowerThanOut": ("PV Voltage Below Battery", False, False),
    "CurrentLimit": ("Current Limit Reached", True, True),
    "HyperVoc": ("HyperVoc Active", False, False),
    "BattTempSensorInstalled": ("Battery Temperature Sensor Installed", False, False),
    "Aux1StateOn": ("Aux 1 On", False, False),
    "Aux2StateOn": ("Aux 2 On", False, False),
    "GroundFaultF": ("Ground Fault", True, True),
    "OCP": ("Over Current Protection", True, True),
    "ArcFaultF": ("Arc Fault", True, True),
    "NegBatCurrentF": ("Negative Battery Current", True, True),
    "XtraInfo2DsplayF": ("Extra Info Available", False, False),
    "PvPartialShadeF": ("Partial Shade Detected", False, False),
    "WatchdogResetF": ("Watchdog Reset", False, False),
    "LowBatteryVF": ("Very Low Battery", True, True),
    "StackumperF": ("Stack Jumper Missing", False, False),
    "EqDoneF": ("Equalize Finished", False, False),
    "TempCompShortedF": ("Temperature Compensation Shorted", True, True),
    "UNLockJumperF": ("Write Protect Jumper Not Installed", False, False),
    "XtraJumperF": ("Extra Jumper Missing", False, False),
    "InputShortedF": ("PV Input Shorted", True, True),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar binary sensors from Table 4130-1."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        InfoFlagBinarySensor(coordinator, entry, flag) for flag in FLAG_ENTITIES
    )
    async_add_entities(
        NetworkFlagBinarySensor(coordinator, entry, flag) for flag in NETWORK_FLAG_ENTITIES
    )


class InfoFlagBinarySensor(CoordinatorEntity[MidniteSolarUpdateCoordinator], BinarySensorEntity):
    """One Info Flag Bit from Table 4130-1."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, flag: str):
        """Initialize the binary sensor for one flag."""
        super().__init__(coordinator)
        self._entry = entry
        self._flag = flag
        name, enabled, is_fault = FLAG_ENTITIES[flag]
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_flag_{flag.lower()}"
        self._attr_entity_registry_enabled_default = enabled
        if is_fault:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    @property
    def info_flags(self) -> Optional[int]:
        """Return the 32 Info Flags, or None while they are not readable."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return None
        group = self.coordinator.data["data"].get("info_flags")
        if not group:
            return None
        low = group.get(REGISTER_MAP["INFO_FLAGS_LOW"])
        high = group.get(REGISTER_MAP["INFO_FLAGS_HIGH"])
        if low is None or high is None:
            return None
        return combine32(low, high)

    @property
    def is_on(self) -> Optional[bool]:
        """Return True if the flag is set."""
        flags = self.info_flags
        if flags is None:
            return None
        return info_flag_set(flags, INFO_FLAGS[self._flag])

    @property
    def extra_state_attributes(self) -> dict[str, Optional[int]]:
        """Return the raw flag words, so a flag can be decoded without HA."""
        flags = self.info_flags
        return {"info_flags": flags if flags is not None else None}


# Table 20481-1 has two flags, and one of them explains the other network
# registers: with DHCP set, the address registers are read-only as far as the
# Classic is concerned.
NETWORK_FLAG_ENTITIES = {
    "DHCP": ("DHCP Enabled", True),
    "WebAccess": ("MyMidnite Web Access", False),
}


class NetworkFlagBinarySensor(CoordinatorEntity[MidniteSolarUpdateCoordinator], BinarySensorEntity):
    """One flag from Table 20481-1, register 20481."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any, flag: str):
        """Initialize the binary sensor for one network flag."""
        super().__init__(coordinator)
        self._entry = entry
        self._flag = flag
        name, enabled = NETWORK_FLAG_ENTITIES[flag]
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_network_flag_{flag.lower()}"
        self._attr_entity_registry_enabled_default = enabled

    @property
    def device_info(self):
        """Return the device info the base class builds for every platform."""
        return MidniteBaseEntityDescription.get_device_info(
            self.coordinator, self._entry, DOMAIN
        )

    @property
    def is_on(self) -> Optional[bool]:
        """Return True if the flag is set."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return None
        group = self.coordinator.data["data"].get("network")
        if not group:
            return None
        value = group.get(REGISTER_MAP["IP_SETTINGS_FLAGS"])
        if value is None:
            return None
        return info_flag_set(value, NETWORK_FLAGS[self._flag])

    @property
    def extra_state_attributes(self) -> dict:
        """The raw register, so the flags can be checked without Home Assistant."""
        if not self.coordinator.data or "data" not in self.coordinator.data:
            return {}
        group = self.coordinator.data["data"].get("network") or {}
        return {"ip_settings": group.get(REGISTER_MAP["IP_SETTINGS_FLAGS"])}
