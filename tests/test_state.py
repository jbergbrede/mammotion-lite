"""Tests for state.py pure functions."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.mammotion_lite.state import (
    MowerState,
    MowerStatus,
    merge_ble_advertisement,
)

_NOW = datetime(2025, 5, 24, 12, 0, 0, tzinfo=UTC)


def test_initial_state_defaults() -> None:
    s = MowerState()
    assert s.status == MowerStatus.UNKNOWN
    assert s.rssi is None
    assert s.last_seen_ble is None
    assert s.plans == ()


def test_merge_ble_sets_rssi_and_timestamp() -> None:
    s = MowerState()
    new = merge_ble_advertisement(s, rssi=-65, now=_NOW)
    assert new.rssi == -65
    assert new.last_seen_ble == _NOW


def test_merge_ble_preserves_other_fields() -> None:
    s = MowerState(status=MowerStatus.MOWING, battery_pct=80)
    new = merge_ble_advertisement(s, rssi=-70, now=_NOW)
    assert new.status == MowerStatus.MOWING
    assert new.battery_pct == 80


def test_merge_ble_immutable() -> None:
    s = MowerState()
    new = merge_ble_advertisement(s, rssi=-70, now=_NOW)
    assert s.rssi is None  # original unchanged
    assert new is not s


def test_merge_ble_updates_rssi() -> None:
    s = MowerState(rssi=-80, last_seen_ble=_NOW)
    later = datetime(2025, 5, 24, 12, 1, 0, tzinfo=UTC)
    new = merge_ble_advertisement(s, rssi=-60, now=later)
    assert new.rssi == -60
    assert new.last_seen_ble == later
