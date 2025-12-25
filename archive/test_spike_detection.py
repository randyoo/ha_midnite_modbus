#!/usr/bin/env python3
"""
Test script to verify temperature spike detection logic.
This simulates the temperature sensor behavior with the actual data from spikes.csv
"""

import csv
from datetime import datetime
import time

class TemperatureSensorSimulator:
    """Simulates the temperature sensor with spike detection."""
    
    def __init__(self):
        self._last_temp = None
        self._last_time = None
        self._recent_readings = []
        self._max_recent_readings = 20
        self._spike_count = 0
        self.valid_readings = []
        self.rejected_readings = []
    
    def process_temperature(self, temp_value, timestamp):
        """
        Process a temperature reading with spike detection.
        Returns True if accepted, False if rejected.
        """
        # Use the actual timestamp from CSV to calculate proper time differences
        current_time = timestamp.timestamp()
        
        # Validate temperature range (-50°C to 150°C is reasonable for batteries)
        if temp_value < -50 or temp_value > 150:
            print(f"❌ REJECTED: Invalid range {temp_value}°C (out of bounds)")
            self._spike_count += 1
            return False
        
        # Check for sudden temperature changes (>0.5°C per second)
        if self._last_temp is not None and self._last_time is not None:
            time_diff = current_time - self._last_time
            if time_diff > 0:
                temp_change_rate = abs(temp_value - self._last_temp) / time_diff
                if temp_change_rate > 0.5:  # More than 0.5°C per second
                    print(f"❌ REJECTED: Sudden change {self._last_temp}°C -> {temp_value}°C "
                          f"({temp_change_rate:.2f}°C/s over {time_diff:.1f}s)")
                    self._spike_count += 1
                    return False
        
        # Statistical outlier detection using recent readings
        if len(self._recent_readings) > 0:
            mean_temp = sum(self._recent_readings) / len(self._recent_readings)
            variance = sum((x - mean_temp) ** 2 for x in self._recent_readings) / len(self._recent_readings)
            std_dev = variance ** 0.5 if variance > 0 else 0
            
            # Check if reading is more than 4 standard deviations from mean (more conservative)
            if std_dev > 0:
                z_score = abs(temp_value - mean_temp) / std_dev
                if z_score > 4:
                    print(f"❌ REJECTED: Outlier {temp_value}°C (mean={mean_temp:.2f}°C, "
                          f"stddev={std_dev:.2f}°C, z-score={z_score:.2f})")
                    self._spike_count += 1
                    return False
        
        # If we have consecutive spikes, be more conservative
        if self._spike_count >= 3:
            print(f"❌ REJECTED: Multiple anomalies in succession (current: {temp_value}°C)")
            return False
        
        # Reset spike counter if we get a valid reading
        self._spike_count = 0
        
        # Update recent readings (keep only the last N valid readings)
        self._recent_readings.append(temp_value)
        if len(self._recent_readings) > self._max_recent_readings:
            self._recent_readings.pop(0)
        
        # Update last values
        self._last_temp = temp_value
        self._last_time = current_time
        
        print(f"✅ ACCEPTED: {temp_value}°C")
        return True
    
    def get_stats(self):
        """Return statistics about processing."""
        return {
            'total_readings': len(self.valid_readings) + len(self.rejected_readings),
            'valid_readings': len(self.valid_readings),
            'rejected_readings': len(self.rejected_readings),
            'rejection_rate': len(self.rejected_readings) / (len(self.valid_readings) + len(self.rejected_readings)) if (len(self.valid_readings) + len(self.rejected_readings)) > 0 else 0
        }

def main():
    print("=" * 80)
    print("Temperature Spike Detection Test")
    print("=" * 80)
    
    sensor = TemperatureSensorSimulator()
    
    # Read the CSV
    with open('spikes.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                temp = float(row['state'])
                timestamp = datetime.fromisoformat(row['last_changed'].replace('Z', '+00:00'))
                
                # Simulate processing with a small delay to match real timing
                time.sleep(0.01)
                
                accepted = sensor.process_temperature(temp, timestamp)
                if accepted:
                    sensor.valid_readings.append(temp)
                else:
                    sensor.rejected_readings.append(temp)
            except ValueError:
                pass
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    stats = sensor.get_stats()
    print(f"Total readings: {stats['total_readings']}")
    print(f"Valid readings: {stats['valid_readings']} ({stats['valid_readings']/stats['total_readings']*100:.1f}%)")
    print(f"Rejected readings: {stats['rejected_readings']} ({stats['rejection_rate']*100:.1f}%)")
    
    if stats['rejected_readings'] > 0:
        print("\nRejected temperature values:")
        for temp in sorted(set(sensor.rejected_readings)):
            count = sensor.rejected_readings.count(temp)
            print(f"  {temp}°C: {count} occurrence(s)")
    
    print("\n" + "=" * 80)
    print("Known spikes that should be rejected:")
    known_spikes = [54.86, 55.58, 54.68, 41.72]
    for spike in known_spikes:
        if spike in sensor.rejected_readings:
            print(f"  ✅ {spike}°C - CORRECTLY REJECTED")
        else:
            print(f"  ❌ {spike}°C - NOT REJECTED (may still be in valid readings)")

if __name__ == '__main__':
    main()
