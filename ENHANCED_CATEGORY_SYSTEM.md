# Enhanced Register Category System

## Overview

This enhanced system provides a **complete, spreadsheet-friendly** way to manage all entity characteristics for the Midnite Solar integration. Every aspect of an entity's behavior is defined in a single CSV file.

## Key Features

✅ **Complete Entity Definition** - All attributes defined in one place  
✅ **Spreadsheet-Friendly** - Edit with Excel, Google Sheets, or Numbers  
✅ **Auto-Generation** - Generate entity classes and registration code automatically  
✅ **Flexible Categorization** - Easy to re-categorize registers (B/A/D)  
✅ **Enabled by Default** - Control whether entities are enabled at creation time  

## Files

### 1. REGISTER_CATEGORIES_ENHANCED.csv (Primary File)
This CSV file contains **all entity characteristics**:

```csv
"Register Name","Address","Category","Entity Type","Device Class","State Class","Unit","Precision","Icon","Enabled By Default","Description"
```

**Columns Explained:**

- **Register Name**: The register name (must match REGISTER_MAP)
- **Address**: Register address (for reference)
- **Category**: B = Basic, A = Advanced, D = Debug
- **Entity Type**: sensor, number, select, or button
- **Device Class**: Home Assistant device class (voltage, current, temperature, etc.)
- **State Class**: measurement, total_increasing, total, or None
- **Unit**: Unit of measurement (V, A, °C, W, kWh, etc.)
- **Precision**: Decimal precision for display
- **Icon**: Material Design Icons icon name (mdi:icon-name)
- **Enabled By Default**: TRUE/FALSE - whether entity is enabled at creation
- **Description**: Human-readable description

### 2. generate_entities.py (Generation Script)
Generates complete entity classes and registration helpers:

```bash
python3 generate_entities.py > generated_entities.py
```

**Output includes:**
- Complete sensor/number/select/button class definitions
- Proper attribute initialization (device_class, state_class, unit, etc.)
- Entity registration helper functions
- Summary statistics

### 3. generated_entities.py (Generated Output)
Contains:
- **Sensor classes** - All sensors with proper attributes
- **Number classes** - All numbers with min/max/step values
- **Select classes** - All selects with option handling
- **Registration helpers** - Functions to create entity lists based on config

## How It Works

### 1. Define Entities in CSV
Edit `REGISTER_CATEGORIES_ENHANCED.csv`:
```csv
"DISP_AVG_VBATT",4115,"B","sensor","voltage","measurement","V","1","mdi:flash-alert","TRUE","Average battery voltage (1 s)"
"ABSORB_SETPOINT_VOLTAGE",4149,"B","number","voltage","","V","0.1","mdi:tune","TRUE","Battery absorb stage set point voltage"
```

### 2. Generate Code
Run the generation script:
```bash
python3 generate_entities.py > generated_entities.py
```

### 3. Copy to Source Files
Copy the generated classes into:
- `sensor.py` - Sensor classes
- `number.py` - Number classes
- `select.py` - Select classes (if needed)

### 4. Use Registration Helpers
In your `async_setup_entry()` function:
```python
sensors = get_sensor_list(entry)
numbers = get_number_list(entry)
selects = get_select_list(entry)
async_add_entities(sensors + numbers + selects)
```

## Entity Creation Logic

### Basic Entities (Always Created & Enabled)
- Category: B
- Enabled By Default: TRUE
- Created regardless of configuration
- Example: Battery voltage, current, temperatures

### Advanced Entities (Created Conditionally)
- Category: A
- Enabled By Default: FALSE or TRUE
- Only created if user enables "Advanced Features"
- Can be individually enabled/disabled in HA UI
- Example: AUX control settings, MPPT mode, voltage offsets

### Debug Entities (Created Conditionally)
- Category: D
- Enabled By Default: FALSE
- Only created if user enables "Debug Information"
- Can be individually enabled/disabled in HA UI
- Example: RESERVED registers, debug values

## Entity Attributes Explained

### Device Class
Standard Home Assistant device classes:
- `voltage` - Voltage measurements
- `current` - Current measurements  
- `temperature` - Temperature measurements
- `power` - Power measurements
- `energy` - Energy consumption
- `duration` - Time durations
- `None` - No specific class

### State Class
Controls how Home Assistant tracks state changes:
- `measurement` - Individual measurements (no history tracking)
- `total_increasing` - Accumulating values (kWh, Ah)
- `total` - Accumulating values that can decrease
- `None` - No specific behavior

### Unit
Standard units of measurement:
- Voltage: V
- Current: A
- Temperature: °C or F
- Power: W
- Energy: kWh, Wh, Ah
- Time: s, ms, days
- None: Dimensionless values

### Precision
Decimal places for display:
- `0` - Whole numbers (e.g., 123)
- `1` - One decimal (e.g., 12.3)
- `0.1` - Step size of 0.1 (for numbers)
- `1.0` - Step size of 1.0

### Icon
Material Design Icons (mdi: prefix):
- `mdi:flash-alert` - Battery voltage
- `mdi:solar-power` - PV voltage/current
- `mdi:thermometer` - Temperature
- `mdi:current-dc` - Current
- `mdi:gauge` - Power
- `mdi:clock` - Time/duration
- See [Material Design Icons](https://pictogrammers.com/library/mdi/) for full list

### Enabled By Default
Controls initial state:
- `TRUE` - Entity is enabled when created
- `FALSE` - Entity exists but is disabled (user can enable in UI)

## Examples

### Basic Sensor Example
```csv
"DISP_AVG_VBATT",4115,"B","sensor","voltage","measurement","V","1","mdi:flash-alert","TRUE","Average battery voltage"
```
**Result:**
- Created always (Basic category)
- Enabled at creation time
- Device class: voltage
- State class: measurement
- Unit: V
- Precision: 1 decimal place
- Icon: mdi:flash-alert

### Advanced Number Example
```csv
"AUX1_VOLTS_LO_ABS",4166,"A","number","voltage","","V","0.1","mdi:gauge-low","FALSE","Aux 1 low absolute threshold voltage"
```
**Result:**
- Created only if Advanced Features enabled
- Disabled at creation (user must enable)
- Device class: voltage
- Unit: V
- Precision: 0.1 (step size)
- Icon: mdi:gauge-low

### Debug Sensor Example
```csv
"RESERVED_4188",4188,"D","sensor","","","","0","mdi:help-circle","FALSE","Factory calibration"
```
**Result:**
- Created only if Debug Information enabled
- Disabled at creation (user must enable)
- No device class or unit
- Precision: 0 (whole numbers)
- Icon: mdi:help-circle
- Entity category: DIAGNOSTIC

## Best Practices

### For Basic Entities
- **Enabled By Default**: TRUE
- **Category**: B
- Include essential monitoring data
- Keep count reasonable (~50 entities max)

### For Advanced Entities  
- **Enabled By Default**: FALSE or TRUE (if commonly used)
- **Category**: A
- Include configuration settings
- Use descriptive icons and names

### For Debug Entities
- **Enabled By Default**: FALSE
- **Category**: D
- Mark as DIAGNOSTIC category
- Use help/question mark icons
- Minimal documentation needed

## Performance Considerations

### Entity Count
- **Basic**: ~50 entities (always created)
- **Advanced**: ~100 entities (optional)
- **Debug**: ~10 entities (optional)
- **Total Max**: ~160 entities

### Polling Impact
- Only enabled entities are polled
- Disabled entities don't consume resources
- Use `EntityCategory.DIAGNOSTIC` for infrequently used entities

## Updating the System

### Step 1: Edit CSV
```bash
# Open in spreadsheet software
open REGISTER_CATEGORIES_ENHANCED.csv

# Or edit directly
nano REGISTER_CATEGORIES_ENHANCED.csv
```

### Step 2: Generate Code
```bash
python3 generate_entities.py > generated_entities.py
```

### Step 3: Update Source Files
Copy relevant sections from `generated_entities.py` to:
- `custom_components/midnite/sensor.py`
- `custom_components/midnite/number.py`
- `custom_components/midnite/select.py` (if needed)

### Step 4: Test
```bash
# Check for syntax errors
python3 -m py_compile custom_components/midnite/sensor.py

# Restart Home Assistant to test
```

## Migration from Old System

If you have existing entities, the new system is **backward compatible**:

1. Existing entities continue working
2. New attributes are additive only
3. No breaking changes to existing functionality
4. Gradually migrate entities to the new CSV-based system

## Troubleshooting

### Common Issues

**Issue: Entity not created**
- Check category (B/A/D) and configuration
- Verify Enabled By Default setting
- Check if register exists in REGISTER_MAP

**Issue: Wrong unit/precision**
- Edit CSV file and regenerate
- Update source files with new code

**Issue: Icon not displaying**
- Verify icon name (must be mdi: prefix)
- Check for typos in icon name

**Issue: Device class errors**
- Use only standard Home Assistant device classes
- Check spelling (voltage, current, temperature, etc.)

## Summary

This enhanced system provides:

✅ **Single Source of Truth** - All entity characteristics in one CSV file  
✅ **Easy Maintenance** - Edit with spreadsheet software  
✅ **Auto-Generation** - Generate code automatically  
✅ **Flexible Control** - Categorize and enable/disable entities easily  
✅ **Consistent Attributes** - Proper device classes, units, icons for all entities  

The system is ready for **Phase 2: Entity Implementation**! 🚀
