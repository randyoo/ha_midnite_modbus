# Missing Sensor Entities Analysis

## Currently Implemented Sensors
The integration currently has the following sensors:
- Battery Voltage (4115)
- PV Voltage (4116)  
- Battery Current (4117)
- Power Output (4119)
- Charge Stage (4120)
- Internal State (4120)
- Device Type (4101)
- Rest Reason (4275)
- Battery Temperature (4132)
- FET Temperature (4133)
- PCB Temperature (4134)
- Daily Amp-Hours (4125)
- Lifetime Energy (4126, 4127)
- Lifetime Amp-Hours (4128, 4129)
- PV Input Current (4121)
- Last Measured VOC (4122)
- Float Time Today (4138)
- Absorb Time Remaining (4139)
- Equalize Time Remaining (4143)
- MAC Address (4106, 4107, 4108)

## High-Value Missing Sensors (Recommended for Implementation)

### Voltage Sensors
1. **HIGHEST_VINPUT_LOG** (4123) - Highest input voltage ever seen
2. **VPV_TARGET_RD** (4191) - Read-only PV target (usually Vmpp)
3. **VBATT_REG_SET_P_TEMP_COMP** (4244) - Battery regulation target voltage, temp-compensated
4. **VBATT_NOMINAL_EEPROM** (4245) - Nominal battery bank voltage (12V, 24V, etc.)

### Current Sensors  
5. **IBATT_RAW_A** (4272) - Battery current, unfiltered
6. **IPV_MINUS_RAW** (4266) - Raw PV negative current from ADC

### Power/Energy Sensors
7. **KW_HOURS** (4118) - Energy to battery (reset daily)
8. **AMP_HOURS_DAILY** (4125) - Daily amp-hours reset at 23:59

### Temperature Sensors
9. **BATTERY_TEMP_PASSED_EEPROM** (4327) - Follow-Me temperature sensor value

### Time/Duration Sensors
10. **NITE_MINUTES_NO_PWR** (4135) - Counts up when no power, resets on power
11. **MINUTE_LOG_INTERVAL_SEC** (4136) - Data logging interval
12. **ABSORB_TIME_EEPROM** (4154) - Absorb setpoint time for batteries
13. **EQUALIZE_TIME_EEPROM** (4162) - Initialize equalize stage duration
14. **EQUALIZE_INTERVAL_DAYS_EEPROM** (4163) - Days between equalize stages (auto EQ)
15. **SIESTA_TIME_SEC** (4238) - Sleep timer (max 5 min)
16. **ENDING_AMPS_TIMER_SEC** (4297) - Timer for ending amps (60 s reference)

### Setpoint/Configuration Sensors (Diagnostic Category)
17. **ABSORB_SETPOINT_VOLTAGE** (4149) - Already in const.py but not implemented as sensor
18. **FLOAT_VOLTAGE_SETPOINT** (4150) - Already in const.py but not implemented as sensor
19. **EQUALIZE_VOLTAGE_SETPOINT** (4151) - Already in const.py but not implemented as sensor
20. **BATTERY_OUTPUT_CURRENT_LIMIT** (4148) - Already in const.py but not implemented as sensor
21. **MAX_BATTERY_TEMP_COMP_VOLTAGE** (4155) - Highest charge voltage limited when using temp sensor
22. **MIN_BATTERY_TEMP_COMP_VOLTAGE** (4156) - Lowest charge voltage limited when using temp sensor
23. **BATTERY_TEMP_COMP_VALUE** (4157) - Temperature compensation value per 2V cell
24. **REBUCK_VOLTS_EEPROM** (4249) - Re-bulk if battery drops below this for >90 s
25. **DAYS_BTW_BULK_ABS_EEPROM** (4252) - Days between bulk/absorb cycles
26. **REBUCK_TIMER_SEC_EEPROM** (4257) - Re-bulk interval timer seconds

### Status/Fault Sensors
27. **INFO_FLAGS_BITS3** (4104) - System-wide status flags (bit field)
28. **STATUSROLL** (4113) - 12-bit status value, updated once per second
29. **REASON_FOR_RESET** (4142) - Reason Classic reset
30. **SLIDING_CURRENT_LIMIT** (4152) - Sliding current limit (varies with V/Temp)
31. **MPPT_MODE** (4164) - Solar, Wind, etc.
32. **AUX_1_AND_2_FUNCTION** (4165) - Combined Aux 1 & 2 function + ON/OFF
33. **ENABLE_FLAGS3** (4182) - Enable forwarding of Modbus traffic
34. **ENABLE_FLAGS2** (4186) - Various feature flags
35. **ENABLE_FLAGS_BITS** (4187) - Legacy flags

### Network/Communication Sensors
36. **MODBUS_PORT_REGISTER** (4137) - Modbus TCP port (default 502)
37. **IP_SETTINGS_FLAGS** (20481) - Network settings flags (DHCP, Web Access)
38. **IP_ADDRESS_LSB_1/2** (20482, 20483) - IP address parts
39. **GATEWAY_ADDRESS_LSB_1/2** (20484, 20485) - Gateway address parts
40. **SUBNET_MASK_LSB_1/2** (20486, 20487) - Subnet mask parts
41. **DNS_1_LSB_1/2** (20488, 20489) - Primary DNS parts
42. **DNS_2_LSB_1/2** (20490, 20491) - Secondary DNS parts

### Version Information
43. **UNIT_SW_DATE_RO** (4102, 4103) - Software build date
44. **APP_VERSION** (16385) - Application firmware version
45. **NET_VERSION** (16386) - Communications stack version

### Whizbang Jr Sensors (if applicable)
46. **WJRB_AMP_HOUR_POSITIVE** (4365, 4366) - Whizbang Jr positive amp-hours
47. **WJRB_AMP_HOUR_NEGATIVE** (4367, 4368) - Whizbang Jr negative amp-hours
48. **WJRB_AMP_HOUR_NET** (4369, 4370) - Whizbang Jr net amp-hours
49. **WJRB_CURRENT_32_SIGNED** (4371) - Whizbang Jr amps (scaled & rounded)
50. **WIZBANG_RAW_CRC_AND_TEMP** (4372) - Raw CRC and temperature

## Implementation Plan

### Phase 1: Core Sensors (High Priority)
These sensors provide essential monitoring capabilities:
- HIGHEST_VINPUT_LOG (4123)
- VPV_TARGET_RD (4191)
- IBATT_RAW_A (4272) 
- NITE_MINUTES_NO_PWR (4135)
- INFO_FLAGS_BITS3 (4104) - as binary sensor or diagnostic
- STATUSROLL (4113) - as diagnostic
- UNIT_SW_DATE_RO (4102, 4103) - software version info

### Phase 2: Configuration/Setpoint Sensors (Medium Priority)
These help users understand and monitor their system configuration:
- ABSORB_SETPOINT_VOLTAGE (4149)
- FLOAT_VOLTAGE_SETPOINT (4150)
- EQUALIZE_VOLTAGE_SETPOINT (4151)
- BATTERY_OUTPUT_CURRENT_LIMIT (4148)
- MAX_BATTERY_TEMP_COMP_VOLTAGE (4155)
- MIN_BATTERY_TEMP_COMP_VOLTAGE (4156)
- BATTERY_TEMP_COMP_VALUE (4157)

### Phase 3: Advanced/Optional Sensors (Low Priority)
These are useful for power users and troubleshooting:
- Network configuration sensors (IP, gateway, DNS)
- Whizbang Jr sensors (only if device is connected)
- Communication statistics registers (10001-10062)
- Wind power curve tables (4301-4316)

## Implementation Strategy

1. **Add to const.py**: Map all new register addresses
2. **Create sensor classes**: Extend MidniteSolarSensor for each new sensor
3. **Categorize properly**: Use EntityCategory.DIAGNOSTIC for configuration/setpoint sensors
4. **Default disabled**: Add configuration option to enable these sensors (default: False)
5. **Add to async_setup_entry**: Include new sensors in the list when enabled
6. **Documentation**: Update README with information about new sensors

## Example Implementation Pattern

```python
class HighestInputVoltageSensor(MidniteSolarSensor):
    """Representation of highest input voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Highest Input Voltage"
        self._attr_unique_id = f"{entry.entry_id}_highest_input_voltage"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = "V"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["HIGHEST_VINPUT_LOG"])
                if value is not None:
                    return value / 10.0
        return None
```

## Configuration Approach

Add to configuration flow or manifest.json:

```json
{
  "domain": "midnite_solar",
  "name": "Midnite Solar",
  "documentation": "https://github.com/your/repo",
  "issue_tracker": "https://github.com/your/repo/issues",
  "dependencies": [],
  "codeowners": ["@owner"],
  "config_flow": true,
  "requirements": ["pymodbus==2.5.3"],
  "iot_class": "local_polling",
  "version": "1.0.0",
  "sensor_platform": {
    "default_disabled": [
      "highest_input_voltage",
      "pv_target_voltage",
      "raw_battery_current",
      "night_minutes_no_power",
      "absorb_setpoint_voltage",
      "float_setpoint_voltage",
      "equalize_setpoint_voltage",
      "battery_current_limit"
    ]
  }
}
```
