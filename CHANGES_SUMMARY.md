# Summary of Changes

## Issues Addressed

### 1. Charge Stage Sensor Fix ✅
**Problem**: Sensor always showed "Rest" even when device was in other states.

**Solution**: 
- Fixed CHARGE_STAGES mapping in `const.py` with correct device values (0, 3, 4, 5, 6, 7, 10, 18)
- Corrected bit extraction to use MSB: `(value >> 8) & 0xFF`
- Added INTERNAL_STATES mapping for LSB decoding
- Verified with test cases including problematic values (1027, 1028)

### 2. Multiple Devices Issue ✅
**Problem**: Two devices created - one for sensors, one for numbers/buttons.

**Solution**: 
- Updated `number.py` base class to use `api.device_info` instead of creating new device_info
- Updated `button.py` base class to use `api.device_info` instead of creating new device_info
- Sensors already using correct pattern, no changes needed

### 3. Serial Number / Device Identification ✅
**Problem**: Device ID showing as 3365322520 but website shows serial number 49880.

**Solution**: 
- Confirmed we're correctly reading Device ID from registers 20492/20493
- This matches Midnite website's "Device ID: C896 BF18" (same value)
- Updated documentation to clarify Device ID vs Serial Number
- Added fallback naming when serial number can't be read

### 4. Connection Errors ✅
**Problem**: Modbus connection errors causing integration to fail.

**Solution**: 
- Added retry logic (3 attempts) with exponential backoff
- Improved connection validation before each read
- Enhanced error handling and reconnection logic
- Comprehensive logging at DEBUG level for troubleshooting

## Files Modified

### custom_components/midnite/const.py
- Corrected CHARGE_STAGES mapping
- Added INTERNAL_STATES mapping
- Verified register addresses

### custom_components/midnite/__init__.py
- Enhanced `read_device_info()` with retry logic
- Improved connection handling in `read_holding_registers()`
- Better error messages and logging
- Updated device naming logic

### custom_components/midnite/sensor.py
- No changes needed (already using correct pattern)

### custom_components/midnite/number.py
- Updated base class `__init__` to use `api.device_info`
- Ensures all numbers belong to same device as sensors

### custom_components/midnite/button.py
- Updated base class `__init__` to use `api.device_info`
- Ensures all buttons belong to same device as sensors

### custom_components/midnite/config_flow.py
- No changes needed

## Testing Recommendations

1. **Charge Stage Sensor**: Verify it shows correct state (BulkMPPT, Float, Absorb, etc.) matching the device display
2. **Single Device**: Confirm only one device is created in Home Assistant with all entities
3. **Device ID**: Verify 3365322520 (or your device's value) is correct identifier
4. **Connection Resilience**: Test with intermittent network to verify retry logic works

## Known Limitations

1. **Serial Number Mismatch**: 
   - We read Device ID (3365322520 = 0xC896BF18)
   - Midnite website shows Serial Number 49880
   - These may be different values or the serial number might not be accessible via Modbus

2. **Register Documentation**: 
   - Some registers in registers.json may have incorrect descriptions
   - Registers 20492/20493 described as "serial number" but used for Device ID

## Next Steps

1. Test with actual Midnite Solar device to verify all functionality
2. Investigate if serial number 49880 is stored in a different register
3. Consider adding more sensors based on available registers
