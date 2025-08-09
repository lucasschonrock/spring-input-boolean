"""Spring Input Booleans integration for Home Assistant."""
import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_NOTIFICATION_SERVICE,
    CONF_PHONE_ENTITY_IDS,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_MONITORED_ENTITIES,
    CONF_AUTO_DISCOVER,
    DEFAULT_NOTIFICATION_SERVICE,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_AUTO_DISCOVER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Spring Input Booleans component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spring Input Booleans from a config entry."""
    
    # Store the config data in hass.data for access throughout the integration
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Add options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Get configuration settings
    config_data = entry.data
    enable_notifications = config_data.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
    notification_service = config_data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
    phone_entity_ids = config_data.get(CONF_PHONE_ENTITY_IDS, [])
    monitored_entities = config_data.get(CONF_MONITORED_ENTITIES, [])
    auto_discover = config_data.get(CONF_AUTO_DISCOVER, DEFAULT_AUTO_DISCOVER)
    
    # If auto_discover is enabled but no entities are specified, monitor all input_booleans
    if auto_discover and not monitored_entities:
        monitored_entities = [
            entity_id for entity_id in hass.states.async_entity_ids("input_boolean")
        ]
        _LOGGER.info("Auto-discovery enabled: monitoring all %d input_boolean entities", len(monitored_entities))
    
    _LOGGER.info(
        "Spring Input Booleans loaded with config: notifications=%s, service=%s, phone_entities=%s, monitoring=%d entities",
        enable_notifications,
        notification_service,
        phone_entity_ids,
        len(monitored_entities)
    )
    
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
            
            # Send notification if the boolean was turned off and notifications are enabled
            if (new_state_value == "off" and old_state.state == "on" and enable_notifications):
                entity_name = new_state.attributes.get("friendly_name", entity_id)
                notification_message = f"Input boolean '{entity_name}' was turned off"
                
                _LOGGER.info("Sending notification: %s", notification_message)
                
                # Prepare notification data
                notification_data = {
                    "title": "Spring Input Boolean",
                    "message": notification_message,
                    "data": {
                        "priority": "normal",
                        "tag": "spring_input_boolean"
                    }
                }
                
                # Add target entity IDs if specified
                if phone_entity_ids:
                    notification_data["target"] = phone_entity_ids
                
                # Send notification using the configured service
                try:
                    await hass.services.async_call(
                        "notify",
                        notification_service,
                        notification_data,
                        blocking=False
                    )
                    _LOGGER.debug("Notification sent successfully via notify.%s", notification_service)
                except Exception as e:
                    _LOGGER.warning("Failed to send notification via notify.%s: %s", notification_service, e)
                    
                    # Fallback: Try the default notify service if the configured one failed
                    if notification_service != "notify":
                        try:
                            fallback_data = notification_data.copy()
                            # Remove target for fallback to avoid errors
                            if "target" in fallback_data:
                                del fallback_data["target"]
                            
                            await hass.services.async_call(
                                "notify",
                                "notify",
                                fallback_data,
                                blocking=False
                            )
                            _LOGGER.debug("Notification sent successfully via fallback notify.notify")
                        except Exception as e2:
                            _LOGGER.warning("Failed to send notification via fallback notify.notify: %s", e2)
            
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
            
        # Handle auto-discovery of new entities
        if auto_discover and entity_id not in monitored_entities:
            _LOGGER.info("Auto-discovered new input_boolean: %s", entity_id)
            monitored_entities.append(entity_id)
            # Update the config entry to persist the new entity
            updated_data = entry.data.copy()
            updated_data[CONF_MONITORED_ENTITIES] = monitored_entities
            hass.config_entries.async_update_entry(entry, data=updated_data)
        elif not auto_discover and monitored_entities and entity_id not in monitored_entities:
            _LOGGER.debug("Ignoring unmonitored entity: %s", entity_id)
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
    # Clean up stored data
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove the domain data if no more entries
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    
    _LOGGER.info("Spring Input Booleans integration unloaded successfully")
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    # Update the stored data with new options
    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.info("Spring Input Booleans configuration updated")
    
    # Reload the integration to apply new settings
    await hass.config_entries.async_reload(entry.entry_id)