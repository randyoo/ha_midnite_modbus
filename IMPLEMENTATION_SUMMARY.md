# Midnite Solar Integration Enhancements

## Summary of Changes

This implementation adds several new features to the Midnite Solar Home Assistant integration:

### 1. Host Name Control (Text Input)
- **New Entity**: `Host Name` text input entity
- **Registers Used**: 4210-4213 (8-character ASCII string)
- **Features**:
  - Read current host name from device
  - Write new host name (up to 8 characters)
  - Automatic EEPROM update after writing
  - Pattern validation: alphanumeric, underscore, hyphen, dot, space
  - Padding with spaces to ensure 8-character length

### 2. MAC Address Sensor
- **New Entity**: `MAC Address` diagnostic sensor
- **Registers Used**: 4106-4108 (3 registers forming 6-byte MAC)
- **Format**: Standard MAC address format (XX:XX:XX:XX:XX:XX)
- **Location**: Diagnostic entity category

### 3. Charge Mode Selector (Replaces Force Buttons)
- **New Entity**: `Charge Mode Control` selector
- **Options**: None, Float, Bulk, Equalize
- **Replaces**: Individual "Force Float", "Force Bulk", and "Force Equalize" buttons
- **Benefits**:
  - Single entity instead of three separate buttons
  - Better UX with dropdown selection
  - Shows current charge mode state

### 4. Device Information Enhancements
All entities now support dynamic device info including:
- Device ID from registers 4111-4112
- Device model from UNIT_ID register
- Manufacturer information

## Files Modified

### `custom_components/midnite/const.py`
- Added MAC_ADDRESS_PART_2 and MAC_ADDRESS_PART_3 to REGISTER_MAP

### `custom_components/midnite/sensor.py`
- Added MACAddressSensor class
- Added MAC address sensor to entity list

### `custom_components/midnite/text.py` (NEW)
- Complete new text input platform
- HostNameText entity for reading/writing host name
- Automatic EEPROM update functionality

### `custom_components/midnite/button.py`
- Added SelectEntity import
- Created ChargeModeSelector class
- Replaced individual force buttons with single selector
- Updated setup to include selector and keep diagnostic buttons

### `custom_components/midnite/coordinator.py`
- Added unit name registers (4210-4213) to device_info group
- Added MAC address registers (4106-4108) to device_info group

### `custom_components/midnite/__init__.py`
- Added Platform.TEXT to _PLATFORMS list

## Technical Details

### Host Name Storage Format
The host name is stored across 4 registers (4210-4213), with each register holding 2 ASCII characters:
- Register 4210: Characters 0-1
- Register 4211: Characters 2-3
- Register 4212: Characters 4-5
- Register 4213: Characters 6-7

Each register is a 16-bit value where:
- MSB (high byte) = Character 0/2/4/6
- LSB (low byte) = Character 1/3/5/7

### MAC Address Format
The MAC address is stored across 3 registers (4106-4108), with each register holding 2 bytes:
- Register 4108: Bytes 0-1 (MSB:LSB)
- Register 4107: Bytes 2-3 (MSB:LSB)
- Register 4106: Bytes 4-5 (MSB:LSB)

Format: `[4108]MSB:[4108]LSB:[4107]MSB:[4107]LSB:[4106]MSB:[4106]LSB`

### EEPROM Update Requirement
After writing the host name, an EEPROM update must be triggered by writing to register 4160 with value `0x0004` (bit 2 set). This ensures the changes are saved to non-volatile memory.

## User Experience Improvements

1. **Simplified Interface**: Three separate buttons replaced with one selector
2. **Better Device Identification**: MAC address visible in diagnostics
3. **Customizable Naming**: Host name can be set via text input
4. **Persistent Settings**: All changes saved to EEPROM automatically

## Compatibility

- Works with all Midnite Classic models (150, 200, 250, 250KS)
- Maintains backward compatibility with existing installations
- No breaking changes to existing entities
