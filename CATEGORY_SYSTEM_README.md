# Register Category System

## Overview
This system allows easy categorization of Midnite Solar registers into three categories:
- **B** = Basic (always enabled)
- **A** = Advanced (opt-in via configuration)
- **D** = Debug (opt-in via configuration)

## Files

### 1. REGISTER_CATEGORIES.csv (Primary File - Edit This!)
This CSV file contains all registers with their category assignments. You can:
- Sort by address, name, or category
- Change categories by editing the "Category" column
- Add descriptions for clarity
- Use spreadsheet software (Excel, Google Sheets, Numbers) to manage

**Format:**
```csv
"Register Name","Address","Category","Description"
"UNIT_ID",4101,"B","Hardware revision & voltage category"
"MODBUS_PORT_REGISTER",4137,"A","Modbus TCP port (default 502)"
```

### 2. generate_categories.py (Generation Script)
Run this script to generate the Python code for const.py:
```bash
python3 generate_categories.py > categories_generated.py
```

### 3. categories_generated.py (Generated Output)
This file contains the Python dictionary that gets copied into const.py.

## How to Re-categorize Registers

### Method 1: Using a Spreadsheet
1. Open `REGISTER_CATEGORIES.csv` in Excel, Google Sheets, or Numbers
2. Sort by "Category" column to see all Basic/Advanced/Debug registers
3. Change the category letter (B/A/D) in the "Category" column
4. Save the CSV file
5. Run: `python3 generate_categories.py > categories_generated.py`
6. Copy the content from `categories_generated.py` into `const.py`

### Method 2: Direct CSV Editing
1. Edit `REGISTER_CATEGORIES.csv` directly in a text editor
2. Change category letters (B/A/D) as needed
3. Run the generation script:
   ```bash
   python3 generate_categories.py > categories_generated.py
   ```
4. Update `const.py` with the generated content

## Current Category Distribution

- **Basic (B)**: 52 registers - Always enabled, core functionality
- **Advanced (A)**: 137 registers - Opt-in via "Enable Advanced Features"
- **Debug (D)**: 9 registers - Opt-in via "Enable Debug Information"

## Entity Creation Logic

The category system is used in entity registration:

```python
# In sensor.py, number.py, etc.
def should_create_entity(entry, register_name):
    """Determine if an entity should be created based on configuration."""
    category = REGISTER_CATEGORIES.get(register_name, "B")
    
    # Basic entities always created
    if category == "B":
        return True
    
    # Advanced entities only with flag enabled
    if category == "A" and entry.options.get(CONF_ENABLE_ADVANCED, False):
        return True
    
    # Debug entities only with flag enabled
    if category == "D" and entry.options.get(CONF_ENABLE_DEBUG, False):
        return True
    
    return False
```

## Configuration Options

Users can enable/disable categories via the Home Assistant UI:
- **Advanced Features**: Enables all "A" category entities
- **Debug Information**: Enables all "D" category entities
- **Write Operations**: Allows writes to writable registers (separate from categorization)

## Best Practices for Categorization

### Basic (B) - Always Include
- Core status information (voltages, currents, temperatures)
- Essential diagnostic data (device ID, MAC address)
- Charge stage and state information
- Lifetime energy metrics

### Advanced (A) - Opt-in
- Configuration settings that most users won't need
- AUX control registers
- Wind/hydro specific settings
- Follow-me features
- Network configuration
- Whizbang Jr. integration

### Debug (D) - Opt-in Only
- RESERVED registers (unimplemented)
- DEBUG registers (internal diagnostics)
- Factory calibration values
- Raw/unfiltered data

## Updating const.py

After changing categories:
1. Run the generation script
2. Copy the `REGISTER_CATEGORIES` dictionary from `categories_generated.py`
3. Replace the existing one in `custom_components/midnite/const.py`
4. Commit and push changes

## Example Category Changes

### Moving a register to Advanced:
```csv
"MODBUS_PORT_REGISTER",4137,"A","Modbus TCP port (default 502)"
```

### Moving a register to Debug:
```csv
"RESERVED_4188",4188,"D","Factory calibration - do not write"
```

### Moving a register to Basic:
```csv
"MATCH_POINT_SHADOW",4124,"B","Current wind power curve step (useful for all users)"
```
