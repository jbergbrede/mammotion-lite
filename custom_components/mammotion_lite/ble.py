from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_passive_listener(
    hass: HomeAssistant,
    device_name: str,
    on_advertisement: Callable[[int], None],
) -> Callable[[], None]:
    """Subscribe to BLE advertisements for this mower. Returns unsubscribe fn.

    NOTE (Phase 1 spike): confirm the exact local_name format during testing.
    Mammotion mowers may advertise as "Luba-XXXX", "Yuka-XXXX", etc.
    If exact match fails, switch BluetoothCallbackMatcher to match by
    service UUID from pymammotion/bluetooth/const.py instead.
    """

    @callback
    def _handle(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        if service_info.name != device_name:
            return
        rssi = service_info.rssi
        if rssi is None:
            return
        on_advertisement(rssi)

    return bluetooth.async_register_callback(
        hass,
        _handle,
        bluetooth.BluetoothCallbackMatcher(local_name=device_name),
        bluetooth.BluetoothScanningMode.ACTIVE,
    )
