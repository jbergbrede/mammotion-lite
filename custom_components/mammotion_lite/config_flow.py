from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_LOCAL_NAME, DOMAIN


class MammotionLiteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered_name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.name)
        self._abort_if_unique_id_configured()
        self._discovered_name = discovery_info.name
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovered_name is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name,
                data={CONF_LOCAL_NAME: self._discovered_name},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_name},
        )

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
