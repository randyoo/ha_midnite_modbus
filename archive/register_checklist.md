# Midnite Solar Classic Register Checklist

## Legend
- ✅ - Register is being read by the integration
- ❌ - Register is NOT being read by the integration
- 📝 - Register is written to (for setpoints/configuration)

## Device Information Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4100 | Connection Test | ✅ | config_flow |
| 4101 | UNIT_ID | ✅ | device_info |
| 4102 | UNIT_SW_DATE_RO | ❌ | - |
| 4103 | UNIT_SW_DATE_MONTH_DAY | ❌ | - |
| 4104 | INFO_FLAGS_BITS3 | ❌ | - |
| 4105 | RESERVED_4105 | ❌ | - |
| 4106-4108 | MAC_ADDRESS_PART_* | ✅ | device_info |
| 4109 | JrAmpHourNET/WBJr_AMP_HOUR_NET_LSW | ❌ | - |
| 4110 | WBJr_AMP_HOUR_NET_MSW | ❌ | - |
| 4111-4112 | DEVICE_ID_LSW/MSW | ✅ | device_info |
| 4113 | STATUSROLL | ❌ | - |
| 4114 | RESTART_TIME_MS | ❌ | - |

## Status Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4115 | DISP_AVG_VBATT | ✅ | Battery Voltage Sensor |
| 4116 | DISP_AVG_VPV | ✅ | PV Voltage Sensor |
| 4117 | IBATT_DISPLAY_S | ✅ | Battery Current Sensor |
| 4118 | KW_HOURS | ❌ | - |
| 4119 | WATTS | ✅ | Power Watts Sensor |
| 4120 | COMBO_CHARGE_STAGE | ✅ | Charge Stage & Internal State Sensors |
| 4121 | PV_INPUT_CURRENT | ✅ | PV Input Current Sensor |
| 4122 | VOC_LAST_MEASURED | ✅ | VOC Measured Sensor |
| 4123 | HIGHEST_VINPUT_LOG | ❌ | - |
| 4124 | MATCH_POINT_SHADOW | ❌ | - |
| 4125 | AMP_HOURS_DAILY | ✅ | Daily Amp Hours Sensor |

## Energy Tracking Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4126-4127 | LIFETIME_KW_HOURS_1 + high word | ✅ | Lifetime Energy Sensor |
| 4128-4129 | LIFETIME_AMP_HOURS_1 + high word | ✅ | Lifetime Amp Hours Sensor |

## Temperature Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4132 | BATT_TEMPERATURE | ✅ | Battery Temperature Sensor |
| 4133 | FET_TEMPERATURE | ✅ | FET Temperature Sensor |
| 4134 | PCB_TEMPERATURE | ✅ | PCB Temperature Sensor |

## Time Settings Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4135 | NITE_MINUTES_NO_PWR | ❌ | - |
| 4136 | MINUTE_LOG_INTERVAL_SEC | ❌ | - |
| 4137 | MODBUS_PORT_REGISTER | ❌ | - |
| 4138 | FLOAT_TIME_TODAY_SEC | ✅ | Float Time Today Sensor |
| 4139 | ABSORB_TIME | ✅ | Absorb Time Remaining Sensor |
| 4142 | REASON_FOR_RESET | ❌ | - |
| 4143 | EQUALIZE_TIME | ✅ | Equalize Time Remaining Sensor |

## Setpoint Registers (Read/Write)

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4148 | BATTERY_OUTPUT_CURRENT_LIMIT | 📝✅ | Battery Current Limit Number |
| 4149 | ABSORB_SETPOINT_VOLTAGE | 📝✅ | Absorb Voltage Setpoint Number |
| 4150 | FLOAT_VOLTAGE_SETPOINT | 📝✅ | Float Voltage Setpoint Number |
| 4151 | EQUALIZE_VOLTAGE_SETPOINT | 📝✅ | Equalize Voltage Setpoint Number |
| 4152 | SLIDING_CURRENT_LIMIT | ❌ | - |
| 4153 | MIN_ABSORB_TIME | ❌ | - |
| 4154 | ABSORB_TIME_EEPROM | 📝✅ | Absorb Time Number |
| 4155-4157 | MAX/BATTERY_TEMP_COMP_* | ❌ | - |
| 4158 | GENERAL_PURPOSE_WORD | ❌ | - |
| 4159 | EQUALIZE_RETRY_DAYS | ❌ | - |

## Force Flags (Write-Only)

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4160 | FORCE_FLAG_BITS/FORCE_FLAGS_LO/HI | ❌ | - |

## EEPROM Time Settings (Read/Write)

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4162 | EQUALIZE_TIME_EEPROM | 📝✅ | Equalize Time Number |
| 4163 | EQUALIZE_INTERVAL_DAYS_EEPROM | 📝✅ | Equalize Interval Days Number |

## MPPT and Auxiliary Settings

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4160 | FORCE_FLAG_BITS/FORCE_FLAGS_LO/HI | ✅ (partial) | Force Charge Mode Selector |
| 4164 | MPPT_MODE | ❌ | **POTENTIAL: MPPT Mode Selector** |
| 4165 | AUX_1_AND_2_FUNCTION | ❌ | - |
| 4166-4181 | AUX* settings | ❌ | - |

## Enable Flags

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4182-4183 | ENABLE_FLAGS* | ❌ | - |

## Calibration and Offset Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4189-4190 | VBATT_OFFSET, VPV_OFFSET | ❌ | - |

## Unit Name (Read/Write)

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4210-4213 | UNIT_NAME_* / ID_NAME_PARTS_* | 📝✅ | Unit Name Text Entity |

## Diagnostics Registers

| Address | Name | Status | Entity Type |
|---------|------|--------|-------------|
| 4275 | REASON_FOR_RESTING | ✅ | Rest Reason Sensor |

## Summary Statistics

**Total registers in both files:** ~150 unique registers

**Registers being read:** 30 registers

**Registers being written to:** 8 registers (setpoints and timings)

**Coverage:** The integration reads approximately 20% of available registers, focusing on core monitoring and configuration functions.
