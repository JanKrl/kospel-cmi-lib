"""Kospel C.MI electric heater HTTP API client."""

from .exceptions import (
    KospelConnectionError,
    KospelError,
    KospelWriteError,
    RegisterMissingError,
    RegisterReadError,
    RegisterValueInvalidError,
)
from .kospel.discovery import (
    DeviceDetail,
    KospelDeviceInfo,
    MODEL_NAMES,
    discover_devices,
    probe_device,
)

__all__ = [
    "DeviceDetail",
    "KospelDeviceInfo",
    "KospelError",
    "KospelConnectionError",
    "KospelWriteError",
    "MODEL_NAMES",
    "RegisterMissingError",
    "RegisterReadError",
    "RegisterValueInvalidError",
    "discover_devices",
    "probe_device",
]
