# CSV Format Specification for Midnite Solar Integration

## Overview

This document specifies the format of `REGISTER_CATEGORIES.csv`, which serves as the single source of truth for all Modbus register definitions in the Midnite Solar Home Assistant integration.

## File Location

`REGISTER_CATEGORIES.csv` should be placed in the root directory of the project alongside the Python code.

## CSV Structure

The CSV file has the following columns (in order):

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **Register Name** | string | Yes | The name of the register (e.g., `UNIT_ID`, `BATTERY_VOLTAGE`) |
| **Address** | integer | Yes | The Modbus register address (e.g., 4101) |
| **Category** | char | Yes | Entity category: B=Basic, A=Advanced, D=Debug |
| **Entity Type** | string | Yes | The Home Assistant entity type: `sensor`, `number`, or `select` |
| **Device Class** | string | No | Home Assistant device class (e.g., `voltage`, `current`, `temperature`) |
| **State Class** | string | No | Home Assistant state class (e.g., `measurement`, `total_increasing`) |
| **Unit** | string | No | Unit of measurement (e.g., `V`, `A`, `°C`, `kWh`) |
| **Precision** | integer or float | No | Number of decimal places to display (e.g., 1, 2) |
| **Icon** | string | Yes | Material Design icon name (e.g., `mdi:flash-alert`, `mdi:thermometer`) |
| **Enabled By Default** | boolean | Yes | `TRUE` or `FALSE` indicating if entity should be enabled by default |
| **Description** | string | Yes | Human-readable description of the register's purpose |

## Category System

Entities are categorized to control their visibility and enablement:

- **B (Basic)**: Always enabled for all users. Core functionality.
- **A (Advanced)**: Opt-in feature. Users must explicitly enable advanced mode.
- **D (Debug)**: Debug/Development only. Users must explicitly enable debug mode.

## Entity Type Mappings

### Sensor Entities

Used for read-only values that Home Assistant should monitor:

```csv
Register Name,Address,Category,Entity Type,Device Class,State Class,Unit,Precision,Icon,Enabled By Default,Description
BATTERY_VOLTAGE,4115,B,sensor,voltage,measurement,V,1,mdi:flash-alert,TRUE,"Average battery voltage"
```

### Number Entities

Used for writable numeric values that users can adjust:

```csv
Register Name,Address,Category,Entity Type,Device Class,State Class,Unit,Precision,Icon,Enabled By Default,Description
ABSORB_VOLTAGE,4149,B,number,voltage,,V,0.1,mdi:tune,TRUE,"Battery absorb voltage setpoint"
```

### Select Entities

Used for choosing from a predefined list of options:

```csv
Register Name,Address,Category,Entity Type,Device Class,State Class,Unit,Precision,Icon,Enabled By Default,Description
MPPT_MODE,4164,A,select,,,,mdi:cog,FALSE,"MPPT operating mode"
```

## Special Considerations

### Unit Conversions

The generator automatically applies conversions based on the unit:
- **V (Voltage)**: Divides value by 10.0 (register stores tenths of volts)
- **A (Current)**: Divides value by 10.0 (register stores tenths of amps)
- **kWh**: Divides value by 100.0 (register stores hundredths of kWh)
- Other units: Returns raw register value

### Device Classes

Common device classes:
- `voltage` → Uses `SensorDeviceClass.VOLTAGE`
- `current` → Uses `UnitOfElectricCurrent.AMPERE`
- `temperature` → Uses `UnitOfTemperature.CELSIUS`
- `power` → Uses `UnitOfPower.WATT`
- `energy` → Uses `UnitOfEnergy.KILO_WATT_HOUR`

### State Classes

Common state classes:
- `measurement` → For continuously measured values
- `total_increasing` → For counters that only increase (e.g., energy production)

## Validation Rules

The generator validates the CSV and will fail if:
1. Required fields are missing
2. Duplicate register names exist
3. Duplicate addresses exist
4. Addresses are not valid integers
5. Entity type is not `sensor`, `number`, or `select`
6. Category is not B, A, or D
7. Enabled By Default is not TRUE or FALSE

## Generation Process

To regenerate Python files from the CSV:

```bash
python generate_from_csv.py REGISTER_CATEGORIES.csv custom_components/midnite/
```

This will generate:
- `custom_components/midnite/const.py` - Contains `REGISTER_MAP` and `REGISTER_CATEGORIES`
- `custom_components/midnite/sensor.py` - All sensor entity classes
- `custom_components/midnite/number.py` - All number entity classes
- `custom_components/midnite/select.py` - All select entity classes

## Adding New Registers

To add a new register:

1. Add a new row to `REGISTER_CATEGORIES.csv` with all required fields
2. Run the generator script
3. Test the integration to ensure the new entity works correctly
4. Commit both the CSV and generated Python files

## Example Entries

### Basic Sensor (Battery Voltage)
```csv
DISP_AVG_VBATT,4115,B,sensor,voltage,measurement,V,1,mdi:flash-alert,TRUE,"Average battery voltage (1 s)"
```

### Advanced Number (Absorb Voltage Setpoint)
```csv
ABSORB_SETPOINT_VOLTAGE,4149,B,number,voltage,,V,0.1,mdi:tune,TRUE,"Battery absorb stage set point voltage"
```

### Debug Sensor (Temperature)
```csv
PCB_TEMPERATURE,4134,D,sensor,temperature,measurement,°C,1,mdi:thermometer-alert,FALSE,"Classic top PCB temperature"
```

## Best Practices

1. **Consistent Naming**: Use uppercase with underscores for register names (SCREAMING_SNAKE_CASE)
2. **Clear Descriptions**: Provide detailed descriptions that explain the register's purpose
3. **Appropriate Icons**: Choose icons that visually represent the register's function
4. **Category Correctly**: Place registers in the appropriate category (B/A/D)
5. **Units Matter**: Specify units correctly for automatic conversion to work
6. **Precision**: Set precision based on what makes sense for the data (0-2 decimals typical)

## Troubleshooting

### Generator Fails Validation
Check that:
- All required fields are filled
- No duplicate names or addresses exist
- Category is B, A, or D
- Entity type is sensor, number, or select
- Enabled By Default is TRUE or FALSE

### Entity Not Showing Up
1. Check the category - advanced/debug entities require explicit enablement
2. Verify the register address is correct
3. Ensure the entity type matches what you expect (sensor/number/select)
4. Check Home Assistant logs for errors

### Incorrect Values
1. Verify unit conversions are appropriate for your data
2. Check precision settings
3. Validate device class and state class mappings
