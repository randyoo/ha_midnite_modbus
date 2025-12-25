# Temperature Sensor Filtering Fix

## Problem Description

The temperature sensor filtering logic was causing a permanent lockout situation where legitimate temperature readings were being rejected indefinitely. This happened when:

1. A legitimate rapid temperature change occurred (e.g., from 55°C to 46.5°C)
2. The statistical outlier detection flagged this as an anomaly
3. The spike counter incremented with each rejection
4. Once the spike counter reached 3, ALL subsequent readings were rejected with the message "Multiple anomalies detected in succession"
5. The spike counter never reset because valid readings couldn't get through to reset it
6. This resulted in thousands of consecutive rejections (2000+ occurrences logged)

## Root Causes

1. **Too aggressive statistical filtering**: Using a z-score threshold of 4 with very low standard deviation (0.11°C) meant even small legitimate changes were flagged as outliers
2. **Permanent lockout mechanism**: The spike counter had no timeout or recovery mechanism, causing indefinite rejection of all readings
3. **Statistical filtering applied too early**: Filtering was applied even with minimal data points (< 5 readings)

## Solution Implemented

### Key Changes to `TemperatureSensorBase._validate_temperature()`:

1. **Increased z-score threshold from 4 to 6**: More lenient statistical filtering that still catches true outliers while allowing legitimate temperature changes

2. **Added timeout mechanism for spike counter**: 
   - Track when the last spike occurred (`_last_spike_time`)
   - Automatically reset spike counter after 30 seconds of no valid readings
   - Prevents permanent lockout scenarios

3. **Graceful degradation at high spike counts**:
   - After 5 consecutive spikes, allow readings through with a warning
   - This prevents permanent lockout from legitimate temperature changes
   - Still maintains some protection against rapid successive anomalies

4. **Require minimum data points for statistical filtering**:
   - Only apply statistical outlier detection when at least 5 valid readings are available
   - Prevents false positives during initial sensor warm-up period

## Benefits

1. **Prevents permanent lockout**: Sensors will recover automatically after 30 seconds even if multiple anomalies occur
2. **More tolerant of legitimate temperature changes**: Higher z-score threshold (6 vs 4) allows real-world temperature variations
3. **Better handling of sensor startup**: Statistical filtering only applies after initial warm-up period
4. **Clearer recovery path**: Readings are allowed through after 5 spikes, preventing indefinite rejection

## Testing Recommendations

1. Monitor temperature sensors during normal operation to ensure readings appear
2. Verify that legitimate temperature changes (e.g., cooling from charge cycles) are properly recorded
3. Check logs for warning messages - they should be infrequent and not continuous
4. Confirm that spike counter resets after 30 seconds if anomalies occur

## Files Modified

- `custom_components/midnite/sensor.py`: Updated `TemperatureSensorBase` class validation logic
