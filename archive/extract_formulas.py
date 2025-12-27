#!/usr/bin/env python3
"""
Extract formulas and other data from registers_clean.json to update REGISTER_CATEGORIES.csv
"""

import json
import csv
import re
from typing import Dict, List, Optional

def parse_json_with_comments(file_path: str) -> dict:
    """Parse JSON file that may contain comments by removing them first."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove /* */ style comments
    content = re.sub(r'//.*', '', content)  # Remove single-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # Remove multi-line comments
    
    # Fix trailing commas in arrays and objects
    content = re.sub(r',\s*\]', ']', content)
    content = re.sub(r',\s*}', '}', content)
    
    return json.loads(content)

def extract_formula_from_description(description: str) -> Optional[str]:
    """Extract formula information from description if not in formula field."""
    # Look for patterns like "(divide by 10)", "(/10)", etc.
    patterns = [
        r'\(divide by (\d+)\)',
        r'\(multiply by (\d+)\)',
        r'(\/\d+|\*\d+)',
        r'(\d+\.\d+ \w+)'  # e.g., "10 V"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(1) if len(match.groups()) > 0 else match.group(0)
    
    return None

def get_friendly_name_from_register_name(register_name: str) -> str:
    """
    Generate friendly entity name from register name.
    Based on pre-csv branch pattern (abbreviated form of register description).
    """
    # Remove special characters and split by underscore
    parts = re.sub(r'[^\w\s]', '', register_name).split('_')
    
    friendly_parts = []
    for part in parts:
        if len(part) > 0:
            friendly_parts.append(part)
    
    # Handle common patterns
    name_mapping = {
        'DISP_AVG_VBATT': 'Battery Voltage',
        'DISP_AVG_VPV': 'PV Voltage', 
        'IBATT_DISPLAY_S': 'Battery Current',
        'WATTS': 'Power Output',
        'COMBO_CHARGE_STAGE': 'Charge Stage',
        'INFO_FLAGS_BITS3': 'System Status Flags',
        'REASON_FOR_RESTING': 'Rest Reason',
        'BATT_TEMPERATURE': 'Battery Temperature',
        'FET_TEMPERATURE': 'FET Temperature',
        'PCB_TEMPERATURE': 'PCB Temperature',
        'AMP_HOURS_DAILY': 'Daily Amp-Hours',
        'LIFETIME_KW_HOURS_1': 'Lifetime Energy',
        'PV_INPUT_CURRENT': 'PV Input Current',
        'VOC_LAST_MEASURED': 'Last Measured VOC',
        'FLOAT_TIME_TODAY_SEC': 'Float Time Today',
        'ABSORB_TIME': 'Absorb Time Remaining',
        'EQUALIZE_TIME': 'Equalize Time Remaining'
    }
    
    if register_name in name_mapping:
        return name_mapping[register_name]
    
    # Default pattern: capitalize first letter of each part, remove duplicates
    friendly_name = ' '.join(friendly_parts)
    
    # Clean up common abbreviations
    friendly_name = friendly_name.replace('Avg', 'Average')
    friendly_name = friendly_name.replace('Vbatt', 'Battery Voltage')
    friendly_name = friendly_name.replace('Vpv', 'PV Voltage')
    friendly_name = friendly_name.replace('Ibatt', 'Battery Current')
    friendly_name = friendly_name.replace('Voc', 'Open Circuit Voltage')
    
    return friendly_name

def main():
    # Load the current CSV
    with open('REGISTER_CATEGORIES.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Parse registers_clean.json
    try:
        registers_data = parse_json_with_comments('archive/registers_clean.json')
        register_map = {reg['name']: reg for reg in registers_data['registers']}
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return
    
    # Add new columns to each row
    for i, row in enumerate(rows):
        register_name = row['Register Name']
        
        # Remove 'Enabled By Default' column (it's redundant)
        if 'Enabled By Default' in row:
            del row['Enabled By Default']
        
        # Add Formula column
        formula = None
        if register_name in register_map:
            reg_data = register_map[register_name]
            if 'formula' in reg_data and reg_data['formula']:
                formula = reg_data['formula']
            elif 'unit' in reg_data and reg_data['unit']:
                # Extract conversion from unit description
                if '/10' in reg_data.get('description', ''):
                    formula = 'value / 10'
        
        row['Formula'] = formula or ''
        
        # Add Friendly Name column
        friendly_name = get_friendly_name_from_register_name(register_name)
        row['Friendly Name'] = friendly_name
        
        # Add Scan Interval column (default values based on entity type and category)
        category = row.get('Category', '')
        entity_type = row.get('Entity Type', '')
        
        if category == 'B':  # Basic - more frequent updates
            scan_interval = 15
        elif category == 'A' or category == 'D':  # Advanced/Debug - less frequent
            scan_interval = 60
        else:
            scan_interval = 30
        
        row['Scan Interval'] = str(scan_interval)
        
        # Add Select Options column (for select entities)
        if entity_type == 'select':
            options = []
            if register_name in register_map:
                reg_data = register_map[register_name]
                if 'bits' in reg_data:
                    for bit_info in reg_data['bits']:
                        options.append(f"{bit_info.get('desc', '')}")
                elif 'tables' in registers_data and register_name in registers_data['tables']:
                    table = registers_data['tables'][register_name]
                    for item in table:
                        if 'name' in item:
                            options.append(item['name'])
                        elif 'description' in item:
                            options.append(item['description'])
            
            row['Select Options'] = '|'.join(options) if options else ''
        else:
            row['Select Options'] = ''
    
    # Write updated CSV with new header
    fieldnames = ['Register Name', 'Address', 'Category', 'Entity Type', 'Device Class', 
                  'State Class', 'Unit', 'Precision', 'Icon', 'Description', 
                  'Formula', 'Friendly Name', 'Scan Interval', 'Select Options']
    
    with open('REGISTER_CATEGORIES_UPDATED.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print("✓ Updated CSV file created: REGISTER_CATEGORIES_UPDATED.csv")

if __name__ == '__main__':
    main()