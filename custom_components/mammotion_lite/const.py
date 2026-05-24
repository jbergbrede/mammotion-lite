from __future__ import annotations

from datetime import timedelta

DOMAIN = "mammotion_lite"

CONF_LOCAL_NAME = "local_name"  # BLE local name e.g. "Luba-ABCD"

# Phase 2+
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_IOT_ID = "iot_id"
CONF_DEVICE_NAME = "device_name"
CONF_PRODUCT_KEY = "product_key"
CONF_PLAN_ID = "plan_id"

UPDATE_INTERVAL_ACTIVE = timedelta(seconds=60)
UPDATE_INTERVAL_IDLE = timedelta(minutes=5)
COMMAND_TIMEOUT = timedelta(seconds=15)
STALE_BLE_THRESHOLD = timedelta(minutes=10)

ACTION_START = "start"
ACTION_PAUSE = "pause"
ACTION_RESUME = "resume"
ACTION_CANCEL = "cancel"
ACTION_DOCK = "dock"
