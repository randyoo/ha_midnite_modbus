# Midnite Solar Classic Register Analysis

## Summary of Registers Read by the Integration

Based on analysis of the custom_components/midnite/ folder, here are all the registers being read:

### Device Information (Read in config_flow.py and coordinator.py)
- **Register 4100** - Used for connection test (not in register maps)
- **Register 4101** (UNIT_ID) - Hardware revision & voltage category
- **Registers 4111-4112** (DEVICE_ID_LSW, DEVICE_ID_MSW) - Device ID used as serial number
- **Registers 4106-4108** (MAC_ADDRESS_PART_1, MAC_ADDRESS_PART_2, MAC_ADDRESS_PART_3) - MAC address
- **Registers 4210-4213** (UNIT_NAME_0 to UNIT_NAME_3) - Unit name (8 characters)

### Status Sensors (sensor.py)
- **Register 4115** (DISP_AVG_VBATT) - Average battery voltage
- **Register 4116** (DISP_AVG_VPV) - Average PV input voltage
- **Register 4117** (IBATT_DISPLAY_S) - Average battery current
- **Register 4119** (WATTS) - Average power to the battery
- **Register 4120** (COMBO_CHARGE_STAGE) - Charge state of the battery
- **Register 4121** (PV_INPUT_CURRENT) - Average PV input current
- **Register 4122** (VOC_LAST_MEASURED) - Last measured open-circuit voltage at PV input
- **Register 4275** (REASON_FOR_RESTING) - Reason Classic went to Rest

### Temperature Sensors
- **Register 4132** (BATT_TEMPERATURE) - Battery temperature sensor
- **Register 4133** (FET_TEMPERATURE) - Power FET temperature
- **Register 4134** (PCB_TEMPERATURE) - Classic top PCB temperature

### Energy Sensors
- **Register 4125** (AMP_HOURS_DAILY) - Daily amp-hours reset at 23:59
- **Registers 4126-4127** (LIFETIME_KW_HOURS_1 + high word) - Lifetime energy generation
- **Registers 4128-4129** (LIFETIME_AMP_HOURS_1 + high word) - Lifetime amp-hour generation

### Time Settings Sensors
- **Register 4138** (FLOAT_TIME_TODAY_SEC) - Seconds spent in float today
- **Register 4139** (ABSORB_TIME) - Absorb time counter
- **Register 4143** (EQUALIZE_TIME) - Battery stage equalize counter

### Number Entities (number.py) - Setpoints and Timings
- **Register 4148** (BATTERY_OUTPUT_CURRENT_LIMIT) - Battery current limit
- **Register 4149** (ABSORB_SETPOINT_VOLTAGE) - Absorb voltage setpoint
- **Register 4150** (FLOAT_VOLTAGE_SETPOINT) - Float voltage setpoint
- **Register 4151** (EQUALIZE_VOLTAGE_SETPOINT) - Equalize voltage setpoint
- **Register 4154** (ABSORB_TIME_EEPROM) - Absorb time EEPROM setting
- **Register 4162** (EQUALIZE_TIME_EEPROM) - Equalize time EEPROM setting
- **Register 4163** (EQUALIZE_INTERVAL_DAYS_EEPROM) - Days between equalize stages

### Text Entities (text.py)
- **Registers 4210-4213** (UNIT_NAME_0 to UNIT_NAME_3) - Unit name (read/write)

## Registers NOT Currently Read by the Integration

Based on registers.json and registers2.json, these are some notable registers that are NOT being read:

### Network Configuration (20481-20493)
- IP_SETTINGS_FLAGS (20481) - DHCP and Web Access flags
- IP_ADDRESS_* (20482-20483, 20488-20489) - IP address configuration
- GATEWAY_* (20484-20485) - Gateway configuration
- SUBNET_MASK_* (20486-20487) - Subnet mask configuration
- DNS_* (20490-20491) - DNS servers
- SERIAL_NUMBER_MSB/LSB (20492-20493) - Serial number (removed due to Modbus errors)

### Additional Status Registers
- **Register 4104** (INFO_FLAGS_BITS3) - System status flags
- **Register 4105** (RESERVED_4105) - Unimplemented
- **Register 4109** (JrAmpHourNET) - Whizbang Jr net amp-hours
- **Register 4113** (STATUSROLL) - 12-bit status value
- **Register 4114** (RESTART_TIME_MS) - Time after which Classic can wake up
- **Register 4118** (KW_HOURS) - Energy to battery (reset daily)
- **Register 4123** (HIGHEST_VINPUT_LOG) - Highest input voltage seen
- **Register 4124** (MATCH_POINT_SHADOW) - Current wind power curve step
- **Register 4135** (NITE_MINUTES_NO_PWR) - Counts up when no power
- **Register 4136** (MINUTE_LOG_INTERVAL_SEC) - Data logging interval
- **Register 4137** (MODBUS_PORT_REGISTER) - Modbus TCP port
- **Register 4142** (REASON_FOR_RESET) - Reason Classic reset
- **Register 4145** (MPP_W_LAST) - Internal watts reference
- **Register 4146** (USB_COMM_MODE) - USB function number
- **Register 4147** (NO_DOUBLE_CLICK_TIMER) - Time between manual sweeps
- **Register 4152** (SLIDING_CURRENT_LIMIT) - Sliding current limit
- **Register 4153** (MIN_ABSORB_TIME) - Minimum absorb time
- **Register 4155-4157** (MAX/BATTERY_TEMP_COMP_*) - Temperature compensation settings
- **Register 4158** (GENERAL_PURPOSE_WORD) - General purpose word
- **Register 4159** (EQUALIZE_RETRY_DAYS) - Auto EQ retry days
- **Register 4160** (FORCE_FLAG_BITS) - Write-only force flags
- **Register 4164** (MPPT_MODE) - MPPT mode selection (NOT currently implemented)
  - PV_Uset (0x0001) - U-SET MPPT MODE
  - DYNAMIC (0x0003) - Slow Dynamic Solar Tracking
  - WIND_TRACK (0x0005) - Wind Track Mode
  - Legacy P&O (0x0009) - Legacy Perturb & Observe sweep mode
  - SOLAR (0x000B) - Fast SOLAR track (PV Learn mode)
  - HYDRO (0x000D) - Micro Hydro mode
- **Register 4165** (AUX_1_AND_2_FUNCTION) - Aux function configuration
- **Registers 4166-4181** (AUX* settings) - Auxiliary output configurations
- **Register 4182-4183** (ENABLE_FLAGS*) - Feature enable flags
- **Register 4189-4190** (VBATT_OFFSET, VPV_OFFSET) - Voltage offset calibrations
- **Registers 4197-4205** (SWEEP_*, WIND_*) - Sweep and wind mode settings
- **Register 4207** (LED_MODE_EEPROM) - LED mode configuration
- **Registers 4214-4218** (CTI_ME*) - Consolidated time registers
- **Registers 4220-4226** (REMOTE_*, PREVOC, AUX2_A2D_D2A) - Remote and auxiliary settings
- **Registers 4231, 4236, 4238-4239** (VOC_RD, ABSORB_TIME_DUPLICATE, SIESTA_*) - VOC and siesta settings
- **Register 4241** (FLAGS_RD_32BIT) - Internal status flags
- **Registers 4244-4257** (VBATT_REG_SET_P_TEMP_COMP to REBUCK_TIMER_SEC_EEPROM) - Battery regulation and rebuck settings
- **Registers 4265-4299** (VOC_QUALIFY_* to PK_AMPS_OVER_LIMIT_LO_EEPA) - Various timing and calibration settings
- **Registers 4301-4318** (WIND_POWER_TABLE_*) - Wind power curve tables
- **Registers 4326-4372** (CLASSIC_MODBUS_ADDR to WIZBANG_RAW_CRC_AND_TEMP) - Modbus address, Follow-Me settings, Whizbang Jr data
- **Registers 10001-10062** - Communication statistics
- **Registers 16385-16390** - Version information

## Conclusion

The current integration reads a focused set of registers that provide:
1. Device identification (UNIT_ID, DEVICE_ID, MAC address, unit name)
2. Real-time status (voltages, currents, power, charge state)
3. Temperature monitoring (battery, FET, PCB)
4. Energy tracking (daily and lifetime)
5. Configurable setpoints (voltages, current limit, timings)

Many advanced features like network configuration, auxiliary outputs, wind power curves, and detailed communication statistics are not currently exposed but could be added in future enhancements.
