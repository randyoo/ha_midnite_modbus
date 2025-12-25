# Implementation Plan for Adding Unimplemented Registers

## Overview
This document outlines the plan for implementing all registers from `registers.json` into the Midnite Solar Home Assistant integration.

## Categorization Summary
Based on analysis of 198 total registers:
- **Already Implemented**: 36 registers (basic functionality)
- **New Registers to Implement**: 162 registers
  - **Advanced Category**: 153 registers (for power users)
  - **Debug Category**: 10 registers (debugging/diagnostic information)

## Implementation Strategy

### Phase 1: Update Constants and Data Structures ✓
- [x] Fix JSON syntax errors in `registers.json`
- [x] Categorize all registers into default/advanced/debug categories
- [x] Add all register mappings to `const.py`
- [ ] Update `REGISTER_GROUPS` in `coordinator.py` to include new groups

### Phase 2: Implement Sensor Entities
Create sensor classes for read-only registers:
- Temperature sensors (already implemented)
- Voltage/current sensors (already implemented)
- Time/duration sensors
- Status/flag sensors
- Diagnostic sensors

### Phase 3: Implement Number Entities
Create number classes for writable registers that represent numeric values:
- Voltage setpoints (already implemented)
- Current limits (already implemented)
- Time settings (already implemented)
- Other configurable parameters

### Phase 4: Implement Select Entities
Create select classes for registers with discrete options:
- MPPT mode selection
- AUX function selection
- LED mode selection
- USB communication mode

### Phase 5: Implement Button Entities
Create button classes for write-only registers that trigger actions:
- Force EEPROM update
- Reset flags
- Force charge stages
- Clear logs

### Phase 6: Update Configuration Flow
Add configuration options to enable/disable entity categories:
- [ ] Add checkboxes for "Advanced Features" and "Debug Information"
- [ ] Add toggle for "Enable Write Operations" (disabled by default)
- [ ] Store category preferences in config entry options

### Phase 7: Update Entity Registration Logic
Modify platform setup to conditionally create entities based on configuration:
- Check user preferences when creating entities
- Only create advanced/debug entities if enabled
- Respect write enable setting for number/select entities

## Detailed Implementation Plan

### Register Groups to Add to Coordinator

#### Advanced Sensors (Read-only)
1. **Status Information**
   - MATCH_POINT_SHADOW (4124)
   - INFO_FLAGS_BITS2_1/2_0 (4130-4131)
   - MINUTE_LOG_INTERVAL_SEC (4136)
   - MODBUS_PORT_REGISTER (4137)
   - PWM_READONLY (4141)
   - MPP_W_LAST (4145)

2. **Auxiliary Controls**
   - AUX1_VOLTS_LO_ABS/HI_ABS (4166, 4172)
   - AUX1_DELAY_T_MS/HOLD_T_MS (4167-4168)
   - AUX2_PWM_VWIDTH (4169)
   - AUX1/2_VOLTS_LO/HI_REL (4174-4177)
   - AUX1/2_VOLTS_LO/HI_PV_ABS (4178-4179, 4181)

3. **Advanced Settings**
   - MPPT_MODE (4164)
   - AUX_1_AND_2_FUNCTION (4165)
   - VARIMAX (4180)
   - ARC_FAULT_SENSITIVITY (4183)
   - ENABLE_FLAGS2/3/BITS (4182, 4186-4187)

#### Advanced Numbers (Read-Write)
1. **Voltage Offsets**
   - VBATT_OFFSET (4189)
   - VPV_OFFSET (4190)

2. **PV Targeting**
   - VPV_TARGET_WR (4192)

3. **Sweep Settings**
   - SWEEP_INTERVAL_SECS_EEPROM (4197)
   - MIN_SWP_VOLTAGE_EEPROM (4198)
   - MAX_INPUT_CURRENT_EEPROM (4199)
   - SWEEP_DEPTH (4200)

4. **Temperature Compensation**
   - MAX_BATTERY_TEMP_COMP_VOLTAGE (4155)
   - MIN_BATTERY_TEMP_COMP_VOLTAGE (4156)
   - BATTERY_TEMP_COMP_VALUE (4157)

#### Debug Sensors (Read-only)
- RESERVED_* registers (4105, 4171, 4185, 4188, 4195-4196)
- DABT_U32_DEBUG_* (4341-4344)

## Configuration Flow Changes

### New Configuration Options
```python
CONF_ENABLE_ADVANCED = "enable_advanced"
CONF_ENABLE_DEBUG = "enable_debug"
CONF_ENABLE_WRITES = "enable_writes"
```

### Options Schema
```python
data_schema = vol.Schema({
    vol.Optional(
        CONF_SCAN_INTERVAL,
        default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    ): int,
    vol.Optional(
        CONF_ENABLE_ADVANCED,
        default=current_options.get(CONF_ENABLE_ADVANCED, False)
    ): bool,
    vol.Optional(
        CONF_ENABLE_DEBUG,
        default=current_options.get(CONF_ENABLE_DEBUG, False)
    ): bool,
    vol.Optional(
        CONF_ENABLE_WRITES,
        default=current_options.get(CONF_ENABLE_WRITES, False)
    ): bool,
})
```

## Entity Registration Logic

### Sensor Platform
```python
async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        # Always include basic sensors
        BatteryVoltageSensor(coordinator, entry),
        PVoltageSensor(coordinator, entry),
        # ... other basic sensors
    ]
    
    # Add advanced sensors if enabled
    if entry.options.get(CONF_ENABLE_ADVANCED, False):
        sensors.extend([
            ModbusPortSensor(coordinator, entry),
            MpptModeSensor(coordinator, entry),
            # ... other advanced sensors
        ])
    
    # Add debug sensors if enabled
    if entry.options.get(CONF_ENABLE_DEBUG, False):
        sensors.extend([
            DebugRegister1Sensor(coordinator, entry),
            # ... other debug sensors
        ])
    
    async_add_entities(sensors)
```

### Number Platform (with write protection)
```python
class MidniteSolarNumber(MidniteSolarBase):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._write_enabled = entry.options.get(CONF_ENABLE_WRITES, False)
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if not self._write_enabled:
            _LOGGER.warning(
                f"Write to {self._attr_name} disabled. "
                "Enable writes in configuration to modify this setting."
            )
            return
        await self._async_set_value(value)
```

## Testing Strategy

1. **Unit Tests**: Test register parsing and value conversion
2. **Integration Tests**: Verify entity creation with different config options
3. **Manual Testing**: Test with actual Midnite Solar device
   - Verify all sensors display correct values
   - Test write operations (with caution)
   - Verify category enable/disable works correctly

## Risk Management

### Write Operations
- Keep write operations disabled by default
- Add prominent warnings in UI when writes are enabled
- Consider adding confirmation dialogs for sensitive writes
- Document which registers should not be modified

### Performance
- Group register reads efficiently to minimize Modbus traffic
- Consider adding a "lite mode" that only reads basic sensors
- Monitor update cycle time with all registers enabled

## Documentation Updates

1. **README.md**: Update with new features and configuration options
2. **CHANGES.md**: Document new entities and breaking changes
3. **Entity Descriptions**: Add clear descriptions for each new entity
4. **Warnings**: Document risks of enabling write operations or debug mode

## Timeline Estimate

- Phase 1: 2 hours (constants and data structures)
- Phase 2: 8 hours (sensor implementations)
- Phase 3: 4 hours (number implementations)
- Phase 4: 2 hours (select implementations)
- Phase 5: 2 hours (button implementations)
- Phase 6: 3 hours (configuration flow updates)
- Phase 7: 4 hours (entity registration logic)
- Testing: 4 hours
- **Total**: ~30 hours

## Next Steps

1. Complete Phase 1 by updating coordinator.py with new register groups
2. Start Phase 2 with the most useful advanced sensors
3. Implement write protection for number entities
4. Update configuration flow to support new options
