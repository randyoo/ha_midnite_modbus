"""Constants for the Midnite Solar integration."""

DOMAIN = "midnite_solar"

DEFAULT_PORT = 502
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15

# The two cadences are deliberately separate. The Classic is polled over
# Modbus every scan_interval - that is the LIVE picture, and it is what the
# bridge cache serves to the desktop app. Entities (and with them HA's
# recorder) are republished at most every sensor_interval, so feeding an app
# that polls its cache once a second never fills the HA database with
# sub-second history rows.
CONF_SENSOR_INTERVAL = "sensor_interval"
DEFAULT_SENSOR_INTERVAL = 60

# The bridge: this integration as the Classic's one Modbus client, serving a
# LAN API on Home Assistant's own HTTP port so a desktop app (or anything
# else) can watch and write without ever touching the single-connection
# the Classic's Ethernet port itself. Off by default - it is a LAN-reachable
# path that can write to the MPPT, so the user opts in. The bridge needs no
# Home Assistant token: reads are open to any device that can reach the port,
# and every call that CHANGES the Classic is gated on the write PIN below
# instead. That is a deliberate trade - no token to hand out, but the PIN is
# then the ONLY thing on the write path, so it must be a real one.
CONF_BRIDGE_ENABLED = "bridge_enabled"
DEFAULT_BRIDGE_ENABLED = False
# Carried in every API answer and in the mDNS record; bumped when the contract
# changes. Version 3: the bridge is open (no Home Assistant token); the write
# PIN is a required 6 digits and the all-zeros placeholder DISABLES writes
# until it is changed; and the datalogger sweep is PIN-gated too (it is a
# minutes-long monopoly on the Classic's one connection, so it is not free).
BRIDGE_API_VERSION = 3

# The gate on WRITES - the whole write path, now the bridge carries no token.
# The entry's options hold the PIN; the desktop app asks for it the moment its
# write switch is flipped.
CONF_WRITE_PIN = "write_pin"
PIN_LENGTH = 6
# The fresh-install PLACEHOLDER. It is NOT a usable PIN: while the entry's PIN
# is still this value the bridge REFUSES every write, so there is no default
# that "just works" and no way to write until the owner sets a real 6-digit
# PIN. Chosen as an obvious sentinel (all zeros) the form will not let you keep.
DEFAULT_WRITE_PIN = "000000"
# The header a write call carries the PIN in (a header, not a body field, so
# the gate is identical on endpoints whose bodies differ - and on the reboot,
# which has no body at all).
PIN_HEADER = "X-Midnite-Pin"
# Apple-passcode style, and STRICT: the n-th consecutive wrong PIN buys this
# many seconds during which the bridge does not look at ANY candidate - right
# or wrong, every attempt returns the same 429. That is the whole point: if the
# bridge kept comparing mid-wait, a spammer would read the one non-429 answer
# as the correct PIN and the ladder would slow nothing. Refusing to compare
# gives a guesser exactly one comparison per rung, so guessing costs hours.
# Capped at an hour; a correct PIN clears the run once its own wait has run.
# Counting is per config entry, across every mutating endpoint (bridge.PinGate).
PIN_LOCKOUT_STEPS = (5, 15, 60, 300, 900, 3600)
# The API is served under Home Assistant's existing port (the HAOS firewall
# already opens it and auth is inherited); the mDNS service is how a desktop
# app finds that address without being told.
BRIDGE_URL_PREFIX = "/api/midnite/{entry_id}"
BRIDGE_MDNS_TYPE = "_midnite-bridge._tcp.local."
BRIDGE_MDNS_NAME = "Midnite Bridge"
# The mDNS record is how a client SHOULD find the bridge, but two platforms
# eat it: HAOS's firewall drops inbound 5353 (so the record never reaches a
# querier) and Apple's responder shares 5353 with SO_REUSEPORT, load-balancing
# answers away from a raw client socket. The beacon is the fallback that no
# firewall is in the way of: Home Assistant BROADCASTS this JSON datagram to
# udp/4627 (next to the Classic's own udp/4626 announce) every interval, and a
# client just binds the port and listens - inbound-to-client, which is allowed
# everywhere, and no platform channel. Same contract on macOS/Linux/Windows/
# Android/iOS. `t` is the type tag so a listener can ignore other tools'
# packets on the port.
BRIDGE_BEACON_PORT = 4627
BRIDGE_BEACON_INTERVAL = 5.0
BRIDGE_BEACON_TYPE = "midnite-bridge"
# Where the views and the advertiser live in hass.data between setup/unload.
BRIDGE_VIEWS_KEY = "midnite_solar_bridge_views"
BRIDGE_ADS_KEY = "midnite_solar_bridge_ads"


# Register numbers as given by the Classic MODBUS register map (see
# spec/register_map.txt); checked row by row. The registers.json files this list
# originally came from are untrustworthy - see FINDINGS.md.
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
    "APP_VERSION": 16385,
    "NET_VERSION": 16386,
    "APP_REV_LOW": 16387,
    "APP_REV_HIGH": 16388,
    "NET_REV_LOW": 16389,
    "NET_REV_HIGH": 16390,
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
    # Register numbers, not step numbers: the map's "WindPowerTableV +0 (EE)" is
    # register 4301 and holds steps 0 and 1, "([WindPowerTableV(stp 1)] << 8) +
    # WindPowerTableV(stp 0)". Eight registers hold the sixteen steps.
    "WIND_POWER_TABLE_V_REG_0": 4301,
    "WIND_POWER_TABLE_V_REG_1": 4302,
    "WIND_POWER_TABLE_V_REG_2": 4303,
    "WIND_POWER_TABLE_V_REG_3": 4304,
    "WIND_POWER_TABLE_V_REG_4": 4305,
    "WIND_POWER_TABLE_V_REG_5": 4306,
    "WIND_POWER_TABLE_V_REG_6": 4307,
    "WIND_POWER_TABLE_V_REG_7": 4308,
    "WIND_POWER_TABLE_I_REG_0": 4309,
    "WIND_POWER_TABLE_I_REG_1": 4310,
    "WIND_POWER_TABLE_I_REG_2": 4311,
    "WIND_POWER_TABLE_I_REG_3": 4312,
    "WIND_POWER_TABLE_I_REG_4": 4313,
    "WIND_POWER_TABLE_I_REG_5": 4314,
    "WIND_POWER_TABLE_I_REG_6": 4315,
    "WIND_POWER_TABLE_I_REG_7": 4316,
    
    # Network configuration. Each address is two registers. The map's text prints
    # them "20482 20483 | IP Address | [20483].[20483] MSB LSB . [20482].[20482] MSB
    # LSB" (high word, high byte first), but a real Classic stores the address the
    # other way round (bench-confirmed): the LOWER-numbered register (the _LOW_WORD
    # key) holds the FIRST two octets and each register is read LOW byte first. So
    # _LOW_WORD = the lower register = the first two octets; _HIGH_WORD = the higher
    # register = the last two. See register_values.format_ipv4 for the reversal and
    # why the hardware beats the document here.
    "IP_SETTINGS_FLAGS": 20481,
    "IP_ADDRESS_LOW_WORD": 20482,
    "IP_ADDRESS_HIGH_WORD": 20483,
    "GATEWAY_ADDRESS_LOW_WORD": 20484,
    "GATEWAY_ADDRESS_HIGH_WORD": 20485,
    "SUBNET_MASK_LOW_WORD": 20486,
    "SUBNET_MASK_HIGH_WORD": 20487,
    "DNS_1_LOW_WORD": 20488,
    "DNS_1_HIGH_WORD": 20489,
    "DNS_2_LOW_WORD": 20490,
    "DNS_2_HIGH_WORD": 20491,
    
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
    "DEVICE_ID_LOW_WORD": 4111,
    "DEVICE_ID_HIGH_WORD": 4112,

    # "Enable Flags 2" (the AIR app's name for it, ClassicDataDictionary.as:543).
    # Bit 2 is the "AutoDlyReset" the app enables as the first half of its
    # Reboot (ConfigMenuLocal.as:4882); the other bits are the diversion,
    # shading, waste-not and similar feature enables (ClassicRegisterConversions.as:18-44).
    # "Enable Flags 1" (4187) carries the protection enables the app puts in
    # its Features panel; the rest of these bits the app passes through.
    "ENABLE_FLAGS_1": 4187,
    "ENABLE_FLAGS_2": 4186,

    # The Classic's own clock, which the AIR app reads from the ordinary block
    # as CTIME0 = ([4215] << 16) + [4214], CTIME1 = ([4217] << 16) + [4216] and
    # CTIME2 = [4218] (an unused 16-bit word) - ClassicDataDictionary.as:727-750.
    # The bench census saw the year move in 4217, matching CTIME1's high word.
    "CTIME_SECONDS_MINUTES": 4214,
    "CTIME_HOURS_WEEKDAY": 4215,
    "CTIME_DAY_MONTH": 4216,
    "CTIME_YEAR": 4217,
    "CTIME2": 4218,
}

# What the bridge API must never write, whatever a client asks for.
BRIDGE_FORBIDDEN_WRITES = frozenset(
    {
        # The unlock registers are the hub's own handshake: it writes them
        # with the serial it read from 28673/28674, and the grant is what
        # makes every other write land. A client that wrote one by hand
        # would not get an error - it would just silently stop being able
        # to write anything else.
        REGISTER_MAP["UNLOCK_SERIAL_MSB"],
        REGISTER_MAP["UNLOCK_SERIAL_LSB"],
    }
    # The app's "untouchables" - registers even the AIR app never writes
    # (ClassicDataDictionary.as:1881-1884, PROTOCOL.md section 8).
    | {4188, 4189, 4190, 4193, 4194, 4195, 4196, 4201, 4300, 4394, 4399}
    # Every Classic Ethernet network register 20481-20491: a write there can move the
    # address the Classic answers on and drop the very connection the client
    # is using (the app's own "Classic will disconnect" alert). Not a casual
    # LAN-API target; keep it in the integration where the consequence is
    # understood.
    | set(range(20481, 20492))
)

# The private "internal file" commands the AIR app uses on the same port.
# See private_pdu.py and air-app-reverse/PROTOCOL.md for the frame.
READ_INTERNAL_FUNCTION = 104
WRITE_INTERNAL_FUNCTION = 105
# The clock lives in internal "file" device 7 at address 0, and the app's
# TimeToFileWrite payload is always 20 bytes (PROTOCOL.md section 4.2).
CLOCK_FILE_DEVICE = 7
CLOCK_FILE_ADDRESS = 0
CLOCK_FILE_LENGTH = 20
# 4186 bit 2 "AutoDlyReset"; the app's reboot is 4186|0x04 then 4160|0x100
# (ForceNite). It deliberately leaves the auto-restart setting enabled.
ENABLE_FLAGS_2_AUTO_DLY_RESET = 0x04

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

# The toggles the AIR app's Features panel actually writes
# (ConfigMenuLocal.handleBtnFeaturesCommit, line 1014). The other bits of
# 4186/4187 the app passes through unchanged, so the switches here preserve
# them the same way; do not add entities for bits the app does not expose
# (and note the app hard-codes PartialShading to true on EVERY commit - the
# decompiled caller passes literal true for it, which we deliberately do not
# copy).
ENABLE_FLAG_TOGGLES = (
    ("ground_fault", "Ground Fault Protection", "ENABLE_FLAGS_1", 0,
     "Enables/disables ground fault protection; see the manual for the jumper setting"),
    ("arc_fault", "Arc Fault Detection", "ENABLE_FLAGS_1", 1,
     "Arc fault settings changes require a Classic reboot to take effect"),
    ("night_auto_reset", "Night Auto Reset", "ENABLE_FLAGS_2", 2,
     "Automatic failsafe reset at night; the reboot button enables this bit too"),
    ("networked_batt_temp", "Networked Battery Sensor", "ENABLE_FLAGS_2", 5,
     "Follows the master Classic's battery temperature sensor in a stacked network"),
    ("low_max_mode", "Low-Max Mode", "ENABLE_FLAGS_2", 7,
     "Low-max mode for low input voltage operation"),
    ("insomnia_mode", "Insomnia Mode", "ENABLE_FLAGS_2", 12,
     "Overrides time shutdown while there is still enough power to keep running"),
    ("log_at_night", "Keep Logging at Night", "ENABLE_FLAGS_2", 14,
     "Keep the Classic's datalogger running through the night"),
)

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

# Which registers reject a READ. An earlier note here claimed reading any
# write-only register answered with a Modbus protocol error, and used that to split
# block reads so none straddled one. A bench read of a real Classic refuted that: a
# holding-register read spanning the write-only Force Flag Bits (4154 through 4163,
# across 4160/4161), and reads of 4160 and 4161 on their own and of the RESERVED
# registers 4105/4140/4170/4171/4273/4274, all came back whole. So blocks may span
# W and RESERVED registers - the request-count optimization holds and no block fails
# every interval, which was the fear behind finding 5.
#
# The ONE registers that genuinely reject a read are the unlock registers
# 20492/20493 ("W Serial Number (Unlock Code)"), which this integration only ever
# WRITES and never reads - and the polled "network" block stops at 20491, so no
# block read can reach them. The read-back of the Force Flags after a write is still
# skipped (they are in NO_READBACK_REGISTERS above) because a write-only register
# holds no readable echo of what was just written, not because the read errors.

# Registers the register map marks "(EE)". The map says: "When you see (EE),
# this means that register value is saved to EEprom whenever the Force write to
# EEprom is set and sent to the Classic. When write to EEprom is requested, ALL
# registers that can be saved to EEprom are saved at this time." A plain write
# therefore takes effect immediately but is lost on the next restart, which is
# why set points such as the absorb voltage appeared not to be saved.
# Read-only views of what the Classic is actually doing, transcribed from the
# register map. None of these had an entity, and two of them are numbers a user
# needs to make sense of a charge cycle: the compensated target the Classic
# regulates to (4244) and the reason it reset (4142).
#
# 4245 VbattNominal, 4246 EndingAmps and 4249 RebulkVolts are deliberately not
# here: the map marks them "R/W (EE)", so they are a select and two numbers
# instead, and a sensor on top of that would report the same quantity twice.
#
# (REGISTER_MAP key, group, name, units, kind, diagnostic, enabled by default)
#
# kind is "tenths" for the map's "([4nnn] /10) x" formulas and "raw" for a plain
# code or counter. (Register 4245 used to be a "nominal" sensor here; it is the
# NominalBatteryVoltageSelect now, so no row of this tuple is "nominal".)
#
# The map's rows for 4276 and 4277 read "([4376] /10)" and "([4377] /10)", which is
# a typo in the document: it has no registers 4376 or 4377. The value shown is the
# row's own register over ten, which is what the row's description says ("Battery
# Voltage Unfiltered"). registers2.json took the typo literally and invented
# 4376/4377 entries with formulas of their own.
CLASSIC_STATUS_SENSORS = (
    ("VBATT_REG_SET_P_TMP_COMP", "classic_status", "Battery Regulation Target", "V", "tenths", False, True),
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

# Register 4245 VbattNominal: "[4245] 12 * 1 thru 10 (120 Max for 250 KS)". The
# register is a multiplier, so the bank voltage is twelve times it: ten values, not
# a range. A user picks volts and the Classic gets the multiplier.
# The register's OWN value is the volts: the map's "[4245] 12 * 1 thru 10"
# spells the legal values (12x1..12x10), not a multiplier the register holds.
# Bench 2026-09-21: raw 4245 = 48 while 4115 measured 51.7 V, and the AIR app
# displays 4245's raw value directly. An earlier version of this integration
# keyed the table by the 1..10 multiplier and showed "Unset (48)" on a unit
# configured for 48 V (FINDINGS section 39 follow-up).
NOMINAL_BATTERY_VOLTAGES = {volts: volts for volts in range(12, 121, 12)}

# The map's own words for these four values:
#   "16385 | app version _ | Major: [16385](15…12) Minor: [16385](11…8)
#    Release: [16385](8..4) | Release version of the application code"
#   "16386 | net version, _ | ... | Release version of the communications stack"
#   "16387 16388 | app rev _ | ([16388] << 16) + [16387] | Build Revision of the
#    application code"
#   "16389 16390 | net rev _ | ([16390] << 16) + [16389] | Build Revision of the
#    communications code stack"
FIRMWARE_VERSION_SENSORS = (
    ("APP_VERSION", "App Version", "application code"),
    ("NET_VERSION", "Comms Version", "communications stack"),
)

FIRMWARE_REVISION_SENSORS = (
    ("APP_REV_LOW", "APP_REV_HIGH", "App Build Revision"),
    ("NET_REV_LOW", "NET_REV_HIGH", "Comms Build Revision"),
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
        # 4245 VbattNominal, 4246 EndingAmps and 4249 RebulkVolts are (EE) too.
        REGISTER_MAP["VBATT_NOMINAL"],
        # Both Enable Flags registers are (EE): the app's Features commit ends
        # with CommitSettingsToEEPROM (ConfigMenuLocal.as:1029).
        REGISTER_MAP["ENABLE_FLAGS_1"],
        REGISTER_MAP["ENABLE_FLAGS_2"],
        REGISTER_MAP["ENDING_AMPS"],
        REGISTER_MAP["REBULK_VOLTS"],
        # Every Aux threshold is marked "(EE)" in the register map, so a change
        # needs the same EEPROM commit the set points do.
        *(REGISTER_MAP[key] for key, *_ in AUX_THRESHOLD_SETTINGS),
    }
    | {REGISTER_MAP[f"WIND_POWER_TABLE_V_REG_{step}"] for step in range(8)}
    | {REGISTER_MAP[f"WIND_POWER_TABLE_I_REG_{step}"] for step in range(8)}
)

# MPPT mode mappings (from register 4164)
MPPT_MODES = {
    0x0001: "PV_Uset",
    0x0003: "DYNAMIC",
    0x0005: "WIND TRACK",  # the map writes it with a space, not an underscore
    0x0007: "RESERVED",
    0x0009: "Legacy P&O",
    0x000B: "SOLAR",
    0x000D: "HYDRO",
    0x000F: "RESERVED",
}

# Table 20481-1 Network Settings Flags: "DHCP | 0x0001 | Set this bit to enable
# DHCP." and "Web Access | 0x0002 | Set this bit to enable online access to your
# Classic through http://www.mymidnite.com".
#
# The map also warns what the first flag means for everything beside it:
# "Read Only if the DHCP flag is set. To assign a static IP to the Classic, first
# clear the DHCP flag in the IP Settings Register (20481)." That is the first thing
# to look at when a network address seems not to change, which is why the DHCP flag
# is the one binary sensor of these two that is on by default.
NETWORK_FLAGS = {
    "DHCP": 0x0001,
    "WebAccess": 0x0002,
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
        REGISTER_MAP["DEVICE_ID_LOW_WORD"],
        REGISTER_MAP["DEVICE_ID_HIGH_WORD"],
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
    # The Classic's clock words. One block read of five registers; the AIR app
    # polls the same three words (4214/4216/4218) once its firmware is new
    # enough (controls/StatusPanel.as:580-584).
    "clock": [
        REGISTER_MAP["CTIME_SECONDS_MINUTES"],
        REGISTER_MAP["CTIME_HOURS_WEEKDAY"],
        REGISTER_MAP["CTIME_DAY_MONTH"],
        REGISTER_MAP["CTIME_YEAR"],
        REGISTER_MAP["CTIME2"],
    ],
    # Add settings registers for MPPT mode, Modbus port, etc.
    "settings": [
        REGISTER_MAP["MPPT_MODE"],
        # The AIR app's Features-panel toggles (EnableFlagSwitch entities).
        REGISTER_MAP["ENABLE_FLAGS_1"],
        REGISTER_MAP["ENABLE_FLAGS_2"],
        # 4135 sits beside 4136/4137, so the block read already brings it.
        REGISTER_MAP["NITE_MINUTES_NO_PWR"],
        REGISTER_MAP["MODBUS_PORT_REGISTER"],
        REGISTER_MAP["MINUTE_LOG_INTERVAL_SEC"],
        REGISTER_MAP["SLIDING_CURRENT_LIMIT"],
    ],
    # Add network configuration registers
    "network": [
        # Table 20481-1, and it sits at the front of the block that is already
        # read, so asking for it costs nothing.
        REGISTER_MAP["IP_SETTINGS_FLAGS"],
        REGISTER_MAP["IP_ADDRESS_LOW_WORD"],
        REGISTER_MAP["IP_ADDRESS_HIGH_WORD"],
        REGISTER_MAP["GATEWAY_ADDRESS_LOW_WORD"],
        REGISTER_MAP["GATEWAY_ADDRESS_HIGH_WORD"],
        REGISTER_MAP["SUBNET_MASK_LOW_WORD"],
        REGISTER_MAP["SUBNET_MASK_HIGH_WORD"],
        REGISTER_MAP["DNS_1_LOW_WORD"],
        REGISTER_MAP["DNS_1_HIGH_WORD"],
        REGISTER_MAP["DNS_2_LOW_WORD"],
        REGISTER_MAP["DNS_2_HIGH_WORD"],
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
    # The Classic's own firmware, at 16385 and up: two version registers and two
    # 32-bit build revisions. One block read covers all six.
    "firmware": [
        REGISTER_MAP["APP_VERSION"],
        REGISTER_MAP["NET_VERSION"],
        REGISTER_MAP["APP_REV_LOW"],
        REGISTER_MAP["APP_REV_HIGH"],
        REGISTER_MAP["NET_REV_LOW"],
        REGISTER_MAP["NET_REV_HIGH"],
    ],
    "wind_power_curve": [
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_0"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_1"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_2"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_3"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_4"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_5"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_6"],
        REGISTER_MAP["WIND_POWER_TABLE_V_REG_7"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_0"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_1"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_2"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_3"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_4"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_5"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_6"],
        REGISTER_MAP["WIND_POWER_TABLE_I_REG_7"],
    ],
}
