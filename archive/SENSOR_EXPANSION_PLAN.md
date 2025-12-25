# Midnite Solar Integration - Sensor Expansion Plan

## Overview
This document outlines a plan to expand the Midnite Solar Home Assistant integration by adding new sensor entities that are currently available in the device registers but not exposed in the integration.

## Current State Analysis

### Implemented Sensors (20 total)
1. Device Type
2. Battery Voltage
3. PV Voltage
4. Battery Current
5. Power Output
6. Charge Stage
7. Internal State
8. Rest Reason
9. Battery Temperature
10. FET Temperature
11. PCB Temperature
12. Daily Amp-Hours
13. Lifetime Energy
14. Lifetime Amp-Hours
15. PV Input Current
16. Last Measured VOC
17. Float Time Today
18. Absorb Time Remaining
19. Equalize Time Remaining
20. MAC Address

### Missing Sensors (50+ identified)
The registers.json and registers2.json files contain 50+ additional readable registers that could be exposed as sensors.

## Proposed Implementation Strategy

### Phase 1: Immediate Expansion (High Priority)
**Goal**: Add the most valuable missing sensors that provide essential monitoring capabilities.

#### Sensors to Implement:

1. **Highest Input Voltage** (4123 - HIGHEST_VINPUT_LOG)
   - Category: Diagnostic
   - Unit: V
   - Description: Highest input voltage ever seen by the device
   
2. **PV Target Voltage** (4191 - VPV_TARGET_RD)
   - Category: Diagnostic  
   - Unit: V
   - Description: Read-only PV target voltage (usually Vmpp)

3. **Raw Battery Current** (4272 - IBATT_RAW_A)
   - Category: Diagnostic
   - Unit: A
   - Description: Unfiltered battery current reading

4. **Night Minutes No Power** (4135 - NITE_MINUTES_NO_PWR)
   - Category: Diagnostic
   - Unit: min
   - Description: Counts up when no power, resets on power

5. **Software Version** (4102-4103 - UNIT_SW_DATE_RO)
   - Category: Diagnostic
   - Unit: None
   - Description: Software build date (Year/Month/Day format)

6. **Modbus Port** (4137 - MODBUS_PORT_REGISTER)
   - Category: Diagnostic
   - Unit: None
   - Description: Modbus TCP port number

#### Implementation Steps:
1. Add register mappings to `const.py`
2. Create sensor classes in `sensor.py` following existing patterns
3. Add sensors to the list in `async_setup_entry()`
4. Test with real device data
5. Update documentation

### Phase 2: Configuration Sensors (Medium Priority)
**Goal**: Expose configuration setpoints and parameters for monitoring.

#### Sensors to Implement:

1. **Absorb Setpoint Voltage** (4149 - ABSORB_SETPOINT_VOLTAGE)
   - Category: Diagnostic
   - Unit: V
   
2. **Float Setpoint Voltage** (4150 - FLOAT_VOLTAGE_SETPOINT)
   - Category: Diagnostic
   - Unit: V
   
3. **Equalize Setpoint Voltage** (4151 - EQUALIZE_VOLTAGE_SETPOINT)
   - Category: Diagnostic
   - Unit: V
   
4. **Battery Current Limit** (4148 - BATTERY_OUTPUT_CURRENT_LIMIT)
   - Category: Diagnostic  
   - Unit: A
   
5. **Max Battery Temp Comp Voltage** (4155 - MAX_BATTERY_TEMP_COMP_VOLTAGE)
   - Category: Diagnostic
   - Unit: V
   
6. **Min Battery Temp Comp Voltage** (4156 - MIN_BATTERY_TEMP_COMP_VOLTAGE)
   - Category: Diagnostic
   - Unit: V
   
7. **Battery Temp Comp Value** (4157 - BATTERY_TEMP_COMP_VALUE)
   - Category: Diagnostic
   - Unit: mV/°C per 2V cell
   
8. **Nominal Battery Voltage** (4245 - VBATT_NOMINAL_EEPROM)
   - Category: Diagnostic
   - Unit: V
   
9. **Rebuck Voltage** (4249 - REBUCK_VOLTS_EEPROM)
   - Category: Diagnostic
   - Unit: V
   
10. **Days Between Bulk/Absorb** (4252 - DAYS_BTW_BULK_ABS_EEPROM)
    - Category: Diagnostic
    - Unit: days

### Phase 3: Advanced Sensors (Low Priority)
**Goal**: Add sensors for power users and troubleshooting.

#### Sensor Categories:
- Network configuration (IP, gateway, DNS)
- Communication statistics
- Whizbang Jr integration (if applicable)
- Wind power curve tables
- Advanced timing parameters

## Default Disabled State Implementation

### Approach 1: Configuration Flow Option
Add a checkbox in the config flow to enable "advanced sensors":
```python
# In config_flow.py
class MidniteSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        # ... existing code ...
        
        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            vol.Optional("enable_advanced_sensors", default=False): bool,
        })
```

### Approach 2: Entity-Specific Default Disabled (Recommended)
Use Home Assistant's `default_disabled` manifest property:

1. Update `manifest.json`:
```json
{
  "domain": "midnite_solar",
  "name": "Midnite Solar",
  "version": "1.2.0",
  "iot_class": "local_polling",
  "sensor_platform": {
    "default_disabled": [
      "highest_input_voltage",
      "pv_target_voltage", 
      "raw_battery_current",
      "night_minutes_no_power",
      "software_version",
      "modbus_port",
      "absorb_setpoint_voltage",
      "float_setpoint_voltage",
      "equalize_setpoint_voltage",
      "battery_current_limit"
    ]
  }
}
```

2. Set entity IDs in sensor classes:
```python
class HighestInputVoltageSensor(MidniteSolarSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Highest Input Voltage"
        self._attr_unique_id = f"{entry.entry_id}_highest_input_voltage"
        # This will be used as the entity ID
```

### Approach 3: Per-Sensor Enable/Disable Configuration
Create a configuration option to selectively enable sensors:
```python
# In __init__.py or config_flow.py
async def async_setup_entry(hass, entry, async_add_devices):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Get enabled sensors from config
    enabled_sensors = entry.options.get("enabled_sensors", [])
    
    all_sensors = [
        DeviceTypeSensor(coordinator, entry),
        BatteryVoltageSensor(coordinator, entry),
        # ... other core sensors ...
        HighestInputVoltageSensor(coordinator, entry),  # New sensor
        PVTargetVoltageSensor(coordinator, entry),      # New sensor
    ]
    
    # Filter by enabled sensors if configuration exists
    if enabled_sensors:
        filtered_sensors = [s for s in all_sensors 
                           if hasattr(s, '_attr_unique_id') and 
                              any(s._attr_unique_id.endswith(suffix) 
                                  for suffix in enabled_sensors)]
        async_add_devices(filtered_sensors)
    else:
        # Enable only core sensors by default
        core_sensor_types = ["device_type", "battery_voltage", "pv_voltage", ...]
        filtered_sensors = [s for s in all_sensors 
                           if hasattr(s, '_attr_unique_id') and 
                              any(s._attr_unique_id.endswith(suffix) 
                                  for suffix in core_sensor_types)]
        async_add_devices(filtered_sensors)
```

## Recommended Implementation (Approach 2 - Manifest Default Disabled)

### Step 1: Update const.py
Add new register mappings:
```python
# Add to REGISTER_MAP in const.py
"HIGHEST_VINPUT_LOG": 4123,
"VPV_TARGET_RD": 4191,
"IBATT_RAW_A": 4272,
"NITE_MINUTES_NO_PWR": 4135,
"UNIT_SW_DATE_RO_YEAR": 4102,
"UNIT_SW_DATE_RO_MONTH_DAY": 4103,
"MODBUS_PORT_REGISTER": 4137,
"ABSORB_SETPOINT_VOLTAGE": 4149,  # Already exists but not implemented
"FLOAT_VOLTAGE_SETPOINT": 4150,   # Already exists but not implemented
"EQUALIZE_VOLTAGE_SETPOINT": 4151,# Already exists but not implemented
"BATTERY_OUTPUT_CURRENT_LIMIT": 4148,  # Already exists but not implemented
```

### Step 2: Create Sensor Classes
Add new sensor classes to `sensor.py`:

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


class PVTargetVoltageSensor(MidniteSolarSensor):
    """Representation of PV target voltage sensor."""

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "PV Target Voltage"
        self._attr_unique_id = f"{entry.entry_id}_pv_target_voltage"
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
                value = status_data.get(REGISTER_MAP["VPV_TARGET_RD"])
                if value is not None:
                    return value / 10.0
        return None
```

### Step 3: Update async_setup_entry()
Add new sensors to the list (they will be disabled by default):
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Midnite Solar sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        DeviceTypeSensor(coordinator, entry),
        BatteryVoltageSensor(coordinator, entry),
        PVoltageSensor(coordinator, entry),
        BatteryCurrentSensor(coordinator, entry),
        PowerWattsSensor(coordinator, entry),
        ChargeStageSensor(coordinator, entry),
        InternalStateSensor(coordinator, entry),
        RestReasonSensor(coordinator, entry),
        BatteryTemperatureSensor(coordinator, entry),
        FETTemperatureSensor(coordinator, entry),
        PCBTemperatureSensor(coordinator, entry),
        DailyAmpHoursSensor(coordinator, entry),
        LifetimeEnergySensor(coordinator, entry),
        LifetimeAmpHoursSensor(coordinator, entry),
        PVInputCurrentSensor(coordinator, entry),
        VOCMeasuredSensor(coordinator, entry),
        FloatTimeTodaySensor(coordinator, entry),
        AbsorbTimeRemainingSensor(coordinator, entry),
        EqualizeTimeRemainingSensor(coordinator, entry),
        MACAddressSensor(coordinator, entry),
        # New sensors (will be disabled by default via manifest.json)
        HighestInputVoltageSensor(coordinator, entry),
        PVTargetVoltageSensor(coordinator, entry),
        RawBatteryCurrentSensor(coordinator, entry),
        NightMinutesNoPowerSensor(coordinator, entry),
        SoftwareVersionSensor(coordinator, entry),
        ModbusPortSensor(coordinator, entry),
    ]
    
    async_add_entities(sensors)
```

### Step 4: Update manifest.json
Add the `default_disabled` configuration:
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
  "version": "1.2.0",
  "sensor_platform": {
    "default_disabled": [
      "highest_input_voltage",
      "pv_target_voltage",
      "raw_battery_current", 
      "night_minutes_no_power",
      "software_version",
      "modbus_port"
    ]
  }
}
```

### Step 5: Update Documentation
Update README.md to document the new sensors:
- Add a section "Available Sensors" listing all sensors
- Indicate which are enabled by default vs. optional
- Provide examples of how to enable disabled sensors in UI

## Testing Strategy

1. **Unit Tests**: Create tests for each new sensor class
2. **Integration Tests**: Test with real device data (if available)
3. **Manual Testing**: Verify sensors appear correctly in Home Assistant UI
4. **Performance Testing**: Ensure adding more sensors doesn't significantly impact scan performance

## Rollout Plan

1. **Development**: Implement Phase 1 sensors
2. **Testing**: Test with various device configurations
3. **Beta Release**: Publish as beta version for community testing
4. **Feedback Collection**: Gather user feedback on which additional sensors are most valuable
5. **Phase 2 Implementation**: Add configuration/setpoint sensors based on feedback
6. **Final Release**: Stable release with all Phase 1 and Phase 2 sensors

## Benefits of This Approach

1. **Backward Compatibility**: Existing installations continue to work without changes
2. **User Control**: Users can enable additional sensors as needed
3. **Reduced Overhead**: Disabled sensors don't consume resources or clutter the UI by default
4. **Flexibility**: Easy to add more sensors in future releases without breaking changes
5. **Discoverability**: Users can easily find and enable additional sensors through the UI

## Alternative Considerations

### Option A: All Sensors Enabled by Default
- Pros: No configuration needed, all data available immediately
- Cons: May overwhelm users with too many entities, increased resource usage

### Option B: Per-Device Configuration
- Pros: More granular control
- Cons: Complexer configuration UI, harder to manage at scale

### Option C: Feature Flags in Config Flow
- Pros: Clear user choice during setup
- Cons: Requires reconfiguration to change later, less flexible

**Recommended**: Approach 2 (Manifest default_disabled) provides the best balance of simplicity, flexibility, and user control.
