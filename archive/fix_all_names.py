#!/usr/bin/env python3
"""Fix all instances of literal {name} in sensor.py."""

with open('custom_components/midnite/sensor.py', 'r') as f:
    content = f.read()

# Fix pattern 1: REGISTER_MAP["'{name}'"]
content = content.replace('REGISTER_MAP["\'{\'name\'}\'"]', 'REGISTER_MAP["{name}"]')

# Fix pattern 2: REGISTER_MAP["'{name}'"] (single quote inside)
content = content.replace('REGISTER_MAP["\'{name}\'"]', 'REGISTER_MAP["{name}"]')

with open('custom_components/midnite/sensor.py', 'w') as f:
    f.write(content)

print("✓ Fixed all name patterns")
