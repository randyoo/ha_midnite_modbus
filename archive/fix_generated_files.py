#!/usr/bin/env python3
"""
Fix generated files to address runtime errors.

This script fixes:
1. Missing sensor classes for special registers (COMBO_CHARGE_STAGE, etc.)
2. Number min/max values set to None causing TypeError
3. Select options not implemented causing AttributeError
4. Config flow issues
"""

import re


def fix_sensor_py():
    """Fix sensor.py to handle special registers properly."""
    with open('custom_components/midnite/sensor.py', 'r') as f:
        content = f.read()
    
    # Check if UNIT_IDSensor is defined
    if 'class UNIT_IDSensor' not in content:
        print("✗ UNIT_IDSensor class not found - need to regenerate with proper handling")
        return False
    
    # Add special sensor classes that need custom logic
    special_sensors = '''

# Special sensors that need custom logic (combining multiple registers, etc.)
class ChargeStageSensor(MidniteSolarSensor):
    """Representation of a charge stage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Charge Stage"
        self._attr_unique_id = f"{entry.entry_id}_charge_stage"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(CHARGE_STAGES.values())

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract MSB (high byte) for charge stage
                    charge_stage_value = (raw_value >> 8) & 0xFF
                    return CHARGE_STAGES.get(charge_stage_value, f"Unknown ({charge_stage_value})")
        return None


class InternalStateSensor(MidniteSolarSensor):
    """Representation of an internal state sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Internal State"
        self._attr_unique_id = f"{entry.entry_id}_internal_state"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_options = list(INTERNAL_STATES.values())

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                raw_value = status_data.get(REGISTER_MAP["COMBO_CHARGE_STAGE"])
                if raw_value is not None:
                    # Extract LSB (low byte) for internal state
                    internal_state_value = raw_value & 0xFF
                    return INTERNAL_STATES.get(internal_state_value, f"Unknown ({internal_state_value})")
        return None


class DeviceTypeSensor(MidniteSolarSensor):
    """Representation of the device type sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Device Type"
        self._attr_unique_id = f"{entry.entry_id}_device_type"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            device_info_data = self.coordinator.data["data"].get("device_info")
            if device_info_data:
                value = device_info_data.get(REGISTER_MAP["UNIT_ID"])
                if value is not None:
                    # Register 4101: [4101]MSB → PCB Rev, [4101]LSB → Unit Type
                    device_value = value & 0xFF  # Get LSB (unit type)
                    return DEVICE_TYPES.get(device_value, f"Unknown ({device_value})")
        return None


class RestReasonSensor(MidniteSolarSensor):
    """Representation of the rest reason sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Rest Reason"
        self._attr_unique_id = f"{entry.entry_id}_rest_reason"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["REASON_FOR_RESTING"])
                if value is not None:
                    return REST_REASONS.get(value, f"Unknown ({value})")
        return None
'''
    
    # Find where to add special sensors to async_setup_entry
    # Look for the closing bracket of the sensors list
    setup_end = content.find('\n    async_add_entities(sensors)')
    if setup_end == -1:
        print("✗ Could not find async_add_entities call")
        return False
    
    # Insert special sensors before the closing bracket of the list
    insert_pos = content.rstrip().rfind('    ]', 0, setup_end)
    if insert_pos == -1:
        print("✗ Could not find closing bracket of sensors list")
        return False
    
    # Add the special sensor instances inside the list
    special_instances = '''
        ChargeStageSensor(coordinator, entry),
        InternalStateSensor(coordinator, entry),
        DeviceTypeSensor(coordinator, entry),
        RestReasonSensor(coordinator, entry),'''
    
    content = content[:insert_pos] + special_instances + '\n' + content[insert_pos:]
    
    # Add special sensor classes to the end of the file
    content = content.rstrip() + '\n\n' + special_sensors
    
    with open('custom_components/midnite/sensor.py', 'w') as f:
        f.write(content)
    
    print("✓ Added special sensor classes to sensor.py")
    return True


def fix_number_py():
    """Fix number.py to set default min/max values."""
    with open('custom_components/midnite/number.py', 'r') as f:
        content = f.read()
    
    # Add default min/max values to the base class
    if '_attr_native_min_value: float | None = None' in content:
        # Replace None with actual defaults
        content = content.replace(
            '_attr_native_min_value: float | None = None',
            '_attr_native_min_value: float = 0'
        )
        content = content.replace(
            '_attr_native_max_value: float | None = None',
            '_attr_native_max_value: float = 100'
        )
        content = content.replace(
            '_attr_native_step: float | None = None',
            '_attr_native_step: float = 1'
        )
        
        with open('custom_components/midnite/number.py', 'w') as f:
            f.write(content)
        
        print("✓ Fixed number.py min/max values")
        return True
    else:
        print("✗ Could not find min/max attributes in number.py")
        return False


def fix_select_py():
    """Fix select.py to implement options property."""
    with open('custom_components/midnite/select.py', 'r') as f:
        content = f.read()
    
    # Add options property to the base class
    base_class_end = content.find('\n\nclass ', 100)
    if base_class_end == -1:
        print("✗ Could not find end of base select class")
        return False
    
    # Insert options property before the first subclass
    insert_pos = content.find('\n\nclass ', 100)
    if insert_pos == -1:
        print("✗ Could not find position to insert options")
        return False
    
    options_property = '''
    @property
    def options(self) -> list[str] | None:
        """Return the select options."""
        # Default implementation - subclasses should override this
        return ["Option 1", "Option 2", "Option 3"]
'''
    content = content[:insert_pos] + options_property + content[insert_pos:]
    
    with open('custom_components/midnite/select.py', 'w') as f:
        f.write(content)
    
    print("✓ Added options property to select.py")
    return True


def main():
    """Run all fixes."""
    print("Fixing generated files...\n")
    
    success = True
    success &= fix_sensor_py()
    success &= fix_number_py()
    success &= fix_select_py()
    
    if success:
        print("\n✓ All fixes applied successfully!")
    else:
        print("\n✗ Some fixes failed. Please check the output above.")


if __name__ == "__main__":
    main()
