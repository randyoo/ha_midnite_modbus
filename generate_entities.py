#!/usr/bin/env python3
"""Script to generate entity classes from CSV file."""

import csv
from collections import defaultdict

# Read the enhanced CSV
with open('REGISTER_CATEGORIES_ENHANCED.csv', 'r') as f:
    reader = csv.DictReader(f)
    registers = list(reader)

# Group by entity type and category
by_type_category = defaultdict(lambda: defaultdict(list))
for reg in registers:
    entity_type = reg['Entity Type']
    category = reg['Category']
    by_type_category[entity_type][category].append(reg)

print("""
# Generated Entity Classes
# DO NOT EDIT - Generated from REGISTER_CATEGORIES_ENHANCED.csv
# Run generate_entities.py to update
""")

print("\n" + "="*80)
print("SENSORS")
print("="*80)

for category, regs in by_type_category['sensor'].items():
    print(f"\n# {category} Sensors")
    for reg in sorted(regs, key=lambda x: int(x['Address'])):
        name = reg['Register Name']
        addr = reg['Address']
        device_class = reg['Device Class'] or "None"
        state_class = reg['State Class'] or "None"
        unit = reg['Unit'] or '""'
        precision = reg['Precision'] or "None"
        icon = reg['Icon'] or 'None'
        enabled = reg['Enabled By Default'] == 'TRUE'
        
        print(f"""
class {name}Sensor(MidniteSolarSensor):
    \"\"\"Representation of a {name.lower().replace('_', ' ')} sensor.\"\"\"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        \"\"\"Initialize the sensor.\"\"\"
        super().__init__(coordinator, entry)
        self._attr_name = "{name}"
        self._attr_unique_id = f"{{entry.entry_id}}_{name.lower()}"
        self._attr_device_class = SensorDeviceClass.{device_class if device_class != 'None' else 'None'}
        self._attr_native_unit_of_measurement = {unit}
        self._attr_state_class = SensorStateClass.{state_class if state_class != 'None' else 'None'}
        {'self._attr_suggested_display_precision = ' + precision if precision != 'None' and precision != '' else ''}
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if {category} == "D" else None
        
    @property
    def native_value(self) -> Optional[float]:
        \"\"\"Return the state of the sensor.\"\"\"
        if self.coordinator.data and "data" in self.coordinator.data:
            # Find which group this register belongs to
            value = self.coordinator.get_register_value({addr})
            if value is not None:
                return value / 10.0 if {unit} == "V" or {unit} == "A" else value
        return None
""")

print("\n" + "="*80)
print("NUMBERS")
print("="*80)

for category, regs in by_type_category['number'].items():
    print(f"\n# {category} Numbers")
    for reg in sorted(regs, key=lambda x: int(x['Address'])):
        name = reg['Register Name']
        addr = reg['Address']
        device_class = reg['Device Class'] or "None"
        unit = reg['Unit'] or '""'
        precision = float(reg['Precision']) if reg['Precision'] else 1.0
        icon = reg['Icon'] or 'None'
        enabled = reg['Enabled By Default'] == 'TRUE'
        
        print(f"""
class {name}Number(MidniteSolarNumber):
    \"\"\"Number to set {name.lower().replace('_', ' ')}.\"\"\"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        \"\"\"Initialize the number.\"\"\"
        super().__init__(coordinator, entry)
        self._attr_name = "{name}"
        self._attr_unique_id = f"{{entry.entry_id}}_{name.lower()}"
        self._attr_native_unit_of_measurement = {unit}
        self.register_address = REGISTER_MAP["{name}"]
        # Typical range based on unit
        if {unit} == "V":
            self._attr_native_min_value = 10.0
            self._attr_native_max_value = 65.0
        elif {unit} == "A":
            self._attr_native_min_value = 1.0
            self._attr_native_max_value = 100.0
        elif {unit} == "s":
            self._attr_native_min_value = 0
            self._attr_native_max_value = 86400  # 24 hours
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 1000
        self._attr_native_step = {precision}
        
    async def async_set_native_value(self, value: float) -> None:
        \"\"\"Update the current value.\"\"\"
        await self._async_set_value(value)
""")

print("\n" + "="*80)
print("SELECTS")
print("="*80)

for category, regs in by_type_category['select'].items():
    print(f"\n# {category} Selects")
    for reg in sorted(regs, key=lambda x: int(x['Address'])):
        name = reg['Register Name']
        addr = reg['Address']
        icon = reg['Icon'] or 'None'
        
        print(f"""
class {name}Select(MidniteSolarSelect):
    \"\"\"Select to set {name.lower().replace('_', ' ')}.\"\"\"

    def __init__(self, coordinator: MidniteSolarUpdateCoordinator, entry: Any):
        \"\"\"Initialize the select.\"\"\"
        super().__init__(coordinator, entry)
        self._attr_name = "{name}"
        self._attr_unique_id = f"{{entry.entry_id}}_{name.lower()}"
        self.register_address = REGISTER_MAP["{name}"]
        # Options will be defined based on register specifics
        
    @property
    def current_option(self) -> str | None:
        \"\"\"Return the selected option.\"\"\"
        value = self.coordinator.get_register_value({addr})
        if value is not None:
            # Map value to option - will be customized per select
            return "Option " + str(value)
        return None
    
    async def async_select_option(self, option: str) -> None:
        \"\"\"Update the selected option.\"\"\"
        # Map option to value - will be customized per select
        await self._async_set_value(0)
""")

print("\n" + "="*80)
print("ENTITY REGISTRATION HELPERS")
print("="*80)

# Generate registration helpers
for entity_type, categories in by_type_category.items():
    print(f"\n# {entity_type.upper()} Registration Helper")
    print(f"def get_{entity_type}_list(entry: Any) -> list:")
    print("    \"\"\"Get list of entities based on configuration.\"\"\"")
    
    for category, regs in categories.items():
        if regs:
            print(f"    # {category} {entity_type}s")
            for reg in sorted(regs, key=lambda x: int(x['Address'])):
                name = reg['Register Name']
                enabled = reg['Enabled By Default'] == 'TRUE'
                
                if enabled:
                    print(f"    entities.append({name}{entity_type.capitalize()}(coordinator, entry))")
                else:
                    print(f"    if should_create_entity(entry, \"{name}\"):")
                    print(f"        entities.append({name}{entity_type.capitalize()}(coordinator, entry))")
    
    print("    return entities")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nTotal Sensors: {len(by_type_category['sensor']['B']) + len(by_type_category['sensor']['A']) + len(by_type_category['sensor']['D'])}")
print(f"  - Basic: {len(by_type_category['sensor']['B'])}")
print(f"  - Advanced: {len(by_type_category['sensor']['A'])}")
print(f"  - Debug: {len(by_type_category['sensor']['D'])}")

print(f"\nTotal Numbers: {len(by_type_category['number']['B']) + len(by_type_category['number']['A']) + len(by_type_category['number']['D'])}")
print(f"  - Basic: {len(by_type_category['number']['B'])}")
print(f"  - Advanced: {len(by_type_category['number']['A'])}")
print(f"  - Debug: {len(by_type_category['number']['D'])}")

print(f"\nTotal Selects: {len(by_type_category['select']['B']) + len(by_type_category['select']['A']) + len(by_type_category['select']['D'])}")
print(f"  - Basic: {len(by_type_category['select']['B'])}")
print(f"  - Advanced: {len(by_type_category['select']['A'])}")
print(f"  - Debug: {len(by_type_category['select']['D'])}")
