"""Config flow for Spring Input Booleans integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SpringInputBooleansConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spring Input Booleans."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Create the entry
            return self.async_create_entry(
                title="Spring Input Booleans",
                data={}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "description": "This integration will automatically reverse any changes made to input_boolean entities. When an input_boolean is turned on, it will immediately be turned off, and vice versa."
            }
        )
