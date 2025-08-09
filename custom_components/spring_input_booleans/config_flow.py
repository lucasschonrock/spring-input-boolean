"""Config flow for Spring Input Booleans integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

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
    NOTIFICATION_SERVICES,
)

_LOGGER = logging.getLogger(__name__)


class SpringInputBooleansConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spring Input Booleans."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._entity_id = None
        self._name = None
        self._discovery_info = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user initiated configuration (redirect to discovery)."""
        # Since we use discovery, abort manual configuration and direct users to discovery
        return self.async_abort(
            reason="use_discovery",
            description_placeholders={
                "info": "This integration uses automatic discovery. Look for discovered Spring Input Boolean devices in the 'Discovered' section below."
            }
        )

    async def async_step_discovery(self, discovery_info: dict[str, Any]) -> FlowResult:
        """Handle discovery."""
        entity_id = discovery_info["entity_id"]
        name = discovery_info["name"]
        unique_id = discovery_info["unique_id"]
        
        # Set unique ID and check if already configured
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        
        # Store discovery info
        self._discovery_info = discovery_info
        self._entity_id = entity_id
        self._name = name
        
        # Set title for the discovery
        self.context["title_placeholders"] = {"name": name}
        
        return await self.async_step_confirm_discovery()

    async def async_step_confirm_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return await self.async_step_config()
            
        return self.async_show_form(
            step_id="confirm_discovery",
            description_placeholders={
                "name": self._name,
                "entity_id": self._entity_id,
            }
        )

    async def async_step_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure the spring behavior."""
        errors = {}
        
        if user_input is not None:
            # Validate custom notification service
            if (user_input.get(CONF_NOTIFICATION_SERVICE) == "custom" and 
                not user_input.get("custom_service_name")):
                errors["custom_service_name"] = "custom_service_required"
            else:
                # Build configuration data
                config_data = {
                    CONF_ENTITY_ID: self._entity_id,
                    CONF_DELAY_SECONDS: user_input.get(CONF_DELAY_SECONDS, DEFAULT_DELAY_SECONDS),
                    CONF_ENABLE_NOTIFICATIONS: user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS),
                }
                
                # Handle notifications
                if config_data[CONF_ENABLE_NOTIFICATIONS]:
                    if user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                        config_data[CONF_NOTIFICATION_SERVICE] = user_input.get("custom_service_name", "").strip()
                    else:
                        config_data[CONF_NOTIFICATION_SERVICE] = user_input.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
                    
                    phone_entities = user_input.get(CONF_PHONE_ENTITY_IDS, "").strip()
                    if phone_entities:
                        config_data[CONF_PHONE_ENTITY_IDS] = [
                            entity.strip() for entity in phone_entities.split(",") if entity.strip()
                        ]
                    else:
                        config_data[CONF_PHONE_ENTITY_IDS] = []
                
                # Create the entry
                return self.async_create_entry(
                    title=self._name,
                    data=config_data
                )

        # Build form schema
        schema_dict = {
            vol.Optional(CONF_DELAY_SECONDS, default=DEFAULT_DELAY_SECONDS): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=60)
            ),
            vol.Optional(CONF_ENABLE_NOTIFICATIONS, default=DEFAULT_ENABLE_NOTIFICATIONS): bool,
        }
        
        # Add notification fields if enabled
        if user_input is None or user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS):
            schema_dict.update({
                vol.Optional(CONF_NOTIFICATION_SERVICE, default=DEFAULT_NOTIFICATION_SERVICE): vol.In(NOTIFICATION_SERVICES),
                vol.Optional(CONF_PHONE_ENTITY_IDS, default=""): str,
            })
            
            if user_input and user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                schema_dict[vol.Optional("custom_service_name", default="")] = str

        return self.async_show_form(
            step_id="config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "name": self._name,
                "entity_id": self._entity_id,
            }
        )



    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SpringInputBooleansOptionsFlow(config_entry)


class SpringInputBooleansOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for individual Spring Input Boolean devices."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # Validate custom notification service
            if (user_input.get(CONF_NOTIFICATION_SERVICE) == "custom" and 
                not user_input.get("custom_service_name")):
                errors["custom_service_name"] = "custom_service_required"
            else:
                # Update configuration
                new_data = self.config_entry.data.copy()
                new_data[CONF_DELAY_SECONDS] = user_input.get(CONF_DELAY_SECONDS, DEFAULT_DELAY_SECONDS)
                new_data[CONF_ENABLE_NOTIFICATIONS] = user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
                
                if new_data[CONF_ENABLE_NOTIFICATIONS]:
                    if user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                        new_data[CONF_NOTIFICATION_SERVICE] = user_input.get("custom_service_name", "").strip()
                    else:
                        new_data[CONF_NOTIFICATION_SERVICE] = user_input.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
                    
                    phone_entities = user_input.get(CONF_PHONE_ENTITY_IDS, "").strip()
                    if phone_entities:
                        new_data[CONF_PHONE_ENTITY_IDS] = [
                            entity.strip() for entity in phone_entities.split(",") if entity.strip()
                        ]
                    else:
                        new_data[CONF_PHONE_ENTITY_IDS] = []
                
                return self.async_create_entry(title="", data=new_data)

        # Get current values
        current_data = self.config_entry.data
        delay_seconds = current_data.get(CONF_DELAY_SECONDS, DEFAULT_DELAY_SECONDS)
        enable_notifications = current_data.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
        notification_service = current_data.get(CONF_NOTIFICATION_SERVICE, DEFAULT_NOTIFICATION_SERVICE)
        phone_entity_ids = current_data.get(CONF_PHONE_ENTITY_IDS, [])
        phone_entities_str = ", ".join(phone_entity_ids) if phone_entity_ids else ""

        # Build schema
        schema_dict = {
            vol.Optional(CONF_DELAY_SECONDS, default=delay_seconds): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=60)
            ),
            vol.Optional(CONF_ENABLE_NOTIFICATIONS, default=enable_notifications): bool,
        }
        
        if user_input is None or user_input.get(CONF_ENABLE_NOTIFICATIONS, enable_notifications):
            schema_dict.update({
                vol.Optional(CONF_NOTIFICATION_SERVICE, default=notification_service): vol.In(NOTIFICATION_SERVICES),
                vol.Optional(CONF_PHONE_ENTITY_IDS, default=phone_entities_str): str,
            })
            
            if user_input and user_input.get(CONF_NOTIFICATION_SERVICE) == "custom":
                schema_dict[vol.Optional("custom_service_name", default="")] = str
            elif notification_service not in NOTIFICATION_SERVICES:
                schema_dict[vol.Optional("custom_service_name", default=notification_service)] = str

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "entity_id": current_data.get(CONF_ENTITY_ID, ""),
            }
        )