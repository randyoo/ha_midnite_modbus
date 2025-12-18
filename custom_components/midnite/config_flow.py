"""Config flow for the Midnite Solar integration."""

from __future__ import annotations

import inspect
import logging
from typing import Any

from pymodbus.client import ModbusTcpClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
try:
    # Try new import path first (Home Assistant 2025.12+)
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
except ImportError:
    # Fallback to old import path for older versions
    from homeassistant.components.dhcp import DhcpServiceInfo

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MidniteSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Midnite Solar."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self.discovery_info: DhcpServiceInfo | None = None

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        try:
            _LOGGER.info("========================================")
            _LOGGER.info("DHCP DISCOVERY TRIGGERED!")
            _LOGGER.info(f"Device IP: {discovery_info.ip}")
            _LOGGER.info(f"MAC Address: {discovery_info.macaddress}")
            if hasattr(discovery_info, 'hostname'):
                _LOGGER.info(f"Hostname: {discovery_info.hostname}")
            _LOGGER.info("========================================")
            
            # Detailed debugging
            _LOGGER.debug(f"Discovery info type: {type(discovery_info)}")
            _LOGGER.debug(f"Discovery info attributes: {dir(discovery_info)}")
            
            # 1. SET UNIQUE ID (Crucial step - use MAC address)
            # Format the MAC address properly for unique ID using Home Assistant's standard format
            from homeassistant.config_entries import ConfigEntries
            try:
                formatted_mac = ConfigEntries.format_mac(discovery_info.macaddress)
                _LOGGER.info(f"Setting unique ID: {formatted_mac}")
                await self.async_set_unique_id(formatted_mac, raise_on_progress=False)
                _LOGGER.info("✓ Unique ID set successfully")
            except Exception as e:
                _LOGGER.error(f"✗ Error setting unique ID: {e}", exc_info=True)
                return self.async_abort(reason="cannot_set_unique_id")
            
            # 2. ABORT IF ALREADY CONFIGURED (prevents duplicate discovery cards)
            try:
                _LOGGER.info("Checking if device is already configured...")
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: discovery_info.ip}
                )
                _LOGGER.info("✓ Device is not already configured, continuing with discovery")
            except Exception as e:
                _LOGGER.error(f"✗ Error checking for existing configuration: {e}", exc_info=True)
            
            # 3. STORE DISCOVERY INFO FOR USER CONFIRMATION
            self.discovery_info = discovery_info
            self.context["title_placeholders"] = {"ip": discovery_info.ip}
            _LOGGER.info(f"✓ Discovery info stored, proceeding to user confirmation step")
            
            # 4. TRIGGER USER FLOW TO SHOW "DISCOVERED" CARD
            _LOGGER.info("Triggering user flow to show discovery card...")
            result = await self.async_step_user()
            _LOGGER.info(f"✓ User flow triggered, result type: {type(result)}")
            return result
        except Exception as e:
            _LOGGER.error(f"Unexpected error in async_step_dhcp: {e}", exc_info=True)
            return self.async_abort(reason="discovery_failed")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (manual or DHCP discovery)."""
        _LOGGER.info("========================================")
        _LOGGER.info("async_step_user CALLED")
        _LOGGER.info(f"user_input: {user_input}")
        
        # Check if we came from DHCP discovery
        discovered = hasattr(self, 'discovery_info') and self.discovery_info is not None
        if discovered:
            _LOGGER.info("✓ Called from DHCP DISCOVERY")
            _LOGGER.info(f"  MAC: {self.discovery_info.macaddress}")
            _LOGGER.info(f"  IP: {self.discovery_info.ip}")
        else:
            _LOGGER.info("✓ Called from MANUAL entry")
        _LOGGER.info("========================================")
        
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # If triggered by discovery, user_input may only contain confirmation
            # If triggered manually, user_input contains full form data
            
            # For DHCP discovery, pre-fill the host from discovery info
            if discovered and CONF_HOST not in user_input:
                user_input[CONF_HOST] = self.discovery_info.ip
            elif not discovered and CONF_HOST not in user_input:
                # Manual entry requires host
                errors["base"] = "missing_host"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    }),
                    errors=errors,
                )
            
            # Check for duplicate entries
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT)}
            )
            
            # Debug: Log pymodbus version and API signature
            import pymodbus
            _LOGGER.info(f"PyModbus version: {pymodbus.__version__}")
            sig = inspect.signature(ModbusTcpClient.read_holding_registers)
            _LOGGER.info(f"read_holding_registers signature: {sig}")
            
            # Test connection
            client = ModbusTcpClient(user_input[CONF_HOST], port=user_input[CONF_PORT])
            try:
                connected = await self.hass.async_add_executor_job(client.connect)
                if not connected:
                    errors["base"] = "cannot_connect"
                else:
                    # Try to read a register to verify communication
                    result = await self.hass.async_add_executor_job(
                        lambda: client.read_holding_registers(address=4100, count=1)
                    )
                    if result.isError():
                        errors["base"] = "cannot_read"
                    
                client.close()
            except Exception as ex:
                _LOGGER.exception("Unexpected exception during connection test")
                errors["base"] = "unknown"
            
            if not errors:
                # Determine title based on discovery or manual entry
                if discovered and self.discovery_info:
                    title = f"Midnite Solar @ {user_input[CONF_HOST]}"
                else:
                    title = user_input.get(CONF_NAME, f"Midnite Solar @ {user_input[CONF_HOST]}")
                
                return self.async_create_entry(
                    title=title,
                    data=user_input
                )

        # Show appropriate form based on discovery status
        if discovered and self.discovery_info:
            # For DHCP discovery, show a confirmation dialog
            _LOGGER.info("========================================")
            _LOGGER.info("SHOWING DISCOVERY CONFIRMATION FORM")
            _LOGGER.info(f"Device IP: {self.discovery_info.ip}")
            _LOGGER.info("User should see a 'Discovered' card in UI")
            _LOGGER.info("========================================")
            result = self.async_show_form(
                step_id="user",
                description_placeholders={"ip": self.discovery_info.ip},
                errors=errors,
            )
            return result
        else:
            # For manual entry, show the full configuration form
            _LOGGER.info("========================================")
            _LOGGER.info("SHOWING MANUAL CONFIGURATION FORM")
            _LOGGER.info("User should see full config form in UI")
            _LOGGER.info("========================================")
            result = self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }),
                errors=errors,
            )
            return result

    async def async_step_import(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        self._async_abort_entries_match(
            {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
        )
        
        client = ModbusTcpClient(user_input[CONF_HOST], port=user_input[CONF_PORT])
        try:
            connected = await self.hass.async_add_executor_job(client.connect)
            if not connected:
                return self.async_abort(reason="cannot_connect")
            
            # Try to read a register to verify communication
            result = await self.hass.async_add_executor_job(
                lambda: client.read_holding_registers(address=4100, count=1)
            )
            if result.isError():
                return self.async_abort(reason="cannot_read")
            
            client.close()
        except Exception:
            _LOGGER.exception("Unexpected exception during import connection test")
            return self.async_abort(reason="unknown")

        return self.async_create_entry(
            title=f"Midnite Solar @ {user_input[CONF_HOST]}",
            data={
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
            },
        )
