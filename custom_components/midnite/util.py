"""Utility functions for the Midnite Solar integration."""

from typing import Any

from .const import REGISTER_CATEGORIES, CONF_ENABLE_ADVANCED, CONF_ENABLE_DEBUG


def should_create_entity(entry: Any, register_name: str) -> bool:
    """Determine if an entity should be created based on configuration and category.
    
    Args:
        entry: The config entry object
        register_name: Name of the register (must exist in REGISTER_CATEGORIES)
        
    Returns:
        True if the entity should be created, False otherwise
    """
    # Get category, default to Basic if not found
    category = REGISTER_CATEGORIES.get(register_name, "B")
    
    # Basic entities always created
    if category == "B":
        return True
    
    # Advanced entities only with flag enabled
    if category == "A" and entry.options.get(CONF_ENABLE_ADVANCED, False):
        return True
    
    # Debug entities only with flag enabled
    if category == "D" and entry.options.get(CONF_ENABLE_DEBUG, False):
        return True
    
    return False


def is_write_enabled(entry: Any) -> bool:
    """Check if write operations are enabled in configuration.
    
    Args:
        entry: The config entry object
        
    Returns:
        True if writes are enabled, False otherwise
    """
    return entry.options.get(CONF_ENABLE_WRITES, False)
