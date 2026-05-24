from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_LOCAL_NAME
from .coordinator import MammotionCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .ble import (
        async_register_passive_listener,  # avoid top-level HA component import
    )

    coordinator = MammotionCoordinator(hass=hass, entry=entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    unsub_ble = async_register_passive_listener(
        hass,
        device_name=entry.data[CONF_LOCAL_NAME],
        on_advertisement=coordinator.handle_advertisement,
    )
    entry.async_on_unload(unsub_ble)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
