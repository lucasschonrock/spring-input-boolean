"""Config flow for Spring Input Booleans integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

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
    NOTIFICATION_SERVICES,
)

_LOGGER = logging.getLogger(__name__)


class SpringInputBooleansConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spring Input Booleans."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Validate custom notification service
            if (user_input.get(CONF_NOTIFICATION_SERVICE) == "custom" and 
                not user_input.get("custom_service_name")):
                errors["custom_service_name"] = "custom_service_required"
            else:
                # Get all input_boolean entities for selection
                input_booleans = [
                    entity_id for entity_id in self.hass.states.async_entity_ids("input_boolean")
                ]
                
                # Process the configuration
                config_data = {
                    CONF_AUTO_DISCOVER: user_input.get(CONF_AUTO_DISCOVER, DEFAULT_AUTO_DISCOVER),
                    CONF_ENABLE_NOTIFICATIONS: user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS),
                }
                
                # Handle entity selection
                if user_input.get(CONF_AUTO_DISCOVER, DEFAULT_AUTO_DISCOVER):
                    config_data[CONF_MONITORED_ENTITIES] = input_booleans
                else:
                    # Parse comma-separated entity IDs
                    entity_string = user_input.get(CONF_MONITORED_ENTITIES, "")
                    if isinstance(entity_string, str):
                        selected_entities = [
                            entity.strip() for entity in entity_string.split(",") 
                            if entity.strip() and entity.strip() in input_booleans
                        ]
                    else:
                        selected_entities = []
                    config_data[CONF_MONITORED_ENTITIES] = selected_entities
                
                # Handle notifications
                if config_data[CONF_ENABLE_NOTIFICATIONS]:
                    # Set notification service
                    if user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                        config_data[CONF_NOTIFICATION_SERVICE] = user_input.get("custom_service_name", "").strip()
                    else:
                        config_data[CONF_NOTIFICATION_SERVICE] = user_input.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
                    
                    # Set phone entity IDs
                    phone_entities = user_input.get(CONF_PHONE_ENTITY_IDS, "").strip()
                    if phone_entities:
                        config_data[CONF_PHONE_ENTITY_IDS] = [
                            entity.strip() for entity in phone_entities.split(",") if entity.strip()
                        ]
                    else:
                        config_data[CONF_PHONE_ENTITY_IDS] = []
                
            # Create the entry
            return self.async_create_entry(
                title="Spring Input Booleans",
                    data=config_data
                )

        # Get all input_boolean entities for display
        input_booleans = {}
        for entity_id in self.hass.states.async_entity_ids("input_boolean"):
            state = self.hass.states.get(entity_id)
            if state:
                friendly_name = state.attributes.get("friendly_name", entity_id)
                input_booleans[entity_id] = f"{friendly_name} ({entity_id})"

        # Build the form schema
        schema_dict = {
            vol.Optional(CONF_AUTO_DISCOVER, default=DEFAULT_AUTO_DISCOVER): bool,
        }
        
        # Add entity selection if auto-discover is disabled and entities exist
        if user_input is None or not user_input.get(CONF_AUTO_DISCOVER, DEFAULT_AUTO_DISCOVER):
            if input_booleans:
                default_entities = ", ".join(input_booleans.keys())
                schema_dict[vol.Optional(CONF_MONITORED_ENTITIES, default=default_entities)] = str
        
        # Add notification settings
        schema_dict[vol.Optional(CONF_ENABLE_NOTIFICATIONS, default=DEFAULT_ENABLE_NOTIFICATIONS)] = bool
        
        # Add notification-specific fields only if notifications are enabled
        if user_input is None or user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS):
            schema_dict.update({
                vol.Optional(CONF_NOTIFICATION_SERVICE, default=DEFAULT_NOTIFICATION_SERVICE): vol.In(NOTIFICATION_SERVICES),
                vol.Optional(CONF_PHONE_ENTITY_IDS, default=""): str,
            })
            
            # Add custom service name field if custom is selected
            if user_input and user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                schema_dict[vol.Optional("custom_service_name", default="")] = str

        # Create helpful description with entity list
        entity_list = ""
        if input_booleans:
            entity_names = list(input_booleans.keys())[:5]  # Show first 5
            entity_list = f"\n\nAvailable entities: {', '.join(entity_names)}"
            if len(input_booleans) > 5:
                entity_list += f" (and {len(input_booleans) - 5} more)"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "description": (
                    "This integration will automatically reverse any changes made to input_boolean entities. "
                    "When an input_boolean is turned on, it will immediately be turned off, and vice versa. "
                    f"Found {len(input_booleans)} input boolean(s) in your system.{entity_list}"
                )
            }
        )



    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SpringInputBooleansOptionsFlow(config_entry)


class SpringInputBooleansOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Spring Input Booleans."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - first step to choose what to configure."""
        if user_input is not None:
            if user_input.get("configure_entities"):
                return await self.async_step_entities()
            elif user_input.get("configure_notifications"):
                return await self.async_step_notifications()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("configure_entities", default=False): bool,
                vol.Optional("configure_notifications", default=False): bool,
            }),
            description_placeholders={
                "description": "Choose what you would like to configure:"
            }
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage monitored entities."""
        # Get all input_boolean entities
        input_booleans = {}
        for entity_id, state in self.hass.states.async_all():
            if entity_id.startswith("input_boolean."):
                friendly_name = state.attributes.get("friendly_name", entity_id)
                input_booleans[entity_id] = f"{friendly_name} ({entity_id})"

        if user_input is not None:
            # Update the configuration with new entity selection
            current_data = self.config_entry.data.copy()
            current_data[CONF_AUTO_DISCOVER] = user_input.get(CONF_AUTO_DISCOVER, DEFAULT_AUTO_DISCOVER)
            
            # Parse comma-separated entity IDs
            entity_string = user_input.get(CONF_MONITORED_ENTITIES, "")
            if isinstance(entity_string, str):
                selected_entities = [
                    entity.strip() for entity in entity_string.split(",") 
                    if entity.strip() and entity.strip() in input_booleans
                ]
            else:
                selected_entities = []
            current_data[CONF_MONITORED_ENTITIES] = selected_entities
            
            return self.async_create_entry(title="", data=current_data)

        # Get current values
        current_data = self.config_entry.data
        monitored_entities = current_data.get(CONF_MONITORED_ENTITIES, [])
        auto_discover = current_data.get(CONF_AUTO_DISCOVER, DEFAULT_AUTO_DISCOVER)

        schema_dict = {
            vol.Optional(CONF_AUTO_DISCOVER, default=auto_discover): bool,
        }

        if input_booleans:
            # Convert list to comma-separated string for display
            default_entities_str = ", ".join(monitored_entities) if monitored_entities else ""
            schema_dict[vol.Optional(CONF_MONITORED_ENTITIES, default=default_entities_str)] = str

        return self.async_show_form(
            step_id="entities",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "description": (
                    f"Found {len(input_booleans)} input boolean(s) in your system. "
                    "Select which ones you want to apply the spring behavior to."
                )
            }
        )

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage notification options."""
        errors = {}
        
        if user_input is not None:
            # Validate custom notification service
            if (user_input.get(CONF_NOTIFICATION_SERVICE) == "custom" and 
                not user_input.get("custom_service_name")):
                errors["custom_service_name"] = "custom_service_required"
            else:
                # Update the configuration with new notification settings
                current_data = self.config_entry.data.copy()
                current_data[CONF_ENABLE_NOTIFICATIONS] = user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
                
                if current_data[CONF_ENABLE_NOTIFICATIONS]:
                    # Set notification service
                    if user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                        current_data[CONF_NOTIFICATION_SERVICE] = user_input.get("custom_service_name", "").strip()
                    else:
                        current_data[CONF_NOTIFICATION_SERVICE] = user_input.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
                    
                    # Set phone entity IDs (convert comma-separated string to list)
                    phone_entities = user_input.get(CONF_PHONE_ENTITY_IDS, "").strip()
                    if phone_entities:
                        current_data[CONF_PHONE_ENTITY_IDS] = [
                            entity.strip() for entity in phone_entities.split(",") if entity.strip()
                        ]
                    else:
                        current_data[CONF_PHONE_ENTITY_IDS] = []
                
                return self.async_create_entry(title="", data=current_data)

        # Get current values from config entry
        current_data = self.config_entry.data
        enable_notifications = current_data.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
        notification_service = current_data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
        phone_entity_ids = current_data.get(CONF_PHONE_ENTITY_IDS, [])
        
        # Convert phone entity IDs list back to comma-separated string for display
        phone_entities_str = ", ".join(phone_entity_ids) if phone_entity_ids else ""

        # Build the form schema
        schema_dict = {
            vol.Optional(CONF_ENABLE_NOTIFICATIONS, default=enable_notifications): bool,
        }
        
        # Add notification-specific fields only if notifications are enabled
        if user_input is None or user_input.get(CONF_ENABLE_NOTIFICATIONS, enable_notifications):
            schema_dict.update({
                vol.Optional(CONF_NOTIFICATION_SERVICE, default=notification_service): vol.In(NOTIFICATION_SERVICES),
                vol.Optional(CONF_PHONE_ENTITY_IDS, default=phone_entities_str): str,
            })
            
            # Add custom service name field if custom is selected
            if user_input and user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                schema_dict[vol.Optional("custom_service_name", default="")] = str
            elif notification_service not in NOTIFICATION_SERVICES:
                # Current service is custom, show the field with current value
                schema_dict[vol.Optional("custom_service_name", default=notification_service)] = str

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "description": "Configure notification settings for when input booleans are turned off."
            }
        )