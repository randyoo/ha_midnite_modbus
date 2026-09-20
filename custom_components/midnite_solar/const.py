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
    "PWM_READ_ONLY": 4141,
    "VPV_TARGET_RD": 4191,
    "VBATT_REG_SET_P_TMP_COMP": 4244,
    "VBATT_NOMINAL": 4245,
    "ENDING_AMPS": 4246,
    "REBULK_VOLTS": 4249,
    "IBATT_UNFILTERED": 4272,
    "VBATT_UNFILTERED": 4276,
    "VPV_UNFILTERED": 4277,
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
    # Force Flag Bits are 32-bit and write-only: "([4161] << 16) + [4160]".
    # Flags at or above 0x10000 live in this high register.
    "FORCE_FLAG_BITS_HIGH": 4161,
    
    # Ethernet write protect. The map: "20492 20493 W Serial Number (Unlock Code)
    # For writing to Classic modbus registers over Ethernet ... Write the Classic's
    # serial number over Ethernet to unlock writing of modbus registers over
    # Ethernet. Setting this will last until the TCP/IP connection is dropped".
    # These are WRITE ONLY, and reading them answers with a Modbus protocol error -
    # which is why an earlier note here claimed they "caused Modbus protocol errors
    # and are not reliably accessible". Nothing is written to them until a user
    # changes a setting, and the Classic reports SerialWriteLock while locked.
    "UNLOCK_SERIAL_MSB": 20492,
    "UNLOCK_SERIAL_LSB": 20493,
    # "28673 28674 R Classic serial number ([28673] << 16) + [28674]"
    "SERIAL_NUMBER_MSB_RO": 28673,
    "SERIAL_NUMBER_LSB_RO": 28674,
    # "4130 4131 R InfoFlagsBits (InfoFlagsBits2) ([4131] << 16) + [4130]
    # See Table 4130-1 (read as 32 bits or singly)"
    "INFO_FLAGS_LOW": 4130,
    "INFO_FLAGS_HIGH": 4131,
    
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
# Table 4130-1 "Info Flag Bits: READ ONLY (can read single 16 bit Low or High
# words if wanted)". Values are the map's; bits marked RESERVED are omitted.
INFO_FLAGS = {
    "ClassicOverTemp": 0x00000001,
    "EepromError": 0x00000002,
    "SerialWriteLock": 0x00000004,
    "EqualizeInProgress": 0x00000008,
    "EQMppt": 0x00000080,
    "InVLowerThanOut": 0x00000100,
    "CurrentLimit": 0x00000200,
    "HyperVoc": 0x00000400,
    "BattTempSensorInstalled": 0x00002000,
    "Aux1StateOn": 0x00004000,
    "Aux2StateOn": 0x00008000,
    "GroundFaultF": 0x00010000,
    "OCP": 0x00020000,
    "ArcFaultF": 0x00040000,
    "NegBatCurrentF": 0x00080000,
    "XtraInfo2DsplayF": 0x00200000,
    "PvPartialShadeF": 0x00400000,
    "WatchdogResetF": 0x00800000,
    "LowBatteryVF": 0x01000000,
    "StackumperF": 0x02000000,
    "EqDoneF": 0x04000000,
    "TempCompShortedF": 0x08000000,
    "UNLockJumperF": 0x10000000,
    "XtraJumperF": 0x20000000,
    "InputShortedF": 0x40000000,
}

# Register 4165 (EE) "Aux 1 and 2 Function ... Combined Aux 1&2 Functions +
# On/Off", decoded exactly as the map spells it out.
AUX_FIELDS = {
    # "Aux1Function = Aux12Function & 0x3f;"
    "aux1_function": (0x003F, 0),
    # "Aux1OffAutoOn = (((Aux12Function & 0xc0) >> 6));"
    "aux1_mode": (0x00C0, 6),
    # "Aux2Function = (Aux12FunctionS & 0x3f00) >> 8;"
    "aux2_function": (0x3F00, 8),
    # "Aux2OffAutoOn = ((Aux12FunctionS & 0xc000) >> 14);"
    "aux2_mode": (0xC000, 14),
}

# Tables 4165-1 and 4165-2, "Aux 1/2 Off Auto On".
AUX_OFF_AUTO_ON = {0: "Off", 1: "Auto", 2: "On", 3: "Unimplemented"}

# Table 4165-3, Aux1Function (bits 0-5). Note there is no value 0.
AUX1_FUNCTIONS = {
    1: "Diversion Slow High",
    2: "Low Battery Disconnect High",
    3: "Waste Not High",
    4: "Waste Not Low",
    7: "PV On High",
    8: "PV On Low",
    13: "Toggle Test",
    14: "Nite Light High",
    15: "Day Light High",
    16: "Wind Clipper Control",
    17: "Float High",
    18: "Float Low",
    19: "Vent Fan High",
    20: "Vent Fan Low",
    21: "GFP Trip High",
}

# Table 4165-4, Aux2Function (bits 8-13). This table does start at 0.
AUX2_FUNCTIONS = {
    0: "Diversion High PWM",
    1: "Diversion Low PWM",
    2: "Waste Not High",
    3: "Waste Not Low",
    6: "Toggle Test",
    7: "PV V On High",
    8: "PV V On Low",
    10: "Wind Clipper Control",
    11: "Nite Light High",
    12: "Day Light High",
    13: "Float High Output",
    14: "Float Low Output",
    15: "Active High Turn Off",
    16: "Active Low Turn Off",
    17: "Active High Float",
    18: "Whizbang Junior (WB Jr.)",
}

# Force Flag Bits, as bit positions. Table 4160-1 gives these as 32-bit
# values spread over registers 4160 (low word) and 4161 (high word); use
# register_values.force_flag_write() to pick the register, or the 16-bit
# register will silently truncate anything above 0xFFFF.
# Note ForceEEpromUpdateWriteF is what makes writes to (EE) registers
# permanent; until it is sent, changed settings apply only until a restart.
FORCE_FLAGS = {
    "ForceEEpromUpdate": 2,       # 0x00000004, low word
    "ForceEEpromInitRead": 3,     # 0x00000008, low word
    "ForceResetInfoFlags": 4,     # 0x00000010, low word
    "ForceFloat": 5,              # 0x00000020, low word
    "ForceBulk": 6,               # 0x00000040, low word
    "ForceEqualize": 7,           # 0x00000080, low word
    "ForceNite": 8,               # 0x00000100, low word
    "ForceSweep": 11,             # 0x00000800, low word
    "ResetAeqCounts": 16,         # 0x00010000, high word
    "ForceResetFaults": 23,       # 0x00800000, high word
}

# Reading a setting back is how we find out whether the Classic took it. Two kinds
# of register cannot take part: the ones whose write changes the Modbus connection
# itself, and the ones the register map says are write-only.
NO_READBACK_REGISTERS = frozenset(
    {
        # "MODBUS_PORT_REGISTER" and 4326 move the connection; the reply cannot
        # arrive on the socket that carried the write.
        REGISTER_MAP["MODBUS_PORT_REGISTER"],
        REGISTER_MAP["CLASSIC_MODBUS_ADDR_EEPROM"],
        # Table 4160-1 is headed "ForceFlagsBits (Write Only)": reading them back
        # would fail for a reason that has nothing to do with the write.
        REGISTER_MAP["FORCE_FLAG_BITS"],
        REGISTER_MAP["FORCE_FLAG_BITS_HIGH"],
    }
)

# Registers the register map marks "(EE)". The map says: "When you see (EE),
# this means that register value is saved to EEprom whenever the Force write to
# EEprom is set and sent to the Classic. When write to EEprom is requested, ALL
# registers that can be saved to EEprom are saved at this time." A plain write
# therefore takes effect immediately but is lost on the next restart, which is
# why set points such as the absorb voltage appeared not to be saved.
# Read-only views of what the Classic is actually doing, transcribed from the
# register map. None of these had an entity, and three of them are the numbers a
# user needs to make sense of a charge cycle: the compensated target the Classic
# regulates to (4244), the nominal bank voltage it settled on (4245), and why it
# reset (4142).
#
# (REGISTER_MAP key, group, name, units, kind, diagnostic, enabled by default)
#
# kind is "tenths" for the map's "([4nnn] /10) x" formulas, "nominal" for register
# 4245 ("[4245] 12 * 1 thru 10"), and "raw" for a plain code or counter.
#
# The map's rows for 4276 and 4277 read "([4376] /10)" and "([4377] /10)", which is
# a typo in the document: it has no registers 4376 or 4377. The value shown is the
# row's own register over ten, which is what the row's description says ("Battery
# Voltage Unfiltered"). registers2.json took the typo literally and invented
# 4376/4377 entries with formulas of their own.
CLASSIC_STATUS_SENSORS = (
    ("VBATT_REG_SET_P_TMP_COMP", "classic_status", "Battery Regulation Target", "V", "tenths", False, True),
    ("VBATT_NOMINAL", "classic_status", "Nominal Battery Voltage", "V", "nominal", False, True),
    ("ENDING_AMPS", "classic_status", "Ending Amperage", "A", "tenths", False, True),
    ("REBULK_VOLTS", "classic_status", "Rebulk Voltage", "V", "tenths", False, True),
    ("VPV_TARGET_RD", "classic_status", "PV Target Voltage", "V", "tenths", True, False),
    ("IBATT_UNFILTERED", "classic_status", "Battery Current Unfiltered", "A", "tenths", True, False),
    ("VBATT_UNFILTERED", "classic_status", "Battery Voltage Unfiltered", "V", "tenths", True, False),
    ("VPV_UNFILTERED", "classic_status", "PV Voltage Unfiltered", "V", "tenths", True, False),
    # Table 4142-1 is referenced by the register map but never printed in this
    # revision, so the reason is the code the Classic sends, undecorated.
    ("REASON_FOR_RESET", "time_settings", "Reason For Reset", None, "raw", True, False),
    ("PWM_READ_ONLY", "time_settings", "PWM Duty Cycle Command", None, "raw", True, False),
    ("NITE_MINUTES_NO_PWR", "settings", "Minutes Without Power", "min", "raw", True, False),
)

# The Aux 1 / Aux 2 thresholds. The register map gives one register per threshold
# and the integration reads all of them every interval, but never had an entity for
# any of them, so they were invisible.
#
# (REGISTER_MAP key, name, units, tenths, minimum, maximum, step)
#
# The minimums and maximums are only filled in where the register map states a
# range - register 4169 says "0,1,2,3,4 or 5 volts". Everywhere else the map gives
# no range, so none is invented.
AUX_THRESHOLD_SETTINGS = (
    ("AUX1_VOLTS_LO_ABS", "Aux 1 Low Absolute Voltage", "V", True, None, None, 0.1),
    ("AUX1_VOLTS_HI_ABS", "Aux 1 High Absolute Voltage", "V", True, None, None, 0.1),
    ("AUX1_DELAY_T_MS", "Aux 1 Delay Before Asserting", "ms", False, None, None, 1.0),
    ("AUX1_HOLD_T_MS", "Aux 1 Hold Before De-asserting", "ms", False, None, None, 1.0),
    ("AUX2_PWM_VWIDTH", "Aux 2 PWM Voltage Width", "V", True, 0.0, 5.0, 1.0),
    ("AUX2_VOLTS_HI_ABS", "Aux 2 High Absolute Voltage", "V", True, None, None, 0.1),
    # The four waste-not thresholds are offsets from the charge stage target. The
    # register map writes "([4174] /10) Volts" and gives no sign convention, so the
    # value is shown as the register holds it and nothing is guessed.
    ("AUX1_VOLTS_LO_REL", "Aux 1 Waste-Not Lower Voltage", "V", True, None, None, 0.1),
    ("AUX1_VOLTS_HI_REL", "Aux 1 Waste-Not Upper Voltage", "V", True, None, None, 0.1),
    ("AUX2_VOLTS_LO_REL", "Aux 2 Waste-Not Lower Voltage", "V", True, None, None, 0.1),
    ("AUX2_VOLTS_HI_REL", "Aux 2 Waste-Not Upper Voltage", "V", True, None, None, 0.1),
    ("AUX1_VOLTS_LO_PV_ABS", "Aux 1 Low PV Absolute Voltage", "V", True, None, None, 0.1),
    ("AUX1_VOLTS_HI_PV_ABS", "Aux 1 High PV Absolute Voltage", "V", True, None, None, 0.1),
    ("AUX2_VOLTS_HI_PV_ABS", "Aux 2 High PV Absolute Voltage", "V", True, None, None, 0.1),
)

EE_BACKED_REGISTERS = frozenset(
    {
        REGISTER_MAP["MODBUS_PORT_REGISTER"],
        REGISTER_MAP["BATTERY_OUTPUT_CURRENT_LIMIT"],
        REGISTER_MAP["ABSORB_SETPOINT_VOLTAGE"],
        REGISTER_MAP["FLOAT_VOLTAGE_SETPOINT"],
        REGISTER_MAP["EQUALIZE_VOLTAGE_SETPOINT"],
        REGISTER_MAP["MIN_ABSORB_TIME"],
        REGISTER_MAP["ABSORB_TIME_EEPROM"],
        REGISTER_MAP["MAX_BATTERY_TEMP_COMP_VOLTAGE"],
        REGISTER_MAP["MIN_BATTERY_TEMP_COMP_VOLTAGE"],
        REGISTER_MAP["BATTERY_TEMP_COMP_VALUE"],
        REGISTER_MAP["EQUALIZE_RETRY_DAYS"],
        REGISTER_MAP["EQUALIZE_TIME_EEPROM"],
        REGISTER_MAP["EQUALIZE_INTERVAL_DAYS_EEPROM"],
        REGISTER_MAP["CLASSIC_MODBUS_ADDR_EEPROM"],
        # Every Aux threshold is marked "(EE)" in the register map, so a change
        # needs the same EEPROM commit the set points do.
        *(REGISTER_MAP[key] for key, *_ in AUX_THRESHOLD_SETTINGS),
    }
    | {REGISTER_MAP[f"WIND_POWER_TABLE_V_{step}_EEPA"] for step in range(8)}
    | {REGISTER_MAP[f"WIND_POWER_TABLE_I_{step}_EEPA"] for step in range(8)}
)

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


# Define the register groups we need to read from the device
# Each group represents a functional category of registers
REGISTER_GROUPS = {
    "info_flags": [
        REGISTER_MAP["INFO_FLAGS_LOW"],
        REGISTER_MAP["INFO_FLAGS_HIGH"],
    ],
    "serial": [
        REGISTER_MAP["SERIAL_NUMBER_MSB_RO"],
        REGISTER_MAP["SERIAL_NUMBER_LSB_RO"],
    ],
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
        # 4141 and 4142 are inside the 4138-4143 block this group already reads.
        REGISTER_MAP["PWM_READ_ONLY"],
        REGISTER_MAP["REASON_FOR_RESET"],
    ],
    # Add settings registers for MPPT mode, Modbus port, etc.
    "settings": [
        REGISTER_MAP["MPPT_MODE"],
        # 4135 sits beside 4136/4137, so the block read already brings it.
        REGISTER_MAP["NITE_MINUTES_NO_PWR"],
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
    # The Classic's own regulation values, read in three blocks:
    # 4191, 4244-4249 and 4272-4277.
    "classic_status": [
        REGISTER_MAP["VPV_TARGET_RD"],
        REGISTER_MAP["VBATT_REG_SET_P_TMP_COMP"],
        REGISTER_MAP["VBATT_NOMINAL"],
        REGISTER_MAP["ENDING_AMPS"],
        REGISTER_MAP["REBULK_VOLTS"],
        REGISTER_MAP["IBATT_UNFILTERED"],
        REGISTER_MAP["VBATT_UNFILTERED"],
        REGISTER_MAP["VPV_UNFILTERED"],
    ],
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
