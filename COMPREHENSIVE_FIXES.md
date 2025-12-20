# Comprehensive Fixes for Midnite Solar Integration

## Issues Addressed

### 1. ✅ Input Numbers Not Being Read
**Problem**: Number entities couldn't read their values because the setpoint registers (4148-4163) were not included in any register group.

**Solution**: Added two new register groups to `coordinator.py`:
- `"setpoints"`: Contains voltage and current setpoint registers
- `"eeprom_settings"`: Contains EEPROM time settings registers

### 2. ✅ Connection Lost and Not Reestablished
**Problem**: When the connection dropped, it wasn't properly reconnected until integration reload.

**Solution**: Enhanced `_async_update_data()` in coordinator with:
- Connection test before reading data
- Automatic reconnection logic with retry
- Better error handling with `UpdateFailed` exceptions

### 3. ✅ Device Identified by IP Instead of Serial Number
**Problem**: Entities were using entry_id/title instead of serial number for identification.

**Solution**: Implemented dynamic device_info properties in all entity base classes:
- `number.py`: Added `device_info` property that updates when data becomes available
- `sensor.py`: Added `device_info` property (same logic)
- `button.py`: Added `device_info` property (same logic)

### 4. ⚠️ Modbus Decoding Errors
**Problem**: "Unable to decode frame" errors suggesting communication issues.

**Solution**: Added retry logic with exponential backoff in hub's `read_holding_registers()`:
- 3 retry attempts
- Exponential backoff (0.1s, 0.2s)
- Better error logging

## Files Modified

### `/custom_components/midnite/coordinator.py`
1. Added `"setpoints"` and `"eeprom_settings"` register groups
2. Enhanced `_async_update_data()` with connection testing and reconnection logic
3. Improved error handling throughout

### `/custom_components/midnite/hub.py`
1. Added retry logic to `read_holding_registers()` method
2. Added exponential backoff for retries
3. Better error logging

### `/custom_components/midnite/number.py`
1. Simplified `__init__` to avoid data availability issues
2. Added dynamic `device_info` property that updates when serial number becomes available

### `/custom_components/midnite/sensor.py`
1. Simplified `__init__` in base class
2. Added dynamic `device_info` property

### `/custom_components/midnite/button.py`
1. Simplified `__init__` in base class
2. Added dynamic `device_info` property

## Key Improvements

### 1. Dynamic Device Identification
Entities now start with entry_id-based identification and automatically switch to serial number when data becomes available. This prevents initialization errors while still providing proper device identification.

### 2. Robust Connection Handling
- Automatic reconnection attempts
- Connection testing before data reads
- Better error recovery
- Retry logic for individual register reads

### 3. Complete Register Coverage
All number entity registers are now included in register groups, ensuring they can be read properly.

### 4. Improved Error Handling
- Proper use of `UpdateFailed` exceptions
- More descriptive error messages
- Better logging at different levels (debug, warning, error)

## Testing Recommendations

1. **Restart Home Assistant** to load the updated integration
2. **Verify number entities**: Check that all input numbers display current values and can be adjusted
3. **Check device identification**: Verify that entities show serial number in device info (may take one data refresh cycle)
4. **Monitor logs**: Look for connection errors and retry attempts
5. **Test connection recovery**: Unplug/replug the device to verify automatic reconnection

## Expected Behavior After Fixes

1. ✅ Number controls display current values from device
2. ✅ Connection automatically recovers if dropped
3. ✅ Devices identified by serial number (when available)
4. ✅ Reduced Modbus decoding errors due to retry logic
5. ✅ No initialization errors due to dynamic device_info

## Migration Notes

- Existing configurations will continue to work without changes
- Device identification may change from IP-based to serial-number-based after first successful data read
- This is a non-breaking change that improves reliability and user experience
