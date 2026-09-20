"""Support for Midnite Solar select platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import MidniteBaseEntityDescription

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .const import (
    AUX_OFF_AUTO_ON,
    AUX1_FUNCTIONS,
    AUX2_FUNCTIONS,
    AUX_FIELDS,
    DOMAIN,
    FORCE_FLAGS,
    MPPT_MODES,
    REGISTER_MAP,
)
from .coordinator import MidniteSolarUpdateCoordinator
from .entity_writes import (
    async_store_settings,
    async_verify_write,
    async_write_setting,
    register_value,
)
from .register_values import force_flag_write, read_field, write_field

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar selectors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    selectors = [
        ChargeModeSelector(coordinator, entry),
        MPPTModeSelector(coordinator, entry),
        Aux1FunctionSelector(coordinator, entry),
        Aux2FunctionSelector(coordinator, entry),
        # Off / Auto / On for each output, so a forced On does not need the
        # function itself to be a manual one.
        Aux1StateSelect(coordinator, entry),
        Aux2StateSelect(coordinator, entry),
    ]
    
    async_add_entities(selectors)


class MidniteSolarSelect(CoordinatorEntity[MidniteSolarUpdateCoordinator], SelectEntity):
    """Base class for all Midnite Solar selectors."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Create device info - will be updated dynamically when data becomes available
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


class ChargeModeSelector(MidniteSolarSelect):
    """Selector for force charge mode control."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "Force Charge Mode"
        self._attr_unique_id = f"{entry.entry_id}_charge_mode_selector"
        self._attr_options = ["None", "Float", "Bulk", "Equalize"]

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        # Check which force flag is active by reading the charge stage
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract MSB (high byte) for charge stage
                    charge_stage_value = (raw_value >> 8) & 0xFF
                    
                    # Map charge stages to mode names
                    if charge_stage_value == 5:  # Float
                        return "Float"
                    elif charge_stage_value == 4:  # BulkMPPT
                        return "Bulk"
                    elif charge_stage_value == 7:  # Equalize
                        return "Equalize"
        
        return "None"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "None":
            _LOGGER.info("Force charge mode control: No action")
            return
        
        # Map option to force flag
        flag_map = {
            "Float": FORCE_FLAGS["ForceFloat"],
            "Bulk": FORCE_FLAGS["ForceBulk"],
            "Equalize": FORCE_FLAGS["ForceEqualize"],
        }
        
        if option not in flag_map:
            raise HomeAssistantError(f"{option} is not a charge mode that can be forced")
        flag_bit = flag_map[option]
        flag_value = 1 << flag_bit
        # Table 4160-1 lists the flags as 32-bit values over two registers, so the
        # register is taken from the value rather than assumed to be 4160; and a
        # failed press has to raise, or Home Assistant shows a charge mode that the
        # Classic never accepted.
        register, word = force_flag_write(flag_value)
        await async_write_setting(self.hass, self.coordinator.api, register, word, f"Force {option}")
        await self.coordinator.async_request_refresh()




class MidniteSolarSettingSelect(MidniteSolarSelect):
    """Base for selects that write a setting the register map marks (EE)."""

    async def _async_write(self, address: int, value: int, label: str) -> None:
        """Write the setting, store it in EEPROM, then refresh."""
        await async_write_setting(self.hass, self.coordinator.api, address, value, label)
        await async_store_settings(self.hass, self.coordinator.api, label)
        await async_verify_write(
            self.hass,
            self.coordinator.api,
            address,
            value,
            label,
            lambda raw: f"0x{raw:04X}",
        )
        await self.coordinator.async_request_refresh()


# Table 4164-1: "Bit 0 is the ON/OFF (Enable/Disable) ... if 0x0000 MPPT mode is OFF".
MPPT_OFF = "MPPT Off"


class MPPTModeSelector(MidniteSolarSettingSelect):
    """Selector for MPPT mode control."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "MPPT Mode"
        self._attr_unique_id = f"{entry.entry_id}_mppt_mode_selector"
        # The RESERVED rows of Table 4164-1 are not modes and are not offered.
        self._attr_options = [
            name for name in MPPT_MODES.values() if name != "RESERVED"
        ] + [MPPT_OFF]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Move to Diagnostics category
        self._attr_entity_registry_enabled_default = False  # Disable by default

    @property
    def current_option(self) -> Optional[str]:
        """Return the mode, marked "(Off)" when bit 0 is clear.

        Table 4164-1 lists the modes with MPPT enabled and says to "Subtract One
        (1) if showing mode as OFF", so an even register value is that mode with
        MPPT disabled, and 0x0000 is MPPT off altogether.
        """
        value = register_value(self.coordinator.data, "settings", REGISTER_MAP["MPPT_MODE"])
        if value is None:
            return None
        if value == 0:
            return MPPT_OFF
        name = MPPT_MODES.get(value | 1)
        if name is None:
            return f"Unknown (0x{value:04X})"
        return name if value % 2 else f"{name} (Off)"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == MPPT_OFF:
            value = 0
        else:
            value = next(
                (address for address, name in MPPT_MODES.items() if name == option), None
            )
            if value is None:
                raise HomeAssistantError(f"{option} is not a mode in Table 4164-1")
        await self._async_write(REGISTER_MAP["MPPT_MODE"], value, f"MPPT mode {option}")


class AuxFieldSelect(MidniteSolarSelect):
    """Base for every select that owns one field of the packed Aux register.

    The map packs both outputs into the one register 4165 and gives the decodes:
    "Aux1Function = Aux12Function & 0x3f;",
    "Aux1OffAutoOn = (((Aux12Function & 0xc0) >> 6));",
    "Aux2Function = (Aux12FunctionS & 0x3f00) >> 8;",
    "Aux2OffAutoOn = ((Aux12FunctionS & 0xc000) >> 14);".
    So any change here has to preserve the other six bits, which is why this
    refuses to write before the register has been read.
    """

    _field: str = ""
    _labels: dict[int, str] = {}
    # Values the Classic can report that a user cannot ask for.
    _unselectable: tuple = ()

    def _register(self) -> Optional[int]:
        """Return the current packed Aux register."""
        return register_value(
            self.coordinator.data, "aux_settings", REGISTER_MAP["AUX_1_AND_2_FUNCTION"]
        )

    @property
    def current_option(self) -> Optional[str]:
        """Return what this field of the register currently says."""
        value = self._register()
        if value is None:
            return None
        mask, shift = AUX_FIELDS[self._field]
        code = read_field(value, mask, shift)
        return self._labels.get(code, f"Unset ({code})")

    async def async_select_option(self, option: str) -> None:
        """Change this field, leaving every other field of 4165 alone."""
        code = next((value for value, name in self._labels.items() if name == option), None)
        if code is None:
            raise HomeAssistantError(f"{option} is not a value the register map gives")
        if code in self._unselectable:
            raise HomeAssistantError(
                f"{option} is something the Classic reports, not something it accepts"
            )
        current = self._register()
        if current is None:
            raise HomeAssistantError(
                f"Aux settings have not been read yet, so {option} cannot be set without "
                "clobbering the other Aux output"
            )
        mask, shift = AUX_FIELDS[self._field]
        new_value = write_field(current, mask, shift, code)
        await async_write_setting(
            self.hass,
            self.coordinator.api,
            REGISTER_MAP["AUX_1_AND_2_FUNCTION"],
            new_value,
            self.name,
        )
        await async_store_settings(self.hass, self.coordinator.api, self.name)
        await async_verify_write(
            self.hass,
            self.coordinator.api,
            REGISTER_MAP["AUX_1_AND_2_FUNCTION"],
            new_value,
            self.name,
            lambda raw: f"0x{raw:04X}",
        )
        await self.coordinator.async_request_refresh()


class AuxFunctionSelect(AuxFieldSelect):
    """Base for the two function selects, Tables 4165-3 and 4165-4."""


class AuxStateSelect(AuxFieldSelect):
    """Base for the Off / Auto / On selects, Tables 4165-1 and 4165-2.

    Value 3 is "Unimplemented" in the map, so it is a thing the Classic can report
    but not a thing a user can ask for; it is left out of the options.
    """

    _labels = AUX_OFF_AUTO_ON
    _unselectable = (3,)


class Aux1FunctionSelector(AuxFunctionSelect):
    """Selector for AUX 1 function control, Table 4165-3 in bits 0-5."""

    _field = "aux1_function"
    _labels = AUX1_FUNCTIONS

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX 1 Function"
        self._attr_unique_id = f"{entry.entry_id}_aux1_function_selector"
        self._attr_options = list(AUX1_FUNCTIONS.values())
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default


class Aux2FunctionSelector(AuxFunctionSelect):
    """Selector for AUX 2 function control, Table 4165-4 in bits 8-13."""

    _field = "aux2_function"
    _labels = AUX2_FUNCTIONS

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX 2 Function"
        self._attr_unique_id = f"{entry.entry_id}_aux2_function_selector"
        self._attr_options = list(AUX2_FUNCTIONS.values())
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = False  # Disable by default


class Aux1StateSelect(AuxStateSelect):
    """Off / Auto / On for AUX 1: bits 6-7, Table 4165-1."""

    _field = "aux1_mode"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX 1 State"
        self._attr_unique_id = f"{entry.entry_id}_aux1_state_select"
        self._attr_options = [
            name for code, name in self._labels.items() if code not in self._unselectable
        ]
        self._attr_entity_category = EntityCategory.CONFIG


class Aux2StateSelect(AuxStateSelect):
    """Off / Auto / On for AUX 2: bits 14-15, Table 4165-2."""

    _field = "aux2_mode"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the selector."""
        super().__init__(coordinator, entry)
        self._attr_name = "AUX 2 State"
        self._attr_unique_id = f"{entry.entry_id}_aux2_state_select"
        self._attr_options = list(self._labels.values())
        self._attr_entity_category = EntityCategory.CONFIG
