# Device Identification Summary

## Current State

The integration is correctly reading the **Device ID** from registers 20492/20493, which matches what Midnite Solar shows on their website.

### What We're Reading
- **Registers**: 20492 (MSB) and 20493 (LSB)
- **Value Read**: 3365322520 (0xC896BF18)
- **Description**: Device ID / Classic serial number
- **Matches Website**: Yes - Midnite website shows "Device ID: C896 BF18"

### What We're NOT Reading (Yet)
- **Website Shows**: Serial Number 49880
- **Status**: This value is not being read from any Modbus register currently

## Device Creation Issue - FIXED

**Problem**: Two devices were being created in Home Assistant:
1. Sensors device: "Midnite Classic 250 (3365322520)"
2. Numbers/Buttons device: "Midnite Solar @ 192.168.88.24"

**Root Cause**: 
- Sensors were using `api.device_info` with proper identifiers
- Numbers and Buttons were creating their own device_info with just `entry.entry_id`

**Fix Applied**: Updated `number.py` and `button.py` to use the same device_info as sensors.

## Serial Number Investigation

### Registers Checked
1. **Registers 20492/20493**: 
   - Description: "Classic serial number MSB/LSB – used to unlock Ethernet write"
   - Value Read: 3365322520 (0xC896BF18)
   - Matches: Device ID on Midnite website
   - Note: Description mentions "used to unlock Ethernet write" suggesting security purpose

2. **Registers 4111/4112** (DEVICE_ID):
   - Description: "Device ID (clone of 4360)"
   - Same value as 20492/20493

### Possible Explanations
1. **The Device ID IS the Serial Number**: The website might be displaying the same value in two different ways
2. **Serial Number Not Accessible via Modbus**: Some information might only be available through other interfaces
3. **Different Register**: The actual serial number (49880) might be stored in a register we haven't checked yet

### Next Steps for Serial Number
If you need the serial number to match exactly what Midnite shows:
1. Check if there are any other registers that might contain this value
2. Verify with Midnite support which register contains the actual product serial number
3. Update the code to read from the correct register

## Current Device Naming

With the fix applied, all entities (sensors, numbers, buttons) will now belong to a single device with:
- **Identifier**: `(DOMAIN, "3365322520")` or `(DOMAIN, "hostname")` if reading fails
- **Name**: `"Midnite Classic 250 (3365322520)"` or `"Midnite Device @ hostname"` if reading fails

## Testing Recommendations

1. **Verify Device ID**: Confirm that 3365322520 (0xC896BF18) is the correct identifier for your device
2. **Check Serial Number Location**: If you need the serial number to be exactly 49880, investigate which register contains this value
3. **Test Connection Resilience**: Verify that the retry logic handles temporary connection issues properly
