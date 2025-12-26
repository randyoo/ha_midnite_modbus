# Current Status - Sensor Fix Progress

## What Has Been Fixed ✅

### Phase 1: Data Group Lookup Fixes (COMPLETED)

The following sensors have been updated to look in the correct coordinator data groups:

**Temperature Sensors** (now use `temperatures` group):
- ✅ BATT_TEMPERATURE (register 4121)
- ✅ FET_TEMPERATURE (register 4122)  
- ✅ PCB_TEMPERATURE (register 4123)

**Time Settings Sensors** (now use `time_settings` group):
- ✅ ABSORB_TIME (register 4125)
- ✅ EQUALIZE_TIME (register 4126) - **This was reported as not working**
- ✅ FLOAT_TIME_TODAY_SEC (register 4124)
- ✅ RESTART_TIME_MS (register 4127) - Already correct

**Energy Sensors** (now use `energy` group):
- ✅ AMP_HOURS_DAILY (register 4115)
- ✅ LIFETIME_KW_HOURS_1 (register 4116)

**Other Sensors Already Correct**:
- ✅ HIGHEST_VINPUT_LOG, JrAmpHourNET, MATCH_POINT_SHADOW (use `advanced_status` group)
- ✅ KW_HOURS, STATUSROLL, INFO_FLAGS_BITS3 (use `status` group)

## What Still Needs Fixing ⚠️

### Sensors Looking in Wrong Data Groups

Out of 176 total sensor classes, **158 are using status_data**. Many of these are correct (DISP_AVG_VBATT, KW_HOURS, STATUSROLL, INFO_FLAGS_BITS3 are actually in the status group), but approximately **~90 sensors** need to be updated to look in other groups.

Here's a breakdown of what needs fixing:

**Energy Group Sensors**:
- LIFETIME_KW_HOURS_1_HIGH (register 4117)
- LIFETIME_AMP_HOURS_1 (register 4118)
- LIFETIME_AMP_HOURS_1_HIGH (register 4119)

**Diagnostics Group Sensors**:
- REASON_FOR_RESTING (register 4128)

**Setpoints Group Sensors**:
- ABSORB_SETPOINT_VOLTAGE, FLOAT_VOLTAGE_SETPOINT, EQUALIZE_VOLTAGE_SETPOINT, BATTERY_OUTPUT_CURRENT_LIMIT

**EEPROM Settings Group Sensors**:
- ABSORB_TIME_EEPROM, EQUALIZE_TIME_EEPROM, EQUALIZE_INTERVAL_DAYS_EEPROM

**Advanced Config Group Sensors**:
- MPPT_MODE, AUX_1_AND_2_FUNCTION, VARIMAX, ENABLE_FLAGS3, ENABLE_FLAGS2, ENABLE_FLAGS_BITS

**Aux Control Group Sensors**:
- AUX1_VOLTS_LO_ABS, AUX1_VOLTS_HI_ABS, AUX1_DELAY_T_MS, AUX1_HOLD_T_MS, etc.

**Voltage Offset Group Sensors**:
- VBATT_OFFSET, VPV_OFFSET, VPV_TARGET_RD, VPV_TARGET_WR

**Temperature Compensation Group Sensors**:
- MAX_BATTERY_TEMP_COMP_VOLTAGE, MIN_BATTERY_TEMP_COMP_VOLTAGE, BATTERY_TEMP_COMP_VALUE

### Sensors Not Being Read at All ❌

These sensors reference registers that are **NOT** in any coordinator group and therefore will never work until the coordinator is updated:

- DNS_1_LSB_1, DNS_1_LSB_2, DNS_2_LSB_1, DNS_2_LSB_2 (network settings)
- IP_ADDRESS_LSB_1, IP_ADDRESS_LSB_2, GATEWAY_ADDRESS_LSB_1, etc. (network settings)
- Many EEPROM and configuration registers

## Testing Instructions

To test if the fixes are working:

1. **Restart Home Assistant** after updating the sensor.py file
2. Check the logs for errors: `journalctl -u home-assistant -f` or check HA logs
3. Look at sensor states in the HA UI - they should show actual values instead of "unknown"
4. Check debug logs to see which data groups are being populated:
   ```python
   # In custom_components/midnite/coordinator.py, add logging:
   _LOGGER.debug(f"Data groups read: {list(data.keys())}")
   for group_name, registers in data.items():
       _LOGGER.debug(f"  {group_name}: {len(registers)} registers")
   ```

## Next Steps

### Immediate (High Priority)
1. **Continue fixing remaining sensors** - Update all ~100 remaining sensors to look in correct data groups
2. **Add missing register groups to coordinator** - Add network settings and other commonly used registers
3. **Test with actual device** - Verify sensors show real values

### Medium Priority
4. **Create improved sensor naming CSV** - Map register names to user-friendly display names
5. **Update sensor entity names** - Use the new display names for better UX
6. **Implement category-based enabling** - Enable Basic (B) by default, allow Advanced (A) and Debug (D) to be enabled

### Low Priority
7. **Clean up unused sensors** - Remove sensors that aren't used or don't have registers defined
8. **Add documentation** - Update README with sensor descriptions and usage
9. **Create test suite** - Add unit tests for sensor data retrieval

## Files Modified

- `custom_components/midnite/sensor.py` - Updated sensor data group lookups (6 sensors fixed so far)
- `SENSOR_FIX_SUMMARY.md` - Documentation of the fix approach

## Technical Details

### How Sensors Retrieve Data

Each sensor's `native_value` property queries a specific data group from the coordinator:

```python
# Correct pattern:
temperatures_data = self.coordinator.data["data"].get("temperatures")
value = temperatures_data.get(REGISTER_MAP["PCB_TEMPERATURE"])

# Wrong pattern (before fix):
status_data = self.coordinator.data["data"].get("status")  # ❌ Wrong group!
value = status_data.get(REGISTER_MAP["PCB_TEMPERATURE"])  # Returns None
```

### Coordinator Data Structure

The coordinator returns data organized by groups:

```python
{
    "data": {
        "device_info": {4103: value, 4106: value, ...},
        "status": {4105: value, 4108: value, ...},
        "temperatures": {4121: value, 4122: value, 4123: value},
        "energy": {4115: value, 4116: value, ...},
        "time_settings": {4124: value, 4125: value, ...},
        "advanced_status": {4137: value, 4138: value, ...},
        # ... other groups
    },
    "availability": {...}
}
```

### Register Conflicts

Some registers appear in multiple groups due to address conflicts:
- Register 4108 appears in both `device_info` (MAC_ADDRESS_PART_3) and `status` (WATTS)
- Registers 4111-4112 appear in both `device_info` (DEVICE_ID) and `status` (VOC_LAST_MEASURED, KW_HOURS)
- Registers 4115-4119 appear in both `device_info` (UNIT_NAME) and `energy` (AMP_HOURS_DAILY, etc.)

These conflicts need to be resolved by either:
1. Updating the coordinator to read these registers only once
2. Creating a unified data structure that handles overlapping registers
3. Documenting which group takes precedence for each conflicting register
