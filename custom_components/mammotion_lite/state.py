from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum


class MowerStatus(StrEnum):
    UNKNOWN = "unknown"
    IDLE = "idle"
    MOWING = "mowing"
    PAUSED = "paused"
    RETURNING = "returning"
    CHARGING = "charging"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Plan:
    plan_id: str
    name: str


@dataclass(frozen=True, slots=True)
class MowerState:
    status: MowerStatus = MowerStatus.UNKNOWN
    battery_pct: int | None = None
    charge_state: int | None = None
    progress_pct: int | None = None
    rssi: int | None = None
    last_seen_ble: datetime | None = None   # timezone-aware UTC
    last_seen_cloud: datetime | None = None  # timezone-aware UTC
    plans: tuple[Plan, ...] = field(default_factory=tuple)


def merge_ble_advertisement(state: MowerState, rssi: int, now: datetime) -> MowerState:
    """Return new state with updated RSSI and BLE timestamp. Pure function."""
    return replace(state, rssi=rssi, last_seen_ble=now)


def merge_cloud_status(
    state: MowerState,
    *,
    status: str,
    battery_pct: int | None,
    charge_state: int | None,
    progress_pct: int | None,
    now: datetime,
) -> MowerState:
    """Return new state with cloud-polled fields merged in."""
    try:
        mower_status = MowerStatus(status)
    except ValueError:
        mower_status = MowerStatus.UNKNOWN
    return replace(
        state,
        status=mower_status,
        battery_pct=battery_pct,
        charge_state=charge_state,
        progress_pct=progress_pct,
        last_seen_cloud=now,
    )
