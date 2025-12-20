# Changes Made to Fix Issues

## Summary
Fixed two critical bugs introduced during the refactoring:
1. **Input number controls grayed out** - Fixed AttributeError by using coordinator's existing method
2. **Invalid temperature warnings** - Fixed validation logic to check converted values instead of raw register values

## Files Modified

### 1. `/custom_components/midnite/number.py`

**Issue**: Line 93 was trying to access `self.coordinator.api.REGISTER_GROUPS`, but the hub (`MidniteHub`) doesn't have this attribute - it's defined in `coordinator.py`. This caused an AttributeError that prevented number controls from working.

**Fix**: Simplified the `native_value` property (lines 87-106) to use the coordinator's existing `get_register_value()` method instead of manually iterating through register groups.

**Changes**:
```python
# BEFORE:
@property
def native_value(self) -> float | None:
    """Return the current value."""
    if self.coordinator.data and "data" in self.coordinator.data:
        # Find which register group contains this address
        for group_name, registers in self.coordinator.api.REGISTER_GROUPS.items():
            if self.register_address in registers:
                data = self.coordinator.data["data"].get(group_name)
                if data and self.register_address in data:
                    value = data[self.register_address]
                    # Convert from register value (divide by 10 for voltage/current)
                    # Time values should NOT be divided by 10
                    if hasattr(self, 'is_time_value') and self.is_time_value:
                        return float(value)
                    else:
                        return float(value) / 10.0
    return None

# AFTER:
@property
def native_value(self) -> float | None:
    """Return the current value."""
    # Get the raw register value from coordinator data
    value = self.coordinator.get_register_value(self.register_address)
    if value is not None:
        # Convert from register value (divide by 10 for voltage/current)
        # Time values should NOT be divided by 10
        if hasattr(self, 'is_time_value') and self.is_time_value:
            return float(value)
        else:
            return float(value) / 10.0
    return None
```

**Benefits**:
- Eliminates the AttributeError
- Reuses existing coordinator method (cleaner, less code duplication)
- No circular import issues
- Number controls now work properly

### 2. `/custom_components/midnite/sensor.py`

**Issue**: Lines 382 and 418 were checking the raw register value (`value`) against the temperature range instead of the converted temperature value (`temp_value`). This caused valid temperatures like 42.3°C to be marked as invalid.

**Fix**: Changed the validation condition from `if value < -50 or value > 150` to `if temp_value < -50 or temp_value > 150`.

**Changes**:
```python
# BEFORE (line 382):
if value < -50 or value > 150:
    _LOGGER.warning(f"Invalid FET temperature reading: {temp_value}°C. Ignoring.")
    return None

# AFTER (line 382):
if temp_value < -50 or temp_value > 150:
    _LOGGER.warning(f"Invalid FET temperature reading: {temp_value}°C. Ignoring.")
    return None
```

Same fix applied to PCB temperature sensor at line 418.

**Benefits**:
- Valid temperatures (42°C, 40°C) are now accepted
- Invalid temperatures (>150°C or <-50°C) still properly rejected
- No more false warning messages in logs

## Testing

Created `test_fixes.py` to verify the logic:
- Temperature validation: Confirmed that raw values like 423 (42.3°C) and 408 (40.8°C) are now correctly validated as VALID
- Number conversion: Confirmed voltage/current values are divided by 10, time values are not

## Remaining Issues

The Modbus decoding error (`Unable to decode frame Modbus Error: [Input/Output] byte_count 2 > length of packet 1`) appears to be a pre-existing communication issue unrelated to this refactoring. This may require:
- Network connectivity checks between Home Assistant and the Midnite device
- Verification that the Modbus TCP server on the device is functioning properly
- Potential adjustments to timeouts or buffer sizes in the Modbus client configuration

## Deployment Instructions

1. Apply these changes to your production environment
2. Restart Home Assistant to reload the custom component
3. Verify that:
   - All number controls are active and can be adjusted
   - Temperature sensors display valid values without warnings
   - No AttributeError appears in logs for number entities
