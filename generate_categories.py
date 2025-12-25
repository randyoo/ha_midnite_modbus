#!/usr/bin/env python3
"""Script to generate REGISTER_CATEGORIES from CSV file."""

import csv

print("# Register categories for entity creation")
print("# B = Basic (always enabled), A = Advanced (opt-in), D = Debug (opt-in)")
print("REGISTER_CATEGORIES = {")

with open('REGISTER_CATEGORIES.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Register Name']
        category = row['Category']
        print(f'    "{name}": "{category}",')

print("}")
