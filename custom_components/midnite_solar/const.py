"""Constants for the Midnite Solar integration."""

DOMAIN = "midnite_solar"

DEFAULT_PORT = 502
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15

# Register addresses from registers.json
REGISTER_MAP = {
    # Base information
    "UNIT_ID": 4101,
    "UNIT_SW_DATE_RO": 4102,
    "UNIT_SW_DATE_MONTH_DAY": 4103,
    "INFO_FLAGS_BITS3": 4104,
    "MAC_ADDRESS_PART_1": 4106,
    "MAC_ADDRESS_PART_2": 4107,
    "MAC_ADDRESS_PART_3": 4108,
    "STATUSROLL": 4113,
    "RESTART_TIME_MS": 4114,
    "MATCH_POINT_SHADOW": 4124,
    "DISP_AVG_VBATT": 4115,
    "DISP_AVG_VPV": 4116,
    "IBATT_DISPLAY_S": 4117,
    "KW_HOURS": 4118,
    "WATTS": 4119,
    "COMBO_CHARGE_STAGE": 4120,
    "PV_INPUT_CURRENT": 4121,
    "VOC_LAST_MEASURED": 4122,
    "HIGHEST_VINPUT_LOG": 4123,
    "AMP_HOURS_DAILY": 4125,
    "LIFETIME_KW_HOURS_1": 4126,
    "LIFETIME_AMP_HOURS_1": 4128,
    "BATT_TEMPERATURE": 4132,
    "FET_TEMPERATURE": 4133,
    "PCB_TEMPERATURE": 4134,
    "NITE_MINUTES_NO_PWR": 4135,
    "MINUTE_LOG_INTERVAL_SEC": 4136,
    "MODBUS_PORT_REGISTER": 4137,
    "FLOAT_TIME_TODAY_SEC": 4138,
    "ABSORB_TIME": 4139,
    "REASON_FOR_RESET": 4142,
    "EQUALIZE_TIME": 4143,
    "REASON_FOR_RESTING": 4275,
    "MPPT_MODE": 4164,
    "AUX_1_AND_2_FUNCTION": 4165,
    "VARIMAX": 4180,
    "CLASSIC_MODBUS_ADDR_EEPROM": 4326,
    # Temperature compensation settings
    "MAX_BATTERY_TEMP_COMP_VOLTAGE": 4155,
    "MIN_BATTERY_TEMP_COMP_VOLTAGE": 4156,
    "BATTERY_TEMP_COMP_VALUE": 4157,
    # Equalize settings
    "EQUALIZE_RETRY_DAYS": 4159,
    # Auxiliary function settings
    "AUX1_VOLTS_LO_ABS": 4166,
    "AUX1_DELAY_T_MS": 4167,
    "AUX1_HOLD_T_MS": 4168,
    "AUX2_PWM_VWIDTH": 4169,
    "AUX1_VOLTS_HI_ABS": 4172,
    "AUX2_VOLTS_HI_ABS": 4173,
    "AUX1_VOLTS_LO_REL": 4174,
    "AUX1_VOLTS_HI_REL": 4175,
    "AUX2_VOLTS_LO_REL": 4176,
    "AUX2_VOLTS_HI_REL": 4177,
    "AUX1_VOLTS_LO_PV_ABS": 4178,
    "AUX1_VOLTS_HI_PV_ABS": 4179,
    "AUX2_VOLTS_HI_PV_ABS": 4181,
    # Wind power curve settings
    "WIND_POWER_TABLE_V_0_EEPA": 4301,
    "WIND_POWER_TABLE_V_1_EEPA": 4302,
    "WIND_POWER_TABLE_V_2_EEPA": 4303,
    "WIND_POWER_TABLE_V_3_EEPA": 4304,
    "WIND_POWER_TABLE_V_4_EEPA": 4305,
    "WIND_POWER_TABLE_V_5_EEPA": 4306,
    "WIND_POWER_TABLE_V_6_EEPA": 4307,
    "WIND_POWER_TABLE_V_7_EEPA": 4308,
    "WIND_POWER_TABLE_I_0_EEPA": 4309,
    "WIND_POWER_TABLE_I_1_EEPA": 4310,
    "WIND_POWER_TABLE_I_2_EEPA": 4311,
    "WIND_POWER_TABLE_I_3_EEPA": 4312,
    "WIND_POWER_TABLE_I_4_EEPA": 4313,
    "WIND_POWER_TABLE_I_5_EEPA": 4314,
    "WIND_POWER_TABLE_I_6_EEPA": 4315,
    "WIND_POWER_TABLE_I_7_EEPA": 4316,
    
    # Network configuration
    "IP_SETTINGS_FLAGS": 20481,
    "IP_ADDRESS_LSB_1": 20482,
    "IP_ADDRESS_LSB_2": 20483,
    "GATEWAY_ADDRESS_LSB_1": 20484,
    "GATEWAY_ADDRESS_LSB_2": 20485,
    "SUBNET_MASK_LSB_1": 20486,
    "SUBNET_MASK_LSB_2": 20487,
    "DNS_1_LSB_1": 20488,
    "DNS_1_LSB_2": 20489,
    "DNS_2_LSB_1": 20490,
    "DNS_2_LSB_2": 20491,
    
    # Setpoints
    "ABSORB_SETPOINT_VOLTAGE": 4149,
    "FLOAT_VOLTAGE_SETPOINT": 4150,
    "EQUALIZE_VOLTAGE_SETPOINT": 4151,
    "BATTERY_OUTPUT_CURRENT_LIMIT": 4148,
    # Sliding current limit
    "SLIDING_CURRENT_LIMIT": 4152,
    
    # Time settings
    "MIN_ABSORB_TIME": 4153,
    "ABSORB_TIME_EEPROM": 4154,
    "EQUALIZE_TIME_EEPROM": 4162,
    "EQUALIZE_INTERVAL_DAYS_EEPROM": 4163,
    
    # Force flags (write-only)
    "FORCE_FLAG_BITS": 4160,
    
    # NOTE: Registers 20492/20493 (SERIAL_NUMBER_MSB/LSB) have been removed
    # These registers caused Modbus protocol errors and are not reliably accessible
    # We now use DEVICE_ID (registers 4111-4112) as the serial number identifier instead
    
    # Unit name (ASCII, 8 characters from registers 4210-4213)
    "UNIT_NAME_0": 4210,
    "UNIT_NAME_1": 4211,
    "UNIT_NAME_2": 4212,
    "UNIT_NAME_3": 4213,
    
    # Device ID (alternative serial, registers 4111-4112)
    "DEVICE_ID_LSW": 4111,
    "DEVICE_ID_MSW": 4112,
}

# Charge stage mappings (from register 4120 MSB)
CHARGE_STAGES = {
    0: "Resting",
    3: "Absorb",
    4: "BulkMPPT",
    5: "Float",
    6: "FloatMppt",
    7: "Equalize",
    10: "HyperVoc",
    18: "EQ MPPT",
}

# Internal state mappings (from register 4120 LSB)
INTERNAL_STATES = {
    0: "Resting",
    1: "Waking/Starting (state 1)",
    2: "Waking/Starting (state 2)",
    3: "MPPT / Regulating Voltage (state 3)",
    4: "MPPT / Regulating Voltage (state 4)",
    6: "MPPT / Regulating Voltage (state 6)",
}

# Device types from register 4101
DEVICE_TYPES = {
    150: "Classic 150",
    200: "Classic 200",
    250: "Classic 250",
    251: "Classic 250 KS (120V battery capability)",
}

# Rest reasons from register 4275
REST_REASONS = {
    1: "Anti-Click. Not enough power available (Wake Up)",
    2: "Insane Ibatt Measurement (Wake Up)",
    3: "Negative Current (load on PV input?) (Wake Up)",
    4: "PV Input Voltage lower than Battery V (Vreg state)",
    5: "Too low of power out and Vbatt below set point for > 90 seconds",
    6: "FET temperature too high (Cover is on maybe?)",
    7: "Ground Fault Detected",
    8: "Arc Fault Detected",
    9: "Too much negative current while operating (backfeed from battery out of PV input)",
    10: "Battery is less than 8.0 Volts",
    11: "PV input is available but V is rising too slowly. Low Light or bad connection (Solar mode)",
    12: "Voc has gone down from last Voc or low light. Re-check (Solar mode)",
    13: "Voc has gone up from last Voc enough to be suspicious. Re-check (Solar mode)",
    14: "Same as 11",
    15: "Same as 12",
    16: "MPPT MODE is OFF (Usually because user turned it off)",
    17: "PV input is higher than operation range (too high for 150V Classic)",
    18: "PV input is higher than operation range (too high for 200V Classic)",
    19: "PV input is higher than operation range (too high for 250V or 250KS)",
    22: "Average Battery Voltage is too high above set point",
    25: "Battery Voltage too high of Overshoot (small battery or bad cable?)",
    26: "Mode changed while running OR Vabsorb raised more than 10.0 Volts at once OR Nominal Vbatt changed by modbus command AND MpptMode was ON when changed",
    27: "Bridge center == 1023 (R132 might have been stuffed) This turns MPPT Mode to OFF",
    28: "NOT Resting but RELAY is not engaged for some reason",
    29: "ON/OFF stays off because WIND GRAPH is illegal (current step is set for > 100 amps)",
    30: "PkAmpsOverLimit... Software detected too high of PEAK output current",
    31: "AD1CH.IbattMinus > 900 Peak negative battery current > 90.0 amps (Classic 250)",
    32: "Aux 2 input commanded Classic off for HI or LO (Aux2Function == 15 or 16)",
    33: "OCP in a mode other than Solar or PV-Uset",
    34: "AD1CH.IbattMinus > 900 Peak negative battery current > 90.0 amps (Classic 150, 200)",
    35: "Battery voltage is less than Low Battery Disconnect (LBD) Typically Vbatt is less than 8.5 volts",
}

# Force flag bit mappings (from register 4160)
FORCE_FLAGS = {
    "ForceEEpromUpdate": 2,      # Bit position
    "ForceEEpromInitRead": 3,
    "ForceResetInfoFlags": 4,
    "ForceFloat": 5,
    "ForceBulk": 6,
    "ForceEqualize": 7,
    "ForceNite": 8,
    "ResetAeqCounts": 13,
    "ForceSweep": 16,
    "ResetFlags": 20,             # Bit position
    "ForceResetFaults": 29,
}

# MPPT mode mappings (from register 4164)
MPPT_MODES = {
    0x0001: "PV_Uset",
    0x0003: "DYNAMIC",
    0x0005: "WIND_TRACK",
    0x0007: "RESERVED",
    0x0009: "Legacy P&O",
    0x000B: "SOLAR",
    0x000D: "HYDRO",
    0x000F: "RESERVED",
}

# IP settings flags (from register 20481)
IP_SETTINGS_FLAGS = {
    "DHCP": 0,
    "Web_Access": 1,
}

# Auxiliary function mappings for AUX_1_AND_2_FUNCTION register
AUX1_FUNCTIONS = [
    "Off",
    "Auto",
    "On",
    "HiAbs",
    "LoAbs",
    "WasteNot",
    "PVHiAbs",
    "PVLoAbs",
]

AUX2_FUNCTIONS = [
    "Off",
    "Auto",
    "On",
    "HiAbs",
    "LoAbs",
    "WasteNot",
    "PWM",
    "PVHiAbs",
]

# Define the register groups we need to read from the device
# Each group represents a functional category of registers
REGISTER_GROUPS = {
    "device_info": [
        REGISTER_MAP["UNIT_ID"],
        # Software build date (registers 4102-4103)
        REGISTER_MAP["UNIT_SW_DATE_RO"],
        REGISTER_MAP["UNIT_SW_DATE_MONTH_DAY"],
        # Use DEVICE_ID (registers 4111-4112) as the serial number identifier
        # This is more reliable than SERIAL_NUMBER registers (20492/20493)
        REGISTER_MAP["DEVICE_ID_LSW"],
        REGISTER_MAP["DEVICE_ID_MSW"],
        # Unit name (8 characters from 4 registers, each holding 2 bytes)
        REGISTER_MAP["UNIT_NAME_0"],
        REGISTER_MAP["UNIT_NAME_1"],
        REGISTER_MAP["UNIT_NAME_2"],
        REGISTER_MAP["UNIT_NAME_3"],
        # MAC address (registers 4106-4108)
        REGISTER_MAP["MAC_ADDRESS_PART_1"],
        REGISTER_MAP["MAC_ADDRESS_PART_2"],
        REGISTER_MAP["MAC_ADDRESS_PART_3"],
    ],
    "status": [
        REGISTER_MAP["DISP_AVG_VBATT"],
        REGISTER_MAP["DISP_AVG_VPV"],
        REGISTER_MAP["IBATT_DISPLAY_S"],
        REGISTER_MAP["WATTS"],
        REGISTER_MAP["COMBO_CHARGE_STAGE"],
        REGISTER_MAP["PV_INPUT_CURRENT"],
        REGISTER_MAP["VOC_LAST_MEASURED"],
        # Add status registers
        REGISTER_MAP["STATUSROLL"],
        REGISTER_MAP["KW_HOURS"],
        REGISTER_MAP["HIGHEST_VINPUT_LOG"],
        REGISTER_MAP["RESTART_TIME_MS"],
        REGISTER_MAP["MATCH_POINT_SHADOW"],
    ],
    "temperatures": [
        REGISTER_MAP["BATT_TEMPERATURE"],
        REGISTER_MAP["FET_TEMPERATURE"],
        REGISTER_MAP["PCB_TEMPERATURE"],
    ],
    "energy": [
        REGISTER_MAP["AMP_HOURS_DAILY"],
        REGISTER_MAP["LIFETIME_KW_HOURS_1"],
        REGISTER_MAP["LIFETIME_KW_HOURS_1"] + 1,  # High word
        REGISTER_MAP["LIFETIME_AMP_HOURS_1"],
        REGISTER_MAP["LIFETIME_AMP_HOURS_1"] + 1,  # High word
    ],
    "time_settings": [
        REGISTER_MAP["FLOAT_TIME_TODAY_SEC"],
        REGISTER_MAP["ABSORB_TIME"],
        REGISTER_MAP["EQUALIZE_TIME"],
        REGISTER_MAP["MIN_ABSORB_TIME"],
    ],
    # Add settings registers for MPPT mode, Modbus port, etc.
    "settings": [
        REGISTER_MAP["MPPT_MODE"],
        REGISTER_MAP["MODBUS_PORT_REGISTER"],
        REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"],
        REGISTER_MAP["SLIDING_CURRENT_LIMIT"],
    ],
    # Add network configuration registers
    "network": [
        REGISTER_MAP["IP_ADDRESS_LSB_1"],
        REGISTER_MAP["IP_ADDRESS_LSB_2"],
        REGISTER_MAP["GATEWAY_ADDRESS_LSB_1"],
        REGISTER_MAP["GATEWAY_ADDRESS_LSB_2"],
        REGISTER_MAP["SUBNET_MASK_LSB_1"],
        REGISTER_MAP["SUBNET_MASK_LSB_2"],
        REGISTER_MAP["DNS_1_LSB_1"],
        REGISTER_MAP["DNS_1_LSB_2"],
        REGISTER_MAP["DNS_2_LSB_1"],
        REGISTER_MAP["DNS_2_LSB_2"],
    ],
    "diagnostics": [
        REGISTER_MAP["REASON_FOR_RESTING"],
    ],
    # Add setpoint registers for number entities
    "setpoints": [
        REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"],
        REGISTER_MAP["FLOAT_VOLTAGE_SETPOINT"],
        REGISTER_MAP["EQUALIZE_VOLTAGE_SETPOINT"],
        REGISTER_MAP["BATTERY_OUTPUT_CURRENT_LIMIT"],
    ],
    # Add EEPROM time settings for number entities
    "eeprom_settings": [
        REGISTER_MAP["ABSORB_TIME_EEPROM"],
        REGISTER_MAP["EQUALIZE_TIME_EEPROM"],
        REGISTER_MAP["EQUALIZE_INTERVAL_DAYS_EEPROM"],
        REGISTER_MAP["CLASSIC_MODBUS_ADDR_EEPROM"],  # Modbus address
        # Add temperature compensation settings
        REGISTER_MAP["MAX_BATTERY_TEMP_COMP_VOLTAGE"],
        REGISTER_MAP["MIN_BATTERY_TEMP_COMP_VOLTAGE"],
        REGISTER_MAP["BATTERY_TEMP_COMP_VALUE"],
        # Add equalize retry days
        REGISTER_MAP["EQUALIZE_RETRY_DAYS"],
    ],
    # Add auxiliary function settings registers
    "aux_settings": [
        REGISTER_MAP["AUX_1_AND_2_FUNCTION"],
        REGISTER_MAP["AUX1_VOLTS_LO_ABS"],
        REGISTER_MAP["AUX1_DELAY_T_MS"],
        REGISTER_MAP["AUX1_HOLD_T_MS"],
        REGISTER_MAP["AUX2_PWM_VWIDTH"],
        REGISTER_MAP["AUX1_VOLTS_HI_ABS"],
        REGISTER_MAP["AUX2_VOLTS_HI_ABS"],
        REGISTER_MAP["AUX1_VOLTS_LO_REL"],
        REGISTER_MAP["AUX1_VOLTS_HI_REL"],
        REGISTER_MAP["AUX2_VOLTS_LO_REL"],
        REGISTER_MAP["AUX2_VOLTS_HI_REL"],
        REGISTER_MAP["AUX1_VOLTS_LO_PV_ABS"],
        REGISTER_MAP["AUX1_VOLTS_HI_PV_ABS"],
        REGISTER_MAP["AUX2_VOLTS_HI_PV_ABS"],
    ],
    # Add wind power curve settings registers
    "wind_power_curve": [
        REGISTER_MAP["WIND_POWER_TABLE_V_0_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_1_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_2_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_3_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_4_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_5_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_6_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_V_7_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_0_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_1_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_2_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_3_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_4_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_5_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_6_EEPA"],
        REGISTER_MAP["WIND_POWER_TABLE_I_7_EEPA"],
    ],
}
