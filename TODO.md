# TODO - Midnite Solar Integration Issues

## Completed Issues ✅

### 4. Invalid Battery Temperature Readings (FIXED ✅)
**Error**: "Invalid battery temperature reading: 6505.1°C" (previously logged for valid temps)
**Location**: `sensor.py:342, 418, 454`
**Status**: ✅ FIXED AND VERIFIED

**Analysis**:
According to Midnite Solar documentation:
- Register 4132 (BATT_TEMPERATURE): ([4132] / 10) °C - Temperature measured at the external Battery Temperature Sensor (if installed, else 25°C)
- Register 4133 (FET_TEMPERATURE): ([4133] / 10) °C - Temperature of Power FETs
- Register 4134 (PCB_TEMPERATURE): ([4134] / 10) °C - Temperature of the Classic Control (top) PCB

All three temperature registers use the same scaling factor (/10). The issue was NOT with the decoding logic itself, which is correct. The problem was in the validation logic:

**Root Cause**: In `sensor.py`, the temperature validation was checking the raw register value instead of the converted temperature value:
```python
# BUGGY CODE (previously at lines 382 and 418):
if value < -50 or value > 150:  # Checking raw register value
```
Since raw register values are in tenths of a degree, valid temperatures like 42.3°C (raw value 423) would fail validation.

**Fix Applied**: Changed validation to check `temp_value` instead:
```python
# FIXED CODE (now at lines 382, 418, and 454):
if temp_value < -50 or temp_value > 150:  # Checking converted temperature value
```

This allows valid temperatures between -50°C and 150°C to be accepted.

**Verification**: Created and ran test script (`test_temperature_fix.py`) that confirms:
- ✅ Valid temperatures (42.3°C, 40.8°C, 25.0°C) are now accepted
- ✅ Invalid temperatures (>150°C, <-50°C) are correctly rejected
- ✅ Edge cases like absurd values (6505.1°C) are properly filtered

**Files Modified**:
- `custom_components/midnite/sensor.py` - Fixed battery temperature validation logic for all three temperature sensors (BatteryTemperatureSensor, FETTemperatureSensor, PCBTemperatureSensor)

**Impact**: Temperature sensors now display valid readings without spurious warning messages.

---

## Critical Issues to Resolve

### 1. Connection Test Failures (High Priority)
**Error**: "Connection test failed - device not responding"
**Location**: `coordinator.py:126, 129`

**Analysis**: 
- The connection test reads register 4101 (UNIT_ID) but consistently fails
- This happens during initialization and periodic updates
- Possible causes:
  - Device not ready after HA restart (timing issue)
  - Register address incorrect or device doesn't support it
  - Connection not fully established when test runs

**Action Items**:
1. Add delay before first connection attempt to allow device to initialize
2. Make connection test more robust with multiple retry attempts
3. Log detailed connection status information
4. Consider making connection test optional or less aggressive
5. Verify register 4101 actually exists on the device

---

### 2. Modbus Decoding Errors (High Priority)
**Error**: "Unable to decode frame Modbus Error: [Input/Output] byte_count 2 > length of packet 1"
**Location**: `hub.py:56`
**Frequency**: 60+ occurrences

**Analysis**:
- Happens regularly during register reads
- Suggests mismatch between expected and actual packet sizes
- Could be device-specific communication issue

**Action Items**:
1. Add detailed logging to identify which specific registers fail
2. Implement per-register retry logic with different strategies
3. Check if this is related to specific register addresses or groups
4. Review pymodbus version compatibility
5. Consider adding packet size validation/handling

---

### 3. Serial Number Register Failures (High Priority)
**Error**: "All 3 attempts failed for address 20492, 20493, 4101"
**Location**: `hub.py:69`

**Analysis**:
- Addresses 20492 and 20493 are SERIAL_NUMBER_MSB/LSB
- Address 4101 is UNIT_ID (used for connection test)
- These failures prevent device identification by serial number
- May indicate these registers don't exist or are inaccessible on this device model

**Action Items**:
1. Verify these register addresses in the Midnite Solar documentation
2. Check if different device models use different register maps
3. Add fallback mechanism when serial number registers fail
4. Log which specific devices/models have these issues
5. Consider making serial number optional for device identification

---



---

## Potential Bugs Identified from Context

### 1. Connection Test Timing Issue
**Location**: `coordinator.py` `_async_update_data()`

The current code tries to connect and immediately tests with a read:
```python
if not self.api.is_still_connected():
    await self.hass.async_add_executor_job(self.api.connect)
# Then immediately tests connection
```

**Potential Fix**: Add small delay after connect before testing:
```python
import asyncio
...
await self.hass.async_add_executor_job(self.api.connect)
await asyncio.sleep(0.5)  # Allow device to respond
```

### 2. Retry Logic May Be Too Aggressive
**Location**: `hub.py` `read_holding_registers()`

Current retry uses exponential backoff (0.1s, 0.2s) but:
- Only 3 attempts total
- No distinction between different types of failures
- All retries use same approach

**Potential Improvement**: Different strategies for different failure modes

### 3. Temperature Validation Logic (FIXED ✅)
**Location**: `sensor.py` battery temperature sensor

**Issue**: The validation logic was checking the raw register value instead of the converted temperature value, causing valid temperatures to be rejected.

**Fix Applied**: Changed from:
```python
if value < -50 or value > 150:  # Checking raw register value (BUG)
```
To:
```python
if temp_value < -50 or temp_value > 150:  # Checking converted temperature value (FIXED)
```

**Status**: ✅ COMPLETED AND VERIFIED
- The code now handles two's complement for negative temperatures correctly
- Validation happens AFTER conversion, which is correct
- All three temperature sensors (BatteryTemperatureSensor, FETTemperatureSensor, PCBTemperatureSensor) have been fixed

---

## Documentation Needed

1. **Register Map Verification**: Confirm all register addresses match the actual device
2. **Device Model Differences**: Document which registers work on different Midnite models
3. **Temperature Scaling**: Verify correct scaling factor for temperature registers
4. **Connection Sequence**: Document proper connection initialization sequence
5. **Error Recovery**: Document expected behavior during connection losses

---

## Testing Strategy

1. ✅ **Temperature Validation Fix**: Verified with test script that validation now correctly accepts valid temperatures
2. 🔄 **Initial Connection**: Test with fresh HA restart to verify timing issues
3. ✅ **Register Verification**: Read and log raw values from all registers (debug logging added)
4. 🔄 **Temperature Calibration**: Compare sensor readings with actual device display
5. 🔄 **Connection Stability**: Test over extended period (hours) for drop/reconnect
6. 🔄 **Different Models**: Test on multiple Midnite device models if available

---

## Immediate Next Steps

1. ✅ **Fix Temperature Validation Logic** - Changed validation to check `temp_value` instead of raw `value`
2. ✅ **Add Debug Logging** to capture raw register values and connection status
3. 🔄 **Verify Register Map** against official Midnite Solar documentation
4. ✅ **Implement Connection Delay** before first read attempt
5. 🔄 **Test Serial Number Fallback** mechanism for devices without those registers

## Summary of Completed Work

### ✅ Temperature Validation Fix (Issue #4) - COMPLETED
**Problem**: Battery temperature sensor was logging warnings for valid temperatures like 42.3°C and 40.8°C, indicating the validation logic was flawed.

**Root Cause**: The validation was checking the raw register value (e.g., 423) instead of the converted temperature value (42.3°C).

**Solution Applied**: 
- Modified `sensor.py` lines 342, 418, and 454 in all three temperature sensor classes:
  - `BatteryTemperatureSensor.native_value()`
  - `FETTemperatureSensor.native_value()`
  - `PCBTemperatureSensor.native_value()`
- Changed from: `if value < -50 or value > 150:`
- Changed to: `if temp_value < -50 or temp_value > 150:`

**Verification**: Created and ran test script (`test_temperature_fix.py`) that confirms:
- ✅ Valid temperatures (42.3°C, 40.8°C, 25.0°C) are now accepted
- ✅ Invalid temperatures (>150°C, <-50°C) are correctly rejected
- ✅ Edge cases like absurd values (6505.1°C) are properly filtered

**Files Modified**:
- `custom_components/midnite/sensor.py` - Fixed temperature validation logic for all three temperature sensors

**Impact**: Temperature sensors now display valid readings without spurious warning messages.

---

### ✅ Enhanced Debug Logging and Connection Management - COMPLETED
**Problem**: Connection test failures, Modbus decoding errors, and serial number register failures were occurring with insufficient debugging information to diagnose root causes.

**Solution Applied**:

1. **Enhanced Retry Logic in hub.py**:
   - Increased max retries from 3 to 5 for better reliability
   - Added detailed debug logging for each retry attempt
   - Increased exponential backoff from 0.1s to 0.2s
   - Added success confirmation logging with register values

2. **Connection Delay Implementation in coordinator.py**:
   - Added 0.5 second delay after initial connection to allow device initialization
   - Added 0.3 second pause before reconnect attempts
   - Added detailed debug logging for connection test process
   - Included UNIT_ID value in successful connection logs

3. **Enhanced Register Reading Debugging**:
   - Added register name mapping to debug logs using REGISTER_MAP
   - Log successful reads with register values
   - Changed failed reads from DEBUG to WARNING level for better visibility
   - Track and log all failed registers at the end of each group read
   - Added exc_info=True to exceptions for full stack traces in logs

**Files Modified**:
- `custom_components/midnite/hub.py` - Enhanced retry logic with better debug logging
- `custom_components/midnite/coordinator.py` - Added connection delays and detailed debugging

**Impact**: 
- Better visibility into connection issues and register read failures
- Connection test is now less aggressive with proper timing
- Easier diagnosis of Modbus communication problems
- Improved reliability through increased retries and backoff times
