# Sensor Fix Summary

## Problem Analysis
Many sensors in the Midnite Solar integration were showing "unknown" values while input_numbers and a few key sensors were working correctly.

### Root Cause
The coordinator (`coordinator.py`) only reads specific groups of registers, but many sensor registers defined in `sensor.py` were not included in these register groups. The sensors that worked were those whose registers were already being read by the coordinator.

## Solution Implemented

Updated `custom_components/midnite/coordinator.py` to add missing registers to the appropriate register groups based on their category:
- **B** = Basic (always enabled)
- **A** = Advanced (opt-in via advanced mode)
- **D** = Debug (opt-in via debug mode)

### Registers Added

#### Basic Sensors (Category "B" - Always Enabled)
Added to the coordinator's register groups:

1. **KW_HOURS** (4118) - Energy to the battery (reset daily)
   - Added to: `status` group
   
2. **STATUSROLL** (4113) - 12-bit status value, updated once per second
   - Added to: `status` group
   
3. **INFO_FLAGS_BITS3** (4104) - Classic system status flags (bitfield)
   - Added to: `status` group
   
4. **RESTART_TIME_MS** (4114) - Time after which classic can wake up
   - Added to: `time_settings` group
   
5. **UNIT_SW_DATE_RO** (4102) - Software build date
   - Added to: `device_info` group
   
6. **UNIT_SW_DATE_MONTH_DAY** (4103) - Software build month/day
   - Added to: `device_info` group

#### Advanced Sensors (Category "A" - Opt-in via Advanced Mode)
Added to the coordinator's register groups:

7. **HIGHEST_VINPUT_LOG** (4123) - Highest input voltage seen (eeprom)
   - Added to: `advanced_status` group
   
8. **JrAmpHourNET** (4109) - Whizbang jr. net amp-hours
   - Added to: `advanced_status` group
   
9. **MATCH_POINT_SHADOW** (4124) - Current wind power curve step (1-16)
   - Already present in: `advanced_status` group

### Sensors Still Showing "Unknown"
The following sensors remain showing "unknown" because they are in the Debug category and require debug mode to be enabled:

- **RESERVED_4105** (4105) - Unimplemented - avoid writing
- Other debug registers (DABT_U32_DEBUG_*, WIZBANG_RX_BUFFER_TEMP_*, etc.)

These can be added if you enable debug mode in the configuration.

## Why Input Numbers Worked
Input numbers continued to work because they read from registers that were already included in the coordinator's register groups:
- Setpoints: ABSORB_SETPOINT_VOLTAGE, FLOAT_VOLTAGE_SETPOINT, EQUALIZE_VOLTAGE_SETPOINT, BATTERY_OUTPUT_CURRENT_LIMIT
- EEPROM settings: ABSORB_TIME_EEPROM, EQUALIZE_TIME_EEPROM, EQUALIZE_INTERVAL_DAYS_EEPROM

## Testing
After this fix, the following sensors should now display values instead of "unknown":
- ✅ KW_HOURS
- ✅ STATUSROLL  
- ✅ INFO_FLAGS_BITS3
- ✅ RESTART_TIME_MS
- ✅ UNIT_SW_DATE_RO
- ✅ UNIT_SW_DATE_MONTH_DAY
- ✅ HIGHEST_VINPUT_LOG (when advanced mode is enabled)
- ✅ JrAmpHourNET (when advanced mode is enabled)
- ✅ MATCH_POINT_SHADOW (when advanced mode is enabled)

## Files Modified
- `custom_components/midnite/coordinator.py` - Added missing registers to REGISTER_GROUPS

## Next Steps
If you need additional sensors to work, you can:
1. Enable Advanced mode in the integration configuration for more sensors
2. Enable Debug mode for debug-level sensors (not recommended for production use)
3. The coordinator already has groups defined for these categories that just need to be populated with more registers as needed
