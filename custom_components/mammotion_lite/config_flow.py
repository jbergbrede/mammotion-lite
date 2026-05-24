from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .cloud import CloudAuthError, CloudTransientError, MammotionCloudClient
from .const import CONF_EMAIL, CONF_IOT_ID, CONF_LOCAL_NAME, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MammotionLiteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered_name: str | None = None
        self._local_name: str | None = None
        self._devices: list[Any] = []
        self._email: str = ""
        self._password: str = ""

    # ------------------------------------------------------------------ #
    # BLE discovery                                                        #
    # ------------------------------------------------------------------ #

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
            self._local_name = self._discovered_name
            return await self.async_step_cloud_auth()
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_name},
        )

    # ------------------------------------------------------------------ #
    # Manual entry                                                         #
    # ------------------------------------------------------------------ #

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
                self._local_name = local_name
                return await self.async_step_cloud_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_LOCAL_NAME): str}),
            errors=errors,
        )

    # ------------------------------------------------------------------ #
    # Cloud credentials                                                    #
    # ------------------------------------------------------------------ #

    async def async_step_cloud_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)
            client = MammotionCloudClient(session, email, password)
            try:
                await client.login()
                self._devices = await client.list_devices()
            except CloudAuthError:
                errors["base"] = "invalid_auth"
            except CloudTransientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during cloud auth")
                errors["base"] = "unknown"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    self._email = email
                    self._password = password
                    return await self.async_step_cloud_device()

        return self.async_show_form(
            step_id="cloud_auth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------ #
    # Device picker                                                        #
    # ------------------------------------------------------------------ #

    async def async_step_cloud_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            iot_id = user_input[CONF_IOT_ID]
            device = next((d for d in self._devices if d.iot_id == iot_id), None)
            if device is None:
                return await self.async_step_cloud_device()
            return self.async_create_entry(
                title=self._local_name or device.device_name,
                data={
                    CONF_LOCAL_NAME: self._local_name or device.device_name,
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_IOT_ID: device.iot_id,
                    "device_name": device.device_name,
                },
            )

        device_options = {d.iot_id: f"{d.nickname} ({d.device_name})" for d in self._devices}
        return self.async_show_form(
            step_id="cloud_device",
            data_schema=vol.Schema({vol.Required(CONF_IOT_ID): vol.In(device_options)}),
        )
