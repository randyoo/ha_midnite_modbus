#!/usr/bin/env python3
"""Check which registers are being read vs defined - reads from actual coordinator file."""
import re

# Read the coordinator.py file
with open('custom_components/midnite/coordinator.py', 'r') as f:
    content = f.read()

# Extract REGISTER_GROUPS using regex
match = re.search(r'REGISTER_GROUPS = \{([^}]+)\}', content, re.DOTALL)
if not match:
    print("Could not find REGISTER_GROUPS")
    exit(1)

groups_str = match.group(1)

# Parse the groups - this is a simplified parser
register_groups = {}
current_group = None
for line in groups_str.split('\n'):
    line = line.strip()
    # Match group name
    group_match = re.match(r'"([^"]+)": \[', line)
    if group_match:
        current_group = group_match.group(1)
        register_groups[current_group] = []
        continue
    
    # Match register references
    if current_group and 'REGISTER_MAP[' in line:
        reg_match = re.search(r'REGISTER_MAP\["([^"]+)"\]', line)
        if reg_match:
            register_groups[current_group].append(reg_match.group(1))

# Read REGISTER_MAP from const.py
with open('custom_components/midnite/const.py', 'r') as f:
    const_content = f.read()

match = re.search(r'REGISTER_MAP = \{([^}]+)\}', const_content, re.DOTALL)
if not match:
    print("Could not find REGISTER_MAP")
    exit(1)

map_str = match.group(1)
register_map = {}
for line in map_str.split('\n'):
    line = line.strip()
    if ':' in line and 'REGISTER_MAP[' not in line:
        parts = line.split(':', 1)
        if len(parts) == 2:
            name = parts[0].strip().strip('"')
            addr = parts[1].strip()
            try:
                register_map[name] = int(addr)
            except ValueError:
                pass

# Get all registers that are being read
all_read_registers = set()
for group in register_groups.values():
    for reg_name in group:
        if reg_name in register_map:
            all_read_registers.add(register_map[reg_name])

print("=" * 80)
print("REGISTERS BEING READ BY COORDINATOR:")
print("=" * 80)
for name, addr in sorted(register_map.items()):
    if addr in all_read_registers:
        print(f"{addr:6d} - {name}")

print("\n" + "=" * 80)
print("REGISTERS NOT BEING READ (likely showing 'unknown'):")
print("=" * 80)
not_read = []
for name, addr in sorted(register_map.items()):
    if addr not in all_read_registers:
        not_read.append((addr, name))

for addr, name in not_read[:30]:  # Show first 30
    print(f"{addr:6d} - {name}")

print(f"\n... and {len(not_read) - 30} more not shown")
