# Sensor Fix Summary - Version 2

## Problem Identified

After the initial fix, we discovered that some sensors still showed "unknown" values:
- ✅ **Working**: KW_HOURS, STATUSROLL, INFO_FLAGS_BITS3
- ❌ **Not Working**: RESTART_TIME_MS, UNIT_SW_DATE_RO, UNIT_SW_DATE_MONTH_DAY, HIGHEST_VINPUT_LOG, JrAmpHourNET, MATCH_POINT_SHADOW

### Root Cause - Part 2

The sensors were hardcoded to look for their data in specific groups (like "status"), but we had moved some registers to different groups in the coordinator:
- `UNIT_SW_DATE_RO` and `UNIT_SW_DATE_MONTH_DAY` were looking in "status" but we put them in "device_info"
- `RESTART_TIME_MS` was looking in "status" but we put it in "time_settings"
- `HIGHEST_VINPUT_LOG`, `JrAmpHourNET`, and `MATCH_POINT_SHADOW` were looking in "status" but we put them in "advanced_status"

## Solution Implemented

Updated the sensor classes to look for their data in the correct groups:

### 1. Device Info Sensors (moved from "status" to "device_info")
- **UNIT_SW_DATE_ROSensor** - Now looks in `device_info_data` instead of `status_data`
- **UNIT_SW_DATE_MONTH_DAYSensor** - Now looks in `device_info_data` instead of `status_data`

### 2. Time Settings Sensor (moved from "status" to "time_settings")
- **RESTART_TIME_MSSensor** - Now looks in `time_settings_data` instead of `status_data`

### 3. Advanced Status Sensors (moved from "status" to "advanced_status")
- **HIGHEST_VINPUT_LOGSensor** - Now looks in `advanced_status_data` instead of `status_data`
- **JrAmpHourNETSensor** - Now looks in `advanced_status_data` instead of `status_data`
- **MATCH_POINT_SHADOWSensor** - Now looks in `advanced_status_data` instead of `status_data`

## Files Modified

1. **custom_components/midnite/coordinator.py** (Initial fix)
   - Added missing registers to appropriate register groups

2. **custom_components/midnite/sensor.py** (This fix)
   - Updated 6 sensor classes to look in the correct data groups

## Testing

After this fix, ALL the following sensors should now display values:
- ✅ KW_HOURS - Energy to battery (daily)
- ✅ STATUSROLL - Status counter
- ✅ INFO_FLAGS_BITS3 - System status flags  
- ✅ RESTART_TIME_MS - Wake-up timer
- ✅ UNIT_SW_DATE_RO - Software build date
- ✅ UNIT_SW_DATE_MONTH_DAY - Software build month/day
- ✅ HIGHEST_VINPUT_LOG - Highest input voltage seen (when advanced mode enabled)
- ✅ JrAmpHourNET - Whizbang Jr net amp-hours (when advanced mode enabled)
- ✅ MATCH_POINT_SHADOW - Wind power curve step (when advanced mode enabled)

## Next Steps for Better Sensor Names

As mentioned in your feedback, the sensor naming could be improved. Here are some suggestions:

### Current Names vs Suggested Improvements

| Current Name | Suggested Name |
|--------------|----------------|
| WATTS | Avg Pwr to Battery |
| DISP_AVG_VBATT | Avg Batt Voltage |
| DISP_AVG_VPV | Avg PV Voltage |
| IBATT_DISPLAY_S | Avg Batt Current |
| KW_HOURS | Daily Energy |
| PV_INPUT_CURRENT | PV Input Current |
| VOC_LAST_MEASURED | Last Open Circuit V |
| BATT_TEMPERATURE | Battery Temp |
| FET_TEMPERATURE | FET Temp |
| PCB_TEMPERATURE | PCB Temp |

### Implementation Plan for Better Names

1. Create a CSV file with columns: Address, RegisterName, DisplayName, Category
2. Use the DisplayName column to generate user-friendly entity names
3. Remove the "Enabled by Default" column as suggested - just use Category (B, A, D)
4. Enable all sensors regardless of category for testing purposes
5. Later, implement proper filtering based on configuration options

Would you like me to proceed with implementing the better sensor naming scheme?
