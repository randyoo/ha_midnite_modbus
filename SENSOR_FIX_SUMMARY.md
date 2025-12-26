# Sensor Data Group Fix Summary

## Problem Analysis

Most sensors in `custom_components/midnite/sensor.py` are hardcoded to look for their data in the `status` data group:

```python
status_data = self.coordinator.data["data"].get("status")
value = status_data.get(REGISTER_MAP["SENSOR_NAME"])
```

However, the coordinator (`custom_components/midnite/coordinator.py`) organizes registers into multiple groups:
- `device_info`
- `status`
- `temperatures`
- `energy`
- `time_settings`
- `diagnostics`
- `setpoints`
- `eeprom_settings`
- `advanced_status`

## Root Cause

Sensors are looking in the wrong data group for their register values. For example:

1. **PCB_TEMPERATURE** (register 4123) is in the `temperatures` group, but the sensor looks in `status`
2. **EQUALIZE_TIME** (register 4126) is in the `time_settings` group, but the sensor looks in `status`
3. **DNS_1_LSB_1** and similar network sensors are not being read at all

## Solution Strategy

### Immediate Fix (Priority)
Update sensors to look in the correct data groups based on their register:

```python
# Current (wrong):
status_data = self.coordinator.data["data"].get("status")
value = status_data.get(REGISTER_MAP["PCB_TEMPERATURE"])

# Fixed:
temperatures_data = self.coordinator.data["data"].get("temperatures")
value = temperatures_data.get(REGISTER_MAP["PCB_TEMPERATURE"])
```

### Register Group Mapping

| Sensor Name | Register | Coordinator Group | Current Lookup | Fixed Lookup |
|-------------|----------|-------------------|----------------|--------------|
| PCB_TEMPERATURE | 4123 | temperatures | status_data | temperatures_data |
| BATT_TEMPERATURE | 4121 | temperatures | status_data | temperatures_data |
| FET_TEMPERATURE | 4122 | temperatures | status_data | temperatures_data |
| EQUALIZE_TIME | 4126 | time_settings | status_data | time_settings_data |
| ABSORB_TIME | 4125 | time_settings | status_data | time_settings_data |
| FLOAT_TIME_TODAY_SEC | 4124 | time_settings | status_data | time_settings_data |
| RESTART_TIME_MS | 4127 | time_settings | time_settings_data ✓ | (already correct) |
| AMP_HOURS_DAILY | 4115 | energy | status_data | energy_data |
| LIFETIME_KW_HOURS_1 | 4116 | energy | status_data | energy_data |
| HIGHEST_VINPUT_LOG | 4137 | advanced_status | advanced_status_data ✓ | (already correct) |
| JrAmpHourNET | 4138 | advanced_status | advanced_status_data ✓ | (already correct) |
| MATCH_POINT_SHADOW | 4139 | advanced_status | advanced_status_data ✓ | (already correct) |

### Sensors Not Being Read

These sensors reference registers that are NOT in any coordinator group and therefore won't work until the coordinator is updated:

- DNS_1_LSB_1, DNS_1_LSB_2, DNS_2_LSB_1, DNS_2_LSB_2 (network settings)
- IP_ADDRESS_LSB_1, IP_ADDRESS_LSB_2, GATEWAY_ADDRESS_LSB_1, etc. (network settings)
- Many EEPROM and configuration registers

## Implementation Plan

### Phase 1: Fix Existing Sensors (High Priority)
Update all sensors to look in the correct data group based on their register.

### Phase 2: Add Missing Register Groups (Medium Priority)
Add network settings and other commonly used registers to coordinator groups.

### Phase 3: Sensor Naming Improvements (Low Priority)
Create improved display names for sensors as requested.

## Files to Modify

1. `custom_components/midnite/sensor.py` - Update sensor data group lookups
2. `custom_components/midnite/coordinator.py` - Add missing register groups (Phase 2)
3. Create `registers_improved.csv` - For sensor naming improvements (Phase 3)
