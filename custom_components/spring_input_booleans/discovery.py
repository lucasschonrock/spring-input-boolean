"""Discovery for Spring Input Boolean devices."""
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@callback
def async_start_discovery(hass: HomeAssistant) -> None:
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
        
        _LOGGER.debug("Discovered input_boolean: %s (%s)", entity_id, friendly_name)
        
        # Create discovery info
        discovery_info = {
            "entity_id": entity_id,
            "name": f"{friendly_name} Spring Configuration",
            "unique_id": unique_id,
        }
        
        # Start discovery flow for this entity
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": "discovery"},
            data=discovery_info,
        )


@callback 
def async_process_discovery(hass: HomeAssistant, entity_id: str) -> None:
    """Process discovery for a single input_boolean entity."""
    state = hass.states.get(entity_id)
    if not state:
        return
        
    friendly_name = state.attributes.get("friendly_name", entity_id)
    unique_id = f"spring_{entity_id}"
    
    discovery_info = {
        "entity_id": entity_id,
        "name": f"{friendly_name} Spring Configuration", 
        "unique_id": unique_id,
    }
    
    discovery_flow.async_create_flow(
        hass,
        DOMAIN,
        context={"source": "discovery"},
        data=discovery_info,
    )
