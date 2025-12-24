# ⚠️ WARNING: USE AT YOUR OWN RISK ⚠️

**IMPORTANT SAFETY NOTICE:** This integration allows you to read and **write settings** to your Midnite Solar MPPT charge controller. Incorrect configuration can result in:
- Damage to your MPPT charge controller
- Damage to your battery bank
- Overcharging or undercharging of batteries
- Potential fire hazard

**You are solely responsible for any consequences that may result from using this integration.** The authors and contributors accept no liability for any damage, loss, or injury caused by the use of this software.

**Always verify your settings before applying them to your charge controller.**

---

# Midnite Solar Integration for Home Assistant

This custom integration provides support for Midnite Solar Classic charge controllers via Modbus TCP.

## Features

### Sensors
- **Battery Voltage**: Current battery voltage in volts
- **PV Voltage**: PV input voltage in volts  
- **Battery Current**: Battery current in amps (positive = charging, negative = discharging)
- **Power Output**: Power output in watts
- **Charge Stage**: Current charge stage (Resting, Bulk, Absorb, Float, Equalize, Slave)
- **Battery Temperature**: Battery temperature in °C
- **FET Temperature**: FET temperature in °C
- **PCB Temperature**: PCB temperature in °C
- **Daily Amp-Hours**: Energy delivered today in kWh
- **Lifetime Energy**: Total lifetime energy generation in kWh
- **Lifetime Amp-Hours**: Total lifetime amp-hours in kWh
- **PV Input Current**: PV input current in amps
- **Last Measured VOC**: Last measured open-circuit voltage in volts
- **Float Time Today**: Time spent in float mode today
- **Absorb Time Remaining**: Remaining absorb time
- **Equalize Time Remaining**: Remaining equalize time

### Buttons (Actions)
- **Force Float**: Force the device into float mode
- **Force Bulk**: Force the device into bulk mode
- **Force Equalize**: Force the device into equalize mode
- **Force EEPROM Update**: Save current settings to non-volatile memory
- **Reset Faults**: Clear any active faults
- **Reset Flags**: Reset system flags

### Numbers (Configurable Parameters)
- **Absorb Voltage Setpoint**: Set the absorb voltage in volts
- **Float Voltage Setpoint**: Set the float voltage in volts
- **Equalize Voltage Setpoint**: Set the equalize voltage in volts
- **Battery Current Limit**: Set maximum battery current limit in amps
- **Absorb Time**: Set absorb time duration in seconds
- **Equalize Time**: Set equalize time duration in seconds
- **Equalize Interval**: Set days between automatic equalizations

## Installation

1. Copy the `custom_components/midnite` folder to your Home Assistant configuration directory
2. Restart Home Assistant
3. Add the integration via the UI or YAML configuration

## Configuration

### UI Setup (Recommended)
1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration** and search for "Midnite Solar"
3. Enter your device's IP address and port (default: 502)
4. Test the connection and save

### YAML Configuration (Legacy)
```yaml
midnite_solar:
  host: 192.168.1.100
  port: 502
```

## Requirements

- Midnite Solar Classic charge controller with Ethernet module enabled
- Network connectivity between Home Assistant and the device
- Python 3.10+
- pymodbus library (included in requirements)

## Technical Details

### Modbus Addressing
The integration uses Modbus TCP to communicate with the device:
- Default slave ID: 10
- Register addresses follow Midnite Solar's register map
- All voltage/current values are scaled by 10 (divide by 10 for display)

### Update Frequency
By default, sensors update every 15 seconds. You can adjust this in the integration settings.

## Troubleshooting

### Connection Issues
- Verify the device IP address is correct
- Check that the Ethernet module is properly configured on the device
- Ensure no firewall is blocking Modbus TCP (port 502)
- Try pinging the device from your Home Assistant host

### Data Not Updating
- Check the logs for Modbus communication errors
- Verify the device is online and accessible
- Ensure the correct slave ID is being used (default: 10)

## Safety Notes

- Changing voltage setpoints can affect battery health and lifespan
- Always consult your battery manufacturer's specifications
- The integration provides direct access to device settings - use with caution
- Some operations may require a device reset to take effect

## License

This integration is open-source software licensed under the MIT License.
