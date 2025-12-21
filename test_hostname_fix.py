#!/usr/bin/env python3
"""
Test to verify the hostname read/write fix.
This test verifies that:
1. Reading hostname from registers works correctly (little-endian)
2. Writing hostname to registers uses correct byte order (little-endian)
3. The fix resolves the "CLASSIC7" -> "LCSAIS7C" issue
"""

import sys
sys.path.insert(0, '/Users/randy/midnite')

print("Test: Hostname Read/Write Fix")
print("=" * 60)

# Test 1: Verify the reading logic (should already be correct)
print("\nTest 1: Reading Logic Verification")
try:
    # Simulate what the device returns for "CLASSIC7"
    # Registers are little-endian: LSB = char 0/2/4/6, MSB = char 1/3/5/7
    
    # For "CLASSIC7" (8 chars):
    # Reg 4210: C(7) | L(76) -> 0x43 | (0x4C << 8) = 0x434C
    # Reg 4211: A(65) | S(83) -> 0x41 | (0x53 << 8) = 0x4153
    # Reg 4212: S(83) | I(73) -> 0x53 | (0x49 << 8) = 0x5349
    # Reg 4213: C(67) | 7(55) -> 0x43 | (0x37 << 8) = 0x4337
    
    test_registers = {
        4210: 0x434C,  # CL
        4211: 0x4153,  # AS
        4212: 0x5349,  # SI
        4213: 0x4337,  # C7
    }
    
    def read_hostname(registers):
        """Simulate the reading logic from text.py"""
        chars = []
        
        for reg_value in [registers[4210], registers[4211], registers[4212], registers[4213]]:
            # Extract two bytes from a 16-bit register value
            # LSB (low byte) first, then MSB (high byte)
            lsb = reg_value & 0xFF
            msb = (reg_value >> 8) & 0xFF
            chars.append(lsb)
            chars.append(msb)
        
        # Filter out null/zero bytes and convert to string
        name = "".join(chr(c) for c in chars if c != 0)
        return name.strip()
    
    result = read_hostname(test_registers)
    print(f"  Register values: {test_registers}")
    print(f"  Expected: CLASSIC7")
    print(f"  Got:      {result}")
    assert result == "CLASSIC7", f"Reading logic failed: got '{result}' instead of 'CLASSIC7'"
    print("✓ Reading logic works correctly (little-endian)")
except Exception as e:
    print(f"✗ Reading test failed: {e}")
    sys.exit(1)

# Test 2: Verify the old writing logic was wrong
print("\nTest 2: Old Writing Logic (Big-Endian) - Should Fail")
try:
    def write_hostname_old(value):
        """Simulate the OLD (incorrect) writing logic"""
        padded_value = (value[:8].ljust(8))
        register_values = []
        
        for i in range(4):
            start_idx = i * 2
            char1 = padded_value[start_idx]
            char2 = padded_value[start_idx + 1]
            # OLD: Big-endian (char1 in MSB, char2 in LSB)
            register_value = (ord(char1) << 8) | ord(char2)
            register_values.append(register_value)
        
        return register_values
    
    registers_old = write_hostname_old("CLASSIC7")
    print(f"  Input: CLASSIC7")
    print(f"  Old logic registers: {registers_old}")
    
    # Now read back using the correct reading logic
    test_regs = {
        4210: registers_old[0],
        4211: registers_old[1],
        4212: registers_old[2],
        4213: registers_old[3],
    }
    result_back = read_hostname(test_regs)
    print(f"  After write+read: {result_back}")
    
    if result_back != "CLASSIC7":
        print(f"✓ Confirmed old logic was wrong (got '{result_back}' instead of 'CLASSIC7')")
    else:
        print("  Note: Old logic happened to work for this case")
except Exception as e:
    print(f"✗ Old writing test failed: {e}")
    sys.exit(1)

# Test 3: Verify the new writing logic is correct
print("\nTest 3: New Writing Logic (Little-Endian) - Should Work")
try:
    def write_hostname_new(value):
        """Simulate the NEW (correct) writing logic"""
        padded_value = (value[:8].ljust(8))
        register_values = []
        
        for i in range(4):
            start_idx = i * 2
            char1 = padded_value[start_idx]
            char2 = padded_value[start_idx + 1]
            # NEW: Little-endian (char1 in LSB, char2 in MSB)
            register_value = ord(char1) | (ord(char2) << 8)
            register_values.append(register_value)
        
        return register_values
    
    registers_new = write_hostname_new("CLASSIC7")
    print(f"  Input: CLASSIC7")
    print(f"  New logic registers: {registers_new}")
    
    # Now read back using the correct reading logic
    test_regs = {
        4210: registers_new[0],
        4211: registers_new[1],
        4212: registers_new[2],
        4213: registers_new[3],
    }
    result_back = read_hostname(test_regs)
    print(f"  After write+read: {result_back}")
    
    assert result_back == "CLASSIC7", f"New logic failed: got '{result_back}' instead of 'CLASSIC7'"
    print("✓ New writing logic works correctly (little-endian)")
except Exception as e:
    print(f"✗ New writing test failed: {e}")
    sys.exit(1)

# Test 4: Test with various strings to ensure robustness
print("\nTest 4: Robustness Testing")
try:
    test_strings = [
        "CLASSIC",
        "CLASSIC7",
        "SOLAR123",
        "TESTING",
        "A",  # Single character
        "12345678",  # All numbers
    ]
    
    for test_str in test_strings:
        padded = test_str.ljust(8)
        registers = write_hostname_new(padded)
        test_regs = {4210 + i: registers[i] for i in range(4)}
        result_back = read_hostname(test_regs)
        
        # Compare without trailing spaces
        expected = padded.rstrip()
        actual = result_back.rstrip()
        
        if expected == actual:
            print(f"  ✓ '{test_str}' -> {registers} -> '{actual}'")
        else:
            print(f"  ✗ '{test_str}' -> {registers} -> '{actual}' (expected '{expected}')")
            sys.exit(1)
    
    print("✓ All robustness tests passed")
except Exception as e:
    print(f"✗ Robustness test failed: {e}")
    sys.exit(1)

# Test 5: Verify the actual code in text.py has been updated
print("\nTest 5: Code Verification")
try:
    with open('custom_components/midnite/text.py', 'r') as f:
        content = f.read()
    
    # Check that the new logic is present
    if "ord(char1) | (ord(char2) << 8)" in content:
        print("✓ Code contains correct little-endian write logic")
    else:
        print("✗ Code does not contain corrected write logic")
        sys.exit(1)
    
    # Check that the old logic is gone
    if "(ord(char1) << 8) | ord(char2)" in content:
        print("⚠ Warning: Old big-endian logic still present in code")
    else:
        print("✓ Old big-endian logic has been removed")
    
    # Check for the comment explaining little-endian
    if "little-endian" in content.lower():
        print("✓ Code includes documentation about endianness")
    else:
        print("⚠ Warning: No documentation about endianness found")
except Exception as e:
    print(f"✗ Code verification failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("All hostname tests passed! ✓")
print("\nSummary of the fix:")
print("- Reading logic was already correct (little-endian)")
print("- Writing logic was wrong (big-endian)")
print("- Fixed by changing: (ord(char1) << 8) | ord(char2)")
print("                to: ord(char1) | (ord(char2) << 8)")
print("- Now hostname writes and reads correctly")
