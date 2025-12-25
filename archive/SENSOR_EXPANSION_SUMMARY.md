# Midnite Solar Integration - Sensor Expansion Summary

## Executive Summary

This document provides a concise overview of the plan to expand the Midnite Solar Home Assistant integration by adding new sensor entities in a default-disabled state.

## Current State

**20 sensors currently implemented:**
- Core monitoring: Battery/PV voltage, current, power, temperatures
- Status information: Charge stage, internal state, device type
- Energy tracking: Daily/ lifetime amp-hours and energy
- Diagnostic data: Rest reason, MAC address, timing information

## Missing Sensors Identified

**50+ additional readable registers** available in the device firmware that could be exposed as sensors.

### Key Categories of Missing Sensors:

1. **Voltage Monitoring** (4 sensors)
   - Highest input voltage ever seen
   - PV target voltage (Vmpp reference)
   - Battery regulation target (temp-compensated)
   - Nominal battery bank voltage

2. **Current Monitoring** (2 sensors)
   - Raw/unfiltered battery current
   - Raw PV negative current

3. **Configuration/Setpoints** (10+ sensors)
   - Absorb/float/equalize voltage setpoints
   - Battery current limits
   - Temperature compensation values
   - Rebuck voltages and timers

4. **Status & Diagnostics** (8+ sensors)
   - System status flags
   - Software version information
   - Modbus port configuration
   - MPPT mode settings

5. **Timing & Duration** (6+ sensors)
   - Night minutes without power
   - Logging intervals
   - Stage timing parameters

## Proposed Implementation Plan

### Phase 1: High Priority Sensors (6 sensors)
These provide essential monitoring capabilities:
- ✅ Highest Input Voltage (4123)
- ✅ PV Target Voltage (4191)
- ✅ Raw Battery Current (4272)
- ✅ Night Minutes No Power (4135)
- ✅ Software Version (4102-4103)
- ✅ Modbus Port (4137)

### Phase 2: Configuration Sensors (10 sensors)
Expose setpoints and parameters for monitoring:
- Absorb/float/equalize voltage setpoints
- Battery current limits
- Temperature compensation values
- Rebuck voltages and timers

### Phase 3: Advanced Sensors (Optional)
For power users and troubleshooting:
- Network configuration (IP, gateway, DNS)
- Communication statistics
- Whizbang Jr integration
- Wind power curve tables

## Implementation Strategy

### Recommended Approach: Manifest default_disabled

**Why this approach:**
- ✅ Backward compatible - existing installations unaffected
- ✅ User control - enable sensors via Home Assistant UI
- ✅ Reduced overhead - disabled sensors don't consume resources
- ✅ Flexible - easy to add more sensors in future
- ✅ Discoverable - users can find and enable through UI

**Implementation steps:**

1. **Update const.py** - Add register mappings for new sensors
2. **Create sensor classes** - Extend MidniteSolarSensor base class
3. **Add to async_setup_entry()** - Include in sensor list
4. **Update manifest.json** - Add default_disabled configuration
5. **Update documentation** - Document all available sensors

### Example: Adding Highest Input Voltage Sensor

```python
# 1. Add to const.py
REGISTER_MAP = {
    ...
    "HIGHEST_VINPUT_LOG": 4123,
}

# 2. Create sensor class in sensor.py
class HighestInputVoltageSensor(MidniteSolarSensor):
    def __init__(self, coordinator, entry):
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
        if self.coordinator.data and "data" in self.coordinator.data:
            status_data = self.coordinator.data["data"].get("status")
            if status_data:
                value = status_data.get(REGISTER_MAP["HIGHEST_VINPUT_LOG"])
                if value is not None:
                    return value / 10.0
        return None

# 3. Add to async_setup_entry()
sensors = [
    ...
    HighestInputVoltageSensor(coordinator, entry),
]

# 4. Update manifest.json
"sensor_platform": {
    "default_disabled": [
        "highest_input_voltage",
        # other sensors...
    ]
}
```

## Benefits

1. **Enhanced Monitoring** - More comprehensive system visibility
2. **Better Diagnostics** - Easier troubleshooting with additional data
3. **Configuration Awareness** - Monitor setpoints and parameters
4. **Future-Proof** - Framework in place for easy expansion
5. **User-Friendly** - No configuration clutter, enable only what's needed

## Rollout Timeline

1. **Week 1-2**: Implement Phase 1 sensors
2. **Week 3**: Testing and bug fixing
3. **Week 4**: Beta release for community testing
4. **Week 5-6**: Gather feedback, refine implementation
5. **Week 7**: Final release with all Phase 1 sensors
6. **Ongoing**: Add Phase 2 sensors based on user demand

## Documentation Updates Required

- Update README.md with complete sensor list
- Document which sensors are enabled by default
- Provide instructions for enabling disabled sensors
- Add examples of sensor usage in dashboards/automations

## Testing Requirements

1. **Unit tests** - Test each new sensor class
2. **Integration tests** - Verify with real device data (if available)
3. **Manual testing** - Validate UI behavior
4. **Performance testing** - Ensure no significant impact on scan performance

## Files to Modify

1. `custom_components/midnite/const.py` - Add register mappings
2. `custom_components/midnite/sensor.py` - Add sensor classes
3. `custom_components/midnite/manifest.json` - Add default_disabled configuration
4. `README.md` - Update documentation
5. Test files - Add unit tests for new sensors

## Risk Assessment

**Low Risk**: 
- Backward compatible implementation
- Sensors disabled by default
- Follows existing patterns and conventions
- Well-tested approach used by other integrations

**Mitigation Strategies**:
- Incremental rollout (Phase 1 → Phase 2)
- Beta testing period for community feedback
- Comprehensive unit tests before release
- Clear documentation and examples

## Conclusion

This expansion plan provides a structured, low-risk approach to adding valuable sensor entities to the Midnite Solar integration. By using Home Assistant's `default_disabled` manifest property, we maintain backward compatibility while giving users access to enhanced monitoring capabilities when they need them.

**Next Steps:**
1. Implement Phase 1 sensors (6 high-priority sensors)
2. Create comprehensive unit tests
3. Update documentation
4. Release as beta version for testing
5. Gather feedback and iterate
