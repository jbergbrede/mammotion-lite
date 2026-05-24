from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, UPDATE_INTERVAL_IDLE
from .state import MowerState, merge_ble_advertisement

AVAILABILITY_REFRESH_INTERVAL = timedelta(minutes=1)

_LOGGER = logging.getLogger(__name__)


class MammotionCoordinator(DataUpdateCoordinator[MowerState]):
    """Single coordinator per config entry.

    Phase 1: BLE-only stub. Cloud polling added in Phase 3.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{entry.title}",
            update_interval=UPDATE_INTERVAL_IDLE,
        )
        self.entry = entry
        entry.async_on_unload(
            async_track_time_interval(
                hass,
                self._async_refresh_listeners,
                AVAILABILITY_REFRESH_INTERVAL,
            )
        )

    @callback
    def _async_refresh_listeners(self, _now: datetime) -> None:
        # Re-push current state so entities re-evaluate wall-clock `available`.
        self.async_update_listeners()

    async def _async_update_data(self) -> MowerState:
        # Phase 1: no cloud. Return current state or initial default.
        return self.data or MowerState()

    @callback
    def handle_advertisement(self, rssi: int) -> None:
        """Called by ble.py on each BLE advertisement arrival."""
        prev = self.data or MowerState()
        self.async_set_updated_data(
            merge_ble_advertisement(prev, rssi, datetime.now(UTC))
        )
