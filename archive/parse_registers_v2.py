#!/usr/bin/env python3
"""
Script to parse both register files and create a comprehensive checklist.
Handles JSON with comments by removing them first.
"""
import json
import re
from collections import defaultdict

def remove_json_comments(text):
    """Remove // and /* */ comments from JSON text."""
    # Remove single-line comments
    text = re.sub(r'//.*', '', text)
    # Remove multi-line comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text

def load_registers(filename):
    """Load registers from JSON file with comment removal."""
    with open(filename, 'r') as f:
        text = f.read()
    
    # Remove comments
    clean_text = remove_json_comments(text)
    
    try:
        data = json.loads(clean_text)
        return data.get('registers', [])
    except json.JSONDecodeError as e:
        print(f"Error parsing {filename}: {e}")
        # Try to find the problematic line
        lines = clean_text.split('\n')
        for i, line in enumerate(lines, 1):
            if 'registers' in line.lower() or (i > 10 and line.strip()):
                print(f"Line {i}: {line[:100]}")
        return []

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
    print("Loading registers from file 1...")
    registers1 = load_registers('/Users/randy/midnite/registers_cleaned.json')
    print(f"Loaded {len(registers1)} registers from file 1")
    
    print("\nLoading registers from file 2...")
    registers2 = load_registers('/Users/randy/midnite/registers2.json')
    print(f"Loaded {len(registers2)} registers from file 2")
    
    # Create checklist
    checklist = create_checklist(registers1, registers2)
    
    # Write to JSON file
    with open('/Users/randy/midnite/register_checklist.json', 'w') as f:
        json.dump(checklist, f, indent=2)
    
    print(f"\nCreated checklist with {len(checklist)} registers")
    only_in_file1 = sum(1 for r in checklist if r['in_file1'] and not r['in_file2'])
    only_in_file2 = sum(1 for r in checklist if r['in_file2'] and not r['in_file1'])
    in_both = sum(1 for r in checklist if r['in_file1'] and r['in_file2'])
    
    print(f"Registers only in file 1: {only_in_file1}")
    print(f"Registers only in file 2: {only_in_file2}")
    print(f"Registers in both files: {in_both}")

if __name__ == '__main__':
    main()
