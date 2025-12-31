# Ideal Prompt for Adding Home Assistant Entities

## Objective
Add missing entities to the Midnite Solar Home Assistant integration by implementing sensors, numbers, selects, etc. based on the device's Modbus registers.

## Process Overview
1. Select unimplemented entities from MISSING_ENTITIES.md
2. Implement each entity in the appropriate file (sensor.py, number.py, select.py)
3. Add register mappings to const.py and coordinator.py
4. Test locally (if possible)
5. Commit changes with descriptive message
6. Push to remote repository
7. Update MISSING_ENTITIES.md to mark as implemented ✓

## Implementation Guide

### Step 1: Register Mapping (const.py)
Add the register to REGISTER_MAP:
```python
REGISTER_MAP["NEW_REGISTER_NAME"] = 4200  # Replace with actual register number
```

### Step 2: Coordinator Setup (coordinator.py)
Add the register to the appropriate group in REGISTER_GROUPS:
- Use "status" for real-time status values
- Use "settings" for configuration values
- Use "temperatures" for temperature readings
- Use "energy" for energy-related data
- Use "time_settings" for time/duration values
- Use "network" for network configuration

```python
"status": [
    ...,
    REGISTER_MAP["NEW_REGISTER_NAME"],
]
```

### Step 3: Entity Implementation (sensor.py/number.py/select.py)

#### Sensor Example:
```python
class NewSensor(MidniteSolarSensor):
    """Representation of new sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        super().__init__(coordinator, entry)
        self._attr_name = "New Sensor Name"
        self._attr_unique_id = f"{entry.entry_id}_new_sensor"
        
        # Choose appropriate category:
        # - None for main entities (voltage, current, power)
        # - EntityCategory.DIAGNOSTIC for diagnostic info
        # - EntityCategory.CONFIG for configurable settings
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        
        # Set device class and units:
        self._attr_device_class = SensorDeviceClass.VOLTAGE  # or None if not applicable
        self._attr_native_unit_of_measurement = "V"  # or appropriate unit
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # REQUIRED: Disable by default
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            data_group = self.coordinator.data["data"].get("status")  # Match coordinator group
            if data_group:
                value = data_group.get(REGISTER_MAP["NEW_REGISTER_NAME"])
                if value is not None:
                    # Apply formula from registers.json (e.g., /10 for voltage)
                    return value / 10.0
        return None
```

#### Number Example:
```python
class NewNumber(MidniteSolarNumber):
    """Number to set new configuration value."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        super().__init__(coordinator, entry)
        self._attr_name = "New Number Name"
        self._attr_unique_id = f"{entry.entry_id}_new_number"
        self.register_address = REGISTER_MAP["NEW_REGISTER_NAME"]
        
        # Set appropriate category
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Set units and range:
        self._attr_native_unit_of_measurement = "V"
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 100.0
        self._attr_native_step = 0.1
        
        # REQUIRED: Disable by default
        self._attr_entity_registry_enabled_default = False
        
        # Special flags (if needed):
        # - is_time_value = True for time values stored in seconds
        # - is_raw_value = True for values that don't need /10 scaling

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._async_set_value(value)
```

### Step 4: Add to Setup Function
Add the new entity class to the appropriate list in `async_setup_entry`:
```python
sensors = [
    ...,
    NewSensor(coordinator, entry),
]
```

## Key Considerations

1. **Entity Categories**: Use appropriate categories to organize UI sections
   - No category → Main entities
   - `EntityCategory.DIAGNOSTIC` → Diagnostic section
   - `EntityCategory.CONFIG` → Configuration section

2. **Formulas**: Apply scaling from registers.json (e.g., `/10` for voltage/current)

3. **Default State**: ALWAYS set `entity_registry_enabled_default = False`

4. **Data Groups**: Match coordinator group names with data access paths
   - "status" → `coordinator.data["data"].get("status")`
   - "settings" → `coordinator.data["data"].get("settings")`

5. **Multi-Register Entities**: For 32-bit values, combine two registers:
```python
low_value = data_group.get(REGISTER_MAP["LOW_REGISTER"])
high_value = data_group.get(REGISTER_MAP["HIGH_REGISTER"] + 1)  # Next register
if low_value is not None and high_value is not None:
    value = (high_value << 16) | low_value
    return value / 10.0
```

## Example Workflow

### Adding "Restart Time" Sensor (Register 4114)

1. **const.py**: Add `"RESTART_TIME_MS": 4114` to REGISTER_MAP
2. **coordinator.py**: Add `REGISTER_MAP["RESTART_TIME_MS"]` to "status" group
3. **sensor.py**: Create RestartTimeSensor class with:
   - Category: DIAGNOSTIC
   - Device class: DURATION
   - Unit: MILLISECONDS
   - No scaling (value is already in milliseconds)
4. Add to sensors list in async_setup_entry
5. Commit: "Add Restart Time sensor (register 4114)"
6. Update MISSING_ENTITIES.md: Mark as ✓
