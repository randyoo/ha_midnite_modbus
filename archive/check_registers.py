#!/usr/bin/env python3
"""Check which registers are being read vs defined."""

# Simplified version without imports
REGISTER_MAP = {
    "UNIT_ID": 4101,
    "UNIT_SW_DATE_RO": 4102,
    "UNIT_SW_DATE_MONTH_DAY": 4103,
    "INFO_FLAGS_BITS3": 4104,
    "RESERVED_4105": 4105,
    "MAC_ADDRESS_PART_1": 4106,
    "MAC_ADDRESS_PART_2": 4107,
    "MAC_ADDRESS_PART_3": 4108,
    "JrAmpHourNET": 4109,
    "DEVICE_ID_LSW": 4111,
    "DEVICE_ID_MSW": 4112,
    "STATUSROLL": 4113,
    "RESTART_TIME_MS": 4114,
    "DISP_AVG_VBATT": 4115,
    "DISP_AVG_VPV": 4116,
    "IBATT_DISPLAY_S": 4117,
    "KW_HOURS": 4118,
    "WATTS": 4119,
    "COMBO_CHARGE_STAGE": 4120,
    "PV_INPUT_CURRENT": 4121,
    "VOC_LAST_MEASURED": 4122,
    "HIGHEST_VINPUT_LOG": 4123,
    "MATCH_POINT_SHADOW": 4124,
    "AMP_HOURS_DAILY": 4125,
    "LIFETIME_KW_HOURS_1": 4126,
    "LIFETIME_KW_HOURS_1_HIGH": 4127,
    "LIFETIME_AMP_HOURS_1": 4128,
    "LIFETIME_AMP_HOURS_1_HIGH": 4129,
}

REGISTER_GROUPS = {
    "device_info": [4101, 4111, 4112, 4210, 4211, 4212, 4213, 4106, 4107, 4108],
    "status": [4115, 4116, 4117, 4119, 4120, 4121, 4122],
    "temperatures": [4132, 4133, 4134],
    "energy": [4125, 4126, 4127, 4128, 4129],
    "time_settings": [4138, 4139, 4143],
    "diagnostics": [4275],
    "setpoints": [4148, 4149, 4150, 4151],
    "eeprom_settings": [4154, 4162, 4163],
}

# Get all registers that are being read
all_read_registers = set()
for group in REGISTER_GROUPS.values():
    for reg in group:
        all_read_registers.add(reg)

print("=" * 80)
print("REGISTERS BEING READ BY COORDINATOR:")
print("=" * 80)
for name, addr in sorted(REGISTER_MAP.items()):
    if addr in all_read_registers:
        print(f"{addr:6d} - {name}")

print("\n" + "=" * 80)
print("REGISTERS NOT BEING READ (likely showing 'unknown'):")
print("=" * 80)
not_read = []
for name, addr in sorted(REGISTER_MAP.items()):
    if addr not in all_read_registers:
        not_read.append((addr, name))

for addr, name in not_read[:30]:  # Show first 30
    print(f"{addr:6d} - {name}")

print(f"\n... and {len(not_read) - 30} more not shown")
