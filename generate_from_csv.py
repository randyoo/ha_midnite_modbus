#!/usr/bin/env python3
"""
CSV-to-Python Generator Script for Midnite Solar Integration.

This script reads REGISTER_CATEGORIES.csv and generates:
1. const.py with REGISTER_MAP and REGISTER_CATEGORIES dictionaries
2. Entity definitions for sensor.py, number.py, select.py, etc.
"""

import csv
import sys
from collections import defaultdict
from typing import Dict, List, Any


def validate_csv(data: List[Dict[str, str]]) -> None:
    """Validate CSV data for completeness and consistency."""
    # Required fields - these must have values
    required_fields = [
        'Register Name', 'Address', 'Category', 'Entity Type', 
        'Icon', 'Description'
    ]
    
    # Optional fields - these can be empty
    optional_fields = ['Device Class', 'State Class', 'Unit', 'Precision']
    
    errors = []
    addresses = set()
    register_names = set()
    
    for i, row in enumerate(data, start=2):  # Start from 2 for header row
        # Check for missing required fields
        for field in required_fields:
            if not row.get(field):
                errors.append(f"Row {i}: Missing value for '{field}'")
        
        # Check for duplicate addresses
        address = row.get('Address')
        if address in addresses:
            errors.append(f"Row {i}: Duplicate address {address}")
        else:
            addresses.add(address)
        
        # Check for duplicate register names
        name = row.get('Register Name')
        if name in register_names:
            errors.append(f"Row {i}: Duplicate register name '{name}'")
        else:
            register_names.add(name)
    
    # Check that all addresses are unique integers
    try:
        for addr in addresses:
            int(addr)
    except ValueError:
        errors.append(f"Invalid address value: {addr}")
    
    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


def generate_const_py(data: List[Dict[str, str]], output_path: str) -> None:
    """Generate const.py file with REGISTER_MAP and REGISTER_CATEGORIES."""
    
    # Build REGISTER_MAP
    register_map = {}
    register_categories = {}
    
    for row in data:
        name = row['Register Name']
        address = int(row['Address'])
        category = row['Category']
        
        register_map[name] = address
        register_categories[name] = category
    
    # Sort by address for better readability
    sorted_registers = sorted(register_map.items(), key=lambda x: x[1])
    
    # Generate the file content
    content = '''"""Constants for the Midnite Solar integration."""

DOMAIN = "midnite_solar"

DEFAULT_PORT = 502
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15
CONF_ENABLE_ADVANCED = "enable_advanced"
CONF_ENABLE_DEBUG = "enable_debug"
CONF_ENABLE_WRITES = "enable_writes"

# Register categories for entity creation
# B = Basic (always enabled), A = Advanced (opt-in), D = Debug (opt-in)
REGISTER_CATEGORIES = {
'''
    
    # Add register categories in sorted order by name
    for name, category in sorted(register_categories.items()):
        content += f'    "{name}": "{category}",\n'
    
    content += '''}

# Register addresses from REGISTER_CATEGORIES.csv (sorted by address for easy reference)
REGISTER_MAP = {
'''
    
    # Add register map in sorted order by address
    for name, address in sorted_registers:
        content += f'    "{name}": {address},\n'
    
    content += '''}

# Charge stage mappings (from register 4120 MSB)
CHARGE_STAGES = {
    0: "Resting",
    3: "Absorb",
    4: "BulkMPPT",
    5: "Float",
    6: "FloatMppt",
    7: "Equalize",
    10: "HyperVoc",
    18: "EqMppt",
}

# Internal state mappings (from register 4120 LSB)
INTERNAL_STATES = {
    0: "Resting",
    1: "Waking/Starting (state 1)",
    2: "Waking/Starting (state 2)",
    3: "MPPT / Regulating Voltage (state 3)",
    4: "MPPT / Regulating Voltage (state 4)",
    6: "MPPT / Regulating Voltage (state 6)",
}

# Device types from register 4101
DEVICE_TYPES = {
    150: "Classic 150",
    200: "Classic 200",
    250: "Classic 250",
    251: "Classic 250 KS (120V battery capability)",
}

# Rest reasons from register 4275
REST_REASONS = {
    1: "Anti-Click. Not enough power available (Wake Up)",
    2: "Insane Ibatt Measurement (Wake Up)",
    3: "Negative Current (load on PV input?) (Wake Up)",
    4: "PV Input Voltage lower than Battery V (Vreg state)",
    5: "Too low of power out and Vbatt below set point for > 90 seconds",
    6: "FET temperature too high (Cover is on maybe?)",
    7: "Ground Fault Detected",
    8: "Arc Fault Detected",
    9: "Too much negative current while operating (backfeed from battery out of PV input)",
    10: "Battery is less than 8.0 Volts",
    11: "PV input is available but V is rising too slowly. Low Light or bad connection (Solar mode)",
    12: "Voc has gone down from last Voc or low light. Re-check (Solar mode)",
    13: "Voc has gone up from last Voc enough to be suspicious. Re-check (Solar mode)",
    14: "Same as 11",
    15: "Same as 12",
    16: "MPPT MODE is OFF (Usually because user turned it off)",
    17: "PV input is higher than operation range (too high for 150V Classic)",
    18: "PV input is higher than operation range (too high for 200V Classic)",
    19: "PV input is higher than operation range (too high for 250V or 250KS)",
    22: "Average Battery Voltage is too high above set point",
    25: "Battery Voltage too high of Overshoot (small battery or bad cable?)",
    26: "Mode changed while running OR Vabsorb raised more than 10.0 Volts at once OR Nominal Vbatt changed by modbus command AND MpptMode was ON when changed",
    27: "Bridge center == 1023 (R132 might have been stuffed) This turns MPPT Mode to OFF",
    28: "NOT Resting but RELAY is not engaged for some reason",
    29: "ON/OFF stays off because WIND GRAPH is illegal (current step is set for > 100 amps)",
    30: "PkAmpsOverLimit... Software detected too high of PEAK output current",
    31: "AD1CH.IbattMinus > 900 Peak negative battery current > 90.0 amps (Classic 250)",
    32: "Aux 2 input commanded Classic off for HI or LO (Aux2Function == 15 or 16)",
    33: "OCP in a mode other than Solar or PV-Uset",
    34: "AD1CH.IbattMinus > 900 Peak negative battery current > 90.0 amps (Classic 150, 200)",
    35: "Battery voltage is less than Low Battery Disconnect (LBD) Typically Vbatt is less than 8.5 volts",
}

# Force flag bit mappings (from register 4160)
FORCE_FLAGS = {
    "ForceEEpromUpdate": 2,      # Bit position
    "ForceEEpromInitRead": 3,
    "ForceResetInfoFlags": 4,
    "ForceFloat": 5,
    "ForceBulk": 6,
    "ForceEqualize": 7,
    "ForceNite": 8,
    "ResetAeqCounts": 13,
    "ForceSweep": 16,
    "ResetFlags": 20,             # Bit position
    "ForceResetFaults": 29,
}
'''
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")


def generate_entity_classes(data: List[Dict[str, str]], output_dir: str) -> None:
    """Generate entity classes for sensor.py, number.py, and select.py."""
    
    # Group registers by entity type
    sensors = []
    numbers = []
    selects = []
    
    for row in data:
        entity_type = row['Entity Type']
        name = row['Register Name']
        address = int(row['Address'])
        device_class = row['Device Class']
        state_class = row['State Class']
        unit = row['Unit']
        precision = row.get('Precision', '')
        icon = row['Icon']
        friendly_name = row.get('Friendly Name', name)
        scan_interval = int(row.get('Scan Interval', 30))
        description = row['Description']
        
        if entity_type == 'sensor':
            sensors.append(row)
        elif entity_type == 'number':
            numbers.append(row)
        elif entity_type == 'select':
            selects.append(row)
    
    # Generate sensor classes
    generate_sensor_classes(sensors, f"{output_dir}/sensor.py")
    
    # Generate number classes
    generate_number_classes(numbers, f"{output_dir}/number.py")
    
    # Generate select classes
    generate_select_classes(selects, f"{output_dir}/select.py")


def generate_sensor_classes(sensors: List[Dict[str, str]], output_path: str) -> None:
    """Generate sensor entity classes."""
    
    # Import section
    content = '''"""Support for Midnite Solar sensor platform."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHARGE_STAGES, DEVICE_TYPES, DOMAIN, INTERNAL_STATES, REGISTER_MAP, REST_REASONS
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
'''
    
    # Add sensor instances (skip special registers that need custom handling)
    special_registers = ['COMBO_CHARGE_STAGE', 'REASON_FOR_RESTING']
    for i, sensor in enumerate(sensors):
        name = sensor['Register Name']
        if name not in special_registers:
            content += f'        {name}Sensor(coordinator, entry),\n'
    
    content += '''    ]
    
    async_add_entities(sensors)


class MidniteSolarSensor(CoordinatorEntity[MidniteSolarUpdateCoordinator], SensorEntity):
    """Base class for all Midnite Solar sensors."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
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
        # Try to get device ID from coordinator data (registers 4111-4112)
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                device_id_lsw = device_info_data.get(REGISTER_MAP["DEVICE_ID_LSW"])
                device_id_msw = device_info_data.get(REGISTER_MAP["DEVICE_ID_MSW"])
                if device_id_lsw is not None and device_id_msw is not None:
                    device_id = (device_id_msw << 16) | device_id_lsw
                    # Try to get device model from UNIT_ID register
                    unit_id_value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                    if unit_id_value is not None:
                        device_type = unit_id_value & 0xFF  # Get LSB (unit type)
                        model = DEVICE_TYPES.get(device_type, f"Unknown ({device_type})")
                    else:
                        model = "Midnite Solar Device"
                    
                    return {
                        "identifiers": {(DOMAIN, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                    }
        
        # Fallback to entry_id if device ID not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        return None
'''
    
    # Add individual sensor classes
    for sensor in sensors:
        name = sensor['Register Name']
        address = int(sensor['Address'])
        device_class = sensor['Device Class']
        state_class = sensor['State Class']
        unit = sensor['Unit']
        precision = sensor.get('Precision', '')
        icon = sensor['Icon']
        description = sensor['Description']
        friendly_name = sensor.get('Friendly Name', name)
        
        # Determine if this is a special sensor that needs custom logic
        # These will be added separately after the generated sensors
        if name in ['COMBO_CHARGE_STAGE', 'REASON_FOR_RESTING']:
            # Skip these as they have special handling - will add manually
            continue
        
        # Build sensor class with friendly name support
        content += '\n\n'
        content += f'class {name}Sensor(MidniteSolarSensor):\n'
        content += f'    """Representation of a {description.lower()} sensor."""\n\n'
        content += '    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):\n'
        content += '        """Initialize the sensor."""\n'
        content += '        super().__init__(coordinator, entry)\n'
        content += f'        self._attr_name = "{friendly_name}"\n'
        content += f'        self._attr_unique_id = f"{{entry.entry_id}}_{name.lower().replace(" ", "_")}"\n'
        
        # Add device class if specified
        if device_class:
            content += f'        self._attr_device_class = SensorDeviceClass.{device_class.upper()}\n'
        
        # Add unit if specified
        if unit:
            if unit == 'V':
                content += f'        self._attr_native_unit_of_measurement = "{unit}"\n'
            elif unit == 'A':
                content += f'        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE\n'
            elif unit == 'W':
                content += f'        self._attr_native_unit_of_measurement = UnitOfPower.WATT\n'
            elif unit == 'kWh':
                content += f'        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR\n'
            elif unit == 'Ah':
                content += f'        self._attr_native_unit_of_measurement = "{unit}"\n'
            elif unit == '°C':
                content += f'        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS\n'
            elif unit == 's':
                content += f'        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS\n'
            else:
                content += f'        self._attr_native_unit_of_measurement = "{unit}"\n'
        
        # Add state class if specified
        if state_class:
            content += f'        self._attr_state_class = SensorStateClass.{state_class.upper()}\n'
        
        # Add precision if specified
        if precision and precision != '':
            content += f'        self._attr_suggested_display_precision = {precision}\n'
        
        # Add icon if specified
        if icon:
            content += f'        self._attr_icon = "{icon}"\n'
        
        # Add formula-based conversion logic
        formula = sensor.get('Formula', '')
        if formula:
            # Use the formula from CSV if available
            content += f'''    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["{name}"])
                if value is not None:
                    # Formula: {formula}
                    return value
                return None
'''.format(name=name, formula=formula)
        else:
            # Use unit-based conversion as fallback
            content += f'''    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["{name}"])
                if value is not None:
'''.format(name=name)
            
            # Add conversion logic based on unit
            if unit == 'V' or unit == 'A':
                content += f'                    return value / 10.0\n'
            elif unit == 'kWh':
                content += f'                    return value / 100.0\n'
            else:
                content += f'                    return value\n'
            
            content += '''                return None
'''
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")


def generate_number_classes(numbers: List[Dict[str, str]], output_path: str) -> None:
    """Generate number entity classes."""
    
    # Import section
    content = '''"""Support for Midnite Solar number platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    numbers = [
'''
    
    # Add number instances
    for i, number in enumerate(numbers):
        name = number['Register Name']
        content += f'        {name}Number(coordinator, entry),\n'
    
    content += '''    ]
    
    async_add_entities(numbers)


class MidniteSolarNumber(CoordinatorEntity[MidniteSolarUpdateCoordinator], NumberEntity):
    """Base class for all Midnite Solar numbers."""

    _attr_native_min_value: float | None = None
    _attr_native_max_value: float | None = None
    _attr_native_step: float | None = None

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the number."""
        super().__init__(coordinator)
        self._entry = entry
        
        # Create device info - use serial number if available, otherwise use entry_id
        # We'll update this dynamically when data becomes available via property override
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def device_info(self):
        """Return dynamic device info with device ID and model if available."""
        # Try to get device ID from coordinator data (registers 4111-4112)
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                device_id_lsw = device_info_data.get(REGISTER_MAP["DEVICE_ID_LSW"])
                device_id_msw = device_info_data.get(REGISTER_MAP["DEVICE_ID_MSW"])
                if device_id_lsw is not None and device_id_msw is not None:
                    device_id = (device_id_msw << 16) | device_id_lsw
                    # Try to get device model from UNIT_ID register
                    unit_id_value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                    if unit_id_value is not None:
                        device_type = unit_id_value & 0xFF  # Get LSB (unit type)
                        model = DEVICE_TYPES.get(device_type, f"Unknown ({device_type})")
                    else:
                        model = "Midnite Solar Device"
                    
                    return {
                        "identifiers": {(DOMAIN, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                    }
        
        # Fallback to entry_id if serial number not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return None
'''
    
    # Add individual number classes
    for number in numbers:
        name = number['Register Name']
        address = int(number['Address'])
        device_class = number['Device Class']
        unit = number['Unit']
        precision = number.get('Precision', '')
        icon = number['Icon']
        description = number['Description']
        
        # Get friendly name if available
        friendly_name = number.get('Friendly Name', name)
        
        # Build number class with friendly name support
        content += '\n\n'
        content += f'class {name}Number(MidniteSolarNumber):\n'
        content += f'    """Representation of a {description.lower()} number."""\n\n'
        content += '    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):\n'
        content += '        """Initialize the number."""\n'
        content += '        super().__init__(coordinator, entry)\n'
        content += f'        self._attr_name = "{friendly_name}"\n'
        content += f'        self._attr_unique_id = f"{{entry.entry_id}}_{name.lower().replace(" ", "_")}_number"\n'
        content += f'        self.register_address = {address}\n'
        
        # Add device class if specified
        if device_class:
            content += f'        self._attr_device_class = "{device_class}"\n'
        
        # Add unit if specified
        if unit:
            if unit == 'V':
                content += f'        self._attr_native_unit_of_measurement = "{unit}"\n'
            elif unit == 'A':
                content += f'        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE\n'
            elif unit == 's':
                content += f'        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS\n'
            else:
                content += f'        self._attr_native_unit_of_measurement = "{unit}"\n'
        
        # Add icon if specified
        if icon:
            content += f'        self._attr_icon = "{icon}"\n'
        
        # Add native_value property with conversion logic
        content += '''
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # Get the raw register value from coordinator data
        value = self.coordinator.get_register_value(self.register_address)
        if value is not None:
'''
        
        # Add conversion logic based on unit
        if unit == 'V' or unit == 'A':
            content += f'            return value / 10.0\n'
        else:
            content += f'            return value\n'
        
        content += '''        return None
'''
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")


def generate_select_classes(selects: List[Dict[str, str]], output_path: str) -> None:
    """Generate select entity classes."""
    
    # Import section
    content = '''"""Support for Midnite Solar select platform."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, DOMAIN, FORCE_FLAGS, REGISTER_MAP
from .coordinator import MidniteSolarUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar selectors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    selectors = [
'''
    
    # Add select instances
    for i, select in enumerate(selects):
        name = select['Register Name']
        content += f'        {name}Select(coordinator, entry),\n'
    
    content += '''    ]
    
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
        # Try to get device ID from coordinator data (registers 4111-4112)
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                device_id_lsw = device_info_data.get(REGISTER_MAP["DEVICE_ID_LSW"])
                device_id_msw = device_info_data.get(REGISTER_MAP["DEVICE_ID_MSW"])
                if device_id_lsw is not None and device_id_msw is not None:
                    device_id = (device_id_msw << 16) | device_id_lsw
                    # Try to get device model from UNIT_ID register
                    unit_id_value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                    if unit_id_value is not None:
                        device_type = unit_id_value & 0xFF  # Get LSB (unit type)
                        model = DEVICE_TYPES.get(device_type, f"Unknown ({device_type})")
                    else:
                        model = "Midnite Solar Device"
                    
                    return {
                        "identifiers": {(DOMAIN, str(device_id))},
                        "name": f"{model} ({device_id})",
                        "manufacturer": "Midnite Solar",
                        "model": model,
                    }
        
        # Fallback to entry_id if device ID not available
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Midnite Solar",
        }
'''
    
    # Add individual select classes
    for select in selects:
        name = select['Register Name']
        address = int(select['Address'])
        device_class = select['Device Class']
        unit = select['Unit']
        precision = select.get('Precision', '')
        icon = select['Icon']
        description = select['Description']
        friendly_name = select.get('Friendly Name', name)
        
        # Build select class with friendly name support
        content += '\n\n'
        content += f'class {name}Select(MidniteSolarSelect):\n'
        content += f'    """Representation of a {description.lower()} selector."""\n\n'
        content += '    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):\n'
        content += '        """Initialize the selector."""\n'
        content += '        super().__init__(coordinator, entry)\n'
        content += f'        self._attr_name = "{friendly_name}"\n'
        content += f'        self._attr_unique_id = f"{{entry.entry_id}}_{name.lower().replace(" ", "_")}_select"\n'
        
        # Add icon if specified
        if icon:
            content += f'        self._attr_icon = "{icon}"\n'
        
        content += '''
    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        return None
'''
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Generated {output_path}")


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python generate_from_csv.py <input_csv> <output_dir>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Read CSV file
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    print(f"Found {len(data)} registers in {input_csv}")
    
    # Validate CSV
    validate_csv(data)
    
    # Generate const.py
    generate_const_py(data, f"{output_dir}/const.py")
    
    # Generate entity classes
    generate_entity_classes(data, output_dir)
    
    print("\n✓ Generation complete!")


if __name__ == "__main__":
    main()
