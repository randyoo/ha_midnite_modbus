# Time Conversion Implementation Summary

## Overview
Modified the `AbsorbTimeNumber` and `EqualizeTimeNumber` entities to display time values in **minutes** instead of seconds, while maintaining backward compatibility with the device registers that store values in seconds.

## Changes Made

### 1. AbsorbTimeNumber Class
- **Unit of Measurement**: Changed from `UnitOfTime.SECONDS` to `UnitOfTime.MINUTES`
- **Value Range**: Updated from 0-7200 (seconds) to 0-120 (minutes)
- **Step Size**: Changed from 60 to 1 (now allows 1-minute increments in UI)
- **Reading Logic**: Added custom `native_value` property that converts register value (seconds) to minutes
- **Writing Logic**: Overrode `_async_set_value` method to convert user input (minutes) to seconds before writing to register

### 2. EqualizeTimeNumber Class
- **Unit of Measurement**: Changed from `UnitOfTime.SECONDS` to `UnitOfTime.MINUTES`
- **Value Range**: Updated from 0-7200 (seconds) to 0-120 (minutes)
- **Step Size**: Changed from 60 to 1 (now allows 1-minute increments in UI)
- **Reading Logic**: Added custom `native_value` property that converts register value (seconds) to minutes
- **Writing Logic**: Overrode `_async_set_value` method to convert user input (minutes) to seconds before writing to register

## Conversion Logic

### Reading from Device (Register → UI)
```python
# Register stores value in seconds
register_value = 3600  # Example: 1 hour in seconds

# Convert to minutes for display
ui_value = float(register_value) / 60.0  # Result: 60.0 minutes
```

### Writing to Device (UI → Register)
```python
# User enters value in minutes
user_input = 30  # Example: 30 minutes

# Convert to seconds for register
register_value = int(user_input * 60)  # Result: 1800 seconds
```

## Benefits

1. **User-Friendly**: Time values are now displayed in minutes, which is more intuitive than seconds
2. **Fine-Grained Control**: Users can now set time values in 1-minute increments instead of 60-second (1-minute) jumps
3. **Backward Compatible**: The device register still receives the correct value in seconds
4. **Consistent with Other Time Entities**: Aligns with how other time-based entities are typically displayed in Home Assistant

## Testing

The conversion logic has been verified with test cases covering:
- Zero values (disabled mode)
- Single minute values
- Multi-minute values
- Hour values (60 minutes)
- Maximum values (120 minutes / 2 hours)

All conversions work correctly in both directions.

## Files Modified

- `custom_components/midnite/number.py`

## Entities Affected

- `number.absorb_time_seconds` → `number.absorb_time_minutes` (display only, internal ID unchanged)
- `number.equalize_time_seconds` → `number.equalize_time_minutes` (display only, internal ID unchanged)

Note: The entity IDs remain the same for backward compatibility. Only the display unit and values have changed.
