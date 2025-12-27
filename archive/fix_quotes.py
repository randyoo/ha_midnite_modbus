#!/usr/bin/env python3
"""Fix the extra quotes around {name}."""

with open('custom_components/midnite/sensor.py', 'r') as f:
    content = f.read()

# Replace REGISTER_MAP["'{name}'"] with REGISTER_MAP["{name}"]
content = content.replace('REGISTER_MAP["\'{\'name\'}\'"]', 'REGISTER_MAP["{name}"]')

with open('custom_components/midnite/sensor.py', 'w') as f:
    f.write(content)

print("✓ Fixed extra quotes")
