"""Spring Input Booleans integration for Home Assistant."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "spring_input_booleans"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Spring Input Booleans component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spring Input Booleans from a config entry."""
    
    @callback
    def handle_input_boolean_change(event: Event) -> None:
        """Handle input_boolean state changes and reverse them."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        
        # Only process input_boolean entities
        if not entity_id or not entity_id.startswith("input_boolean."):
            return
            
        # Ignore if no state change or if state is None
        if not new_state or not old_state or new_state.state == old_state.state:
            return
            
        # Get the new state value
        new_state_value = new_state.state
        
        _LOGGER.debug(
            "Input boolean %s changed from %s to %s, reversing...",
            entity_id,
            old_state.state,
            new_state_value
        )
        
        # Determine the reverse action
        if new_state_value == "on":
            # If it turned on, turn it off
            service_action = "turn_off"
        elif new_state_value == "off":
            # If it turned off, turn it on
            service_action = "turn_on"
        else:
            # Unknown state, skip
            return
            
        # Call the service to reverse the state
        hass.async_create_task(
            hass.services.async_call(
                "input_boolean",
                service_action,
                {"entity_id": entity_id},
                blocking=False
            )
        )
        
        _LOGGER.info(
            "Reversed input boolean %s state from %s back to %s",
            entity_id,
            new_state_value,
            old_state.state
        )
    
    # Listen for all state change events
    hass.bus.async_listen(EVENT_STATE_CHANGED, handle_input_boolean_change)
    
    _LOGGER.info("Spring Input Booleans integration loaded successfully")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True