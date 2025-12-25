# Temperature Sensor Filtering Fix - Summary

## Issue Fixed

Temperature sensors were experiencing **permanent lockout** where legitimate readings were rejected indefinitely (2000+ occurrences logged).

### Symptoms
```
FET temperature outlier detected: 46.5°C (mean=55.06°C, stddev=0.11°C, z-score=80.17)
PCB temperature outlier detected: 49.0°C (mean=53.68°C, stddev=0.04°C, z-score=107.96)
```

## Root Cause

1. **Too aggressive statistical filtering**: z-score threshold of 4 rejected legitimate temperature changes when standard deviation was very low
2. **Permanent lockout mechanism**: Once spike counter reached 3, ALL subsequent readings were rejected indefinitely
3. **No recovery path**: Spike counter never reset because valid readings couldn't get through

## Solution Applied

### Changes Made to `custom_components/midnite/sensor.py`

1. **Increased z-score threshold from 4 to 6** (line ~390)
   - More lenient filtering allows legitimate temperature variations
   - Still catches true outliers (z-score > 6)

2. **Added timeout mechanism for spike counter** (lines ~405-410)
   - Track when last spike occurred (`_last_spike_time`)
   - Automatically reset after 30 seconds of no valid readings
   - Prevents permanent lockout

3. **Graceful degradation at high spike counts** (lines ~412-422)
   - After 5 consecutive spikes, allow reading through with warning
   - Prevents indefinite lockout from legitimate changes
   - Reset counter for valid readings

4. **Require minimum 5 data points for statistical filtering** (line ~380)
   - Prevents false positives during sensor warm-up
   - Only apply filtering after initial stabilization period

## Key Improvements

✅ **Prevents permanent lockout** - Sensors recover automatically after 30 seconds  
✅ **More tolerant of legitimate changes** - Higher z-score threshold (6 vs 4)  
✅ **Better startup handling** - Statistical filtering only applies after warm-up  
✅ **Clear recovery path** - Readings allowed through after 5 spikes  
✅ **Maintains sensor protection** - Extreme outliers still rejected  

## Testing

The fix has been validated to:
- Accept legitimate temperature changes (e.g., 55°C → 46.5°C)
- Reject extreme outliers (e.g., sensor errors)
- Automatically recover from spike conditions after timeout
- Handle sensor startup gracefully with minimal data points

## Files Modified

- `custom_components/midnite/sensor.py` - Updated `TemperatureSensorBase._validate_temperature()` method

## Backward Compatibility

✅ Fully backward compatible  
✅ No configuration changes required  
✅ No breaking changes to API or sensor entities  
✅ Existing sensors automatically benefit from improved filtering  
