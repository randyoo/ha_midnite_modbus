# Phase 2 Implementation Plan: CSV-Driven Entity Generation

## Overview
This document outlines the next phase of the Midnite Solar integration, focusing on transitioning to a completely CSV-driven entity generation system.

## Current State
- **REGISTER_CATEGORIES.csv**: Contains all 206 registers with basic information (name, address, category, description)
- **REGISTER_CATEGORIES_ENHANCED.csv**: Now contains all 206 registers with complete entity metadata (type, device class, unit, precision, icon, enabled by default)
- **const.py**: Still maintains hardcoded REGISTER_MAP and REGISTER_CATEGORIES dictionaries

## Phase 2 Goals
1. **Eliminate hardcoded register definitions** - Replace const.py mappings with CSV-driven generation
2. **Simplify entity creation** - Generate all entities from a single source of truth (CSV)
3. **Improve maintainability** - Make it easy for developers to add/modify registers without touching code
4. **Add validation** - Ensure CSV data is complete and consistent before generation

## Implementation Steps

### Step 1: Create CSV-to-Python Generator Script ✓ COMPLETED
Created `generate_from_csv.py` that reads REGISTER_CATEGORIES.csv and generates:
- `const.py` with REGISTER_MAP and REGISTER_CATEGORIES dictionaries
- Entity definitions for sensor.py, number.py, select.py, etc.

**Script Features:**
- Input: REGISTER_CATEGORIES.csv (now contains all enhanced metadata)
- Output: Python files in custom_components/midnite/
- Validation: Checks for missing/duplicate addresses, consistent categories
- Error handling: Graceful failure with clear error messages
- Automatic unit conversions based on unit type

### Step 2: Update Entity Generation Logic ✓ COMPLETED
The generator script now:
1. Reads from REGISTER_CATEGORIES.csv instead of hardcoded const.py dictionaries
2. Supports dynamic entity creation based on CSV metadata (device class, unit, precision, icon)
3. Handles category-based enabling (B=Basic, A=Advanced, D=Debug)
4. Automatically applies appropriate unit conversions

### Step 3: Replace Hardcoded Mappings ✓ COMPLETED
The generator now creates a new const.py that:
- Contains REGISTER_MAP and REGISTER_CATEGORIES generated from CSV
- Preserves all other hardcoded constants (DOMAIN, ports, mappings like CHARGE_STAGES)
- Documents CSV as the source of truth in file header

### Step 4: Add Documentation ✓ COMPLETED
Created comprehensive documentation:
- `CSV_FORMAT_SPECIFICATION.md` - Complete CSV format guide with examples
- Updated this PHASE_2_PLAN.md to reflect completed work
- Generator script includes inline documentation

## Files to Archive
The following files are no longer needed after Phase 2:
- `registers.json` - Replaced by REGISTER_CATEGORIES.csv
- `registers_fixed.json` - Replaced by REGISTER_CATEGORIES.csv
- `categorized_registers.json` - Replaced by REGISTER_CATEGORIES_ENHANCED.csv
- `categories_generated.py` - Replaced by new generator script
- `generate_categories.py` - Replaced by new generator script
- `generate_const.py` - Replaced by new generator script
- `generate_entities.py` - May be integrated into new system
- `generated_entities.py` - Generated file, not source
- `categorize_registers.py` - Replaced by CSV-based approach

## Validation Checklist ✓ COMPLETED
All Phase 2 requirements have been met:
- ✓ All registers from REGISTER_CATEGORIES.csv are properly formatted with enhanced metadata
- ✓ Generated const.py contains all 206 register definitions
- ✓ Entity generation produces entities for all register types (168 sensors, 21 numbers, 12 selects)
- ✓ Category-based enabling works correctly (B=Basic, A=Advanced, D=Debug)
- ✓ CSV validation catches errors (missing fields, invalid values, duplicates)
- ✓ Documentation is complete and accurate

## Benefits of Phase 2
1. **Single Source of Truth**: All register information in one easily editable CSV
2. **Rapid Development**: Add new registers without modifying Python code
3. **Consistency**: Automatic generation reduces human error
4. **Maintainability**: Clear separation between data and logic
5. **Collaboration**: Non-Python developers can modify register definitions

## Phase 2 Completion Summary

Phase 2 has been successfully completed! All implementation steps are complete:

### Deliverables
- ✓ `generate_from_csv.py` - CSV-to-Python generator script
- ✓ Updated `custom_components/midnite/const.py` - Generated from CSV
- ✓ Updated `custom_components/midnite/sensor.py` - 168 sensor classes
- ✓ Updated `custom_components/midnite/number.py` - 21 number classes
- ✓ Updated `custom_components/midnite/select.py` - 12 select classes
- ✓ `CSV_FORMAT_SPECIFICATION.md` - Comprehensive documentation
- ✓ `verify_generated.py` - Validation script

### Key Features Implemented
- CSV validation with clear error messages
- Automatic unit conversions (V, A, kWh)
- Device class and state class mappings
- Icon assignment from CSV metadata
- Category-based entity enabling (B/A/D)
- Precision settings for display

### Usage
To regenerate files after modifying REGISTER_CATEGORIES.csv:

```bash
# Generate all Python files
python generate_from_csv.py REGISTER_CATEGORIES.csv custom_components/midnite/

# Verify generation
python verify_generated.py
```

### Next Steps
Phase 2 is complete. The integration now uses a completely CSV-driven entity generation system. Future work can focus on:
- Adding more registers to REGISTER_CATEGORIES.csv as needed
- Enhancing the generator with additional features (e.g., custom conversion formulas)
- Improving documentation for end-users

## Next Steps
1. Implement CSV-to-Python generator script
2. Update entity generation to use CSV directly
3. Test with existing installation
4. Document the new system thoroughly
5. Archive obsolete files
