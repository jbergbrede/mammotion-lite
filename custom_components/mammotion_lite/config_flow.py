from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_LOCAL_NAME, DOMAIN


class MammotionLiteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            local_name = user_input[CONF_LOCAL_NAME].strip()
            if not local_name:
                errors[CONF_LOCAL_NAME] = "invalid_local_name"
            else:
                await self.async_set_unique_id(local_name)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=local_name,
                    data={CONF_LOCAL_NAME: local_name},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_LOCAL_NAME): str}),
            errors=errors,
        )
