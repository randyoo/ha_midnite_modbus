# Temperature Sensor Filtering Fix - Complete Analysis

## Problem Summary

The temperature sensor filtering was causing **permanent lockout** of legitimate readings due to:

1. **Too aggressive statistical filtering**: z-score threshold of 4 rejected even moderate temperature changes when standard deviation was very low (0.11°C)
2. **No recovery mechanism**: Once the spike counter reached 3, ALL subsequent readings were rejected indefinitely
3. **Statistical filtering applied too early**: Filtering was applied even with minimal data points (< 5 readings)

### Example from Logs
```
FET temperature outlier detected: 46.5°C (mean=55.06°C, stddev=0.11°C, z-score=80.17). Possible sensor error. Ignoring reading.
PCB temperature outlier detected: 49.0°C (mean=53.68°C, stddev=0.04°C, z-score=107.96). Possible sensor error. Ignoring reading.
```

These readings were legitimate temperature changes after charging stopped, but they triggered the outlier detection and caused 2000+ consecutive rejections.

## Root Cause Analysis

### The Lockout Mechanism (Before Fix)

1. Reading at 46.5°C was flagged as outlier (z-score = 80.17 > threshold of 4)
2. `spike_count` incremented to 1
3. Next reading also flagged, `spike_count` incremented to 2
4. Third reading flagged, `spike_count` reached 3
5. **Permanent lockout**: All subsequent readings rejected with message "Multiple anomalies detected in succession"
6. `spike_count` never reset because valid readings couldn't get through
7. Result: 2000+ consecutive rejections logged

### Why the Statistical Filtering Was Too Aggressive

When temperatures are very stable (e.g., during idle periods), the standard deviation becomes extremely low:
- Mean temperature: 55.06°C
- Standard deviation: 0.11°C
- A change to 46.5°C gives z-score = (55.06 - 46.5) / 0.11 = **80.17**

With a threshold of 4, even small legitimate changes would be rejected when std_dev is very low.

## Solution Implemented

### Key Changes to `TemperatureSensorBase._validate_temperature()`

#### 1. Increased z-score threshold from 4 to 6
```python
# Old: if z_score > 4:
# New: if z_score > 6:
```
**Effect**: More lenient filtering that allows legitimate temperature variations while still catching true outliers.

#### 2. Added timeout mechanism for spike counter
```python
self._last_spike_time: Optional[float] = None  # Track when last spike occurred

# Check if timeout has expired (30 seconds)
if self._last_spike_time is not None and (current_time - self._last_spike_time) > 30:
    _LOGGER.info(f"Resetting {sensor_name} spike counter after timeout.")
    self._spike_count = 0
    self._last_spike_time = None
```
**Effect**: Automatic recovery after 30 seconds, preventing permanent lockout.

#### 3. Graceful degradation at high spike counts
```python
# Old: if self._spike_count >= 3:
#     return None  # Permanent rejection

# New: if self._spike_count >= 5:
#     Allow reading through with warning
else:
    self._spike_count = 0  # Reset for valid readings
```
**Effect**: Prevents indefinite lockout from legitimate temperature changes.

#### 4. Require minimum data points for statistical filtering
```python
# Old: if len(self._recent_readings) > 0:
# New: if len(self._recent_readings) >= 5:
```
**Effect**: Prevents false positives during sensor warm-up period.

## Benefits of the Fix

1. **Prevents permanent lockout**: Sensors recover automatically after 30 seconds
2. **More tolerant of legitimate changes**: Higher z-score threshold (6 vs 4) allows real-world variations
3. **Better startup handling**: Statistical filtering only applies after initial warm-up
4. **Clear recovery path**: Readings allowed through after 5 spikes, preventing indefinite rejection
5. **Maintains sensor protection**: Extreme outliers (z-score > 6) are still rejected

## Testing Recommendations

1. Monitor temperature sensors during normal operation - readings should appear regularly
2. Verify legitimate temperature changes (e.g., cooling after charge cycles) are recorded
3. Check logs for warning messages - they should be infrequent and not continuous
4. Confirm spike counter resets after 30 seconds if anomalies occur
5. Test with extreme values (e.g., < 0°C or > 100°C) to ensure they're still rejected

## Files Modified

- `custom_components/midnite/sensor.py`: Updated `TemperatureSensorBase` class validation logic

## Backward Compatibility

This fix is fully backward compatible:
- Existing temperature sensors will automatically benefit from the improved filtering
- No configuration changes required
- No breaking changes to the API or sensor entities

## Future Improvements (Optional)

1. **Adaptive z-score threshold**: Adjust threshold based on historical standard deviation
2. **Machine learning approach**: Train a model on normal temperature patterns
3. **User-configurable sensitivity**: Allow users to adjust filtering aggressiveness
4. **Temperature change rate adjustment**: Make the 0.5°C/s threshold configurable
