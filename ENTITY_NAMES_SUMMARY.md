# Entity Naming and Diagnostic Sensors Summary

## Changes Made

### 1. Entity Name Improvements ✅

**Before**: All entities had "Midnite" prefix (e.g., "Midnite Battery Voltage", "Midnite Charge Stage")

**After**: Clean, generic names following Home Assistant best practices:
- "Battery Voltage"
- "PV Voltage"  
- "Charge Stage"
- "Internal State"
- "Power Output"
- etc.

This matches the pattern seen in well-designed integrations like APC UPS where entity names are concise and generic.

### 2. Diagnostic Sensors Split ✅

**Operational Sensors** (visible by default):
- Battery Voltage
- PV Voltage
- Battery Current
- Power Output
- Charge Stage
- Internal State
- Battery Temperature
- FET Temperature
- PCB Temperature

**Diagnostic Sensors** (hidden by default, shown in diagnostics):
- Device Type
- Rest Reason
- Daily Amp-Hours
- Lifetime Energy
- Lifetime Amp-Hours
- PV Input Current
- Last Measured VOC
- Float Time Today
- Absorb Time Remaining
- Equalize Time Remaining

**Implementation**: Added `self._attr_entity_category = "diagnostic"` to diagnostic sensor classes.

### 3. Single Device Consistency ✅

All entities (sensors, numbers, buttons) now belong to a single device with:
- Consistent naming pattern
- Shared device_info from API
- Proper identifiers for device registry

## Entity Examples in UI

### Sensors
- `sensor.battery_voltage` → "Battery Voltage"
- `sensor.charge_stage` → "Charge Stage"
- `sensor.pv_voltage` → "PV Voltage"
- `sensor.device_type` (diagnostic) → "Device Type"

### Numbers
- `number.absorb_voltage_setpoint` → "Absorb Voltage Setpoint"
- `number.float_voltage_setpoint` → "Float Voltage Setpoint"
- `number.battery_current_limit` → "Battery Current Limit"

### Buttons
- `button.force_float` → "Force Float"
- `button.force_bulk` → "Force Bulk"
- `button.reset_faults` → "Reset Faults"

## Benefits

1. **Cleaner UI**: Users see only the most important sensors by default
2. **Professional Appearance**: Matches patterns from well-established integrations
3. **Better Organization**: Diagnostic information is accessible but not cluttering the main view
4. **Consistency**: All entities follow the same naming convention
5. **Discoverability**: Users can find diagnostic sensors in the diagnostics section

## Testing Recommendations

1. Verify that only operational sensors appear by default
2. Confirm diagnostic sensors are visible when "Show diagnostic entities" is enabled
3. Check that all entity names are clear and descriptive
4. Ensure single device is created with all entities belonging to it
