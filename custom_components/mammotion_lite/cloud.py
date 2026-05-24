from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession
from pymammotion.http.http import MammotionHTTP
from pymammotion.transport.base import AuthError

_LOGGER = logging.getLogger(__name__)


class CloudAuthError(Exception):
    """Login failed — user must reconfigure."""


class CloudTransientError(Exception):
    """Temporary failure; coordinator will retry."""


class CloudRateLimitedError(CloudTransientError):
    """HTTP 429 — back off."""


class CloudDeviceOfflineError(CloudTransientError):
    """Device offline per Aliyun (code 6205)."""


@dataclass(frozen=True)
class CloudDevice:
    device_name: str
    iot_id: str
    nickname: str


class MammotionCloudClient:
    """Minimal wrapper around MammotionHTTP for HA use.

    One instance per config entry. Call login() once at setup;
    invoke() refreshes the token automatically before each request.
    """

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._http = MammotionHTTP(session=session)
        self._email = email
        self._password = password

    async def login(self) -> None:
        try:
            resp = await self._http.login_v2(self._email, self._password)
        except AuthError as err:
            raise CloudAuthError(str(err)) from err
        if resp.code != 0:
            raise CloudAuthError(f"login failed code={resp.code}: {resp.msg}")

    async def list_devices(self) -> list[CloudDevice]:
        resp = await self._http.get_user_device_list()
        if resp.code != 0:
            raise CloudTransientError(f"device list failed: {resp.msg}")
        devices = resp.data or []
        return [
            CloudDevice(
                device_name=d.device_name,
                iot_id=d.iot_id,
                nickname=getattr(d, "nick_name", "") or d.device_name,
            )
            for d in devices
            if d.iot_id  # skip any malformed entries
        ]

    async def invoke(self, *, iot_id: str, device_name: str, command: bytes) -> bytes:
        """Send a protobuf command; return raw response bytes.

        Logs the raw envelope once (first call only) so we can confirm
        the response shape during Phase 3 integration. Remove after confirmed.
        """
        content_b64 = base64.b64encode(command).decode("ascii")
        try:
            resp = await self._http.mqtt_invoke(
                content=content_b64,
                device_name=device_name,
                iot_id=iot_id,
            )
        except AuthError as err:
            raise CloudAuthError(str(err)) from err

        if resp.code == 401:
            raise CloudAuthError(f"invoke 401: {resp.msg}")
        if resp.code == 429:
            raise CloudRateLimitedError(f"invoke 429: {resp.msg}")
        if resp.code == 6205:
            raise CloudDeviceOfflineError(f"device offline: {resp.msg}")
        if resp.code != 0:
            raise CloudTransientError(f"invoke code={resp.code}: {resp.msg}")

        data: dict[str, Any] = resp.data or {}
        _LOGGER.debug("mqtt_invoke raw response data: %s", data)  # remove after confirmed
        raw_b64: str = data.get("content") or data.get("data", {}).get("content", "")
        if not raw_b64:
            raise CloudTransientError(f"no content in invoke response: {data}")
        return base64.b64decode(raw_b64)
