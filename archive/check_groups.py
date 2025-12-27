#!/usr/bin/env python3
import re

# Read the coordinator file to see what groups we have
with open('custom_components/midnite/coordinator.py', 'r') as f:
    content = f.read()

# Extract all register groups
groups = re.findall(r'"([^"]+)":\s*\[(.*?)\]', content, re.DOTALL)
group_names = [g[0] for g in groups]
print('Current Register Groups:')
for name in group_names:
    print(f'  - {name}')
