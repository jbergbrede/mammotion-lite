from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud import (
    CloudAuthError,
    CloudDeviceOfflineError,
    CloudRateLimitedError,
    CloudTransientError,
    MammotionCloudClient,
)
from .codec import decode_status_response, encode_get_status
from .const import (
    CONF_EMAIL,
    CONF_IOT_ID,
    CONF_PASSWORD,
    DOMAIN,
    UPDATE_INTERVAL_ACTIVE,
    UPDATE_INTERVAL_IDLE,
)
from .state import MowerState, merge_ble_advertisement, merge_cloud_status

_LOGGER = logging.getLogger(__name__)

AVAILABILITY_REFRESH_INTERVAL = timedelta(minutes=1)

# Consecutive 429s before we back off to 30-min interval
_RATE_LIMIT_BACKOFF = timedelta(minutes=30)


class MammotionCoordinator(DataUpdateCoordinator[MowerState]):
    """Single coordinator per config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{entry.title}",
            update_interval=UPDATE_INTERVAL_IDLE,
        )
        self.entry = entry
        self._cloud: MammotionCloudClient | None = None
        self._iot_id: str | None = entry.data.get(CONF_IOT_ID)
        self._device_name: str | None = entry.data.get("device_name")
        self._rate_limited = False

        entry.async_on_unload(
            async_track_time_interval(
                hass,
                self._async_refresh_listeners,
                AVAILABILITY_REFRESH_INTERVAL,
            )
        )

    @callback
    def _async_refresh_listeners(self, _now: datetime) -> None:
        self.async_update_listeners()

    async def _async_setup(self) -> None:
        """Login once at setup. Called by DataUpdateCoordinator before first refresh."""
        if not self._iot_id:
            return  # BLE-only entry (no cloud credentials yet)
        email = self.entry.data.get(CONF_EMAIL)
        password = self.entry.data.get(CONF_PASSWORD)
        if not email or not password:
            return
        session = async_get_clientsession(self.hass)
        self._cloud = MammotionCloudClient(session, email, password)
        try:
            await self._cloud.login()
        except CloudAuthError as err:
            _LOGGER.error("Cloud login failed for %s: %s", self.entry.title, err)
            self._cloud = None
            raise UpdateFailed(f"cloud login failed: {err}") from err

    async def _async_update_data(self) -> MowerState:
        prev = self.data or MowerState()

        if self._cloud is None or not self._iot_id or not self._device_name:
            # No cloud credentials — return current state unchanged.
            return prev

        if self._rate_limited:
            _LOGGER.debug("Skipping poll for %s: rate limited", self.entry.title)
            return prev

        try:
            raw = await self._cloud.invoke(
                iot_id=self._iot_id,
                device_name=self._device_name,
                command=encode_get_status(),
            )
        except CloudAuthError as err:
            raise UpdateFailed(f"auth error: {err}") from err
        except CloudRateLimitedError as err:
            _LOGGER.warning("Rate limited for %s — backing off", self.entry.title)
            self._rate_limited = True
            self.update_interval = _RATE_LIMIT_BACKOFF
            raise UpdateFailed(f"rate limited: {err}") from err
        except CloudDeviceOfflineError:
            _LOGGER.debug("Device %s is offline", self.entry.title)
            raise UpdateFailed("device offline") from None
        except CloudTransientError as err:
            raise UpdateFailed(f"transient: {err}") from err

        # Successful response — clear any rate-limit backoff
        if self._rate_limited:
            self._rate_limited = False
            self.update_interval = UPDATE_INTERVAL_IDLE

        payload = decode_status_response(raw)
        _LOGGER.debug(
            "%s status=%s battery=%s charge=%s progress=%s",
            self.entry.title,
            payload.status,
            payload.battery_pct,
            payload.charge_state,
            payload.progress_pct,
        )

        new_state = merge_cloud_status(
            prev,
            status=payload.status,
            battery_pct=payload.battery_pct,
            charge_state=payload.charge_state,
            progress_pct=payload.progress_pct,
            now=datetime.now(UTC),
        )

        # Adjust poll interval based on activity
        if payload.status in {"mowing", "returning"}:
            self.update_interval = UPDATE_INTERVAL_ACTIVE
        else:
            self.update_interval = UPDATE_INTERVAL_IDLE

        return new_state

    @callback
    def handle_advertisement(self, rssi: int) -> None:
        """Called by ble.py on each BLE advertisement arrival."""
        prev = self.data or MowerState()
        self.async_set_updated_data(
            merge_ble_advertisement(prev, rssi, datetime.now(UTC))
        )
