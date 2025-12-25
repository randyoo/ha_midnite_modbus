#!/usr/bin/env python3
"""
Script to parse both register files and create a comprehensive checklist.
"""
import json
from collections import defaultdict

def load_registers(filename):
    """Load registers from JSON file."""
    with open(filename, 'r') as f:
        data = json.load(f)
    return data.get('registers', [])

def create_checklist(registers1, registers2):
    """Create a comprehensive checklist of all registers from both files."""
    
    # Create dictionaries for quick lookup
    reg_dict1 = {int(r['address']): r for r in registers1}
    reg_dict2 = {int(r['address']): r for r in registers2}
    
    # Get all unique addresses
    all_addresses = set(reg_dict1.keys()) | set(reg_dict2.keys())
    
    checklist = []
    
    for addr in sorted(all_addresses):
        entry = {
            'address': addr,
            'name': '',
            'unit': '',
            'description': '',
            'in_file1': False,
            'in_file2': False,
            'access': '',
            'formula': ''
        }
        
        # Check if in file1
        if addr in reg_dict1:
            r1 = reg_dict1[addr]
            entry['name'] = r1.get('name', '')
            entry['unit'] = r1.get('unit', '')
            entry['description'] = r1.get('description', '')
            entry['in_file1'] = True
            entry['access'] = r1.get('access', '')
            entry['formula'] = r1.get('formula', '')
        
        # Check if in file2
        if addr in reg_dict2:
            r2 = reg_dict2[addr]
            if not entry['name']:  # Prefer name from file1 if both have it
                entry['name'] = r2.get('name', '')
            if not entry['unit']:
                entry['unit'] = r2.get('unit', '')
            if not entry['description']:
                entry['description'] = r2.get('description', '')
            entry['in_file2'] = True
            if not entry['access']:
                entry['access'] = r2.get('access', '')
            if not entry['formula']:
                entry['formula'] = r2.get('formula', '')
        
        checklist.append(entry)
    
    return checklist

def main():
    # Load registers from both files
    registers1 = load_registers('/Users/randy/midnite/registers_clean2.json')
    registers2 = load_registers('/Users/randy/midnite/registers2.json')
    
    # Create checklist
    checklist = create_checklist(registers1, registers2)
    
    # Write to JSON file
    with open('/Users/randy/midnite/register_checklist.json', 'w') as f:
        json.dump(checklist, f, indent=2)
    
    print(f"Created checklist with {len(checklist)} registers")
    print(f"Registers only in file1: {sum(1 for r in checklist if r['in_file1'] and not r['in_file2'])}")
    print(f"Registers only in file2: {sum(1 for r in checklist if r['in_file2'] and not r['in_file1'])}")
    print(f"Registers in both files: {sum(1 for r in checklist if r['in_file1'] and r['in_file2'])}")

if __name__ == '__main__':
    main()
