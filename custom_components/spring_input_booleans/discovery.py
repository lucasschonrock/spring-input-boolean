"""Discovery for Spring Input Boolean devices."""
import logging

from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery_flow import async_create_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_start_discovery(hass: HomeAssistant) -> None:
    """Start discovery for input_boolean entities."""
    _LOGGER.debug("Starting discovery for input_boolean entities")
    
    # Get all input_boolean entities
    input_boolean_entities = hass.states.async_entity_ids("input_boolean")
    
    for entity_id in input_boolean_entities:
        state = hass.states.get(entity_id)
        if not state:
            continue
            
        # Get friendly name or use entity_id
        friendly_name = state.attributes.get("friendly_name", entity_id)
        
        # Create unique identifier for this device
        unique_id = f"spring_{entity_id}"
        
        # Check if already configured
        existing_entries = hass.config_entries.async_entries(DOMAIN)
        already_configured = any(
            entry.unique_id == unique_id for entry in existing_entries
        )
        
        if already_configured:
            _LOGGER.debug("Input boolean %s already configured, skipping", entity_id)
            continue
        
        _LOGGER.debug("Discovered input_boolean: %s (%s)", entity_id, friendly_name)
        
        # Create discovery info
        discovery_info = {
            "entity_id": entity_id,
            "name": f"{friendly_name} Spring Configuration",
            "unique_id": unique_id,
        }
        
        # Start discovery flow for this entity
        async_create_flow(
            hass,
            DOMAIN,
            context={"source": "discovery"},
            data=discovery_info,
        )
