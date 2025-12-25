# Midnite Solar Integration - Entity to Register Mapping

## Complete Reference Guide

This document provides a comprehensive mapping of every Home Assistant entity created by the integration to the specific Modbus registers it reads from or writes to.

## 📊 Sensor Entities

### Device Information Sensors
| Entity | Register(s) | Description |
|--------|-------------|-------------|
| Device Type | 4101 (UNIT_ID) | Hardware revision & device type |
| MAC Address | 4106-4108 | Ethernet MAC address |
| Device ID | 4111-4112 | Used as serial number identifier |

### Voltage Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Battery Voltage | 4115 (DISP_AVG_VBATT) | Average battery voltage (divided by 10) |
| PV Voltage | 4116 (DISP_AVG_VPV) | Average PV input voltage (divided by 10) |

### Current Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Battery Current | 4117 (IBATT_DISPLAY_S) | Average battery current (divided by 10, handles negative values) |
| PV Input Current | 4121 (PV_INPUT_CURRENT) | Average PV input current (divided by 10) |

### Power Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Power Watts | 4119 (WATTS) | Average power to battery (raw value) |

### Charge State Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Charge Stage | 4120 MSB (COMBO_CHARGE_STAGE) | Current charge stage (Resting, Absorb, BulkMPPT, Float, Equalize, etc.) |
| Internal State | 4120 LSB (COMBO_CHARGE_STAGE) | Internal MPPT state |

### Temperature Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Battery Temperature | 4132 (BATT_TEMPERATURE) | Battery temperature (°C, divided by 10) |
| FET Temperature | 4133 (FET_TEMPERATURE) | Power FET temperature (°C, divided by 10) |
| PCB Temperature | 4134 (PCB_TEMPERATURE) | Top PCB temperature (°C, divided by 10) |

### Energy Sensors
| Entity | Register(s) | Description |
|--------|-------------|-------------|
| Daily Amp Hours | 4125 (AMP_HOURS_DAILY) | Daily amp-hours (reset at 23:59, raw value) |
| Lifetime Energy | 4126-4127 (LIFETIME_KW_HOURS_1 + high word) | Lifetime energy generation (combined 32-bit, divided by 10) |
| Lifetime Amp Hours | 4128-4129 (LIFETIME_AMP_HOURS_1 + high word) | Lifetime amp-hour generation (combined 32-bit, raw value) |

### Time Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Float Time Today | 4138 (FLOAT_TIME_TODAY_SEC) | Seconds spent in float today (reset at midnight, raw value) |
| Absorb Time Remaining | 4139 (ABSORB_TIME) | Absorb time counter (raw value) |
| Equalize Time Remaining | 4143 (EQUALIZE_TIME) | Equalize time counter (raw value) |

### Diagnostic Sensors
| Entity | Register | Description |
|--------|----------|-------------|
| Rest Reason | 4275 (REASON_FOR_RESTING) | Reason Classic went to Rest mode (mapped to human-readable text) |
| VOC Measured | 4122 (VOC_LAST_MEASURED) | Last measured open-circuit voltage (divided by 10) |

## 🔢 Number Entities (Configurable Setpoints)

### Voltage Setpoints
| Entity | Register | Min | Max | Step | Unit | Description |
|--------|----------|-----|-----|------|------|-------------|
| Absorb Voltage | 4149 (ABSORB_SETPOINT_VOLTAGE) | 10.0 | 65.0 | 0.1 | V | Battery absorb stage voltage |
| Float Voltage | 4150 (FLOAT_VOLTAGE_SETPOINT) | 10.0 | 65.0 | 0.1 | V | Battery float stage voltage |
| Equalize Voltage | 4151 (EQUALIZE_VOLTAGE_SETPOINT) | 10.0 | 65.0 | 0.1 | V | Battery equalize stage voltage |

### Current Limit
| Entity | Register | Min | Max | Step | Unit | Description |
|--------|----------|-----|-----|------|------|-------------|
| Battery Current Limit | 4148 (BATTERY_OUTPUT_CURRENT_LIMIT) | 1.0 | 100.0 | 1.0 | A | Maximum battery output current |

### Time Settings
| Entity | Register | Min | Max | Step | Unit | Description |
|--------|----------|-----|-----|------|------|-------------|
| Absorb Time | 4154 (ABSORB_TIME_EEPROM) | 0 | 7200 | 60 | s | Duration battery stays in absorb stage |
| Equalize Time | 4162 (EQUALIZE_TIME_EEPROM) | 0 | 7200 | 60 | s | Duration of equalize stage |
| Equalize Interval | 4163 (EQUALIZE_INTERVAL_DAYS_EEPROM) | 0 | 365 | 1 | days | Days between automatic equalizations |

## 📝 Text Entities

### Device Configuration
| Entity | Register(s) | Description |
|--------|-------------|-------------|
| Unit Name | 4210-4213 (UNIT_NAME_*) | 8-character ASCII device name (read/write) |

## 🔧 Button Entities

(No button entities currently implemented in the integration)

## 📡 Select Entities

### Charge Mode Control
| Entity | Register(s) | Description |
|--------|-------------|-------------|
| Force Charge Mode | 4160 (FORCE_FLAG_BITS) | Write-only select to force Float/Bulk/Equalize modes |

**Note:** This entity writes to register 4160 but does not read MPPT_MODE from register 4164. The current charge stage is read from register 4120 (COMBO_CHARGE_STAGE).

## 🎛️ Device Information

The following registers contribute to device information:
- **Identifiers:** DEVICE_ID (registers 4111-4112)
- **Name:** Unit Name (registers 4210-4213) or entry title
- **Manufacturer:** "Midnite Solar"
- **Model:** Derived from UNIT_ID register (4101) - Classic 150/200/250/250 KS

## 🔄 Data Flow

### Reading Process
1. Coordinator reads all registers in groups during each update cycle
2. Register values are stored in coordinator data structure
3. Entities retrieve their specific register value from coordinator data
4. Values are converted using appropriate formulas (e.g., divide by 10 for voltages)

### Writing Process
1. User changes value in Home Assistant number entity
2. Value is converted to register format (multiply by 10 for voltages, except time values)
3. Write request is sent to device via Modbus write_register
4. Coordinator requests refresh to update all sensor values

## 📈 Register Groups

The coordinator organizes registers into these groups:

### device_info
- UNIT_ID (4101)
- DEVICE_ID_LSW/MSW (4111-4112)
- UNIT_NAME_* (4210-4213)
- MAC_ADDRESS_PART_* (4106-4108)

### status
- DISP_AVG_VBATT (4115)
- DISP_AVG_VPV (4116)
- IBATT_DISPLAY_S (4117)
- WATTS (4119)
- COMBO_CHARGE_STAGE (4120)
- PV_INPUT_CURRENT (4121)
- VOC_LAST_MEASURED (4122)

### temperatures
- BATT_TEMPERATURE (4132)
- FET_TEMPERATURE (4133)
- PCB_TEMPERATURE (4134)

### energy
- AMP_HOURS_DAILY (4125)
- LIFETIME_KW_HOURS_1 + high word (4126-4127)
- LIFETIME_AMP_HOURS_1 + high word (4128-4129)

### time_settings
- FLOAT_TIME_TODAY_SEC (4138)
- ABSORB_TIME (4139)
- EQUALIZE_TIME (4143)

### diagnostics
- REASON_FOR_RESTING (4275)

### setpoints
- ABSORB_SETPOINT_VOLTAGE (4149)
- FLOAT_VOLTAGE_SETPOINT (4150)
- EQUALIZE_VOLTAGE_SETPOINT (4151)
- BATTERY_OUTPUT_CURRENT_LIMIT (4148)

### eeprom_settings
- ABSORB_TIME_EEPROM (4154)
- EQUALIZE_TIME_EEPROM (4162)
- EQUALIZE_INTERVAL_DAYS_EEPROM (4163)

## 🔍 Formula Reference

| Register | Formula |
|----------|---------|
| Voltage registers (4115, 4116, 4122, etc.) | value / 10 → volts |
| Current registers (4117, 4121) | value / 10 → amps (handle negative values) |
| Time registers (4138, 4139, 4143, 4154, 4162) | raw value → seconds/days |
| 32-bit values (4126-4127, 4128-4129) | (high_word << 16) \| low_word → combined value |
| Setpoint writes | value * 10 → register value (except time values) |

## 📋 Summary Statistics

- **Total Entities Created:** ~20 sensors + 7 numbers + 1 text + 1 select = 29 entities
- **Registers Read:** 30 unique registers
- **Registers Written To:** 8 unique registers (4160, 4148-4151, 4154, 4162-4163)
- **Update Interval:** Configurable (default: 15 seconds)
- **Modbus Protocol:** TCP (port 502 by default)

This comprehensive mapping provides complete documentation of how every entity in the Midnite Solar integration corresponds to specific Modbus registers on the Classic MPPT charge controller.
