# Sensor Update Interval Configuration

## Overview
This document describes the implementation of user-configurable sensor update intervals for the Midnite Solar integration.

## Changes Made

### 1. Constants Definition (`const.py`)
Added two new constants:
- `CONF_SCAN_INTERVAL`: The configuration key for scan interval (string: "scan_interval")
- `DEFAULT_SCAN_INTERVAL`: The default scan interval in seconds (integer: 15)

```python
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15
```

### 2. Configuration Flow (`config_flow.py`)

#### Imports
Added the new constants to the imports:
```python
from .const import DEFAULT_PORT, DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL
```

#### Manual Configuration Form
Updated the manual configuration form to include an optional scan_interval field:
```python
vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
```

#### Entry Creation
Modified `async_create_entry` to separate scan_interval into options instead of data:
```python
# Separate scan_interval from data to store in options
entry_data = {
    CONF_HOST: user_input[CONF_HOST],
    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
}
entry_options = {}
if CONF_SCAN_INTERVAL in user_input:
    entry_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

return self.async_create_entry(
    title=title,
    data=entry_data,
    options=entry_options
)
```

#### Options Update Flow
Added a new `async_step_options` method to allow users to update the scan interval after initial setup:
```python
async def async_step_options(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
    """Handle options update."""
    if user_input is not None:
        return self.async_create_entry(
            title="",
            data=user_input,
        )
    
    # Get current options from the config entry
    entry = self._get_current_entries()[0]
    current_options = entry.options
    
    return self.async_show_form(
        step_id="options",
        data_schema=vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL, 
                default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ): int,
        }),
    )
```

### 3. Main Integration (`__init__.py`)

#### Reading Options
Modified `async_setup_entry` to read the scan interval from options:
```python
interval = entry.options.get("scan_interval", 15)
```

#### Update Listener
Added an update listener to handle options changes and reload the integration:
```python
# Register update listener to handle options changes
entry.add_update_listener(update_listener)
```

Created a new `update_listener` function:
```python
async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle options updates."""
    _LOGGER.info("Options updated, reloading Midnite Solar integration")
    
    await hass.config_entries.async_reload(entry.entry_id)
    return True
```

## User Experience

### Initial Setup
When users manually configure the integration, they will see a new field:
- **Scan Interval (seconds)**: Optional field with default value of 15 seconds

Users can customize this to any integer value based on their needs.

### DHCP Discovery
For devices discovered via DHCP, the scan interval defaults to 15 seconds. Users can later update it through the options flow.

### Updating After Setup
After the integration is set up, users can:
1. Go to Home Assistant Settings
2. Find their Midnite Solar integration
3. Click "Configure" or "Options"
4. Adjust the scan interval value
5. Save changes

The integration will automatically reload with the new settings.

## Technical Details

### Why Store in Options?
- **Data vs Options**: Configuration data (host, port) is stored in `entry.data` while user preferences (scan_interval) are stored in `entry.options`
- **Separation of Concerns**: This follows Home Assistant best practices by separating configuration from preferences
- **Update Capability**: Options can be updated without recreating the config entry

### Coordinator Update Mechanism
The `MidniteSolarUpdateCoordinator` receives the interval during initialization:
```python
def __init__(self, hass: HomeAssistant, host: str, port: int, interval: int = 15) -> None:
    super().__init__(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=interval)
    )
```

When the integration reloads after an options change, a new coordinator is created with the updated interval.

## Benefits

1. **Flexibility**: Users can adjust the polling frequency based on their needs
2. **Performance**: Faster updates for critical monitoring or slower updates to reduce network load
3. **User-Friendly**: Easy to configure through the Home Assistant UI
4. **Persistent**: Settings are saved and persist across restarts
5. **Dynamic**: Can be changed without removing and re-adding the integration

## Testing

Run the validation script to verify all changes:
```bash
python validate_changes.py
```

All checks should pass, confirming:
- Constants are properly defined
- Configuration flow includes scan_interval
- Options update mechanism is in place
- Integration reloads on options change
