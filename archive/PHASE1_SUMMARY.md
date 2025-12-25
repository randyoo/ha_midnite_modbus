# Phase 1 Summary: Constants and Configuration

## Completed Tasks ✓

### 1. JSON File Fixes
- Fixed syntax errors in `registers.json` (trailing commas)
- Created `registers_fixed.json` with valid JSON structure
- Categorized all 198 registers into:
  - **Already Implemented**: 36 registers
  - **Advanced Category**: 153 registers
  - **Debug Category**: 10 registers

### 2. Constants Update (`const.py`)
- Added all 198 register mappings to `REGISTER_MAP`
- Organized by address for better readability
- Added new configuration constants:
  ```python
  CONF_ENABLE_ADVANCED = "enable_advanced"
  CONF_ENABLE_DEBUG = "enable_debug"
  CONF_ENABLE_WRITES = "enable_writes"
  ```

### 3. Coordinator Update (`coordinator.py`)
- Added new register groups:
  - `advanced_status`: Status information (match point, log interval, Modbus port, MPP watts)
  - `advanced_config`: Configuration settings (MPPT mode, AUX functions, enable flags)
  - `aux_control`: AUX control registers (voltages, delays, PWM width)
  - `voltage_offsets`: Voltage offset and target registers
  - `temp_comp`: Temperature compensation registers

### 4. Configuration Flow Update (`config_flow.py`)
- Updated `async_step_options()` to include new checkboxes:
  - Enable Advanced Features (default: False)
  - Enable Debug Information (default: False)
  - Enable Write Operations (default: False)
- Updated `async_step_reconfigure()` to preserve new options
- All options are stored in config entry options (not data)

## Files Modified

1. **custom_components/midnite/const.py**
   - Added all register mappings (198 total)
   - Added 3 new configuration constants

2. **custom_components/midnite/coordinator.py**
   - Added 5 new register groups to `REGISTER_GROUPS`

3. **custom_components/midnite/config_flow.py**
   - Updated options form with 3 new checkboxes
   - Updated reconfigure flow to handle new options

## Next Steps (Phase 2)

### Entity Implementation Strategy

#### Priority 1: Advanced Sensors (Read-only)
These should be implemented first as they provide useful information without write risks:

1. **Status Information**
   - `ModbusPortSensor`: Current Modbus TCP port (4137)
   - `MpptModeSensor`: MPPT mode setting (4164)
   - `MatchPointShadowSensor`: Current wind power curve step (4124)

2. **AUX Control Status**
   - `Aux1VoltageLoAbsSensor`, `Aux1VoltageHiAbsSensor`
   - `Aux2PwmWidthSensor`

3. **Advanced Settings**
   - `EnableFlagsSensor`: Combined enable flags status
   - `VarimaxSensor`: Variable maximum current and voltage differential

#### Priority 2: Advanced Numbers (Read-Write with Protection)
These require write protection implementation:

1. **Voltage Offsets**
   - `VBattOffsetNumber`, `VPVOffsetNumber`

2. **PV Targeting**
   - `VPVTargetWriteNumber`

3. **Temperature Compensation**
   - `MaxTempCompVoltageNumber`
   - `MinTempCompVoltageNumber`
   - `BatteryTempCompValueNumber`

#### Priority 3: Debug Sensors (Read-only)
These can be implemented last as they're only useful for troubleshooting:

- `ReservedRegisterSensor` (generic class for RESERVED_* registers)
- `DebugRegisterSensor` (generic class for DABT_U32_DEBUG_* registers)

### Implementation Plan for Phase 2

1. **Update Base Classes**
   - Modify `MidniteSolarNumber` to respect write enable setting
   - Add warning when write is attempted with writes disabled

2. **Implement Advanced Sensors**
   - Create sensor classes in `sensor.py`
   - Add them to the sensors list conditionally based on config

3. **Implement Advanced Numbers**
   - Create number classes in `number.py`
   - Add write protection logic
   - Add them to numbers list conditionally

4. **Update Entity Registration**
   - Modify `async_setup_entry()` in sensor.py and number.py
   - Check config options before creating entities
   - Only create advanced/debug entities if enabled

5. **Testing**
   - Verify basic sensors still work
   - Test entity creation with different config combinations
   - Verify write protection works correctly

## Configuration Options Behavior

### Default State (All Disabled)
- Only basic sensors are created
- Numbers exist but writes are blocked
- Debug entities are not created

### Advanced Features Enabled
- Additional sensors for advanced status and configuration
- AUX control sensors
- Voltage offset sensors (read-only)

### Write Operations Enabled
- Numbers become writable
- Clear warnings in logs when writes occur
- Select entities become controllable

### Debug Information Enabled
- RESERVED registers exposed as sensors
- DEBUG registers exposed as sensors
- Raw/unfiltered data available

## Risk Management

### Write Protection
- All write operations are disabled by default
- Explicit user action required to enable writes
- Warnings logged when writes occur
- Consider adding UI warnings in future

### Performance
- New register groups add ~30 registers to read cycle
- Monitor update time with all features enabled
- May need to optimize or add "lite mode" if performance issues arise

## Documentation Needs

1. Update `README.md` with:
   - Description of new configuration options
   - List of advanced sensors available
   - Warnings about enabling write operations

2. Update `CHANGES.md` with:
   - Summary of new entities
   - Breaking changes (if any)
   - Configuration migration notes

3. Add inline documentation:
   - Docstrings for all new classes
   - Clear descriptions in entity attributes
   - Warnings about sensitive registers
