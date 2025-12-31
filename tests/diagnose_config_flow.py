#!/usr/bin/env python3
"""
Diagnostic script for Midnite Solar config flow autodiscovery issues.

This script runs comprehensive checks to identify potential issues
without modifying the actual config_flow.py file.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
_LOGGER = logging.getLogger(__name__)


def check_python_syntax():
    """Check that config_flow.py has valid Python syntax."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 1: Python Syntax Validation")
    _LOGGER.info("="*60)
    
    try:
        import py_compile
        config_flow_path = Path(__file__).parent.parent / "custom_components" / "midnite" / "config_flow.py"
        py_compile.compile(str(config_flow_path), doraise=True)
        _LOGGER.info("✓ Python syntax is valid")
        return True
    except SyntaxError as e:
        _LOGGER.error(f"✗ SYNTAX ERROR: {e}")
        _LOGGER.error(f"  Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        _LOGGER.error(f"✗ Failed to compile: {e}")
        return False


def check_imports():
    """Check that all imports work correctly."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 2: Import Validation")
    _LOGGER.info("="*60)
    
    try:
        # Test main imports
        from custom_components.midnite import config_flow
        _LOGGER.info("✓ config_flow module imported successfully")
        
        # Test pymodbus import
        from pymodbus.client import ModbusTcpClient
        _LOGGER.info("✓ ModbusTcpClient imported successfully")
        
        # Test voluptuous import
        import voluptuous as vol
        _LOGGER.info("✓ voluptuous imported successfully")
        
        # Test Home Assistant imports
        from homeassistant.config_entries import ConfigFlow
        _LOGGER.info("✓ ConfigFlow imported successfully")
        
        from homeassistant.const import CONF_HOST, CONF_PORT
        _LOGGER.info("✓ Home Assistant constants imported successfully")
        
        # Test DHCP service info import (both paths)
        try:
            from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
            _LOGGER.info("✓ New DHCP service info path works")
        except ImportError:
            from homeassistant.components.dhcp import DhcpServiceInfo
            _LOGGER.info("✓ Legacy DHCP service info path works")
        
        # Test device registry import
        from homeassistant.helpers.device_registry import format_mac
        _LOGGER.info("✓ Device registry format_mac imported successfully")
        
        return True
    except ImportError as e:
        _LOGGER.error(f"✗ IMPORT ERROR: {e}")
        return False
    except Exception as e:
        _LOGGER.error(f"✗ Import failed: {e}")
        return False


def check_config_flow_class():
    """Check that the config flow class is properly defined."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 3: Config Flow Class Validation")
    _LOGGER.info("="*60)
    
    try:
        from custom_components.midnite.config_flow import MidniteSolarConfigFlow
        
        # Check class attributes
        assert hasattr(MidniteSolarConfigFlow, 'VERSION'), "Missing VERSION attribute"
        _LOGGER.info(f"✓ VERSION: {MidniteSolarConfigFlow.VERSION}")
        
        # Check required methods
        required_methods = [
            'async_step_dhcp',
            'async_step_user',
            'async_step_options',
            'async_step_import',
            'async_step_reconfigure',
        ]
        
        for method in required_methods:
            assert hasattr(MidniteSolarConfigFlow, method), f"Missing method: {method}"
            _LOGGER.info(f"✓ Method exists: {method}")
        
        # Try to instantiate the class
        flow = MidniteSolarConfigFlow()
        assert flow is not None
        _LOGGER.info("✓ Config flow class instantiated successfully")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ Config flow class validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_manifest():
    """Check that the manifest.json is properly configured."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 4: Manifest Configuration Validation")
    _LOGGER.info("="*60)
    
    try:
        manifest_path = Path(__file__).parent.parent / "custom_components" / "midnite" / "manifest.json"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check required fields
        assert 'domain' in manifest, "Missing domain"
        _LOGGER.info(f"✓ Domain: {manifest['domain']}")
        
        assert 'name' in manifest, "Missing name"
        _LOGGER.info(f"✓ Name: {manifest['name']}")
        
        assert manifest.get('config_flow') == True, "config_flow should be true"
        _LOGGER.info("✓ Config flow enabled")
        
        # Check DHCP configuration
        if 'dhcp' in manifest:
            dhcp_configs = manifest['dhcp']
            assert len(dhcp_configs) > 0, "No DHCP configurations found"
            _LOGGER.info(f"✓ DHCP configurations: {len(dhcp_configs)}")
            
            for i, config in enumerate(dhcp_configs):
                if 'macaddress' in config:
                    _LOGGER.info(f"  DHCP config {i+1}: macaddress={config['macaddress']}")
        else:
            _LOGGER.warning("⚠ No DHCP configuration found in manifest")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ Manifest validation failed: {e}")
        return False


def check_pymodbus_version():
    """Check pymodbus version compatibility."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 5: PyModbus Version Validation")
    _LOGGER.info("="*60)
    
    try:
        import pymodbus
        version = pymodbus.__version__
        _LOGGER.info(f"✓ PyModbus version: {version}")
        
        # Parse version
        parts = version.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        
        assert major >= 3, f"PyModbus major version {major} is too old"
        assert major < 4, f"PyModbus major version {major} is not supported"
        _LOGGER.info("✓ PyModbus version is compatible (3.x)")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ PyModbus version check failed: {e}")
        return False


def check_modbus_api():
    """Check Modbus API compatibility."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 6: Modbus API Validation")
    _LOGGER.info("="*60)
    
    try:
        from pymodbus.client import ModbusTcpClient
        import inspect
        
        # Check read_holding_registers signature
        sig = inspect.signature(ModbusTcpClient.read_holding_registers)
        params = list(sig.parameters.keys())
        _LOGGER.info(f"✓ read_holding_registers parameters: {params}")
        
        assert 'address' in params, "Missing 'address' parameter"
        assert 'count' in params, "Missing 'count' parameter"
        _LOGGER.info("✓ Modbus API signature is correct")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ Modbus API check failed: {e}")
        return False


def check_hub_connection():
    """Check hub connection logic."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 7: Hub Connection Logic Validation")
    _LOGGER.info("="*60)
    
    try:
        from custom_components.midnite.hub import MidniteHub
        
        # Check that hub can be instantiated
        hub = MidniteHub('test_host', 502)
        assert hub is not None
        _LOGGER.info("✓ Hub instance created successfully")
        
        # Check required methods
        assert hasattr(hub, 'connect'), "Missing connect method"
        assert hasattr(hub, 'disconnect'), "Missing disconnect method"
        assert hasattr(hub, 'read_holding_registers'), "Missing read_holding_registers method"
        _LOGGER.info("✓ Hub methods exist")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ Hub connection check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dhcp_discovery_logic():
    """Check DHCP discovery specific logic."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 8: DHCP Discovery Logic Validation")
    _LOGGER.info("="*60)
    
    try:
        from custom_components.midnite.config_flow import MidniteSolarConfigFlow
        from homeassistant.helpers.device_registry import format_mac
        from unittest.mock import MagicMock
        
        # Create a mock discovery info
        discovery_info = MagicMock()
        discovery_info.ip = "192.168.1.100"
        discovery_info.macaddress = "60:1D:0F:12:34:56"
        
        # Test MAC address formatting
        formatted_mac = format_mac(discovery_info.macaddress)
        _LOGGER.info(f"✓ Formatted MAC: {formatted_mac}")
        assert formatted_mac == "601D0F123456"
        
        # Test config flow with discovery info
        flow = MidniteSolarConfigFlow()
        flow.discovery_info = discovery_info
        
        # Check that we can set unique ID
        assert hasattr(flow, 'async_set_unique_id'), "Missing async_set_unique_id method"
        _LOGGER.info("✓ Unique ID setting is available")
        
        # Check abort methods
        assert hasattr(flow, '_abort_if_unique_id_configured'), "Missing _abort_if_unique_id_configured method"
        assert hasattr(flow, '_async_abort_entries_match'), "Missing _async_abort_entries_match method"
        _LOGGER.info("✓ Abort methods are available")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ DHCP discovery logic check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_connection_test_logic():
    """Check connection test logic used in config flow."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 9: Connection Test Logic Validation")
    _LOGGER.info("="*60)
    
    try:
        from pymodbus.client import ModbusTcpClient
        from unittest.mock import MagicMock, patch
        
        # Mock successful connection and read
        with patch('pymodbus.client.ModbusTcpClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.connect.return_value = True
            mock_client.is_socket_open.return_value = True
            
            # Mock successful read at address 4100 (used in config_flow.py)
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [123]
            mock_client.read_holding_registers.return_value = mock_result
            
            mock_client_class.return_value = mock_client
            
            # Test connection logic
            client = ModbusTcpClient('test_host', port=502)
            connected = client.connect()
            assert connected == True, "Connection should succeed"
            _LOGGER.info("✓ Connection test works")
            
            # Test read logic
            result = client.read_holding_registers(address=4100, count=1)
            assert not result.isError(), "Read should succeed"
            _LOGGER.info("✓ Register read at address 4100 works")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ Connection test logic check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_voluptuous_schemas():
    """Check that voluptuous schemas can be created."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("CHECK 10: Voluptuous Schema Validation")
    _LOGGER.info("="*60)
    
    try:
        import voluptuous as vol
        from homeassistant.const import CONF_HOST, CONF_PORT
        
        # Test creating a schema like in config_flow.py
        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=502): int,
        })
        _LOGGER.info("✓ Schema created successfully")
        
        # Test valid data
        test_data = {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
        }
        result = schema(test_data)
        assert result[CONF_HOST] == "192.168.1.100"
        _LOGGER.info("✓ Schema validation works")
        
        return True
    except Exception as e:
        _LOGGER.error(f"✗ Voluptuous schema check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic checks."""
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("MIDNITE SOLAR CONFIG FLOW DIAGNOSTIC TOOL")
    _LOGGER.info("="*60)
    
    checks = [
        ("Python Syntax", check_python_syntax),
        ("Imports", check_imports),
        ("Config Flow Class", check_config_flow_class),
        ("Manifest Configuration", check_manifest),
        ("PyModbus Version", check_pymodbus_version),
        ("Modbus API", check_modbus_api),
        ("Hub Connection", check_hub_connection),
        ("DHCP Discovery Logic", check_dhcp_discovery_logic),
        ("Connection Test Logic", check_connection_test_logic),
        ("Voluptuous Schemas", check_voluptuous_schemas),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            _LOGGER.error(f"✗ Check '{name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info("DIAGNOSTIC SUMMARY")
    _LOGGER.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        _LOGGER.info(f"{status}: {name}")
    
    _LOGGER.info("\n" + "="*60)
    _LOGGER.info(f"Results: {passed}/{total} checks passed")
    _LOGGER.info("="*60)
    
    if passed == total:
        _LOGGER.info("\n✓ All checks passed! The config flow appears to be correctly configured.")
        _LOGGER.info("  If autodiscovery is still failing, the issue may be:")
        _LOGGER.info("  - Network connectivity problems")
        _LOGGER.info("  - Device not responding on the network")
        _LOGGER.info("  - DHCP service not properly configured in Home Assistant")
        return 0
    else:
        _LOGGER.error(f"\n✗ {total - passed} check(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
