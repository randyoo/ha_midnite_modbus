# Sensor Expansion Implementation Checklist

## 📋 Overview
This checklist guides the implementation of new sensor entities for the Midnite Solar integration, ensuring all steps are completed systematically.

## ✅ Pre-Implementation Tasks

### [ ] Review & Planning
- [x] Analyzed registers.json and registers2.json files
- [x] Identified currently implemented sensors (20 total)
- [x] Compiled list of missing sensor opportunities (50+ identified)
- [x] Prioritized sensors into Phase 1, 2, and 3
- [x] Reviewed existing code patterns in sensor.py
- [x] Reviewed const.py register mappings
- [x] Reviewed manifest.json structure

### [ ] Documentation Review
- [x] Read Home Assistant sensor platform documentation
- [x] Reviewed EntityCategory.DIAGNOSTIC usage guidelines
- [x] Reviewed default_disabled manifest property documentation
- [x] Studied existing Midnite Solar integration patterns

## 🔧 Implementation Tasks - Phase 1

### Step 1: Update const.py
**File**: `custom_components/midnite/const.py`

- [ ] Add register mapping for HIGHEST_VINPUT_LOG (4123)
- [ ] Add register mapping for VPV_TARGET_RD (4191)
- [ ] Add register mapping for IBATT_RAW_A (4272)
- [ ] Add register mapping for NITE_MINUTES_NO_PWR (4135)
- [ ] Add register mappings for UNIT_SW_DATE_RO (4102, 4103)
- [ ] Add register mapping for MODBUS_PORT_REGISTER (4137)
- [ ] Verify all new mappings follow existing naming conventions
- [ ] Run integration tests to ensure no conflicts

### Step 2: Create Sensor Classes
**File**: `custom_components/midnite/sensor.py`

#### Highest Input Voltage Sensor
- [ ] Create class `HighestInputVoltageSensor`
- [ ] Set proper entity name and unique_id pattern
- [ ] Set EntityCategory.DIAGNOSTIC
- [ ] Set device_class = VOLTAGE
- [ ] Set unit_of_measurement = "V"
- [ ] Set state_class = MEASUREMENT
- [ ] Implement native_value property with /10 scaling
- [ ] Add proper error handling and None checks

#### PV Target Voltage Sensor
- [ ] Create class `PVTargetVoltageSensor`
- [ ] Set proper entity name and unique_id pattern
- [ ] Set EntityCategory.DIAGNOSTIC
- [ ] Set device_class = VOLTAGE
- [ ] Set unit_of_measurement = "V"
- [ ] Set state_class = MEASUREMENT
- [ ] Implement native_value property with /10 scaling
- [ ] Add proper error handling and None checks

#### Raw Battery Current Sensor
- [ ] Create class `RawBatteryCurrentSensor`
- [ ] Set proper entity name and unique_id pattern
- [ ] Set EntityCategory.DIAGNOSTIC
- [ ] Set device_class = CURRENT
- [ ] Set unit_of_measurement = UnitOfElectricCurrent.AMPERE
- [ ] Set state_class = MEASUREMENT
- [ ] Implement native_value property with /10 scaling
- [ ] Add two's complement handling for negative values
- [ ] Add range validation (-200A to 200A)

#### Night Minutes No Power Sensor
- [ ] Create class `NightMinutesNoPowerSensor`
- [ ] Set proper entity name and unique_id pattern
- [ ] Set EntityCategory.DIAGNOSTIC
- [ ] Set device_class = DURATION
- [ ] Set unit_of_measurement = UnitOfTime.MINUTES
- [ ] Set state_class = MEASUREMENT
- [ ] Implement native_value property with /60 scaling (seconds to minutes)
- [ ] Add extra_state_attributes for seconds and hours

#### Software Version Sensor
- [ ] Create class `SoftwareVersionSensor`
- [ ] Set proper entity name and unique_id pattern
- [ ] Set EntityCategory.DIAGNOSTIC
- [ ] Set device_class = None (string sensor)
- [ ] Implement native_value property to return formatted date string
- [ ] Parse year from register 4102
- [ ] Parse month/day from register 4103
- [ ] Format as "YYYY-MM-DD" or similar

#### Modbus Port Sensor
- [ ] Create class `ModbusPortSensor`
- [ ] Set proper entity name and unique_id pattern
- [ ] Set EntityCategory.DIAGNOSTIC
- [ ] Set device_class = None (integer sensor)
- [ ] Implement native_value property (no scaling needed)

### Step 3: Update async_setup_entry()
**File**: `custom_components/midnite/sensor.py`

- [ ] Add `HighestInputVoltageSensor(coordinator, entry)` to sensors list
- [ ] Add `PVTargetVoltageSensor(coordinator, entry)` to sensors list
- [ ] Add `RawBatteryCurrentSensor(coordinator, entry)` to sensors list
- [ ] Add `NightMinutesNoPowerSensor(coordinator, entry)` to sensors list
- [ ] Add `SoftwareVersionSensor(coordinator, entry)` to sensors list
- [ ] Add `ModbusPortSensor(coordinator, entry)` to sensors list
- [ ] Verify all new sensors are added at the end of the list
- [ ] Ensure proper indentation and formatting

### Step 4: Update manifest.json
**File**: `custom_components/midnite/manifest.json`

- [ ] Add "sensor_platform" section if not present
- [ ] Add "default_disabled" array under sensor_platform
- [ ] Add "highest_input_voltage" to default_disabled list
- [ ] Add "pv_target_voltage" to default_disabled list
- [ ] Add "raw_battery_current" to default_disabled list
- [ ] Add "night_minutes_no_power" to default_disabled list
- [ ] Add "software_version" to default_disabled list
- [ ] Add "modbus_port" to default_disabled list
- [ ] Verify JSON syntax is valid
- [ ] Increment version number (e.g., "1.2.0")

### Step 5: Create Unit Tests
**Files**: `tests/test_sensors.py` or similar

#### Test HighestInputVoltageSensor
- [ ] Test with valid data (scaled value)
- [ ] Test with None/missing data
- [ ] Test coordinator data structure access

#### Test PVTargetVoltageSensor
- [ ] Test with valid data (scaled value)
- [ ] Test with None/missing data
- [ ] Test coordinator data structure access

#### Test RawBatteryCurrentSensor
- [ ] Test with positive current
- [ ] Test with negative current (two's complement)
- [ ] Test with out-of-range values
- [ ] Test with None/missing data

#### Test NightMinutesNoPowerSensor
- [ ] Test with valid seconds value
- [ ] Test conversion to minutes
- [ ] Test extra_state_attributes
- [ ] Test with None/missing data

#### Test SoftwareVersionSensor
- [ ] Test with valid year, month, day values
- [ ] Test string formatting
- [ ] Test with None/missing data

#### Test ModbusPortSensor
- [ ] Test with valid port number
- [ ] Test with None/missing data

## 📝 Documentation Tasks

### Update README.md
- [ ] Add "Available Sensors" section
- [ ] List all 26 sensors (20 existing + 6 new)
- [ ] Mark which are enabled by default vs. optional
- [ ] Add table with sensor names, units, and descriptions
- [ ] Add instructions for enabling disabled sensors
- [ ] Include screenshots of Home Assistant UI showing how to enable

### Update CHANGES.md
- [ ] Add new version entry (e.g., "1.2.0")
- [ ] List new sensors under "Added" section
- [ ] Note that new sensors are disabled by default
- [ ] Link to documentation for enabling them

### Create INSTALLATION_GUIDE.md (if needed)
- [ ] Add troubleshooting section for sensor configuration
- [ ] Explain how to enable/disable individual sensors
- [ ] Provide dashboard examples using new sensors

## 🧪 Testing Tasks

### Local Testing
- [ ] Run unit tests locally
- [ ] Fix any test failures
- [ ] Test with mock coordinator data
- [ ] Verify sensor values are calculated correctly
- [ ] Check entity IDs and names in Home Assistant UI

### Integration Testing (if device available)
- [ ] Test with real Midnite Solar device
- [ ] Verify all sensors receive valid data
- [ ] Check for any Modbus communication errors
- [ ] Monitor performance impact
- [ ] Validate sensor values match expected ranges

### User Acceptance Testing
- [ ] Create test Home Assistant instance
- [ ] Install integration with new sensors
- [ ] Verify disabled sensors don't appear in UI
- [ ] Enable sensors and verify they appear correctly
- [ ] Test sensor data updates over time
- [ ] Check entity attributes and device info

## 🚀 Deployment Tasks

### Beta Release
- [ ] Create beta branch from main
- [ ] Commit all changes to beta branch
- [ ] Tag beta release (e.g., "v1.2.0-beta.1")
- [ ] Publish to HACS beta channel
- [ ] Announce on GitHub Discussions
- [ ] Request community testing and feedback

### Feedback Collection
- [ ] Monitor GitHub issues for bug reports
- [ ] Track feature requests for Phase 2 sensors
- [ ] Collect performance metrics from testers
- [ ] Document common questions/concerns

### Final Release
- [ ] Address all beta feedback
- [ ] Fix any reported bugs
- [ ] Update documentation based on feedback
- [ ] Merge beta branch to main
- [ ] Tag final release (e.g., "v1.2.0")
- [ ] Publish to HACS stable channel
- [ ] Announce general availability

## 📊 Post-Release Tasks

### Monitoring
- [ ] Track download statistics
- [ ] Monitor issue tracker for problems
- [ ] Collect user feedback on new sensors
- [ ] Identify most/least used new sensors

### Iteration Planning
- [ ] Prioritize Phase 2 sensors based on feedback
- [ ] Plan next release timeline
- [ ] Update roadmap documentation
- [ ] Schedule community review meetings if needed

## ✅ Final Verification Checklist

### Code Quality
- [ ] All new code follows PEP 8 style guidelines
- [ ] Type hints are consistent with existing code
- [ ] Docstrings follow Google style format
- [ ] No hardcoded values (use const.py)
- [ ] Proper error handling throughout

### Testing Coverage
- [ ] Unit tests created for all new sensors
- [ ] Test coverage matches existing patterns
- [ ] Edge cases are tested (None, invalid data, etc.)
- [ ] Integration tests pass locally

### Documentation
- [ ] README.md updated with new sensor information
- [ ] CHANGES.md properly documents the release
- [ ] All code changes are documented
- [ ] Examples and screenshots included where helpful

### User Experience
- [ ] Sensor names are clear and descriptive
- [ ] Units of measurement are correct
- [ ] Device classes are appropriately set
- [ ] Entity categories (DIAGNOSTIC) are used correctly
- [ ] Sensors can be easily enabled/disabled in UI

### Performance
- [ ] No significant increase in scan time
- [ ] Memory usage is reasonable
- [ ] Modbus requests are optimized
- [ ] Coordinator updates handle new sensors efficiently

## 🎉 Completion Criteria

The implementation is complete when:
1. ✅ All Phase 1 sensor classes are implemented and tested
2. ✅ Unit tests pass for all new sensors
3. ✅ Documentation is updated and accurate
4. ✅ Beta testing completes with no critical issues
5. ✅ Final release is published to HACS stable channel
6. ✅ Community feedback is positive overall

## 📅 Timeline Estimate

- **Implementation**: 2-3 weeks
- **Testing**: 1-2 weeks (including beta)
- **Documentation**: 1 week (parallel with implementation)
- **Total**: 4-6 weeks from start to stable release

## 🤝 Resources & References

### Documentation Links
- [Home Assistant Sensor Platform](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [Entity Categories](https://developers.home-assistant.io/docs/core/entity#generic-properties)
- [default_disabled Manifest Property](https://developers.home-assistant.io/docs/manifest/default-disabled/)

### Code References
- Existing sensor.py implementation patterns
- const.py register mapping conventions
- manifest.json structure examples

### Testing Resources
- Home Assistant test fixtures
- Mock coordinator data patterns
- Pymodbus testing documentation
