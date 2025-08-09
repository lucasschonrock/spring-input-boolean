"""Spring Input Booleans integration for Home Assistant."""
import asyncio
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
    
    # Track entities we're currently processing to prevent loops
    processing_entities = {}  # entity_id -> timestamp when we started processing
    import time
    
    async def async_handle_state_change(entity_id: str, new_state, old_state) -> None:
        """Async function to handle the state change with delay."""
        try:
            # Get the new state value
            new_state_value = new_state.state
            
            _LOGGER.debug(
                "Input boolean %s changed from %s to %s (context: %s, user: %s), waiting 2 seconds before reversing...",
                entity_id,
                old_state.state,
                new_state_value,
                new_state.context.id if new_state.context else "None",
                new_state.context.user_id if new_state.context and new_state.context.user_id else "None"
            )
            
            # Wait 2 seconds before reversing the state
            await asyncio.sleep(2)
            
            # Double-check: Make sure the entity still exists and hasn't changed again
            current_state = hass.states.get(entity_id)
            if not current_state or current_state.state != new_state_value:
                _LOGGER.debug(
                    "Entity %s state changed during delay (from %s to %s), skipping reversal",
                    entity_id,
                    new_state_value,
                    current_state.state if current_state else "None"
                )
                return
            
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
            await hass.services.async_call(
                "input_boolean",
                service_action,
                {"entity_id": entity_id},
                blocking=True
            )
            
            _LOGGER.info(
                "Reversed input boolean %s state from %s back to %s after 2-second delay",
                entity_id,
                new_state_value,
                old_state.state
            )
            
        finally:
            # Always remove from processing set when done
            processing_entities.pop(entity_id, None)

    @callback
    def handle_input_boolean_change(event: Event) -> None:
        """Handle input_boolean state changes and reverse them after a 2-second delay."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        
        # Only process input_boolean entities
        if not entity_id or not entity_id.startswith("input_boolean."):
            return
            
        # Ignore if no state change or if state is None
        if not new_state or not old_state or new_state.state == old_state.state:
            return
        
        # Prevent loops: Check if we're already processing this entity
        current_time = time.time()
        if entity_id in processing_entities:
            # Check if it's been more than 5 seconds (safety cleanup)
            if current_time - processing_entities[entity_id] < 5:
                _LOGGER.debug(
                    "Ignoring state change for %s - already processing (started %d seconds ago)",
                    entity_id,
                    int(current_time - processing_entities[entity_id])
                )
                return
            else:
                # Clean up stale entry
                _LOGGER.debug("Cleaning up stale processing entry for %s", entity_id)
                processing_entities.pop(entity_id, None)
        
        # Check if this change has a user_id (indicating manual user interaction)
        # Only process changes that have a user_id OR are from automations with user_id
        if new_state.context and not new_state.context.user_id:
            _LOGGER.debug(
                "Ignoring state change for %s - no user_id, likely programmatic (context: %s)",
                entity_id,
                new_state.context.id
            )
            return
            
        # Mark this entity as being processed
        processing_entities[entity_id] = current_time
        
        _LOGGER.debug(
            "Processing state change for %s from %s to %s (user: %s)",
            entity_id,
            old_state.state,
            new_state.state,
            new_state.context.user_id if new_state.context else "None"
        )
        
        # Schedule the async work
        hass.async_add_job(async_handle_state_change, entity_id, new_state, old_state)
    
    # Listen for all state change events
    hass.bus.async_listen(EVENT_STATE_CHANGED, handle_input_boolean_change)
    
    _LOGGER.info("Spring Input Booleans integration loaded successfully")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True