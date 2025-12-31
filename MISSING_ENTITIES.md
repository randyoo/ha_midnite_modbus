# Missing Entities from registers.json

This document tracks entities that need to be implemented based on the registers.json file.

## Already Implemented Registers

### Sensors (sensor.py)
- UNIT_ID (4101) - Device Type sensor ✓
- DISP_AVG_VBATT (4115) - Battery Voltage ✓
- DISP_AVG_VPV (4116) - PV Voltage ✓
- IBATT_DISPLAY_S (4117) - Battery Current ✓
- WATTS (4119) - Power Output ✓
- COMBO_CHARGE_STAGE (4120) - Charge Stage & Internal State ✓
- PV_INPUT_CURRENT (4121) - PV Input Current ✓
- VOC_LAST_MEASURED (4122) - Last Measured VOC ✓
- AMP_HOURS_DAILY (4125) - Daily Amp-Hours ✓
- LIFETIME_KW_HOURS_1 (4126, 4127) - Lifetime Energy ✓
- LIFETIME_AMP_HOURS_1 (4128, 4129) - Lifetime Amp-Hours ✓
- BATT_TEMPERATURE (4132) - Battery Temperature ✓
- FET_TEMPERATURE (4133) - FET Temperature ✓
- PCB_TEMPERATURE (4134) - PCB Temperature ✓
- FLOAT_TIME_TODAY_SEC (4138) - Float Time Today ✓
- ABSORB_TIME (4139) - Absorb Time Remaining ✓
- EQUALIZE_TIME (4143) - Equalize Time Remaining ✓
- MAC_ADDRESS_PART_1/2/3 (4106-4108) - MAC Address ✓
- REASON_FOR_RESTING (4275) - Rest Reason ✓
- MPPT_MODE (4164) - MPPT Mode ✓
- MODBUS_PORT_REGISTER (4137) - Modbus Port ✓
- IP_ADDRESS_LSB_1/2 (20482, 20483) - IP Address ✓
- GATEWAY_ADDRESS_LSB_1/2 (20484, 20485) - Gateway Address ✓
- SUBNET_MASK_LSB_1/2 (20486, 20487) - Subnet Mask ✓
- DNS_1_LSB_1/2 (20488, 20489) - Primary DNS Server ✓
- DNS_2_LSB_1/2 (20490, 20491) - Secondary DNS Server ✓
- STATUSROLL (4113) - Status Roll ✓
- KW_HOURS (4118) - Daily Energy ✓
- HIGHEST_VINPUT_LOG (4123) - Highest Input Voltage ✓
- MINUTE_LOG_INTERVAL_SEC (4136) - Logging Interval ✓
- SLIDING_CURRENT_LIMIT (4152) - Sliding Current Limit ✓

### Numbers (number.py)
- ABSORB_SETPOINT_VOLTAGE (4149) - Absorb Voltage Setpoint ✓
- FLOAT_VOLTAGE_SETPOINT (4150) - Float Voltage Setpoint ✓
- EQUALIZE_VOLTAGE_SETPOINT (4151) - Equalize Voltage Setpoint ✓
- BATTERY_OUTPUT_CURRENT_LIMIT (4148) - Battery Current Limit ✓
- ABSORB_TIME_EEPROM (4154) - Absorb Time ✓
- EQUALIZE_TIME_EEPROM (4162) - Equalize Time ✓
- EQUALIZE_INTERVAL_DAYS_EEPROM (4163) - Equalize Interval Days ✓
- CLASSIC_MODBUS_ADDR_EEPROM (4326) - Modbus Address ✓
- MAX_BATTERY_TEMP_COMP_VOLTAGE (4155) - Max Battery Temp Comp Voltage ✓
- MIN_BATTERY_TEMP_COMP_VOLTAGE (4156) - Min Battery Temp Comp Voltage ✓
- BATTERY_TEMP_COMP_VALUE (4157) - Battery Temp Comp Value ✓
- EQUALIZE_RETRY_DAYS (4159) - EQ Retry Days ✓

### Selects (select.py)
- FORCE_FLAG_BITS (4160) - Force Charge Mode ✓
- MPPT_MODE (4164) - MPPT Mode ✓

### Sensors (sensor.py)
- MODBUS_PORT_REGISTER (4137) - Modbus Port ✓

### Text (text.py)
- UNIT_NAME_0-3 (4210-4213) - Host Name ✓

### Buttons (button.py)
- FORCE_FLAG_BITS (4160) - Force EEPROM Update, Reset Faults, Reset Flags ✓

## Missing Entities to Implement

### Sensors (sensor.py)

#### Status Information
- RESTART_TIME_MS (4114) - Time after which Classic can wake up ✓
- MATCH_POINT_SHADOW (4124) - Current wind power curve step ✓
- NITE_MINUTES_NO_PWR (4135) - Counts up when no power, resets on power
- PWM_READONLY (4141) - Duty cycle command of PWM
- REASON_FOR_RESET (4142) - Reason Classic reset
- MIN_ABSORB_TIME (4153) - Minimum absorb time
- MAX_BATTERY_TEMP_COMP_VOLTAGE (4155) - Highest charge voltage with temp sensor
- MIN_BATTERY_TEMP_COMP_VOLTAGE (4156) - Lowest charge voltage with temp sensor
- BATTERY_TEMP_COMP_VALUE (4157) - Temperature compensation value
- GENERAL_PURPOSE_WORD (4158) - Stored & retrieved with other EEPROM
- EQUALIZE_RETRY_DAYS (4159) - Auto EQ retry days until giving up

- AUX_1_AND_2_FUNCTION (4165) - Combined Aux 1 & 2 function + ON/OFF ✓
- VARIMAX (4180) - Variable maximum current & voltage differential
- ENABLE_FLAGS3 (4182) - Enable forwarding of Modbus traffic
- ENABLE_FLAGS2 (4186) - Various feature flags
- ENABLE_FLAGS_BITS (4187) - Legacy flags moved to EnableFlags2
- VBATT_OFFSET (4189) - Battery voltage offset tweak
- VPV_OFFSET (4190) - PV input voltage offset tweak
- VPV_TARGET_RD (4191) - PV input target (usually Vmpp)
- SWEEP_INTERVAL_SECS_EEPROM (4197) - Legacy P&O sweep interval
- MIN_SWP_VOLTAGE_EEPROM (4198) - Minimum input voltage for hydro MPPT mode sweep
- MAX_INPUT_CURRENT_EEPROM (4199) - Maximum input current limit
- SWEEP_DEPTH (4200) - Legacy/Hydro mode sweep depth as % of current MPP
- CLIPPER_CMD_VOLTS (4202) - Aux clipper reference varies with stage and headroom
- LED_MODE_EEPROM (4207) - LED mode
- PREVOC (4224) - Voc before relay
- VOC_RD (4231) - Last VOC reading
- ABSORB_TIME_DUPLICATE (4236) - Duplicate absorb time counter
- SIESTA_TIME_SEC (4238) - Sleep timer
- SIESTA_ABORT_VOC_ADJ (4239) - Voc difference to abort Siesta
- FLAGS_RD_32BIT (4241) - Internal status flags
- VBATT_REG_SET_P_TEMP_COMP (4244) - Battery regulation target voltage, temp-compensated
- VBATT_NOMINAL_EEPROM (4245) - Nominal battery bank voltage
- ENDING_AMPES_EEPROM (4246) - End of absorb amps threshold
- ENDING_SOC_EEPROM (4247) - SOC to end absorb
- REBUCK_VOLTS_EEPROM (4249) - Re-bulk if battery drops below this for > 90 s
- DAYS_BTW_BULK_ABS_EEPROM (4252) - Days between bulk/absorb cycles
- DAY_LOG_COMB_CAT_INDEX (4254) - Daily logs combined category / day index
- MIN_LOG_COMB_CAT_INDEX (4256) - Minute logs combined category / sample offset
- REBUCK_TIMER_SEC_EEPROM (4257) - Re-bulk interval timer seconds
- VOC_QUALIFY_TIMER_MS_EEPROM (4264, 4265) - Qualifying time till turn-on
- IPV_MINUS_RAW (4266) - Raw PV negative current from ADC
- RESTART_TIME_MS2 (4271) - Countdown time to wake up
- IBATT_RAW_A (4272) - Battery current, unfiltered
- OUTPUT_VBATT_RAW (4376) - Battery voltage, unfiltered
- INPUT_VPV_RAW (4377) - PV voltage, unfiltered
- PK_HOLD_VPV_STAMP (4280) - Solar MPPT internal variable
- VPV_TARGET_RD_TMP (4283) - Temporary PV target voltage
- SWP_DEEP_TIMEOUT_SEC (4284) - Solar MPPT internal variable
- LOW_WATTS_EEPA (4286) - Classic rests when watts < this for > 90 s
- WIND_LOW_WATTS_EEPA (4287) - Wind low watts threshold
- WIND_WINDOW_WATTS_REF_EEPA (4288) - Wind power window reference to keep running
- WINDOW_WATTS_RO_DELTA_EEPA (4289) - Delta watts below WindLowWatts for power wiggling
- WIND_TIMEOUT_REF_EEPA (4290) - Wind timeout to go resting
- WIND_TIMEOUT2_REF_EEPA (4291) - Half-hour wind timeout reference
- WIND_TIMEOUT_SECONDS (4292) - Wind timeout counter
- WIND_TIMEOUT2_SECONDS (4293) - Wind timeout counter 2
- MIN_VPV_TURN_ON (4294) - Minimum input voltage to exit Resting
- VPV_B4_TURN_OFF (4295) - Internal reference of Vpv when going to Resting
- H2O_SWEEP_AMPS_10TIME6_EEPA (4296) - Hydro sweep speed reference
- ENDING_AMPS_TIMER_SEC (4297) - Timer for ending amps
- PK_AMPS_OVER_LIMIT_HI_EEPA (4298) - Factory calibration
- PK_AMPS_OVER_LIMIT_LO_EEPA (4299) - Factory calibration
- FACTORY_VBATT_OFFSET_EEPA (4300) - Factory V battery offset calibration
- WIND_POWER_TABLE_V_0-7_EEPA (4301-4308) - Wind power curve voltage steps ✓
- WIND_POWER_TABLE_I_0-7_EEPA (4309-4316) - Wind power curve current steps ✓
- PK_AMPS_OVER_TRIP_EEPROM (4318) - Factory calibration
- MNGP_REVISION (4319) - Preliminary – shows unit connected
- MNLP_REVISION (4320) - Preliminary – shows unit connected
- CLASSIC_MODBUS_ADDR_EEPROM (4326) - Classic Modbus address
- BATTERY_TEMP_PASSED_EEPROM (4327) - Follow-Me temperature sensor value
- I_FLAGS_RO_HIGH (4330) - Follow-Me high bits – charge stage coordination
- MODBUS_CONTROL_EEPROM (4331) - Follow-Me Modbus control
- CLASSIC_FME_PASSED_BITS_EEPROM (4332) - Follow-Me state bits
- WIND_SYNCH_A_EEPROM (4333) - Wind power tracking amps
- WIND_SYNCH_V_EEPROM (4334) - Wind power tracking volts
- FOLLOW_ME_PASS_REF_EEPROM (4335) - Follow-Me enabled if > 0
- DABT_U32_DEBUG_01-04 (4341-4344) - Debug registers
- CLEAR_LOGS_CAT (4354) - Clear various logging values
- CLEAR_LOGS_COUNTER_10MS (4355) - Timer for sending second ClearLogsCat command
- USER_VARIABLE_02 (4356) - General purpose user variable
- WIZBANG_RX_BUFFER_TEMP_SH1-4 (4357-4360) - Raw Whizbang Junior buffer reads
- WJRB_CMD_S_EEPROM (4361) - Whizbang Junior command
- WJRB_RAW_CURRENT (4362) - Whizbang Junior raw current
- WJRB_NUMERATOR_SS_EEPROM (4363) - Whizbang Junior gain adjustment
- WJRB_AMP_HOUR_POSITIVE (4365, 4366) - Whizbang Jr. positive amp-hours
- WJRB_AMP_HOUR_NEGATIVE (4367, 4368) - Whizbang Jr. negative amp-hours
- WJRB_AMP_HOUR_NET (4369, 4370) - Whizbang Jr. net amp-hours
- WJRB_CURRENT_32_SIGNED_EEPROM (4371) - Whizbang Jr. amps (scaled & rounded)
- WJRB_RAW_CRC_AND_TEMP (4372) - Raw CRC << 8 | Temp & 0xff + 50°C

#### Network Configuration
- IP_SETTINGS_FLAGS (20481) - Network settings flags (DHCP, Web Access)

### Numbers (number.py)

#### Configuration Settings
- MIN_ABSORB_TIME (4153) - Minimum absorb time ✓
- AUX1_VOLTS_LO_ABS (4166) - Aux 1 low absolute threshold voltage
- AUX1_DELAY_T_MS (4167) - Aux 1 delay before asserting
- AUX1_HOLD_T_MS (4168) - Aux 1 hold before de-asserting
- AUX2_PWM_VWIDTH (4169) - Voltage range for Aux 2 PWM (0-5V)
- AUX1_VOLTS_HI_ABS (4172) - Aux 1 high absolute threshold voltage
- AUX2_VOLTS_HI_ABS (4173) - Aux 2 high absolute threshold voltage
- AUX1_VOLTS_LO_REL (4174) - Aux 1 waste-not relative lower voltage
- AUX1_VOLTS_HI_REL (4175) - Aux 1 waste-not relative upper voltage
- AUX2_VOLTS_LO_REL (4176) - Aux 2 waste-not relative lower voltage
- AUX2_VOLTS_HI_REL (4177) - Aux 2 waste-not relative upper voltage
- AUX1_VOLTS_LO_PV_ABS (4178) - Aux 1 lower PV absolute threshold voltage
- AUX1_VOLTS_HI_PV_ABS (4179) - Aux 1 higher PV absolute threshold voltage
- AUX2_VOLTS_HI_PV_ABS (4181) - Aux 2 higher PV absolute threshold voltage
- ARC_FAULT_SENSITIVITY (4183) - Arc fault protection sensitivity
- SWEEP_INTERVAL_SECS_EEPROM (4197) - Legacy P&O sweep interval
- MIN_SWP_VOLTAGE_EEPROM (4198) - Minimum input voltage for hydro MPPT mode sweep
- MAX_INPUT_CURRENT_EEPROM (4199) - Maximum input current limit
- SWEEP_DEPTH (4200) - Legacy/Hydro mode sweep depth as % of current MPP
- NEGATIVE_CURRENT_ADJ (4201) - Factory calibration
- CLIPPER_CMD_VOLTS (4202) - Aux clipper reference varies with stage and headroom
- WIND_NUMBER_OF_POLES_EEPROM (4203) - Number of turbine alternator poles
- MPP_PERCENT_VOC_EEPROM (4204) - % of Voc for U-Set mode
- WIND_TABLE_TO_USE_EEPROM (4205) - Future power curve select
- LED_MODE_EEPROM (4207) - LED mode
- SIESTA_TIME_SEC (4238) - Sleep timer (max 5 min)
- SIESTA_ABORT_VOC_ADJ (4239) - Voc difference to abort Siesta
- VBATT_REG_SET_P_TEMP_COMP (4244) - Battery regulation target voltage, temp-compensated
- VBATT_NOMINAL_EEPROM (4245) - Nominal battery bank voltage (12V, 24V, etc.)
- ENDING_AMPES_EEPROM (4246) - End of absorb amps threshold (float if reached)
- ENDING_SOC_EEPROM (4247) - SOC to end absorb
- REBUCK_VOLTS_EEPROM (4249) - Re-bulk if battery drops below this for > 90 s
- DAYS_BTW_BULK_ABS_EEPROM (4252) - Days between bulk/absorb cycles
- VOC_QUALIFY_TIMER_MS_EEPROM (4264, 4265) - Qualifying time till turn-on (ms)
- IPV_MINUS_RAW (4266) - Raw PV negative current from ADC
- RESTART_TIME_MS2 (4271) - Countdown time to wake up (<= 500 ms)
- LOW_WATTS_EEPA (4286) - Classic rests when watts < this for > 90 s
- WIND_LOW_WATTS_EEPA (4287) - Wind low watts threshold (default 50 W)
- WIND_WINDOW_WATTS_REF_EEPA (4288) - Wind power window reference to keep running
- WINDOW_WATTS_RO_DELTA_EEPA (4289) - Delta watts below WindLowWatts for power wiggling
- WIND_TIMEOUT_REF_EEPA (4290) - Wind timeout to go resting (default 90 s)
- WIND_TIMEOUT2_REF_EEPA (4291) - Half-hour wind timeout reference (default 1800 s)
- MIN_VPV_TURN_ON (4294) - Minimum input voltage to exit Resting
- H2O_SWEEP_AMPS_10TIME6_EEPA (4296) - Hydro sweep speed reference
- ENDING_AMPS_TIMER_SEC (4297) - Timer for ending amps (60 s reference)
- WIND_POWER_TABLE_V_0-7_EEPA (4301-4308) - Wind power curve voltage steps
- WIND_POWER_TABLE_I_0-7_EEPA (4309-4316) - Wind power curve current steps
- AUX_1_AND_2_FUNCTION (4165) - Combined Aux 1 & 2 function + ON/OFF

- FOLLOW_ME_PASS_REF_EEPROM (4335) - Follow-Me enabled if > 0

### Selects (select.py)

#### Mode Settings
- MPPT_MODE (4164) - Solar, Wind, etc.

## Implementation Priority

High priority entities that provide useful functionality:
1. **Auxiliary Function Settings** - Aux 1 & 2 configuration (select.py or number.py)
2. **Wind Power Curve** - Wind power table settings (number.py)
3. **Temperature Compensation** - Battery temp compensation values (number.py)
4. **Current Limits** - Additional current limit settings (number.py)
