# Fixes Summary

## Issue 1: Input Number Controls Grayed Out - AttributeError

**Problem:** The input number controls were grayed out and throwing an error:
```
AttributeError: 'MidniteHub' object has no attribute 'REGISTER_GROUPS'
```

**Root Cause:** In the refactored code, `number.py` was trying to access `self.coordinator.api.REGISTER_GROUPS`, but `REGISTER_GROUPS` is defined in `coordinator.py`, not in the hub (`MidniteHub`). The hub only manages the Modbus connection and doesn't know about register groups.

**Fix:** Modified `/Users/randy/midnite/custom_components/midnite/number.py` line 87-106 to use the coordinator's existing `get_register_value()` method instead of trying to access `REGISTER_GROUPS` through the hub:

```python
# Before (line 93):
for group_name, registers in self.coordinator.api.REGISTER_GROUPS.items():
    if self.register_address in registers:
        data = self.coordinator.data["data"].get(group_name)
        if data and self.register_address in data:
            value = data[self.register_address]
            # ... conversion logic

# After (line 89):
value = self.coordinator.get_register_value(self.register_address)
if value is not None:
    # ... conversion logic
```

This is cleaner because it reuses the coordinator's existing method for retrieving register values, avoiding code duplication and potential circular imports.

## Issue 2: Invalid Temperature Readings

**Problem:** Temperature sensors were logging warnings for valid temperatures:
```
Invalid FET temperature reading: 42.3°C. Ignoring.
Invalid PCB temperature reading: 40.8°C. Ignoring.
```

**Root Cause:** In `sensor.py`, the temperature validation logic had a bug where it was checking the raw register value (`value`) instead of the converted temperature value (`temp_value`) against the valid range:

```python
# Before (line 382 and 418):
if value < -50 or value > 150:  # Checking raw register value
```

Since the raw register values are typically in the hundreds (representing tenths of a degree), they would always fail this validation.

**Fix:** Modified `/Users/randy/midnite/custom_components/midnite/sensor.py` to check `temp_value` instead:

```python
# After (line 382 and 418):
if temp_value < -50 or temp_value > 150:  # Checking converted temperature value
```

This allows valid temperatures between -50°C and 150°C to be accepted.

## Issue 3: Modbus Decoding Errors (Not Fixed)

**Problem:** The logs show:
```
Unable to decode frame Modbus Error: [Input/Output] byte_count 2 > length of packet 1
```

**Analysis:** This appears to be a pre-existing I/O error with the Modbus communication, not directly related to the refactoring. The error suggests there's a mismatch between expected and actual packet sizes during Modbus communication.

**Recommendation:** This may require:
- Checking network connectivity between Home Assistant and the Midnite device
- Verifying the Modbus TCP server on the device is functioning properly
- Adding retry logic or better error handling in the hub connection code
- Potentially adjusting timeouts or buffer sizes in the Modbus client configuration

## Testing Recommendations

After applying these fixes:
1. Restart Home Assistant to reload the custom component
2. Verify that all number controls are now active and can be adjusted
3. Check that temperature sensors display valid values without warnings
4. Monitor the logs for any remaining Modbus communication issues
