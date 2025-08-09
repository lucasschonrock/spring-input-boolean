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
    
    # Track our own context IDs to prevent loops
    our_context_ids = set()
    max_context_ids = 100  # Limit the size of our tracking set
    
    async def async_handle_state_change(entity_id: str, new_state, old_state) -> None:
        """Async function to handle the state change with delay."""
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
            
        # Call the service to reverse the state and track our context
        await hass.services.async_call(
            "input_boolean",
            service_action,
            {"entity_id": entity_id},
            blocking=True
        )
        
        # Track our context ID to prevent loops
        # Note: We get the context from the state that will be created by our service call
        # We'll add it to our tracking set so we can ignore the resulting state change
        await asyncio.sleep(0.1)  # Small delay to ensure state has been updated
        latest_state = hass.states.get(entity_id)
        if latest_state and latest_state.context:
            our_context_ids.add(latest_state.context.id)
            _LOGGER.debug(
                "Added context ID %s to tracking set for entity %s",
                latest_state.context.id,
                entity_id
            )
            
            # Clean up the tracking set if it gets too large
            if len(our_context_ids) > max_context_ids:
                # Remove the oldest half of the entries (convert to list, sort, remove first half)
                sorted_ids = sorted(our_context_ids)
                for old_id in sorted_ids[:len(sorted_ids) // 2]:
                    our_context_ids.discard(old_id)
                _LOGGER.debug(
                    "Cleaned up context tracking set, now has %d entries",
                    len(our_context_ids)
                )
        
        _LOGGER.info(
            "Reversed input boolean %s state from %s back to %s after 2-second delay",
            entity_id,
            new_state_value,
            old_state.state
        )

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
            
        # Prevent loops: Check if this change was caused by our own service call
        if new_state.context and new_state.context.id in our_context_ids:
            _LOGGER.debug(
                "Ignoring state change for %s - caused by our own service call (context: %s)",
                entity_id,
                new_state.context.id
            )
            # Remove the context ID from our tracking set to keep it clean
            our_context_ids.discard(new_state.context.id)
            return
            
        # Additional check: If there's no user_id in context, it might be programmatic
        # But we still process it unless it's from our own context above
        if new_state.context and not new_state.context.user_id:
            _LOGGER.debug(
                "State change for %s has no user_id - might be programmatic but not from us (context: %s)",
                entity_id,
                new_state.context.id
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