from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STALE_BLE_THRESHOLD
from .coordinator import MammotionCoordinator
from .state import MowerState


@dataclass(frozen=True, kw_only=True)
class MammotionSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[MowerState], Any] = field(default=lambda _: None)
    available_fn: Callable[[MowerState], bool] = field(default=lambda _: True)


SENSOR_DESCRIPTIONS: tuple[MammotionSensorEntityDescription, ...] = (
    # ── Cloud-sourced ──────────────────────────────────────────────────
    MammotionSensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "unknown", "idle", "mowing", "paused", "returning", "charging", "error"
        ],
        value_fn=lambda s: s.status.value,
        available_fn=lambda s: s.last_seen_cloud is not None,
    ),
    MammotionSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.battery_pct,
        available_fn=lambda s: (
            s.battery_pct is not None and s.last_seen_cloud is not None
        ),
    ),
    MammotionSensorEntityDescription(
        key="last_seen_cloud",
        translation_key="last_seen_cloud",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_seen_cloud,
        available_fn=lambda s: s.last_seen_cloud is not None,
    ),
    # ── BLE-sourced (passive bonus) ────────────────────────────────────
    MammotionSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.rssi,
        available_fn=lambda s: (
            s.last_seen_ble is not None
            and (datetime.now(UTC) - s.last_seen_ble) < STALE_BLE_THRESHOLD
        ),
    ),
    MammotionSensorEntityDescription(
        key="last_seen_ble",
        translation_key="last_seen_ble",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_seen_ble,
        available_fn=lambda s: s.last_seen_ble is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MammotionCoordinator = entry.runtime_data
    async_add_entities(
        MammotionSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class MammotionSensorEntity(CoordinatorEntity[MammotionCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: MammotionSensorEntityDescription

    def __init__(
        self,
        coordinator: MammotionCoordinator,
        description: MammotionSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Mammotion",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or MowerState())

    @property
    def available(self) -> bool:
        if not bool(super().available):
            return False
        return self.entity_description.available_fn(
            self.coordinator.data or MowerState()
        )
