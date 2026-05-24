from __future__ import annotations

import time
from dataclasses import dataclass

# pb2 classes (google.protobuf wire format)
from pymammotion.proto.luba_msg_pb2 import (
    DEV_MAINCTL,
    DEV_MOBILEAPP,
    MSG_ATTR_REQ,
    MSG_CMD_TYPE_EMBED_SYS,
    LubaMsg,
    MsgAttr,
    MsgCmdType,
    MsgDevice,
)
from pymammotion.proto.mctrl_sys_pb2 import (
    RPT_START,
    MctlSys,
    report_info_cfg,
    rpt_act,
)

_STATUS_REPORT_SUBS = [1, 3, 5, 6]  # RIT_CONNECT, RIT_DEV_LOCAL, RIT_WORK, RIT_DEV_STA

# Silence unused-import warnings from mypy for pb2 type aliases
_ = (MsgAttr, MsgCmdType, MsgDevice, rpt_act)

# Integer values from WorkMode enum — avoids hard dependency on enum attributes
# that may be missing in older pymammotion releases.
_WORK_MODE_TO_STATUS: dict[int, str] = {
    0: "idle",  # MODE_NOT_ACTIVE
    1: "idle",  # MODE_ONLINE
    3: "idle",  # MODE_POWER_OFF
    8: "idle",  # MODE_DISABLE
    10: "idle",  # MODE_INITIALIZATION
    11: "idle",  # MODE_READY
    13: "mowing",  # MODE_WORKING
    14: "returning",  # MODE_RETURNING
    15: "charging",  # MODE_CHARGING
    17: "error",  # MODE_LOCK
    19: "paused",  # MODE_PAUSE
    20: "mowing",  # MODE_MANUAL_MOWING
    37: "error",  # MODE_LOCATION_ERROR
    39: "paused",  # MODE_CHARGING_PAUSE
}


@dataclass(frozen=True)
class StatusPayload:
    battery_pct: int | None
    status_raw: int
    status: str
    charge_state: int | None
    progress_pct: int | None


def encode_get_status() -> bytes:
    """Build a one-shot get_report_cfg LubaMsg. Returns serialised bytes."""
    cfg = report_info_cfg()
    cfg.act = RPT_START
    cfg.timeout = 10_000
    cfg.period = 1_000
    cfg.no_change_period = 4_000
    cfg.count = 1
    for sub in _STATUS_REPORT_SUBS:
        cfg.sub.append(sub)

    sys = MctlSys()
    sys.todev_report_cfg.CopyFrom(cfg)

    msg = LubaMsg()
    msg.msgtype = MSG_CMD_TYPE_EMBED_SYS
    msg.sender = DEV_MOBILEAPP
    msg.rcver = DEV_MAINCTL
    msg.msgattr = MSG_ATTR_REQ
    msg.seqs = int(time.time()) & 0xFF
    msg.version = 1
    msg.sys.CopyFrom(sys)
    msg.timestamp = int(time.time() * 1000)

    return bytes(msg.SerializeToString())


def decode_status_response(data: bytes) -> StatusPayload:
    """Parse LubaMsg response bytes into a StatusPayload."""
    msg = LubaMsg()
    msg.ParseFromString(data)

    dev = msg.sys.toapp_report_data.dev
    work = msg.sys.toapp_report_data.work

    battery: int | None = dev.battery_val if dev.battery_val > 0 else None
    charge: int | None = dev.charge_state if dev.charge_state > 0 else None
    progress: int | None = work.progress if work.progress > 0 else None
    sys_status: int = dev.sys_status

    return StatusPayload(
        battery_pct=battery,
        status_raw=sys_status,
        status=_WORK_MODE_TO_STATUS.get(sys_status, "unknown"),
        charge_state=charge,
        progress_pct=progress,
    )
