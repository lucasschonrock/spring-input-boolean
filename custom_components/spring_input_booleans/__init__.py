"""Spring Input Booleans integration for Home Assistant."""
import asyncio
import hashlib
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_ENTITY_ID,
    CONF_DELAY_SECONDS,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_NOTIFICATION_SERVICE,
    CONF_PHONE_ENTITY_IDS,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_NOTIFICATION_SERVICE,
)
from .discovery import async_start_discovery

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Spring Input Booleans component."""
    # Start discovery when the component loads
    await async_start_discovery(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spring Input Booleans from a config entry."""
    
    # Store the config data in hass.data for access throughout the integration
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Store active delays for action overrides
    hass.data.setdefault(f"{DOMAIN}_delays", {})
    
    # Add options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Get configuration settings for this specific device
    config_data = entry.data
    entity_id = config_data.get(CONF_ENTITY_ID)
    delay_seconds = config_data.get(CONF_DELAY_SECONDS, DEFAULT_DELAY_SECONDS)
    enable_notifications = config_data.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
    notification_service = config_data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
    phone_entity_ids = config_data.get(CONF_PHONE_ENTITY_IDS, [])
    
    if not entity_id:
        _LOGGER.error("No entity_id configured for entry %s", entry.entry_id)
        return False
    
    _LOGGER.info(
        "Spring Input Boolean loaded for %s: delay=%ds, notifications=%s, service=%s",
        entity_id,
        delay_seconds,
        enable_notifications,
        notification_service
    )
    
    # Track entities we're currently processing to prevent loops
    processing_entities = {}  # entity_id -> timestamp when we started processing
    import time
    
    # Listen for mobile app actionable notification events
    @callback
    def _handle_mobile_app_action(event: Event) -> None:
        # Android uses 'action', iOS uses 'actionName'
        action: str | None = event.data.get("action") or event.data.get("actionName")
        if not action or not isinstance(action, str):
            return

        # Expected formats: "SIB_OFF_10::<entity_id>", "SIB_OFF_20::<entity_id>", "SIB_REACTIVATE::<entity_id>"
        if not action.startswith("SIB_"):
            return

        try:
            action_key, target = action.split("::", 1)
        except ValueError:
            return

        if target != entity_id:
            return

        delay_key = f"{DOMAIN}_delays"
        if action_key == "SIB_OFF_10":
            hass.data[delay_key][entity_id] = 10
            _LOGGER.info("Action received: Off 10s for %s", entity_id)
        elif action_key == "SIB_OFF_20":
            hass.data[delay_key][entity_id] = 20
            _LOGGER.info("Action received: Off 20s for %s", entity_id)
        elif action_key == "SIB_REACTIVATE":
            hass.data[delay_key][entity_id] = 0
            _LOGGER.info("Action received: Reactivate now for %s", entity_id)

    # Register listeners for both Android/iOS mobile app events
    remove_mobile_app = hass.bus.async_listen("mobile_app_notification_action", _handle_mobile_app_action)
    remove_ios = hass.bus.async_listen("ios.action_fired", _handle_mobile_app_action)
    entry.async_on_unload(remove_mobile_app)
    entry.async_on_unload(remove_ios)
    
    # Log available mobile app notify services for debugging
    mobile_services = [s for s in hass.services.async_services().get("notify", {}).keys() if "mobile_app" in s]
    if mobile_services:
        _LOGGER.info("Available mobile app notify services: %s", mobile_services)
    else:
        _LOGGER.warning("No mobile app notify services found. Make sure the Home Assistant mobile app is installed and configured.")
    
    async def async_handle_state_change(changed_entity_id: str, new_state, old_state) -> None:
        """Async function to handle the state change with delay."""
        # Only process if this is our configured entity
        if changed_entity_id != entity_id:
            return
            
        try:
            # Get the new state value
            new_state_value = new_state.state
            
            _LOGGER.debug(
                "Input boolean %s changed from %s to %s (context: %s, user: %s), waiting %d seconds before reversing...",
                changed_entity_id,
                old_state.state,
                new_state_value,
                new_state.context.id if new_state.context else "None",
                new_state.context.user_id if new_state.context and new_state.context.user_id else "None",
                delay_seconds
            )
            
            # Send notification if the boolean was turned off and notifications are enabled
            if (new_state_value == "off" and old_state.state == "on" and enable_notifications):
                entity_name = new_state.attributes.get("friendly_name", changed_entity_id)
                notification_message = f"Input boolean '{entity_name}' was turned off and will reactivate in {delay_seconds} seconds"
                
                _LOGGER.info("Sending notification: %s", notification_message)
                
                # Create a shortened tag to avoid APNS collapse ID length limit (64 bytes)
                # Use a hash of the entity ID to ensure uniqueness while keeping it short
                entity_hash = hashlib.md5(changed_entity_id.encode()).hexdigest()[:8]
                short_tag = f"sib_{entity_hash}"
                _LOGGER.debug("Using notification tag '%s' (length: %d) for entity %s", 
                            short_tag, len(short_tag), changed_entity_id)
                
                # Prepare notification data with actions
                notification_data = {
                    "title": "Spring Input Boolean",
                    "message": notification_message,
                    "data": {
                        "priority": "normal",
                        "tag": short_tag,
                        "actions": [
                            {"action": f"SIB_OFF_10::{changed_entity_id}", "title": "Off for 10s"},
                            {"action": f"SIB_OFF_20::{changed_entity_id}", "title": "Off for 20s"},
                            {"action": f"SIB_REACTIVATE::{changed_entity_id}", "title": "Reactivate Now"}
                        ]
                    }
                }
                
                # Only send to specific targets if specified, otherwise don't send at all
                if phone_entity_ids:
                    # Resolve service: use notify.notify for aggregator/targets
                    service_to_call = "notify"
                    if notification_service not in ("notify", "mobile_app"):
                        service_to_call = notification_service

                    try:
                        if service_to_call == "notify":
                            # For each phone entity ID, try to send individually
                            for phone_id in phone_entity_ids:
                                try:
                                    # Determine the correct service name
                                    if phone_id.startswith("mobile_app_"):
                                        # Already has prefix, use as-is
                                        service_name = phone_id
                                    else:
                                        # Add prefix
                                        service_name = f"mobile_app_{phone_id}"
                                    
                                    if hass.services.has_service("notify", service_name):
                                        payload = dict(notification_data)
                                        await hass.services.async_call(
                                            "notify",
                                            service_name,
                                            payload,
                                            blocking=False,
                                        )
                                        _LOGGER.debug("Notification sent via notify.%s", service_name)
                                    else:
                                        available_services = [s for s in hass.services.async_services().get("notify", {}).keys() if "mobile_app" in s]
                                        _LOGGER.warning("Notify service %s not found. Available mobile app services: %s", 
                                                      service_name, available_services)
                                except Exception as e:
                                    _LOGGER.warning("Failed to send notification to %s: %s", phone_id, e)
                        else:
                            # Custom notifier (no targets)
                            await hass.services.async_call(
                                "notify",
                                service_to_call,
                                notification_data,
                                blocking=False,
                            )
                            _LOGGER.debug(
                                "Notification sent via notify.%s (no explicit targets)",
                                service_to_call,
                            )
                    except Exception as e:
                        _LOGGER.warning(
                            "Failed to send notification via notify.%s: %s",
                            service_to_call,
                            e,
                        )
                else:
                    _LOGGER.debug("No phone entity IDs configured, skipping notification")
            
            # Check for action override and use that delay instead
            delay_key = f"{DOMAIN}_delays"
            actual_delay = hass.data[delay_key].get(changed_entity_id, delay_seconds)
            
            # Clear the override after using it
            if changed_entity_id in hass.data[delay_key]:
                del hass.data[delay_key][changed_entity_id]
                _LOGGER.debug("Using action override delay: %d seconds for %s", actual_delay, changed_entity_id)
            else:
                _LOGGER.debug("Using default delay: %d seconds for %s", actual_delay, changed_entity_id)
            
            # Wait for the actual delay (which might be overridden by action)
            if actual_delay > 0:
                await asyncio.sleep(actual_delay)
            else:
                _LOGGER.debug("Immediate reactivation requested for %s", changed_entity_id)
            
            # Double-check: Make sure the entity still exists and hasn't changed again
            current_state = hass.states.get(changed_entity_id)
            if not current_state or current_state.state != new_state_value:
                _LOGGER.debug(
                    "Entity %s state changed during delay (from %s to %s), skipping reversal",
                    changed_entity_id,
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
                {"entity_id": changed_entity_id},
                blocking=True
            )
            
            _LOGGER.info(
                "Reversed input boolean %s state from %s back to %s after %d-second delay",
                changed_entity_id,
                new_state_value,
                old_state.state,
                actual_delay
            )
            
        finally:
            # Always remove from processing set when done
            processing_entities.pop(changed_entity_id, None)

    @callback
    def handle_input_boolean_change(event: Event) -> None:
        """Handle input_boolean state changes and reverse them after a configured delay."""
        changed_entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        
        # Only process our specific configured entity
        if changed_entity_id != entity_id:
            return
            
        # Ignore if no state change or if state is None
        if not new_state or not old_state or new_state.state == old_state.state:
            return
        
        # Prevent loops: Check if we're already processing this entity
        current_time = time.time()
        if changed_entity_id in processing_entities:
            # Check if it's been more than 10 seconds (safety cleanup)
            if current_time - processing_entities[changed_entity_id] < 10:
                _LOGGER.debug(
                    "Ignoring state change for %s - already processing (started %d seconds ago)",
                    changed_entity_id,
                    int(current_time - processing_entities[changed_entity_id])
                )
                return
            else:
                # Clean up stale entry
                _LOGGER.debug("Cleaning up stale processing entry for %s", changed_entity_id)
                processing_entities.pop(changed_entity_id, None)
        
        # Check if this change has a user_id (indicating manual user interaction)
        # Only process changes that have a user_id OR are from automations with user_id
        if new_state.context and not new_state.context.user_id:
            _LOGGER.debug(
                "Ignoring state change for %s - no user_id, likely programmatic (context: %s)",
                changed_entity_id,
                new_state.context.id
            )
            return
            
        # Mark this entity as being processed
        processing_entities[changed_entity_id] = current_time
        
        _LOGGER.debug(
            "Processing state change for %s from %s to %s (user: %s)",
            changed_entity_id,
            old_state.state,
            new_state.state,
            new_state.context.user_id if new_state.context else "None"
        )
        
        # Schedule the async work
        hass.async_add_job(async_handle_state_change, changed_entity_id, new_state, old_state)
    
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